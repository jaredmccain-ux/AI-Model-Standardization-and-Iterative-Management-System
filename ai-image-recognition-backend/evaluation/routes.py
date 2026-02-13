from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Optional
import uuid
import datetime
import threading
import json

from .models import EvaluationResultDB
from .metrics import EvaluationMetrics
from training.models import TrainingTaskDB
from database import get_db  # 假设main.py中有获取数据库会话的函数

router = APIRouter()

# 数据模型
class Prediction(BaseModel):
    class_name: str
    box: List[float]  # [x1, y1, x2, y2]
    confidence: float

class GroundTruth(BaseModel):
    class_name: str
    box: List[float]  # [x1, y1, x2, y2]

class EvaluationRequest(BaseModel):
    model_id: str
    task_id: Optional[str] = None
    predictions: List[Prediction]
    ground_truths: List[GroundTruth]
    iou_threshold: float = 0.5

class EvaluationResponse(BaseModel):
    evaluation_id: str
    status: str
    message: str

# 评估服务类
class EvaluationService:
    def __init__(self):
        self.running_evaluations = {}
    
    def start_evaluation(self, db: Session, eval_request: EvaluationRequest) -> str:
        """开始评估任务"""
        evaluation_id = str(uuid.uuid4())
        
        # 创建评估记录
        eval_result = EvaluationResultDB(
            evaluation_id=evaluation_id,
            model_id=eval_request.model_id,
            task_id=eval_request.task_id,
            status="pending",
            config={
                "iou_threshold": eval_request.iou_threshold
            }
        )
        
        db.add(eval_result)
        db.commit()
        db.refresh(eval_result)
        
        # 在后台线程中执行评估
        thread = threading.Thread(
            target=self._run_evaluation,
            args=(db, evaluation_id, eval_request)
        )
        thread.daemon = True
        thread.start()
        
        self.running_evaluations[evaluation_id] = thread
        
        return evaluation_id
    
    def _run_evaluation(self, db: Session, evaluation_id: str, eval_request: EvaluationRequest):
        """执行评估任务"""
        # 获取评估记录
        eval_result = db.query(EvaluationResultDB).filter(
            EvaluationResultDB.evaluation_id == evaluation_id
        ).first()
        
        if not eval_result:
            return
        
        try:
            # 更新状态为运行中
            eval_result.status = "running"
            db.commit()
            
            # 转换数据格式
            predictions = [
                {
                    'class': pred.class_name,
                    'box': pred.box,
                    'confidence': pred.confidence
                }
                for pred in eval_request.predictions
            ]
            
            ground_truths = [
                {
                    'class': gt.class_name,
                    'box': gt.box
                }
                for gt in eval_request.ground_truths
            ]
            
            # 计算评估指标
            precision, recall = EvaluationMetrics.calculate_precision_recall(
                predictions, ground_truths, eval_request.iou_threshold
            )
            
            # 计算mAP
            map50, map50_95, class_maps = EvaluationMetrics.calculate_map(
                predictions, ground_truths
            )
            
            # 计算F1分数
            f1_score = 2 * (precision['overall'] * recall['overall']) / \
                      (precision['overall'] + recall['overall'] + 1e-10)
            
            # 生成PR曲线数据
            pr_curve_data = EvaluationMetrics.generate_pr_curve_data(
                predictions, ground_truths, eval_request.iou_threshold
            )
            
            # 组织类别评估指标(注意位置)
            class_metrics = {}
            all_classes = set(precision.keys()) - {'overall'}
            for cls in all_classes:
                class_f1 = 2 * (precision[cls] * recall[cls]) / \
                          (precision[cls] + recall[cls] + 1e-10)
                
                class_metrics[cls] = {
                    'precision': precision[cls],
                    'recall': recall[cls],
                    'f1_score': class_f1,
                    'ap': class_maps.get(cls, 0.0)
                }
            
            # 更新评估结果
            eval_result.status = "completed"
            eval_result.completed_at = datetime.datetime.utcnow()
            eval_result.precision = precision['overall']
            eval_result.recall = recall['overall']
            eval_result.f1_score = f1_score
            eval_result.mAP50 = map50
            eval_result.mAP50_95 = map50_95
            eval_result.class_metrics = class_metrics
            eval_result.pr_curve_data = pr_curve_data
            
            # 添加日志
            eval_result.logs = json.dumps([
                f"Evaluation completed successfully at {datetime.datetime.utcnow()}",
                f"mAP@0.5: {map50:.4f}",
                f"mAP@0.5:0.95: {map50_95:.4f}",
                f"Overall precision: {precision['overall']:.4f}",
                f"Overall recall: {recall['overall']:.4f}",
                f"Overall F1 score: {f1_score:.4f}"
            ])
            
            db.commit()
            
        except Exception as e:
            # 处理错误
            eval_result.status = "failed"
            eval_result.error_message = str(e)
            eval_result.logs = json.dumps([
                f"Evaluation failed at {datetime.datetime.utcnow()}",
                f"Error: {str(e)}"
            ])
            db.commit()
        finally:
            if evaluation_id in self.running_evaluations:
                del self.running_evaluations[evaluation_id]

# 创建评估服务
evaluation_service = EvaluationService()

# API路由
@router.post("/api/models/{model_id}/evaluate", response_model=EvaluationResponse)
def evaluate_model(
    model_id: str,
    eval_request: EvaluationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """评估模型性能"""
    try:
        eval_request.model_id = model_id
        
        # 开始评估
        evaluation_id = evaluation_service.start_evaluation(db, eval_request)
        
        return {
            "evaluation_id": evaluation_id,
            "status": "pending",
            "message": "Evaluation started successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/models/{model_id}/evaluation/{evaluation_id}")
def get_evaluation_result(
    model_id: str,
    evaluation_id: str,
    db: Session = Depends(get_db)
):
    """获取评估结果"""
    eval_result = db.query(EvaluationResultDB).filter(
        EvaluationResultDB.evaluation_id == evaluation_id,
        EvaluationResultDB.model_id == model_id
    ).first()
    
    if not eval_result:
        raise HTTPException(status_code=404, detail="Evaluation result not found")
    
    # 生成PR曲线图像
    pr_curve_image = None
    if eval_result.status == "completed" and eval_result.pr_curve_data:
        pr_curve_image = EvaluationMetrics.plot_pr_curve(
            eval_result.pr_curve_data,
            f"PR Curve for Model {model_id}"
        )
    
    return {
        "evaluation_id": eval_result.evaluation_id,
        "model_id": eval_result.model_id,
        "task_id": eval_result.task_id,
        "status": eval_result.status,
        "created_at": eval_result.created_at,
        "completed_at": eval_result.completed_at,
        "metrics": {
            "mAP50": eval_result.mAP50,
            "mAP50_95": eval_result.mAP50_95,
            "precision": eval_result.precision,
            "recall": eval_result.recall,
            "f1_score": eval_result.f1_score,
            "class_metrics": eval_result.class_metrics
        },
        "pr_curve_data": eval_result.pr_curve_data,
        "pr_curve_image": pr_curve_image,
        "logs": eval_result.logs,
        "error_message": eval_result.error_message
    }

@router.get("/api/models/{model_id}/evaluations")
def get_model_evaluations(
    model_id: str,
    db: Session = Depends(get_db)
):
    """获取模型的所有评估记录"""
    evaluations = db.query(EvaluationResultDB).filter(
        EvaluationResultDB.model_id == model_id
    ).order_by(EvaluationResultDB.created_at.desc()).all()
    
    return [
        {
            "evaluation_id": eval_result.evaluation_id,
            "status": eval_result.status,
            "created_at": eval_result.created_at,
            "completed_at": eval_result.completed_at,
            "metrics": {
                "mAP50": eval_result.mAP50,
                "mAP50_95": eval_result.mAP50_95
            }
        }
        for eval_result in evaluations
    ]