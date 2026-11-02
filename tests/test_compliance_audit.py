"""合规审计服务单元测试（注入 FakeRAGEngine，验证解析逻辑）。"""

from bank_audit_rag.core.compliance_audit import (
    AMLComplianceResult,
    ComplianceAuditService,
    RegulatoryComplianceResult,
)
from tests.conftest import FakeRAGEngine

REG_ANSWER = """
总体合规得分：88分。业务基本合规。
适用《商业银行法》《反洗钱法》相关规定。

存在部分合规风险问题
该事项风险较高，属重大违规隐患。

整改建议
1. 完善内控制度
2. 加强合规培训
"""

AML_ANSWER = """
KYC评分：90分。交易风险评分：70分。总体风险评分：80分。
身份验证已完成，受益所有人已识别。
该客户整体风险等级为中风险。
客户存在可疑交易异常情况。
某笔大额资金快进快出，存在异常交易特征。

整改建议
1. 上报可疑交易报告
2. 持续监控客户交易
"""


def test_regulatory_compliance_parse():
    svc = ComplianceAuditService(rag_engine=FakeRAGEngine(REG_ANSWER))
    r: RegulatoryComplianceResult = svc.check_regulatory_compliance("信贷审批流程", "信贷")
    assert r.audit_content == "信贷审批流程"
    assert r.compliance_score == 88.0
    assert r.compliance_level == "基本合规"
    names = [p["name"] for p in r.applicable_policies]
    assert "商业银行法" in names
    assert "反洗钱法" in names
    assert len(r.compliance_risks) >= 1
    assert r.compliance_risks[0]["severity"] == "高风险"
    assert len(r.rectification_suggestions) >= 2


def test_aml_compliance_parse():
    svc = ComplianceAuditService(rag_engine=FakeRAGEngine(AML_ANSWER))
    r: AMLComplianceResult = svc.aml_compliance_check("某公司", "企业")
    assert r.customer_name == "某公司"
    assert r.kyc_score == 90.0
    assert r.transaction_risk_score == 70.0
    assert r.overall_score == 80.0
    assert r.identity_verification is True
    assert r.beneficial_owner_identified is True
    assert r.overall_risk_level == "中风险"
    assert len(r.suspicious_transactions) >= 1
    assert len(r.recommendations) >= 2
