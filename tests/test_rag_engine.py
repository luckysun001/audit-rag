"""RAG 查询引擎单元测试（mock 模式，无需 LLM / 向量库）。"""

from langchain_core.documents import Document

from bank_audit_rag.config.settings import Settings
from bank_audit_rag.core.rag_engine import RAGQueryEngine
from bank_audit_rag.core.vector_store import RAGResult


def _mock_settings() -> Settings:
    return Settings(
        llm_provider="mock",
        embedding_provider="mock",
        vector_store_type="memory",
        retrieval_top_k=3,
    )


def test_mock_mode_when_unknown_provider():
    eng = RAGQueryEngine(settings=_mock_settings())
    assert eng.is_mock_mode is True


def test_query_returns_result_in_mock():
    eng = RAGQueryEngine(settings=_mock_settings())
    docs = [
        Document(page_content="贷前调查 不足", metadata={}),
        Document(page_content="合规 问题", metadata={}),
    ]
    eng.vector_store.add_documents(docs, "c")
    result = eng.query("贷前调查 是否有问题", collection_name="c")
    assert isinstance(result, RAGResult)
    assert result.metadata["mock_mode"] is True
    assert "Mock" in result.answer
    assert result.latency_ms >= 0
    assert len(result.sources) == 2


def test_build_context_format():
    eng = RAGQueryEngine(settings=_mock_settings())
    docs = [
        Document(page_content="内容A", metadata={}),
        Document(page_content="内容B", metadata={}),
    ]
    ctx = eng._build_context(docs)
    assert "[文档1]" in ctx and "[文档2]" in ctx
    assert "内容A" in ctx and "内容B" in ctx


def test_build_context_empty():
    eng = RAGQueryEngine(settings=_mock_settings())
    assert "暂无相关文档" in eng._build_context([])


def test_get_stats():
    eng = RAGQueryEngine(settings=_mock_settings())
    stats = eng.get_stats()
    assert stats["mock_mode"] is True
    assert stats["llm_provider"] == "mock"


def test_index_documents():
    eng = RAGQueryEngine(settings=_mock_settings())
    docs = [Document(page_content="x", metadata={})]
    ids = eng.index_documents(docs, "idx")
    assert ids == ["doc_0"]


def test_custom_prompt_variable_filtering():
    """验证传入的自定义 Prompt 只接收其 input_variables 声明的变量。"""
    eng = RAGQueryEngine(settings=_mock_settings())

    class FakeMsg:
        content = "FAKE_ANSWER"

    class FakeLLM:
        def invoke(self, messages):
            return FakeMsg()

    eng._llm = FakeLLM()

    class FakePrompt:
        input_variables = ["context", "question"]

        def __init__(self):
            self.captured = {}

        def format_messages(self, **kwargs):
            self.captured = kwargs
            return []

    prompt = FakePrompt()
    result = eng.query(
        "问题Q",
        collection_name="c",
        custom_prompt=prompt,
        prompt_variables={"loan_id": "L1", "extra": "should_be_filtered"},
    )
    assert result.answer == "FAKE_ANSWER"
    # loan_id / extra 不是模板变量，应被过滤掉
    assert set(prompt.captured.keys()) == {"context", "question"}
