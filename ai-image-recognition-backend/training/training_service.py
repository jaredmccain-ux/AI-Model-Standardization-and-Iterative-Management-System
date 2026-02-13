import os
import uuid
import asyncio
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, asdict
import json
from pathlib import Path
import torch
from ultralytics import YOLO

from .enhanced_training import train_model_with_enhanced_freeze, get_model_size_from_type
from .incremental_newtrain import IncrementalTrainer
try:
    from .distillation_trainer import DistillationTrainer
    from .seg_distillation_trainer import SegDistillationTrainer
    from .cls_distillation_trainer import ClsDistillationTrainer
    DISTILLATION_AVAILABLE = True
except ImportError:
    DISTILLATION_AVAILABLE = False
    print("Warning: Distillation trainers could not be imported.")


class TrainingStatus(Enum):
    """训练状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TrainingType(Enum):
    """训练类型枚举"""
    REGULAR = "regular"
    INCREMENTAL = "incremental"
    FREEZE_STRATEGY = "freeze_strategy"
    DISTILLATION = "distillation"


@dataclass
class TrainingConfig:
    """训练配置"""
    task: str = "detect"  # detect, segment, classify
    model_type: str = "s"  # n, s, m, l, x
    data_path: str = "data.yaml"
    epochs: int = 50
    imgsz: int = 640
    batch: int = 8
    project: str = "runs/train"
    name: Optional[str] = None
    resume_weights: Optional[str] = None
    patience: int = 15
    use_freeze_strategy: bool = True
    min_epochs_per_stage: int = 15
    # 增量训练特有参数
    base_model_path: Optional[str] = None
    new_classes: Optional[List[str]] = None
    old_data_path: Optional[str] = None # 用于增量训练的旧数据
    
    # 蒸馏训练参数
    teacher_model_path: Optional[str] = None
    distill_temperature: float = 2.0
    distill_cls_weight: float = 1.0
    distill_reg_weight: float = 2.0
    distill_feat_weight: float = 5.0
    distill_mask_weight: float = 1.0
    distill_bg_weight: float = 0.05
    
    # 伪标签与一致性
    pseudo_conf_threshold: float = 0.7
    enable_consistency: bool = False
    consistency_weight: float = 1.0
    
    # 旧样本回放
    replay_ratio: float = 0.0
    replay_distill_boost: float = 1.0
    max_replay_samples: int = 1000
    
    def to_dict(self):
        return asdict(self)


@dataclass
class TrainingTask:
    """训练任务"""
    task_id: str
    training_type: TrainingType
    config: TrainingConfig
    status: TrainingStatus = TrainingStatus.PENDING
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    current_epoch: int = 0
    total_epochs: int = 0
    logs: List[str] = None
    error_message: Optional[str] = None
    result_path: Optional[str] = None
    metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.logs is None:
            self.logs = []
        if self.metrics is None:
            self.metrics = {}
    
    def to_dict(self):
        data = asdict(self)
        # 转换枚举为字符串
        data['training_type'] = self.training_type.value
        data['status'] = self.status.value
        # 转换datetime为字符串
        for field in ['created_at', 'started_at', 'completed_at']:
            if data[field]:
                data[field] = data[field].isoformat()
        return data


class TrainingService:
    """训练服务管理类"""
    
    def __init__(self):
        self.tasks: Dict[str, TrainingTask] = {}
        self.running_tasks: Dict[str, threading.Thread] = {}
        
    def create_task(self, training_type: TrainingType, config: TrainingConfig) -> str:
        """创建训练任务"""
        # 使用更易读的格式: Task_类型_YYYYMMDD_HHMMSS
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        # 获取类型名称，如 regular, incremental
        type_str = training_type.value if hasattr(training_type, 'value') else str(training_type)
        task_id = f"Task_{type_str}_{timestamp}"
        
        # 防止极端情况下的ID冲突
        if task_id in self.tasks:
            import random
            task_id = f"{task_id}_{random.randint(100, 999)}"
            
        task = TrainingTask(
            task_id=task_id,
            training_type=training_type,
            config=config,
            total_epochs=config.epochs
        )
        self.tasks[task_id] = task
        return task_id
    
    def get_task(self, task_id: str) -> Optional[TrainingTask]:
        """获取训练任务"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[TrainingTask]:
        """获取所有训练任务"""
        return list(self.tasks.values())
    
    def start_task(self, task_id: str) -> bool:
        """启动训练任务"""
        task = self.tasks.get(task_id)
        if not task or task.status != TrainingStatus.PENDING:
            return False
        
        task.status = TrainingStatus.RUNNING
        task.started_at = datetime.now()
        
        # 在新线程中执行训练
        thread = threading.Thread(target=self._run_training, args=(task,))
        thread.daemon = True
        self.running_tasks[task_id] = thread
        thread.start()
        
        return True
    
    def cancel_task(self, task_id: str) -> bool:
        """取消训练任务"""
        task = self.tasks.get(task_id)
        if not task or task.status not in [TrainingStatus.PENDING, TrainingStatus.RUNNING]:
            return False
        
        task.status = TrainingStatus.CANCELLED
        task.completed_at = datetime.now()
        
        # 如果任务正在运行，尝试停止线程（注意：Python线程无法强制停止）
        if task_id in self.running_tasks:
            del self.running_tasks[task_id]
        
        return True
    
    def _run_training(self, task: TrainingTask):
        """执行训练任务"""
        try:
            self._log_message(task, f"开始训练任务: {task.task_id}")
            
            if task.training_type == TrainingType.INCREMENTAL:
                result = self._run_incremental_training(task)
            elif task.training_type == TrainingType.FREEZE_STRATEGY:
                result = self._run_freeze_strategy_training(task)
            elif task.training_type == TrainingType.DISTILLATION:
                result = self._run_distillation_training(task)
            else:
                result = self._run_regular_training(task)
            
            if result:
                task.status = TrainingStatus.COMPLETED
                task.result_path = result.get('model_path')
                task.metrics = result.get('metrics', {})
                self._log_message(task, f"训练完成，模型保存至: {task.result_path}")
            else:
                task.status = TrainingStatus.FAILED
                task.error_message = "训练失败，未返回结果"
                
        except Exception as e:
            task.status = TrainingStatus.FAILED
            task.error_message = str(e)
            self._log_message(task, f"训练失败: {str(e)}")
        
        finally:
            task.completed_at = datetime.now()
            task.progress = 100.0
            if task.task_id in self.running_tasks:
                del self.running_tasks[task.task_id]
    
    def _run_incremental_training(self, task: TrainingTask) -> Optional[Dict]:
        """执行增量训练 (使用新的 IncrementalTrainer)"""
        config = task.config
        
        try:
            # 确保旧数据配置存在
            old_data_yaml = config.old_data_path
            if not old_data_yaml:
                 # 如果没有提供，尝试从base_model_path推断或者报错
                 # 这里简单起见，如果没提供就报错
                 raise ValueError("增量训练需要提供旧数据集配置 (old_data_path)")

            trainer = IncrementalTrainer(
                existing_model_path=config.base_model_path,
                old_data_yaml=old_data_yaml,
                new_data_yaml=config.data_path,
                task=config.task
            )
            
            # 分析变化
            trainer.analyze_changes()
            
            # 使用单阶段训练 (为了简单起见，或者可以根据config增加stage选项)
            # 这里我们使用单阶段，并支持 freeze
            trainer.train(
                project=config.project,
                name=config.name or f"inc_{task.task_id}",
                epochs=config.epochs,
                batch=config.batch,
                imgsz=config.imgsz,
                old_data_ratio=config.replay_ratio or 0.2, # 复用 replay_ratio 作为 old_data_ratio
                lr0=1e-4, # 默认值
                lrf=1e-5,
                freeze=0, # 默认不冻结，或者可以加参数
                plots=True,
                device='0' if torch.cuda.is_available() else 'cpu'
            )
            
            # 结果路径
            result_dir = os.path.join(config.project, config.name or f"inc_{task.task_id}")
            best_model_path = os.path.join(result_dir, "weights", "best.pt")
            
            return {
                "model_path": best_model_path,
                "metrics": {} # 需要从训练结果中解析
            }
            
        except Exception as e:
            self._log_message(task, f"增量训练出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def _run_distillation_training(self, task: TrainingTask) -> Optional[Dict]:
        """执行蒸馏训练"""
        if not DISTILLATION_AVAILABLE:
            raise ImportError("蒸馏训练模块未安装或导入失败")
            
        config = task.config
        
        try:
            # 选择训练器
            if config.task == 'detect':
                TrainerClass = DistillationTrainer
            elif config.task == 'segment':
                TrainerClass = SegDistillationTrainer
            elif config.task == 'classify':
                TrainerClass = ClsDistillationTrainer
            else:
                raise ValueError(f"不支持的任务类型: {config.task}")
            
            # 加载教师模型
            teacher_yolo = YOLO(config.teacher_model_path)
            teacher_model = teacher_yolo.model
            
            # 加载学生模型 (可以是同一个，或者更小的)
            student_model = YOLO(config.base_model_path or config.teacher_model_path) # 如果没指定base，就用teacher作为起点
            
            # 准备参数
            train_args = {
                'epochs': config.epochs,
                'batch': config.batch,
                'imgsz': config.imgsz,
                'project': config.project,
                'name': config.name or f"distill_{task.task_id}",
                'device': '0' if torch.cuda.is_available() else 'cpu',
                'plots': True,
                
                # 蒸馏参数
                'temperature': config.distill_temperature,
                'distill_cls_weight': config.distill_cls_weight,
                'distill_reg_weight': config.distill_reg_weight,
                'distill_feat_weight': config.distill_feat_weight,
                # 'distill_mask_weight': config.distill_mask_weight, # 只有分割任务需要
                # 'distill_bg_weight': config.distill_bg_weight,   # 只有分类任务需要
                
                # 一致性参数
                'enable_consistency': config.enable_consistency,
                'consistency_weight': config.consistency_weight,
                'pseudo_conf_threshold': config.pseudo_conf_threshold,
                
                # 回放参数
                'replay_ratio': config.replay_ratio,
                'replay_distill_boost': config.replay_distill_boost,
                'max_replay_samples': config.max_replay_samples,
                'old_data_yaml': config.old_data_path,
            }

            if config.task == 'segment':
                train_args['distill_mask_weight'] = config.distill_mask_weight
            
            if config.task == 'classify':
                train_args['distill_bg_weight'] = config.distill_bg_weight
            
            # 启动训练
            student_model.train(
                trainer=TrainerClass,
                teacher_model=teacher_model,
                data=config.data_path,
                **train_args
            )
            
            # 结果路径
            result_dir = os.path.join(config.project, config.name or f"distill_{task.task_id}")
            best_model_path = os.path.join(result_dir, "weights", "best.pt")
            
            return {
                "model_path": best_model_path,
                "metrics": {} 
            }
            
        except Exception as e:
            self._log_message(task, f"蒸馏训练出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _run_freeze_strategy_training(self, task: TrainingTask) -> Optional[Dict]:
        """执行冻结策略训练"""
        config = task.config
        
        def progress_callback(epoch, total_epochs):
            task.current_epoch = epoch
            task.progress = (epoch / total_epochs) * 100
            self._log_message(task, f"训练进度: {epoch}/{total_epochs} ({task.progress:.1f}%)")
        
        result = train_model_with_enhanced_freeze(
            task=config.task,
            model_type=config.model_type,
            data_path=config.data_path,
            epochs=config.epochs,
            imgsz=config.imgsz,
            batch=config.batch,
            project=config.project,
            name=config.name,
            resume_weights=config.resume_weights,
            patience=config.patience,
            use_freeze_strategy=config.use_freeze_strategy,
            min_epochs_per_stage=config.min_epochs_per_stage,
            progress_callback=progress_callback
        )
        
        return result
    
    def _run_regular_training(self, task: TrainingTask) -> Optional[Dict]:
        """执行常规训练"""
        config = task.config
        
        def progress_callback(epoch, total_epochs):
            task.current_epoch = epoch
            task.progress = (epoch / total_epochs) * 100
            self._log_message(task, f"训练进度: {epoch}/{total_epochs} ({task.progress:.1f}%)")
        
        # 使用冻结策略训练但禁用冻结功能
        result = train_model_with_enhanced_freeze(
            task=config.task,
            model_type=config.model_type,
            data_path=config.data_path,
            epochs=config.epochs,
            imgsz=config.imgsz,
            batch=config.batch,
            project=config.project,
            name=config.name,
            resume_weights=config.resume_weights,
            patience=config.patience,
            use_freeze_strategy=False,  # 禁用冻结策略
            progress_callback=progress_callback
        )
        
        return result
    
    def _log_message(self, task: TrainingTask, message: str):
        """记录日志消息"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        task.logs.append(log_entry)
        print(log_entry)  # 同时输出到控制台


# 全局训练服务实例
training_service = TrainingService()