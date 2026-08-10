"""
配置管理模块
使用 dataclass 管理应用配置，支持环境变量
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

try:
    from dotenv import load_dotenv

    load_dotenv()  # 载入项目根目录 .env，使 .env.example 中的 ATRAG_* 配置生效
except Exception:
    # 无 python-dotenv 时，手动解析简单的 KEY=VALUE 形式 .env（不引入新依赖）
    _dotenv_path = os.path.join(os.getcwd(), ".env")
    if os.path.isfile(_dotenv_path):
        with open(_dotenv_path, "r", encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if not _line or _line.startswith("#") or "=" not in _line:
                    continue
                _k, _, _v = _line.partition("=")
                _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
                os.environ.setdefault(_k, _v)


def _env_int(name: str, default: int) -> int:
    """读取整型环境变量，解析失败时回退默认值。"""
    val = os.getenv(name)
    if val is None:
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    """读取浮点型环境变量，解析失败时回退默认值。"""
    val = os.getenv(name)
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


@dataclass
class Settings:
    """应用配置"""

    # 应用信息
    app_name: str = "Bank Audit RAG"
    app_version: str = "2.0.0"
    debug: bool = False

    # LLM 配置
    llm_provider: str = "openai"
    llm_model: str = field(default_factory=lambda: os.getenv("ATRAG_LLM_MODEL", "gpt-4"))
    llm_api_key: str = field(default_factory=lambda: os.getenv("ATRAG_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY", ""))
    llm_base_url: str = field(default_factory=lambda: os.getenv("ATRAG_OPENAI_BASE_URL") or os.getenv("OPENAI_BASE_URL", ""))
    llm_temperature: float = field(default_factory=lambda: _env_float("ATRAG_LLM_TEMPERATURE", 0.3))
    llm_max_tokens: int = field(default_factory=lambda: _env_int("ATRAG_LLM_MAX_TOKENS", 4096))

    # Embedding 配置
    embedding_provider: str = "openai"
    embedding_model: str = field(default_factory=lambda: os.getenv("ATRAG_EMBEDDING_MODEL", "text-embedding-ada-002"))
    embedding_api_key: str = field(default_factory=lambda: os.getenv("ATRAG_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY", ""))
    embedding_base_url: str = field(default_factory=lambda: os.getenv("ATRAG_OPENAI_BASE_URL") or os.getenv("OPENAI_BASE_URL", ""))

    # 向量存储配置
    vector_store_type: str = "chroma"
    vector_store_path: str = "./data/chroma"
    vector_store_host: str = "localhost"
    vector_store_port: int = 8000

    # 文档处理配置
    chunk_size: int = field(default_factory=lambda: _env_int("ATRAG_DOCUMENT_CHUNK_SIZE", 1000))
    chunk_overlap: int = field(default_factory=lambda: _env_int("ATRAG_DOCUMENT_CHUNK_OVERLAP", 200))
    max_file_size_mb: int = 50

    # 检索配置
    retrieval_top_k: int = field(default_factory=lambda: _env_int("ATRAG_RETRIEVER_TOP_K", 5))
    retrieval_score_threshold: float = field(default_factory=lambda: _env_float("ATRAG_RETRIEVER_SCORE_THRESHOLD", 0.5))

    # 日志配置
    log_level: str = field(default_factory=lambda: os.getenv("ATRAG_LOG_LEVEL", "INFO"))
    log_format: str = "structured"
    log_file: Optional[str] = None

    # API 配置
    api_host: str = field(default_factory=lambda: os.getenv("ATRAG_API_HOST", "0.0.0.0"))
    api_port: int = field(default_factory=lambda: _env_int("ATRAG_API_PORT", 8080))

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return getattr(self, key, default)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            k: v for k, v in self.__dict__.items()
            if not k.startswith("_")
        }


# 全局配置单例
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """获取全局配置实例（单例模式）"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """重置配置单例（用于测试）"""
    global _settings
    _settings = None
