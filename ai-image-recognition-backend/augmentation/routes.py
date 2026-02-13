"""
智能体数据增广 API：接收图片+指令，返回增广后的图片列表。
"""
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any

from .config import is_configured, get_diagnostic
from .llm import parse_instruction_to_params
from .apply import apply_augmentation
import base64
import re
import time

router = APIRouter(
    prefix="/api/augmentation",
    tags=["augmentation"],
    responses={404: {"description": "Not found"}},
)


@router.get("/status")
async def augmentation_status():
    """
    检查 API Key 是否已配置。若 api_configured 为 false，则不会调用千问，用量不会增加。
    用于排查「模型用量未显示调用」的问题。
    """
    return JSONResponse(content=get_diagnostic())


def _params_to_slug(params: Dict[str, Any]) -> str:
    """将增广参数转为见名知义的短标签，用于文件名。"""
    parts = []
    if _truthy(params.get("flip_horizontal")):
        parts.append("水平翻转")
    if _truthy(params.get("flip_vertical")):
        parts.append("垂直翻转")
    r = params.get("rotate")
    if r is not None and float(r) != 0:
        a = int(round(float(r)))
        if a == 90:
            parts.append("逆时针90度")
        elif a == -90:
            parts.append("顺时针90度")
        elif a == 180:
            parts.append("旋转180度")
        else:
            parts.append(f"旋转{a}度")
    if params.get("noise_std") and float(params["noise_std"]) > 0:
        parts.append("加噪")
    if params.get("brightness") and float(params["brightness"]) != 1.0:
        parts.append("调亮度")
    if params.get("contrast") and float(params["contrast"]) != 1.0:
        parts.append("调对比度")
    if params.get("saturation") and float(params["saturation"]) != 1.0:
        parts.append("调饱和度")
    if params.get("blur") and int(params["blur"]) > 0:
        parts.append("模糊")
    if not parts:
        return "增广"
    return "_".join(parts)


def _truthy(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "是")
    return bool(v)


def _sanitize_filename(original_name: str, params: Dict[str, Any], index: int = 0) -> str:
    """生成见名知义且不重复的增广文件名。"""
    base = re.sub(r"\.[^.]+$", "", original_name or "image")
    slug = _params_to_slug(params)
    # 去掉可能影响文件系统的字符
    slug = re.sub(r'[<>:"/\\|?*]', "_", slug)
    slug = slug.strip("._ ") or "增广"
    # 加短时间戳避免同一张图同一种增广多次时重名
    unique = int(time.time() * 1000) % 100000
    if index > 0:
        return f"{base}_{slug}_{unique}_{index}.jpg"
    return f"{base}_{slug}_{unique}.jpg"


@router.post("/run")
async def run_augmentation(
    instruction: str = Form(..., description="增广指令，如：增加光照变化、添加轻微噪声"),
    images: List[UploadFile] = File(..., description="要增广的图片"),
):
    """
    根据指令对选中的图片进行智能增广，返回增广后的图片（base64）及文件名。
    """
    if not images:
        raise HTTPException(status_code=400, detail="请至少上传一张图片")

    # 解析指令为参数（未配置 API Key 时使用空参数，相当于不增广或仅做默认处理）
    params = parse_instruction_to_params(instruction or "不做任何增广")

    results = []
    for i, f in enumerate(images):
        try:
            raw = await f.read()
            aug_bytes = apply_augmentation(raw, params)
            b64 = base64.b64encode(aug_bytes).decode("utf-8")
            name = _sanitize_filename(f.filename or "image.jpg", params, index=i)
            results.append({"filename": name, "image_base64": b64})
        except Exception as e:
            results.append({
                "filename": f.filename or "image.jpg",
                "error": str(e),
                "image_base64": None,
            })

    return JSONResponse(content={
        "success": True,
        "instruction": instruction,
        "params_used": params,
        "augmented": results,
        "api_configured": is_configured(),
    })
