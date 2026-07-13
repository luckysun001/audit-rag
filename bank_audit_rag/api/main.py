"""
Bank Audit RAG API Module
"""

from bank_audit_rag.config.settings import get_settings
from bank_audit_rag.utils.logger import get_logger

logger = get_logger(__name__)


def create_app():
    """创建 FastAPI 应用"""
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
    except ImportError:
        logger.warning("FastAPI not available, API server disabled")
        return None

    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="银行审计部智能检索问答系统 API",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health_check():
        """健康检查"""
        return {"status": "healthy", "version": settings.app_version}

    @app.get("/api/v1/stats")
    async def get_stats():
        """系统统计信息"""
        from bank_audit_rag.core.rag_engine import RAGQueryEngine
        engine = RAGQueryEngine()
        return engine.get_stats()

    logger.info("api_app_created", extra={"app_name": settings.app_name})
    return app


# 全局 app 实例
app = create_app()

__all__ = ["app", "create_app"]
