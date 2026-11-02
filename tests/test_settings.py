"""配置中心（settings）单元测试。"""

from bank_audit_rag.config.settings import Settings, get_settings, reset_settings


def test_defaults():
    s = Settings()
    assert s.llm_provider == "openai"
    assert s.chunk_size == 1000
    assert s.chunk_overlap == 200
    assert s.retrieval_top_k == 5
    assert s.app_version == "2.0.0"
    assert s.vector_store_type == "chroma"


def test_to_dict_excludes_private():
    s = Settings()
    d = s.to_dict()
    assert "app_name" in d
    assert all(not k.startswith("_") for k in d)


def test_get_missing_returns_default():
    s = Settings()
    assert s.get("nonexistent_key", "fallback") == "fallback"
    assert s.get("app_name") == "Bank Audit RAG"


def test_get_settings_singleton():
    reset_settings()
    a = get_settings()
    b = get_settings()
    assert a is b
    reset_settings()
    c = get_settings()
    assert c is not a


def test_env_int_float_fallback(monkeypatch):
    monkeypatch.delenv("ATRAG_RETRIEVER_TOP_K", raising=False)
    reset_settings()
    s = Settings()
    assert isinstance(s.retrieval_top_k, int)

    # 非法值应回退到默认值而非抛异常
    monkeypatch.setenv("ATRAG_RETRIEVER_TOP_K", "not-a-number")
    reset_settings()
    s2 = Settings()
    assert s2.retrieval_top_k == 5
