"""向量存储与 Embedding 服务单元测试（内存模式，无需 chroma / API Key）。"""

import math

from langchain_core.documents import Document

from bank_audit_rag.config.settings import Settings
from bank_audit_rag.core.vector_store import EmbeddingService, VectorStoreService


def _memory_settings() -> Settings:
    return Settings(
        vector_store_type="memory",
        embedding_provider="mock",
        retrieval_top_k=3,
    )


def test_embedding_mock_deterministic_and_normalized():
    es = EmbeddingService(_memory_settings())
    v1 = es.embed_text("银行 审计")
    v2 = es.embed_text("银行 审计")
    assert v1 == v2
    assert len(v1) == 128
    norm = math.sqrt(sum(x * x for x in v1))
    assert abs(norm - 1.0) < 1e-6


def test_embedding_mock_difference():
    es = EmbeddingService(_memory_settings())
    assert es.embed_text("a") != es.embed_text("b")


def test_embed_texts_batch_consistent():
    es = EmbeddingService(_memory_settings())
    vecs = es.embed_texts(["x", "x"])
    assert len(vecs) == 2
    assert vecs[0] == vecs[1]


def test_vector_store_memory_add_and_stats():
    vs = VectorStoreService(_memory_settings())
    docs = [
        Document(page_content="贷款三查贷前调查", metadata={"i": 0}),
        Document(page_content="合规检查反洗钱", metadata={"i": 1}),
    ]
    ids = vs.add_documents(docs, "col1")
    assert ids == ["doc_0", "doc_1"]
    stats = vs.get_collection_stats("col1")
    assert stats["document_count"] == 2
    assert stats["store_type"] == "memory"


def test_vector_store_memory_similarity():
    vs = VectorStoreService(_memory_settings())
    docs = [
        Document(page_content="贷前调查 不完整 风险", metadata={}),
        Document(page_content="财务报表 真实性 核查", metadata={}),
    ]
    vs.add_documents(docs, "col2")
    res = vs.similarity_search("贷前调查", collection_name="col2", top_k=1)
    assert len(res) >= 1
    assert "贷前调查" in res[0].page_content
