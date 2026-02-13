import os
import torch
import datetime
import yaml
import time
from pathlib import Path
from ultralytics import YOLO
from typing import Optional, Dict, Any, List
from .train_freeze_strategy import EnhancedFreezeScheduler, create_yolov8_freeze_scheduler


def get_model_size_from_type(model_type: str) -> str:
    """根据模型类型字符获取模型尺寸"""
    size_mapping = {
        'n': 'n', 's': 's', 'm': 'm', 'l': 'l', 'x': 'x'
    }
    return size_mapping.get(model_type.lower(), 's')


def train_model_with_enhanced_freeze(
    task: str = 'detect',
    model_type: str = 's',
    data_path: str = "data.yaml",
    epochs: int = 50,
    imgsz: int = 640,
    batch: int = 8,
    project: str = 'runs/train',
    name: Optional[str] = None,
    resume_weights: Optional[str] = None,
    patience: int = 15,
    use_freeze_strategy: bool = True,
    min_epochs_per_stage: int = 15,
    progress_callback: Optional[callable] = None  # 添加进度回调参数
) -> Dict[str, Any]:
    """使用增强版冻结策略的训练函数"""
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"🖥️ 使用设备: {device}")
    
    # 根据是否传入 resume_weights 选择模型路径
    if resume_weights and os.path.exists(resume_weights):
        model_path = resume_weights
        print(f"📁 加载指定权重: {resume_weights}")
    else:
        # 依据任务类型选择对应预训练权重
        if task == 'classify':
            model_path = f'yolov8{model_type}-cls.pt'
        elif task == 'segment':
            model_path = f'yolov8{model_type}-seg.pt'
        else:
            model_path = f'yolov8{model_type}.pt'
        print(f"📁 使用预训练模型: {model_path}")
    
    model = YOLO(model_path)
    
    # 构建训练结果保存名称
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    if name is None:
        name = f'{task}_{model_type}_enhanced_{timestamp}'
    
    # 创建训练目录
    train_dir = os.path.join(project, name)
    os.makedirs(train_dir, exist_ok=True)
    
    freeze_scheduler = None
    if use_freeze_strategy:
        try:
            # 使用增强版冻结调度器
            model_size = get_model_size_from_type(model_type)
            
            # 预先计算路径
            freeze_logs_dir = os.path.join(train_dir, 'freeze_logs')
            stage_weights_dir = os.path.join(train_dir, 'stage_weights')
            
            # 创建调度器时传入路径，确保日志初始化在正确位置
            freeze_scheduler = create_yolov8_freeze_scheduler(
                model, 
                model_size,
                output_dir=freeze_logs_dir,
                stage_weights_dir=stage_weights_dir
            )
            
            freeze_scheduler.min_epochs_per_stage = min_epochs_per_stage
            
            # 确保目录存在
            os.makedirs(freeze_scheduler.output_dir, exist_ok=True)
            os.makedirs(freeze_scheduler.stage_weights_dir, exist_ok=True)
            
            print(f"🔥 增强版冻结策略已启用")
            print(f"📊 总共 {len(freeze_scheduler.stages)} 个训练阶段")
            print(f"🎯 当前阶段: {freeze_scheduler.current_stage} - {freeze_scheduler.stages[freeze_scheduler.current_stage]}")
            
            status = freeze_scheduler.get_training_status()
            print(f"📈 可训练参数比例: {status['trainable_ratio']:.2%}")
            
        except Exception as e:
            print(f"⚠️ 初始化增强版冻结策略失败: {str(e)}")
            print("   切换到常规训练模式")
            use_freeze_strategy = False
            freeze_scheduler = None
    
    # 如果使用增强版冻结策略，需要自定义训练循环
    if use_freeze_strategy and freeze_scheduler:
        results = train_with_enhanced_freeze_loop(
            model, data_path, epochs, imgsz, batch, device,
            project, name, patience, freeze_scheduler, task
        )
    else:
        # 常规训练
        print("🚀 开始常规训练...")
        results = model.train(
            task=task,
            data=data_path,
            epochs=epochs,
            imgsz=imgsz,
            batch=batch,
            device=device,
            project=project,
            name=name,
            resume=bool(resume_weights and os.path.exists(resume_weights)),
            patience=patience,
        )
    
    # 训练后处理
    if freeze_scheduler:
        print("📊 生成训练分析图表...")
        freeze_scheduler.plot()
        freeze_scheduler.save_state()
        
        # 保存详细的训练状态信息
        status = freeze_scheduler.get_training_status()
        status_path = os.path.join(train_dir, 'enhanced_freeze_status.yaml')
        with open(status_path, 'w', encoding='utf-8') as f:
            yaml.dump(status, f, default_flow_style=False, allow_unicode=True)
        
        print(f"💾 冻结策略状态已保存: {status_path}")
    
    # 保存训练日志
    log_path = os.path.join(train_dir, 'train_results.yaml')
    if hasattr(results, 'results_dict'):
        with open(log_path, 'w', encoding='utf-8') as f:
            yaml.dump(results.results_dict, f, default_flow_style=False, allow_unicode=True)
    
    # 尝试导出模型
    try:
        export_path = os.path.join(train_dir, f'model.onnx')
        model.export(format='onnx', dynamic=True, simplify=True, imgsz=imgsz)
        print(f"✅ ONNX 模型已导出")
    except Exception as e:
        print(f"⚠️ ONNX 导出失败: {str(e)}")
    
    print(f"\n🎉 训练完成！")
    print(f"📁 结果保存至：{train_dir}")
    print(f"📄 日志文件：{log_path}")
    
    return {
        'success': True,
        'train_dir': train_dir,
        'results': results,
        'freeze_scheduler': freeze_scheduler,
        'message': '训练完成'
    }


def train_with_enhanced_freeze_loop(model, data_path, total_epochs, imgsz, batch, device,
                                   project, name, patience, freeze_scheduler, task):
    """
    增强版冻结策略的自定义训练循环
    """
    print("🚀 开始使用增强版冻结策略训练...")
    
    train_dir = os.path.join(project, name)
    weights_dir = os.path.join(train_dir, 'weights')
    os.makedirs(weights_dir, exist_ok=True)
    
    current_epoch = 0
    all_results = []
    
    while current_epoch < total_epochs and freeze_scheduler.current_stage >= 0:
        # 检查是否需要切换阶段并重新开始训练
        stage_changed = freeze_scheduler.is_stage_changed()
        
        # 计算本次训练的epochs数
        remaining_epochs = total_epochs - current_epoch
        stage_epochs = min(
            freeze_scheduler.min_epochs_per_stage * 2,  # 每次训练较多epochs
            remaining_epochs
        )
        
        print(f"\n{'=' * 60}")
        print(f"📊 训练阶段 {len(freeze_scheduler.stages) - freeze_scheduler.current_stage}/{len(freeze_scheduler.stages)}")
        print(f"🔥 当前解冻模块: {freeze_scheduler.stages[freeze_scheduler.current_stage]}")
        print(f"📈 训练轮数: {stage_epochs} (总进度: {current_epoch}/{total_epochs})")
        
        status = freeze_scheduler.get_training_status()
        print(f"📈 可训练参数: {status['trainable_params']:,} / {status['total_params']:,} ({status['trainable_ratio']:.2%})")
        print(f"💾 阶段历史: 已训练 {status['stage_epochs']} 轮，最佳指标: {status['stage_best_metric']:.4f}")
        
        try:
            # 确定是否resume
            should_resume = not stage_changed and len(all_results) > 0
            
            # 如果阶段刚切换，尝试加载上个阶段的最佳权重
            if stage_changed:
                print("🔄 阶段已切换，将从上阶段最佳权重开始训练")
                should_resume = False
            
            # 执行训练
            stage_name = f"{name}_stage_{len(freeze_scheduler.stages) - freeze_scheduler.current_stage}"
            stage_results = model.train(
                task=task,
                data=data_path,
                epochs=stage_epochs,
                imgsz=imgsz,
                batch=batch,
                device=device,
                project=project,
                name=stage_name,
                resume=should_resume,
                patience=patience,
                save_period=max(1, stage_epochs // 5),  # 适当保存检查点
                val=True,
                plots=True
            )
            
            all_results.append(stage_results)
            current_epoch += stage_epochs
            
            # 获取训练结果中的验证指标
            val_metric = extract_validation_metric(stage_results)
            
            # 获取权重文件路径
            stage_weights_dir = os.path.join(project, stage_name, 'weights')
            best_weights = os.path.join(stage_weights_dir, 'best.pt')
            last_weights = os.path.join(stage_weights_dir, 'last.pt')
            
            # 更新冻结调度器状态
            freeze_scheduler.step_epoch(val_metric, best_weights if os.path.exists(best_weights) else last_weights)
            
            # 更新梯度范数历史
            freeze_scheduler.update_grad_norms()
            
            print(f"✅ 阶段训练完成，验证指标: {val_metric:.4f}")
            
            # 检查是否所有阶段都已完成
            if freeze_scheduler.current_stage < 0:
                print("🎉 所有冻结阶段已完成！")
                break
                
        except Exception as e:
            print(f"❌ 阶段训练失败: {str(e)}")
            # 可以选择继续下一阶段或终止训练
            freeze_scheduler.current_stage -= 1
            if freeze_scheduler.current_stage < 0:
                break
        
        # 打印当前整体进度
        overall_status = freeze_scheduler.get_training_status()
        print(f"\n📋 整体训练状态:")
        print(f"   - 当前轮数: {current_epoch}/{total_epochs}")
        print(f"   - 剩余阶段: {freeze_scheduler.current_stage + 1}")
        print(f"   - 验证历史: {len(freeze_scheduler.val_metrics)} 个记录")
        
        # 每几个阶段保存一次状态
        if (len(freeze_scheduler.stages) - freeze_scheduler.current_stage) % 2 == 0:
            freeze_scheduler.save_state()
            print("💾 冻结调度器状态已保存")
    
    print(f"\n🏁 训练循环结束，总共完成 {current_epoch} 轮训练")
    return all_results[-1] if all_results else None


def extract_validation_metric(results):
    """
    从训练结果中提取验证指标
    优先使用loss，其次使用mAP等指标
    """
    try:
        if hasattr(results, 'results_dict'):
            results_dict = results.results_dict
        elif hasattr(results, 'metrics'):
            results_dict = results.metrics
        else:
            # 如果无法获取指标，返回一个模拟值
            return 0.5
        
        # 尝试不同的指标键名
        metric_keys = [
            'val/box_loss', 'val/cls_loss', 'val/dfl_loss',  # 检测任务
            'val/seg_loss', 'val/mask_loss',  # 分割任务
            'val/loss', 'loss', 'val_loss',  # 通用loss
            'metrics/mAP50', 'metrics/mAP50-95',  # mAP指标
        ]
        
        for key in metric_keys:
            if key in results_dict:
                value = results_dict[key]
                if isinstance(value, (list, tuple)) and len(value) > 0:
                    return float(value[-1])  # 取最后一个值
                elif isinstance(value, (int, float)):
                    return float(value)
        
        # 如果都找不到，返回默认值
        return 0.5
        
    except Exception as e:
        print(f"⚠️ 提取验证指标失败: {str(e)}")
        return 0.5