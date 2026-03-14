"""
阶段2：调用千问图像编辑模型（图+文本 -> 图）。
"""
from __future__ import annotations

import base64
import imghdr
from typing import Any, Dict, List

import requests

from .config import get_api_key, QWEN_IMAGE_EDIT_MODEL, QWEN_IMAGE_EDIT_URL


def edit_images_with_qwen(
    image_bytes: bytes,
    description: str,
    *,
    n: int = 1,
    timeout: int = 120,
) -> List[bytes]:
    """
    使用千问图像编辑模型对单张图片进行编辑，返回编辑后的图像字节列表。
    """
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("未配置 DASHSCOPE_API_KEY，无法调用千问图像编辑模型")

    text = (description or "").strip() or "不进行任何修改"
    n = max(1, min(6, int(n or 1)))
    payload = _build_request_payload(image_bytes, text, n=n)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    resp = requests.post(QWEN_IMAGE_EDIT_URL, json=payload, headers=headers, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"图像编辑请求失败: HTTP {resp.status_code} {resp.text[:300]}")
    data = resp.json()
    if data.get("code"):
        raise RuntimeError(f"图像编辑请求失败: {data.get('code')} {data.get('message')}")

    image_urls = _extract_image_urls(data)
    if not image_urls:
        raise RuntimeError("图像编辑响应中未找到输出图片 URL")
    outputs: List[bytes] = []
    for image_url in image_urls:
        img_resp = requests.get(image_url, timeout=timeout)
        if img_resp.status_code != 200:
            raise RuntimeError(f"下载编辑结果失败: HTTP {img_resp.status_code}")
        outputs.append(img_resp.content)
    return outputs


def _build_request_payload(image_bytes: bytes, text: str, *, n: int) -> Dict[str, Any]:
    mime = _guess_mime(image_bytes)
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    image_data = f"data:{mime};base64,{b64}"
    return {
        "model": QWEN_IMAGE_EDIT_MODEL,
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"image": image_data},
                        {"text": text},
                    ],
                }
            ]
        },
        "parameters": {
            "n": n,
            "watermark": False,
            "prompt_extend": True,
        },
    }


def _extract_image_urls(data: Dict[str, Any]) -> List[str]:
    choices = (((data or {}).get("output") or {}).get("choices") or [])
    if not choices:
        return []
    content = (((choices[0] or {}).get("message") or {}).get("content") or [])
    urls: List[str] = []
    for item in content:
        if isinstance(item, dict) and item.get("image"):
            urls.append(str(item["image"]))
    return urls


def _guess_mime(image_bytes: bytes) -> str:
    kind = imghdr.what(None, h=image_bytes) or ""
    if kind == "png":
        return "image/png"
    if kind in ("jpg", "jpeg"):
        return "image/jpeg"
    if kind == "webp":
        return "image/webp"
    if kind == "gif":
        return "image/gif"
    if kind == "bmp":
        return "image/bmp"
    return "image/jpeg"
