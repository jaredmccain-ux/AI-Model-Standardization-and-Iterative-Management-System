"""
智能体数据增广 - API Key 配置
优先从环境变量 DASHSCOPE_API_KEY 读取，否则从项目根目录的 .augmentation_api_key 文件读取。
"""
import os
from pathlib import Path

# 后端项目根目录（augmentation 包的上层目录）
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_API_KEY_FILE = _BACKEND_ROOT / ".augmentation_api_key"
# Windows 下可能被保存为 .augmentation_api_key.txt
_API_KEY_FILE_ALT = _BACKEND_ROOT / ".augmentation_api_key.txt"

# 千问 API 兼容地址
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "qwen-turbo"


def _read_key_from_file(path: Path) -> str:
    """从文件中读取第一行非空、非注释的内容作为 Key。"""
    try:
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line
    except Exception:
        pass
    return ""


def get_api_key() -> str:
    """获取千问 API Key：环境变量优先，否则读 .augmentation_api_key 文件。"""
    key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    if key:
        return key
    for path in (_API_KEY_FILE, _API_KEY_FILE_ALT):
        if path.exists():
            key = _read_key_from_file(path)
            if key:
                return key
    return ""


def is_configured() -> bool:
    """是否已配置 API Key。"""
    return bool(get_api_key())


def get_diagnostic() -> dict:
    """返回 Key 配置诊断信息（不包含 Key 内容），便于排查未调用模型的问题。"""
    return {
        "api_configured": is_configured(),
        "env_var_set": bool(os.environ.get("DASHSCOPE_API_KEY", "").strip()),
        "key_file_primary_exists": _API_KEY_FILE.exists(),
        "key_file_primary_path": str(_API_KEY_FILE),
        "key_file_alt_exists": _API_KEY_FILE_ALT.exists(),
    }
