"""
使用千问大模型将用户指令解析为图像增广参数（JSON）。
"""
import json
import re
from openai import OpenAI

from .config import get_api_key, QWEN_BASE_URL, QWEN_MODEL

# 系统 prompt：让模型只输出一行 JSON
AUGMENTATION_SYSTEM_PROMPT = """你是一个图像数据增广助手。根据用户的一句中文指令，输出一行 JSON，表示要对图像执行的增广操作及参数。不要输出任何其他文字、 markdown 或说明，只输出一行合法 JSON。

可选操作及参数说明（未出现的键可省略，表示不执行该操作）：
- brightness: 亮度倍数，范围 0.5 到 2.0，默认 1.0
- contrast: 对比度倍数，范围 0.5 到 2.0，默认 1.0
- noise_std: 高斯噪声标准差，范围 0 到 0.08，默认 0.02
- rotate: 旋转角度（度），范围 -180 到 180，默认 0
- flip_horizontal: 是否水平翻转，true/false
- flip_vertical: 是否垂直翻转，true/false
- blur: 高斯模糊核大小（奇数），0 表示不模糊，范围 0 到 9，默认 0
- saturation: 饱和度倍数，范围 0.0 到 2.0，默认 1.0

示例：用户说「增加一点亮度和轻微噪声」 -> {"brightness":1.2,"noise_std":0.02}
用户说「水平翻转」 -> {"flip_horizontal":true}
用户说「逆时针转90度」 -> {"rotate":90}"""


def _keyword_fallback(instruction: str) -> dict:
    """当模型未返回有效 JSON 时，根据指令关键词生成简单参数。"""
    if not instruction or not instruction.strip():
        return _default_params()
    s = instruction.strip()
    params = {}
    # 水平翻转
    if "水平翻转" in s or "左右翻转" in s or "水平" in s and "翻" in s:
        params["flip_horizontal"] = True
    # 垂直翻转
    if "垂直翻转" in s or "上下翻转" in s:
        params["flip_vertical"] = True
    # 旋转：逆时针90 / 顺时针90 / 180 等
    if "旋转" in s or "转" in s:
        if "90" in s or "九十" in s:
            if "顺" in s or "顺时针" in s:
                params["rotate"] = -90
            else:
                params["rotate"] = 90  # 逆时针 90
        elif "180" in s or "一百八" in s:
            params["rotate"] = 180
        elif "270" in s or "二百七" in s:
            params["rotate"] = 270
    return params if params else _default_params()


def parse_instruction_to_params(instruction: str) -> dict:
    """
    调用千问 API，将用户指令解析为增广参数字典。
    若 API 未配置或调用失败，先用关键词回退，再返回默认。
    """
    api_key = get_api_key()
    raw = instruction.strip() or "不做任何增广"

    if api_key:
        try:
            client = OpenAI(api_key=api_key, base_url=QWEN_BASE_URL)
            response = client.chat.completions.create(
                model=QWEN_MODEL,
                messages=[
                    {"role": "system", "content": AUGMENTATION_SYSTEM_PROMPT},
                    {"role": "user", "content": raw},
                ],
                max_tokens=512,
                temperature=0.2,
            )
            text = (response.choices[0].message.content or "").strip()
            params = _extract_json_params(text)
            # 若解析结果为空，用关键词回退
            if not params:
                params = _keyword_fallback(raw)
            return params
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("千问解析增广指令失败: %s", e)
    return _keyword_fallback(raw)


def _extract_json_params(text: str) -> dict:
    """从模型输出中提取 JSON，兼容被 markdown 包裹的情况。"""
    if not text:
        return _default_params()
    # 尝试直接解析
    text = text.strip()
    # 去掉可能的 markdown 代码块
    for marker in ("```json", "```"):
        if marker in text:
            parts = text.split(marker)
            if len(parts) >= 2:
                text = parts[1].strip()
            break
    # 匹配可能包含嵌套的 JSON（例如数值、布尔）
    # 先尝试整段
    for candidate in (text, text.split("\n")[0].strip()):
        # 找最外层 {} 包裹的内容
        match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", candidate)
        if not match:
            match = re.search(r"\{[^{}]*\}", candidate)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    try:
        return json.loads(text.split("\n")[0].strip())
    except json.JSONDecodeError:
        pass
    return _default_params()


def _default_params() -> dict:
    """默认不执行任何增广。"""
    return {}
