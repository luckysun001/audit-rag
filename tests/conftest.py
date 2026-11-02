"""
共享测试夹具：FakeRAGEngine / 环境隔离

audit-rag 的四大审计服务（信贷 / 合规 / 风险 / 报告）都通过「注入的
rag_engine.query()」取得一段文本答案，再由各自的解析器用正则 / 关键词抽取
出结构化字段。这里用一个假的 RAG 引擎返回构造好的答案，即可在
「无需任何 API Key、不触发任何重型依赖（torch / chromadb 等）」的前提下，
确定性地测试真实的解析逻辑（思路与 bank-audit-agents 的 FakeLLM 一致）。
"""

from typing import Any, Dict, List, Optional

import pytest

from bank_audit_rag.core.vector_store import RAGResult


class FakeRAGEngine:
    """返回固定答案的假 RAG 引擎，用于测试审计服务的解析逻辑。"""

    def __init__(
        self,
        answer: str = "",
        sources: Optional[List[Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.answer = answer
        self._sources = sources or []
        self._metadata = metadata or {}
        self.last_query: Optional[str] = None
        self.last_collection: Optional[str] = None
        self.last_prompt_variables: Optional[Dict[str, Any]] = None

    def query(
        self,
        question,
        collection_name: str = "default",
        custom_prompt=None,
        prompt_variables: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None,
    ) -> RAGResult:
        self.last_query = question
        self.last_collection = collection_name
        self.last_prompt_variables = prompt_variables
        return RAGResult(
            question=question,
            answer=self.answer,
            sources=self._sources,
            context="",
            metadata={"mock_mode": False, **self._metadata},
            latency_ms=1.0,
        )


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    """隔离环境变量与全局 settings 单例，保证 mock 模式可复现。"""
    monkeypatch.delenv("ATRAG_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ATRAG_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("ATRAG_EMBEDDING_PROVIDER", raising=False)
    from bank_audit_rag.config.settings import reset_settings

    reset_settings()
    yield
    reset_settings()
