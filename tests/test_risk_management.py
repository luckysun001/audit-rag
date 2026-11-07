"""风险管理服务单元测试（注入 FakeRAGEngine，验证解析与等级映射）。"""

from bank_audit_rag.core.risk_management import CreditRiskAssessmentResult, RiskManagementService
from tests.conftest import FakeRAGEngine

RISK_ANSWER = """
财务风险：80分。经营风险：75分。信用记录：85分。担保能力：70分。行业风险：78分。
总体评分：65分。
存在偿债风险隐患
该风险属于中等程度。

整改建议
1. 压降授信额度
2. 增加担保措施
"""


def test_credit_risk_assessment_parse():
    svc = RiskManagementService(rag_engine=FakeRAGEngine(RISK_ANSWER))
    r: CreditRiskAssessmentResult = svc.assess_credit_risk("甲公司", "企业", "制造", 2_000_000)
    assert r.customer_name == "甲公司"
    assert r.industry == "制造"
    assert r.financial_risk_score == 80.0
    assert r.operational_risk_score == 75.0
    assert r.credit_history_score == 85.0
    assert r.guarantee_capacity_score == 70.0
    assert r.industry_risk_score == 78.0
    assert r.total_score == 65.0
    assert r.risk_level == "中风险"
    assert len(r.risk_points) >= 1
    assert r.risk_points[0]["severity"] == "中"
    assert len(r.risk_mitigation_suggestions) >= 2


def test_determine_risk_level_boundaries():
    svc = RiskManagementService(rag_engine=FakeRAGEngine(""))
    mapping = {
        85: "低风险",
        84: "中低风险",
        70: "中低风险",
        55: "中风险",
        40: "中高风险",
        39: "高风险",
        0: "高风险",
    }
    for score, expected in mapping.items():
        assert svc._determine_risk_level(score) == expected


def test_batch_risk_assessment():
    svc = RiskManagementService(rag_engine=FakeRAGEngine(RISK_ANSWER))
    customers = [
        {"name": "A", "type": "企业", "industry": "制造", "credit_limit": 1_000_000},
        {"name": "B", "type": "企业", "industry": "零售", "credit_limit": 500_000},
        {"name": "C", "type": "个人", "industry": "其他", "credit_limit": 100_000},
    ]
    results = svc.batch_risk_assessment(customers)
    assert len(results) == 3
    assert all(isinstance(r, CreditRiskAssessmentResult) for r in results)


def test_generate_risk_alerts_empty():
    svc = RiskManagementService(rag_engine=FakeRAGEngine(""))
    assert svc.generate_risk_alerts() == []
