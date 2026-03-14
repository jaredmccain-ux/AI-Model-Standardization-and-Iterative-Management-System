"""
智能体数据增广 - API Key 配置
优先从环境变量 DASHSCOPE_API_KEY 读取，否则从项目根目录的 .augmentation_api_key 文件读取。
"""
import os
from pathlib import Path

# 后端项目根目录（augmentation 包的上层目录）
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_DOTENV_FILES = (
    _BACKEND_ROOT / ".env.local",
    _BACKEND_ROOT / ".env.production",
    _BACKEND_ROOT / ".env",
)
_API_KEY_FILE = _BACKEND_ROOT / ".augmentation_api_key"
# Windows 下可能被保存为 .augmentation_api_key.txt
_API_KEY_FILE_ALT = _BACKEND_ROOT / ".augmentation_api_key.txt"


def _load_env_from_project_files() -> list[str]:
    """
    从项目根目录自动加载 .env 文件（不覆盖已存在的环境变量）。
    支持 .env / .env.production / .env.local。
    """
    loaded = []
    for path in _DOTENV_FILES:
        if not path.exists():
            continue
        try:
            for raw_line in path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[len("export "):].strip()
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if not key:
                    continue
                # 去掉包裹引号
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    value = value[1:-1]
                # 不覆盖进程中已设置的变量
                os.environ.setdefault(key, value)
            loaded.append(path.name)
        except Exception:
            # 环境加载失败时保持静默，避免影响服务启动
            pass
    return loaded


_LOADED_ENV_FILES = _load_env_from_project_files()

# 千问 API 兼容地址
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "qwen-turbo"

# 两阶段增广流水线配置
# 阶段1：文本规范化（Chat Completions）
QWEN_TEXT_MODEL = os.environ.get("AUGMENTATION_TEXT_MODEL", QWEN_MODEL).strip() or QWEN_MODEL
# 阶段2：图像编辑（图+文本 -> 图）
QWEN_IMAGE_EDIT_MODEL = os.environ.get("AUGMENTATION_IMAGE_MODEL", "qwen-image-2.0").strip() or "qwen-image-2.0"
QWEN_IMAGE_EDIT_URL = os.environ.get(
    "AUGMENTATION_IMAGE_URL",
    "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
).strip() or "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"


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
        "loaded_env_files": _LOADED_ENV_FILES,
        "env_var_set": bool(os.environ.get("DASHSCOPE_API_KEY", "").strip()),
        "text_model": QWEN_TEXT_MODEL,
        "image_edit_model": QWEN_IMAGE_EDIT_MODEL,
        "image_edit_url": QWEN_IMAGE_EDIT_URL,
        "key_file_primary_exists": _API_KEY_FILE.exists(),
        "key_file_primary_path": str(_API_KEY_FILE),
        "key_file_alt_exists": _API_KEY_FILE_ALT.exists(),
    }
