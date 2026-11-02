"""API 层单元测试（FastAPI TestClient，mock 模式下运行）。

注意：bank_audit_rag.api 包在导入时即构建 app（api/__init__.py 的
create_app()），并通过 lifespan 注入 DocumentProcessor / 各审计服务。
无 API Key 时这些服务自动降级为 mock 模式，因此端到端测试无需任何外部依赖。
"""

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from bank_audit_rag.api import app, create_app  # noqa: E402


def test_create_app_returns_app():
    a = create_app()
    assert a is not None
    assert a.title == "Bank Audit RAG Service"


def test_health_endpoint():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert "services" in body
    assert body["services"]["credit_audit_service"] is True


def test_loan_review_endpoint():
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/credit/loan-review",
            json={
                "loan_id": "L-2024-001",
                "customer_name": "测试客户",
                "loan_amount": 1_000_000,
                "loan_term": 12,
                "guarantee_type": "信用",
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["loan_id"] == "L-2024-001"
    assert body["customer_name"] == "测试客户"


def test_query_endpoint_echoes_question():
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/query",
            json={"question": "信贷三查包括哪些环节？"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "信贷三查包括哪些环节？" in body["question"]


def test_report_generate_endpoint():
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/report/generate",
            json={
                "project_name": "专项审计X",
                "audited_unit": "某分行",
                "audit_period": "2024",
                "audit_type": "专项审计",
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["project_name"] == "专项审计X"
    assert body["report_id"].startswith("RPT-")
