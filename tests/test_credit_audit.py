"""信贷审计服务单元测试（注入 FakeRAGEngine，验证解析逻辑）。"""

from bank_audit_rag.core.credit_audit import (
    ContractComplianceResult,
    CreditAuditService,
    LoanReviewResult,
)
from tests.conftest import FakeRAGEngine

LOAN_ANSWER = """
贷前调查：92分。贷中审查：88分。贷后检查：85分。风险识别：90分。
总体信贷三查基本合规。

一、审计发现
发现贷款用途监控不足
该问题属于中风险，需持续关注。
发现客户收入证明不完整
该问题属于高风险，应重点整改。

整改建议
1. 加强贷后资金流向监测
2. 补充收入证明材料
"""

CONTRACT_ANSWER = """
要素完整性：95分。利率合规性：90分。担保合规性：88分。禁止性规定：92分。
总体合同合规性良好。

发现存在违规条款
合同中约定以贷还贷，违反监管规定。

整改建议
1. 删除以贷还贷条款
2. 重新审查担保手续
"""


def test_loan_three_review_parse():
    svc = CreditAuditService(rag_engine=FakeRAGEngine(LOAN_ANSWER))
    r: LoanReviewResult = svc.loan_three_review_check("L1", "张三", 1_000_000)
    assert r.loan_id == "L1"
    assert r.customer_name == "张三"
    assert r.pre_loan_score == 92.0
    assert r.in_loan_score == 88.0
    assert r.post_loan_score == 85.0
    assert r.risk_identification_score == 90.0
    assert abs(r.total_score - (92 + 88 + 85 + 90) / 4) < 1e-6
    assert r.risk_level == "低风险"
    assert len(r.issues) >= 2
    assert len(r.high_risk_issues) == 1
    assert len(r.medium_risk_issues) == 1
    assert len(r.rectification_suggestions) >= 2


def test_contract_compliance_parse():
    svc = CreditAuditService(rag_engine=FakeRAGEngine(CONTRACT_ANSWER))
    r: ContractComplianceResult = svc.contract_compliance_check(
        "C1", "流动资金借款合同", 500_000, "2024-01-01"
    )
    assert r.contract_id == "C1"
    assert r.element_integrity_score == 95.0
    assert r.rate_compliance_score == 90.0
    assert r.guarantee_compliance_score == 88.0
    assert r.prohibition_compliance_score == 92.0
    assert r.total_compliance_score == (95 + 90 + 88 + 92) / 4
    assert r.compliance_level == "完全合规"
    assert len(r.violations) == 1
    assert len(r.rectification_suggestions) >= 2


def test_loan_review_empty_answer_is_safe():
    svc = CreditAuditService(rag_engine=FakeRAGEngine(""))
    r = svc.loan_three_review_check("LX", "匿名", 100)
    assert r.loan_id == "LX"
    assert r.total_score == 0.0
    assert r.risk_level == "高风险"  # 0 分 -> 高风险
    assert r.issues == []
