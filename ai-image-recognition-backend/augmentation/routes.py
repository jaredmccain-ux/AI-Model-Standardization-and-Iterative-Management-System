"""
智能体数据增广 API：接收图片+指令，返回增广后的图片列表。
"""
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any

from .config import is_configured, get_diagnostic, QWEN_IMAGE_EDIT_MODEL, QWEN_TEXT_MODEL
from .llm import parse_instruction_to_params, normalize_instruction_to_description
from .apply import apply_augmentation
from .image_edit import edit_images_with_qwen
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


def _slugify_text(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return "增广"
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[，。；：、,.!！?？()（）\[\]{}]+", "_", text)
    text = re.sub(r'[<>:"/\\|?*]+', "_", text)
    text = re.sub(r"_+", "_", text).strip("._ ")
    # 限制长度，避免文件名过长
    return (text[:24] or "增广")


def _parse_requested_count(instruction: str) -> int:
    """
    从用户指令中提取期望生成张数，默认 1，最大 6。
    示例：生成2张 / 来三张 / 出两张图
    """
    s = (instruction or "").strip()
    if not s:
        return 1
    # 阿拉伯数字：2张、3个结果
    m = re.search(r"(\d+)\s*(?:张|个|幅)", s)
    if m:
        try:
            return max(1, min(6, int(m.group(1))))
        except Exception:
            pass
    # 中文数字
    zh_map = {"一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6}
    m2 = re.search(r"(一|两|二|三|四|五|六)\s*(?:张|个|幅)", s)
    if m2:
        return zh_map.get(m2.group(1), 1)
    return 1


def _sanitize_filename(original_name: str, slug_source: Any, index: int = 0) -> str:
    """生成见名知义且不重复的增广文件名，统一加 aug_ 前缀以区分原图。"""
    base = re.sub(r"\.[^.]+$", "", original_name or "image")
    if isinstance(slug_source, dict):
        slug = _params_to_slug(slug_source)
    else:
        slug = _slugify_text(str(slug_source or "增广"))
    # 去掉可能影响文件系统的字符
    slug = re.sub(r'[<>:"/\\|?*]', "_", slug)
    slug = slug.strip("._ ") or "增广"
    # 加短时间戳避免同一张图同一种增广多次时重名
    unique = int(time.time() * 1000) % 100000
    # 统一 aug_ 前缀，便于在文件列表和导出中区分原图与增广图
    if index > 0:
        return f"aug_{base}_{slug}_{unique}_{index}.jpg"
    return f"aug_{base}_{slug}_{unique}.jpg"


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

    raw_instruction = instruction or "不做任何增广"
    # 阶段1：文本规范化（qwen-turbo）
    description = normalize_instruction_to_description(raw_instruction)
    requested_n = _parse_requested_count(raw_instruction)
    # qwen-image-edit 基础模型仅支持单张输出
    effective_n = requested_n
    tips: List[str] = []
    model_lower = (QWEN_IMAGE_EDIT_MODEL or "").lower()
    if model_lower == "qwen-image-edit" and requested_n > 1:
        effective_n = 1
        tips.append(
            f"当前模型 {QWEN_IMAGE_EDIT_MODEL} 仅支持单张输出，已按 1 张处理。若需多张请切换到 qwen-image-2.0 / qwen-image-2.0-pro / qwen-image-edit-max。"
        )

    results = []
    fallback_count = 0
    for i, f in enumerate(images):
        try:
            raw = await f.read()
            method = "qwen-image"
            try:
                # 阶段2：图+描述 -> 图（qwen-image-2.0）
                aug_bytes_list = edit_images_with_qwen(raw, description, n=effective_n)
                slug_source: Any = description
            except Exception as e:
                # 回退：沿用现有参数化 OpenCV 流程，避免接口整体失败
                params = parse_instruction_to_params(raw_instruction)
                aug_bytes = apply_augmentation(raw, params)
                aug_bytes_list = [aug_bytes]
                slug_source = params
                method = "opencv-fallback"
                fallback_count += 1
                fallback_error = str(e)
                if effective_n > 1:
                    tips.append(
                        f"第 {i + 1} 张输入图调用图像编辑模型失败，已回退到传统增广，仅返回 1 张结果。"
                    )

            if method == "qwen-image" and len(aug_bytes_list) < effective_n:
                tips.append(
                    f"第 {i + 1} 张输入图请求 {effective_n} 张，模型实际返回 {len(aug_bytes_list)} 张。"
                )

            for j, aug_bytes in enumerate(aug_bytes_list):
                b64 = base64.b64encode(aug_bytes).decode("utf-8")
                # j+1 是同一输入图的变体索引；i+1 避免和原始输入索引冲突
                name = _sanitize_filename(f.filename or "image.jpg", slug_source, index=(i + 1) * 100 + (j + 1))
                item = {
                    "filename": name,
                    "image_base64": b64,
                    "method": method,
                    "source_index": i,
                    "variant_index": j,
                }
                if method == "opencv-fallback":
                    item["fallback_reason"] = fallback_error
                results.append(item)
        except Exception as e:
            results.append({
                "filename": f.filename or "image.jpg",
                "error": str(e),
                "image_base64": None,
            })

    return JSONResponse(content={
        "success": True,
        "instruction": instruction,
        "description_used": description,
        "requested_count": requested_n,
        "effective_count": effective_n,
        "text_model_used": QWEN_TEXT_MODEL,
        "image_model_used": QWEN_IMAGE_EDIT_MODEL,
        "augmented": results,
        "fallback_count": fallback_count,
        "tips": tips,
        "api_configured": is_configured(),
    })
