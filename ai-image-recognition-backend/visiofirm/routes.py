from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Optional
import json
import os
import uuid
import tempfile
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from fastapi import Depends

from database import get_db
from ai_models import ai_service
from .models import VisioFirmAnnotation
from . import model_registry

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
    """使用AI模型进行图像自动标注"""
    try:
        temp_file_path = f"temp_{uuid.uuid4()}.jpg"
        with open(temp_file_path, "wb") as buffer:
            buffer.write(await image.read())

        category_list = []
        if categories:
            try:
                category_list = json.loads(categories)
            except json.JSONDecodeError:
                category_list = []

        annotations = []
        if tool == "object_detection":
            detections = ai_service.detect_objects(temp_file_path, model_name=model)
            for det in detections:
                class_name = det["class_name"]
                if category_list and class_name not in category_list:
                    continue
                x_percent, y_percent, w_percent, h_percent = det["bbox_percent"]
                annotations.append({
                    "type": "bbox",
                    "label": class_name,
                    "confidence": det["confidence"],
                    "bbox": {
                        "x": x_percent * 100,
                        "y": y_percent * 100,
                        "width": w_percent * 100,
                        "height": h_percent * 100
                    }
                })
        elif tool == "image_classification":
            classifications = ai_service.classify_image(temp_file_path, model_name=model)
            for cls in classifications:
                annotations.append({
                    "type": "classification",
                    "label": cls["class_name"],
                    "confidence": cls["confidence"]
                })
        elif tool == "image_segmentation":
            try:
                segments = ai_service.segment_objects(temp_file_path, model_name=model)
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

        db_annotation = VisioFirmAnnotation(
            filename=image.filename,
            tool_type=tool,
            model=model,
            annotation_data=annotations,
            created_at=datetime.utcnow()
        )
        db.add(db_annotation)
        db.commit()

        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

        return JSONResponse(content={
            "success": True,
            "annotations": annotations,
            "message": f"使用AI成功标注了{len(annotations)}个对象"
        })

    except ValueError as e:
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        import traceback
        print(f"标注过程中出错: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"标注过程中出错: {str(e)}")


BUILTIN_MODELS = [
    {"id": "YOLO", "name": "YOLOv8-nano", "task": "detection", "source": "builtin", "isLocal": True, "description": "轻量级目标检测", "accuracy": "37.3% mAP", "speed": "极快"},
    {"id": "FasterRCNN", "name": "Faster R-CNN", "task": "detection", "source": "builtin", "isLocal": True, "description": "高精度目标检测", "accuracy": "42.1% mAP", "speed": "慢速"},
    {"id": "SSD", "name": "SSD", "task": "detection", "source": "builtin", "isLocal": True, "description": "SSD 目标检测", "accuracy": "中", "speed": "中等"},
    {"id": "ResNet", "name": "ResNet50", "task": "classification", "source": "builtin", "isLocal": True, "description": "通用图像分类", "accuracy": "76.2%", "speed": "快速"},
    {"id": "EfficientNet", "name": "EfficientNet", "task": "classification", "source": "builtin", "isLocal": True, "description": "高效图像分类", "accuracy": "84.5%", "speed": "中等"},
    {"id": "YOLO-Seg", "name": "YOLOv8-Seg", "task": "segmentation", "source": "builtin", "isLocal": True, "description": "实例分割", "accuracy": "中高", "speed": "快速"},
    {"id": "MaskRCNN", "name": "Mask R-CNN", "task": "segmentation", "source": "builtin", "isLocal": True, "description": "实例分割", "accuracy": "中高", "speed": "中等"},
    {"id": "SAM", "name": "SAM", "task": "segmentation", "source": "builtin", "isLocal": True, "description": "需本地权重", "accuracy": "高", "speed": "中等"},
]

BUILTIN_DOWNLOAD_ALIAS = {
    "YOLO": "yolov8n",
    "FasterRCNN": "yolov8s",
    "SSD": "yolov8m",
    "ResNet": "yolov8n-cls",
    "EfficientNet": "yolov8s-cls",
    "YOLO-Seg": "yolov8n-seg",
    "MaskRCNN": "yolov8s-seg",
    "SAM": "yolov8m-seg",
}


def _resolve_download_target(model_id: str):
    if model_id.startswith("user:"):
        user_path = model_registry.get_user_model_path(model_id)
        if not user_path:
            raise ValueError("用户模型不存在或文件已丢失")
        return {"kind": "user", "resolved_id": model_id, "path": user_path}

    catalog = model_registry.load_catalog()
    catalog_ids = {e.get("id") for e in catalog}
    if model_id in catalog_ids:
        return {"kind": "catalog", "resolved_id": model_id, "path": None}

    alias_id = BUILTIN_DOWNLOAD_ALIAS.get(model_id)
    if alias_id and alias_id in catalog_ids:
        return {"kind": "catalog", "resolved_id": alias_id, "path": None}

    builtin_entry = next((m for m in BUILTIN_MODELS if m.get("id") == model_id), None)
    if builtin_entry:
        task = (builtin_entry.get("task") or "detection").lower()
        fallback = next((e.get("id") for e in catalog if (e.get("task") or "").lower() == task), None)
        if fallback:
            return {"kind": "catalog", "resolved_id": fallback, "path": None}

    raise ValueError(f"该模型暂无可下载来源: {model_id}")


@router.get("/models")
async def get_available_models():
    """获取可用模型列表：内置 + 已下载目录模型 + 用户上传模型"""
    result = []
    for m in BUILTIN_MODELS:
        result.append({**m})
    catalog = model_registry.load_catalog()
    for e in catalog:
        is_local = model_registry.is_catalog_model_local(e["id"])
        result.append({
            "id": e["id"],
            "name": e.get("name", e["id"]),
            "task": e.get("task", "detection"),
            "source": "catalog",
            "isLocal": is_local,
            "description": e.get("description", ""),
            "accuracy": e.get("accuracy", ""),
            "speed": e.get("speed", ""),
            "size": e.get("size", ""),
        })
    for e in model_registry.load_user_metadata():
        result.append({
            "id": e["id"],
            "name": e.get("name", e["id"]),
            "task": e.get("task", "detection"),
            "source": "user",
            "isLocal": True,
            "description": "用户上传模型",
        })
    return JSONResponse(content=result)


@router.get("/models/catalog")
async def get_models_catalog():
    """获取可下载模型目录（含是否已下载到本地）"""
    catalog = model_registry.load_catalog()
    out = []
    for e in catalog:
        out.append({
            **e,
            "isLocal": model_registry.is_catalog_model_local(e["id"]),
        })
    return JSONResponse(content=out)


@router.post("/models/upload")
async def upload_model(
    file: UploadFile = File(...),
    name: str = Form(...),
    task: str = Form(...),
):
    """上传用户自定义模型（.pt/.pth/.onnx）"""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in model_registry.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"仅支持格式: {', '.join(model_registry.ALLOWED_EXTENSIONS)}")
    content = await file.read()
    if len(content) > model_registry.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="模型文件不得超过 500MB")
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        entry = model_registry.add_user_model(tmp_path, name.strip(), task)
        return JSONResponse(content={"success": True, "model": entry})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")
    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


@router.post("/models/download")
async def download_model_to_local(model_id: str = Form(...)):
    """将模型下载到服务器本地。支持内置/目录/用户模型。"""
    if not model_id or not model_id.strip():
        raise HTTPException(status_code=400, detail="请提供 model_id")
    model_id = model_id.strip()
    try:
        target = _resolve_download_target(model_id)
        resolved_id = target["resolved_id"]
        if target["kind"] == "user":
            path = target["path"]
        else:
            path = model_registry.download_catalog_model(resolved_id)
            try:
                entry = next((e for e in model_registry.load_catalog() if e.get("id") == resolved_id), None)
                task = (entry or {}).get("task", "detection")
                if task == "segmentation":
                    ai_service._get_segmentation_model(resolved_id)
                elif task == "classification":
                    pass
                else:
                    ai_service._get_detection_model(resolved_id)
            except Exception as warmup_err:
                print(f"模型预热失败: model_id={resolved_id}, err={warmup_err}")
        return JSONResponse(content={
            "success": True,
            "path": str(path),
            "model_id": model_id,
            "resolved_model_id": resolved_id,
            "isLocal": True,
        })
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        msg = str(e) or "下载失败"
        raise HTTPException(status_code=500, detail=f"下载失败: {msg}")


@router.get("/models/{model_id}/file")
async def get_model_file(model_id: str):
    """返回已下载的模型文件流，供前端「另存为」到用户选择的路径。"""
    if not model_id or not model_id.strip():
        raise HTTPException(status_code=400, detail="请提供 model_id")
    model_id = model_id.strip()
    try:
        target = _resolve_download_target(model_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if target["kind"] == "user":
        path = target["path"]
    else:
        path = model_registry.get_downloaded_model_path(target["resolved_id"])
        if not path:
            raise HTTPException(
                status_code=404,
                detail="该模型尚未下载到服务器，请先点击「下载到本地」将模型下载到服务器后再保存到电脑。",
            )
    if not path.exists():
        raise HTTPException(status_code=404, detail="模型文件不存在或已被删除。")
    return FileResponse(
        path=str(path),
        filename=path.name,
        media_type="application/octet-stream",
    )
