from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Session, relationship
from datetime import datetime
import uuid
import os

# 导入数据库设置
from database import Base, engine, get_db

# 导入AI模型服务
from ai_models import ai_service

# 数据库模型
class Image(Base):
    __tablename__ = "images"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=True, index=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    annotations = relationship("AutoAnnotation", back_populates="image")
    manual_annotations = relationship("ManualAnnotation", back_populates="image")

class AutoAnnotation(Base):
    __tablename__ = "auto_annotations"
    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(Integer, ForeignKey("images.id"))
    tool_type = Column(String)
    annotation_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    image = relationship("Image", back_populates="annotations")

class ManualAnnotation(Base):
    __tablename__ = "manual_annotations"
    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(Integer, ForeignKey("images.id"))
    tool_type = Column(String)
    annotation_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    image = relationship("Image", back_populates="manual_annotations")

# 导入其他模块的模型，确保它们在创建表之前被加载
from training import models as training_models
from evaluation import models as evaluation_models
from visiofirm import models as visiofirm_models
from settings import models as settings_models

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 创建FastAPI应用
app = FastAPI(
    title="AI Auto-Annotation Service",
    description="An API for automatic and manual image annotation.",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://aivisioniterate.top",
        "https://aivisioniterate.top"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 导入并包含训练API路由
from training.api import router as training_router
app.include_router(training_router)

# 导入并包含评估API路由
from evaluation.routes import router as evaluation_router
app.include_router(evaluation_router)

# 导入并包含VisioFirm API路由
from visiofirm.routes import router as visiofirm_router
app.include_router(visiofirm_router)

# 导入并包含Settings API路由
from settings.api import router as settings_router
app.include_router(settings_router)

# 智能体数据增广 API：在 main 中直接注册，避免子模块导入失败导致 404
try:
    from augmentation.routes import router as augmentation_router
    app.include_router(augmentation_router)
except Exception as e:
    import logging
    _log = logging.getLogger("uvicorn.error")
    _log.warning("增广模块加载失败，/api/augmentation/run 将返回 503: %s", e)
    from typing import List
    @app.post("/api/augmentation/run")
    async def _augmentation_unavailable(
        instruction: str = Form(...),
        images: List[UploadFile] = File(...),
    ):
        return JSONResponse(
            status_code=503,
            content={"detail": "增广模块未加载。请：1) 在 ai-image-recognition-backend 目录下启动；2) pip install openai；3) 配置 .augmentation_api_key 或 DASHSCOPE_API_KEY"}
        )

# 在应用启动时打印已注册路由，便于部署环境排障
@app.on_event("startup")
async def log_registered_routes():
    try:
        route_info = []
        for route in app.routes:
            path = getattr(route, "path", None)
            methods = getattr(route, "methods", None)
            if path:
                route_info.append({
                    "path": path,
                    "methods": sorted(list(methods)) if methods else []
                })
        print(f"已注册路由数量: {len(route_info)}")
        for r in route_info:
            print(f"路由: {r['path']} 方法: {','.join(r['methods'])}")
    except Exception as e:
        print(f"启动时打印路由失败: {e}")

@app.get("/api/tools")
async def get_tools():
    """返回可用的AI标注工具列表"""
    tools = [
        {"value": "object_detection", "label": "目标检测"},
        {"value": "image_classification", "label": "图像分类"},
        {"value": "image_segmentation", "label": "图像分割"}
    ]
    return JSONResponse(content=tools)

def generate_bbox_annotation():
    return {
        "from_name": "tag",
        "to_name": "img",
        "type": "rectanglelabels",
        "value": {
            "rectanglelabels": ["Object"],
            "x": 10,
            "y": 15,
            "width": 20,
            "height": 25
        }
    }

def generate_polygon_annotation():
    return {
        "from_name": "tag",
        "to_name": "img",
        "type": "polygonlabels",
        "value": {
            "polygonlabels": ["Area"],
            "points": [[20, 20], [50, 20], [50, 50], [20, 50]]
        }
    }

def generate_keypoint_annotation():
    return {
        "from_name": "tag",
        "to_name": "img",
        "type": "keypointlabels",
        "value": {
            "keypointlabels": ["Point"],
            "x": 35,
            "y": 40
        }
    }

@app.post("/api/auto_annotate")
async def auto_annotate(
    image: UploadFile = File(...),
    tool: str = Form(...),
    model: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    try:
        # 1. 读取图片数据
        image_bytes = await image.read()
        
        # 2. 保存图片信息到数据库
        db_image = db.query(Image).filter(Image.filename == image.filename).first()
        if not db_image:
            db_image = Image(filename=image.filename)
            db.add(db_image)
            db.commit()
            db.refresh(db_image)

        # 3. 使用AI模型生成标注
        annotations = []
        annotated_image_base64 = None
        
        # 保存上传的图片到临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            temp_file.write(image_bytes)
            temp_file_path = temp_file.name
        
        try:
            if tool == "object_detection":
                # 调用带可视化的检测方法，传入前端选择的模型名
                annotations, annotated_image_base64 = ai_service.detect_objects_with_visualization(
                    image_bytes, model_name=model or "YOLO"
                )
            elif tool == "image_classification":
                # 调用分类方法，传入前端选择的模型名
                classification_results = ai_service.classify_image(temp_file_path, model_name=model)
                annotations = classification_results
            elif tool == "image_segmentation":
                # 调用分割方法；未传 model 时默认用 YOLO-Seg，避免走模拟数据
                seg_model = (model and str(model).strip()) or "YOLO-Seg"
                print(f"[分割] 收到 model={repr(model)}, 使用 seg_model={seg_model}")
                segmentation_results = ai_service.segment_objects(temp_file_path, model_name=seg_model)
                annotations = segmentation_results
            else:
                raise HTTPException(status_code=400, detail=f"Tool type '{tool}' is not supported.")
        finally:
            # 清理临时文件
            import os
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

        # 4. 保存所有标注到数据库
        for annotation in annotations:
            db_annotation = AutoAnnotation(
                image_id=db_image.id,
                tool_type=tool,
                annotation_data=annotation
            )
            db.add(db_annotation)
        
        db.commit()

        # 5. 封装响应数据
        response_data = {
            "annotations": annotations,
            "annotated_image": annotated_image_base64, # 添加标注后的图片
            "database_info": {
                "image_id": db_image.id,
                "annotation_count": len(annotations)
            }
        }

        return JSONResponse(content=response_data)

    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error processing image: {str(e)}"}
        )

# 添加手动标注提交API
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class AnnotationItem(BaseModel):
    id: Optional[str] = None
    type: str
    label: Optional[str] = None
    confidence: Optional[float] = 1.0
    bbox: Optional[Dict[str, float]] = None
    points: Optional[List[List[float]]] = None
    rectanglelabels: Optional[List[str]] = None
    polygonlabels: Optional[List[str]] = None
    keypointlabels: Optional[List[str]] = None
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None

class SingleAnnotationRequest(BaseModel):
    imageName: str
    tool: str
    annotation: AnnotationItem

class MultipleAnnotationRequest(BaseModel):
    imageName: str
    tool: str
    annotations: List[AnnotationItem]

@app.post("/api/annotations/single")
async def submit_single_annotation(request: SingleAnnotationRequest, db: Session = Depends(get_db)):
    try:
        print(f"收到单标注保存请求: {request}")
        print(f"请求数据类型: imageName={type(request.imageName)}, tool={type(request.tool)}, annotation={type(request.annotation)}")
        print(f"标注数据: {request.annotation.dict()}")
        
        # 查找或创建图片记录
        db_image = db.query(Image).filter(Image.filename == request.imageName).first()
        if not db_image:
            db_image = Image(filename=request.imageName)
            db.add(db_image)
            db.commit()
            db.refresh(db_image)
        
        # 保存手动标注
        db_annotation = ManualAnnotation(
            image_id=db_image.id,
            tool_type=request.tool,
            annotation_data=request.annotation.dict()
        )
        db.add(db_annotation)
        db.commit()
        db.refresh(db_annotation)
        
        return JSONResponse(content={
            "success": True,
            "message": "Annotation saved successfully",
            "annotation_id": db_annotation.id,
            "image_id": db_image.id
        })
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error saving annotation: {str(e)}"}
        )

@app.post("/api/annotations/batch")
async def submit_batch_annotations(request: MultipleAnnotationRequest, db: Session = Depends(get_db)):
    try:
        # 查找或创建图片记录
        db_image = db.query(Image).filter(Image.filename == request.imageName).first()
        if not db_image:
            db_image = Image(filename=request.imageName)
            db.add(db_image)
            db.commit()
            db.refresh(db_image)
        
        # 保存多个手动标注
        created_annotations = []
        for annotation in request.annotations:
            db_annotation = ManualAnnotation(
                image_id=db_image.id,
                tool_type=request.tool,
                annotation_data=annotation.dict()
            )
            db.add(db_annotation)
            created_annotations.append(db_annotation)
        
        db.commit()
        
        return JSONResponse(content={
            "success": True,
            "message": "Annotations saved successfully",
            "annotation_ids": [ann.id for ann in created_annotations],
            "image_id": db_image.id,
            "count": len(created_annotations)
        })
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error saving annotations: {str(e)}"}
        )

@app.delete("/api/annotations/{annotation_id}")
async def delete_annotation(annotation_id: int, db: Session = Depends(get_db)):
    try:
        # 查找标注
        db_annotation = db.query(ManualAnnotation).filter(ManualAnnotation.id == annotation_id).first()
        if not db_annotation:
            raise HTTPException(status_code=404, detail="Annotation not found")
        
        # 删除标注
        db.delete(db_annotation)
        db.commit()
        
        return JSONResponse(content={
            "success": True,
            "message": "Annotation deleted successfully"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error deleting annotation: {str(e)}"}
        )

# 保留原有API以确保向后兼容性
@app.post("/api/annotations")
async def submit_annotation(annotation_data: dict, db: Session = Depends(get_db)):
    try:
        print(f"收到标注保存请求: {annotation_data}")
        
        # 根据图片名称查找图片
        image_name = annotation_data.get('imageName')
        tool_type = annotation_data.get('tool')
        annotation = annotation_data.get('annotation')
        
        if not all([image_name, tool_type, annotation]):
            print(f"缺少必需字段: image_name={image_name}, tool_type={tool_type}, annotation={annotation}")
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        # 查找或创建图片记录
        db_image = db.query(Image).filter(Image.filename == image_name).first()
        if not db_image:
            print(f"创建新图片记录: {image_name}")
            db_image = Image(filename=image_name)
            db.add(db_image)
            db.commit()
            db.refresh(db_image)
        
        # 保存手动标注
        print(f"保存标注到数据库，图片ID: {db_image.id}, 工具类型: {tool_type}")
        db_annotation = ManualAnnotation(
            image_id=db_image.id,
            tool_type=tool_type,
            annotation_data=annotation
        )
        db.add(db_annotation)
        db.commit()
        db.refresh(db_annotation)
        
        print(f"标注保存成功，ID: {db_annotation.id}")
        return JSONResponse(content={
            "success": True,
            "message": "Annotation saved successfully",
            "annotation_id": db_annotation.id,
            "image_id": db_image.id
        })
        
    except HTTPException as http_exc:
        print(f"HTTP错误: {http_exc.detail}")
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"保存标注时出错: {str(e)}")
        print(f"错误堆栈: {error_trace}")
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "detail": f"Error saving annotation: {str(e)}"}
        )

# 获取图片的所有标注
@app.get("/api/images/{image_id}/annotations")
async def get_image_annotations(image_id: int, db: Session = Depends(get_db)):
    try:
        db_image = db.query(Image).filter(Image.id == image_id).first()
        if not db_image:
            raise HTTPException(status_code=404, detail="Image not found")
        
        auto_annotations = db.query(AutoAnnotation).filter(AutoAnnotation.image_id == image_id).all()
        manual_annotations = db.query(ManualAnnotation).filter(ManualAnnotation.image_id == image_id).all()
        
        return JSONResponse(content={
            "image_id": image_id,
            "filename": db_image.filename,
            "auto_annotations": [{
                "id": ann.id,
                "tool_type": ann.tool_type,
                "annotation_data": ann.annotation_data,
                "created_at": ann.created_at.isoformat()
            } for ann in auto_annotations],
            "manual_annotations": [{
                "id": ann.id,
                "tool_type": ann.tool_type,
                "annotation_data": ann.annotation_data,
                "created_at": ann.created_at.isoformat()
            } for ann in manual_annotations]
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving annotations: {str(e)}"}
        )

@app.get("/api/annotations/{image_name}")
async def get_annotations_by_image_name(image_name: str, db: Session = Depends(get_db)):
    try:
        db_image = db.query(Image).filter(Image.filename == image_name).first()
        if not db_image:
            return JSONResponse(content={
                "image_id": None,
                "filename": image_name,
                "auto_annotations": [],
                "manual_annotations": []
            })

        auto_annotations = db.query(AutoAnnotation).filter(AutoAnnotation.image_id == db_image.id).all()
        manual_annotations = db.query(ManualAnnotation).filter(ManualAnnotation.image_id == db_image.id).all()

        return JSONResponse(content={
            "image_id": db_image.id,
            "filename": db_image.filename,
            "auto_annotations": [{
                "id": ann.id,
                "tool_type": ann.tool_type,
                "annotation_data": ann.annotation_data,
                "created_at": ann.created_at.isoformat()
            } for ann in auto_annotations],
            "manual_annotations": [{
                "id": ann.id,
                "tool_type": ann.tool_type,
                "annotation_data": ann.annotation_data,
                "created_at": ann.created_at.isoformat()
            } for ann in manual_annotations]
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving annotations by name: {str(e)}"}
        )

@app.get("/")
def read_root():
    return {"message": "AI Auto-Annotation Backend is running."}

# 调试接口：返回已注册路由列表
@app.get("/api/routes")
async def list_routes():
    routes = []
    for route in app.routes:
        path = getattr(route, "path", None)
        name = getattr(route, "name", None)
        methods = getattr(route, "methods", None)
        if path:
            routes.append({
                "path": path,
                "name": name,
                "methods": sorted(list(methods)) if methods else []
            })
    return {"count": len(routes), "routes": routes}

@app.get("/api/images/list")
async def get_images_list(db: Session = Depends(get_db)):
    """
    获取所有已上传图片的列表
    """
    try:
        images = db.query(Image).all()
        
        # 为每个图片统计标注数量
        result = []
        for image in images:
            auto_count = db.query(AutoAnnotation).filter(AutoAnnotation.image_id == image.id).count()
            manual_count = db.query(ManualAnnotation).filter(ManualAnnotation.image_id == image.id).count()
            
            result.append({
                "id": image.id,
                "filename": image.filename,
                "uploaded_at": image.uploaded_at.isoformat() if image.uploaded_at else None,
                "auto_annotation_count": auto_count,
                "manual_annotation_count": manual_count
            })
        
        return JSONResponse(content={
            "success": True,
            "images": result
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving images list: {str(e)}"}
        )

@app.get("/api/health")
async def health_check():
    """
    健康检查端点
    """
    import datetime
    return {"status": "healthy", "timestamp": datetime.datetime.utcnow().isoformat()}

# 调试接口：返回版本与环境信息
@app.get("/api/version")
async def version_info():
    import os
    return {
        "app_title": app.title,
        "version": app.version,
        "openapi_url": app.openapi_url,
        "environment": os.environ.get("ENVIRONMENT", "unknown")
    }

@app.get("/pipeline-test")
def pipeline_test():
    """
    这是一个用于测试CI/CD流水线的API接口。
    """
    return {"message": "CI/CD pipeline test successful! The code has been updated."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
