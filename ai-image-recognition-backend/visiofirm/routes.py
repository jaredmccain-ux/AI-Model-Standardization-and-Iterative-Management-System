from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Optional
import json
import os
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import Depends

# 导入数据库和AI模型服务
from database import get_db
from ai_models import ai_service
from .models import VisioFirmAnnotation

router = APIRouter(
    prefix="/api/visiofirm",
    tags=["visiofirm"],
    responses={404: {"description": "Not found"}},
)

@router.post("/annotate")
async def annotate_image(
    image: UploadFile = File(...),
    tool: str = Form(...),
    model: Optional[str] = Form(None),
    categories: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    使用AI模型标准化迭代系统进行图像自动标注
    
    - **file**: 要标注的图像文件
    - **tool_type**: 标注工具类型 (bbox, polygon, obb)
    - **model**: 可选的模型名称
    - **categories**: 可选的类别列表，JSON格式字符串
    """
    try:
        # 创建临时文件保存上传的图像
        temp_file_path = f"temp_{uuid.uuid4()}.jpg"
        with open(temp_file_path, "wb") as buffer:
            buffer.write(await image.read())
        
        # 解析类别列表
        category_list = []
        if categories:
            try:
                category_list = json.loads(categories)
            except json.JSONDecodeError:
                category_list = []
        
        # 根据工具类型选择不同的标注方法
        annotations = []
        if tool == "object_detection":
            # 使用AI服务进行边界框检测
            detections = ai_service.detect_objects(temp_file_path, model_name=model)
            
            # 转换为前端需要的格式
            for det in detections:
                class_name = det["class_name"]
                if category_list and class_name not in category_list:
                    continue
                    
                # 从bbox_percent中获取百分比坐标
                x_percent, y_percent, w_percent, h_percent = det["bbox_percent"]
                
                annotations.append({
                    "type": "bbox",
                    "label": class_name,
                    "confidence": det["confidence"],
                    "bbox": {
                        "x": x_percent * 100,  # 转换为百分比
                        "y": y_percent * 100,  # 转换为百分比
                        "width": w_percent * 100,  # 转换为百分比
                        "height": h_percent * 100  # 转换为百分比
                    }
                })
        elif tool == "image_classification":
            # 使用AI服务进行图像分类
            classifications = ai_service.classify_image(temp_file_path, model_name=model)
            
            # 转换为前端需要的格式
            for cls in classifications:
                annotations.append({
                    "type": "classification",
                    "label": cls["class_name"],
                    "confidence": cls["confidence"]
                })

        elif tool == "image_segmentation":
            # 使用AI服务进行分割
            try:
                segments = ai_service.segment_objects(temp_file_path, model_name=model)
                
                # 转换为前端需要的格式
                for seg in segments:
                    class_name = seg["class_name"]
                    if category_list and class_name not in category_list:
                        continue
                        
                    annotations.append({
                        "type": "polygon",
                        "label": class_name,
                        "confidence": seg["confidence"],
                        "points": seg["points"]
                    })
            except Exception as seg_error:
                print(f"分割处理错误: {str(seg_error)}")
                import traceback
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=f"图像分割处理错误: {str(seg_error)}")
        else:
            raise HTTPException(status_code=400, detail=f"不支持的标注工具类型: {tool}")
        
        # 保存标注结果到数据库
        db_annotation = VisioFirmAnnotation(
            filename=image.filename,
            tool_type=tool,
            model=model,
            annotation_data=annotations,
            created_at=datetime.utcnow()
        )
        db.add(db_annotation)
        db.commit()
        
        # 删除临时文件
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        
        # 返回标注结果
        return JSONResponse(content={
            "success": True,
            "annotations": annotations,
            "message": f"使用VisioFirm AI成功标注了{len(annotations)}个对象"
        })
        
    except Exception as e:
        # 确保临时文件被删除
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        
        # 打印详细错误信息
        import traceback
        print(f"标注过程中出错: {str(e)}")
        traceback.print_exc()
        
        # 返回错误信息
        raise HTTPException(status_code=500, detail=f"标注过程中出错: {str(e)}")

@router.get("/models")
async def get_available_models():
    """获取可用的VisioFirm AI模型列表"""
    models = [
        {"value": "visiofirm-v1", "label": "VisioFirm 通用检测 V1"},
        {"value": "visiofirm-segment", "label": "VisioFirm 分割模型"},
        {"value": "visiofirm-obb", "label": "VisioFirm 方向框检测"}
    ]
    return JSONResponse(content=models)