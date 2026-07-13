"""
配置管理模块
使用 dataclass 管理应用配置，支持环境变量
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Settings:
    """应用配置"""

    # 应用信息
    app_name: str = "Bank Audit RAG"
    app_version: str = "2.0.0"
    debug: bool = False

    # LLM 配置
    llm_provider: str = "openai"
    llm_model: str = "gpt-4"
    llm_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    llm_base_url: str = field(default_factory=lambda: os.getenv("OPENAI_BASE_URL", ""))
    llm_temperature: float = 0.3
    llm_max_tokens: int = 4096

    # Embedding 配置
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-ada-002"
    embedding_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    embedding_base_url: str = field(default_factory=lambda: os.getenv("OPENAI_BASE_URL", ""))

    # 向量存储配置
    vector_store_type: str = "chroma"
    vector_store_path: str = "./data/chroma"
    vector_store_host: str = "localhost"
    vector_store_port: int = 8000

    # 文档处理配置
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_file_size_mb: int = 50

    # 检索配置
    retrieval_top_k: int = 5
    retrieval_score_threshold: float = 0.5

    # 日志配置
    log_level: str = "INFO"
    log_format: str = "structured"
    log_file: Optional[str] = None

    # API 配置
    api_host: str = "0.0.0.0"
    api_port: int = 8080

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
