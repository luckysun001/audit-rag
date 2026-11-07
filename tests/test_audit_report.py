"""审计报告服务单元测试（注入 FakeRAGEngine，验证章节解析与导出）。"""

from bank_audit_rag.core.audit_report import AuditReport, AuditReportService
from tests.conftest import FakeRAGEngine

REPORT_ANSWER = """
一、审计概况
本次审计覆盖信贷与合规业务。审计方法包括抽样检查、数据分析。审计依据《商业银行法》相关规定。

二、审计发现
- 发现贷款三查执行不到位
该问题属于高风险，违反监管规定。
- 发现内控流程存在缺陷
该问题属于中风险。

三、风险评估
整体风险水平偏高，需重点关注信贷领域。

四、审计建议
1. 强化三查制度执行
2. 完善内控流程

五、审计结论
审计结果表明存在多项需整改问题。
"""


def test_generate_audit_report_parse():
    svc = AuditReportService(rag_engine=FakeRAGEngine(REPORT_ANSWER))
    r: AuditReport = svc.generate_audit_report(
        "2024年度信贷合规审计", "某分行", "2024-01-01至2024-12-31", "专项审计"
    )
    assert r.report_id.startswith("RPT-")
    assert r.project_name == "2024年度信贷合规审计"
    assert len(r.findings) == 2
    assert len(r.high_risk_findings) == 1
    assert len(r.medium_risk_findings) == 1
    assert any("抽样检查" in m or "数据分析" in m for m in r.audit_methods)
    assert any("商业银行法" in b for b in r.audit_basis)
    assert "整体风险水平偏高" in r.overall_risk_assessment
    assert len(r.suggestions) >= 2
    assert "需整改问题" in r.audit_conclusion


def test_export_report_markdown():
    svc = AuditReportService(rag_engine=FakeRAGEngine(REPORT_ANSWER))
    r = svc.generate_audit_report("项目X", "单位Y", "2024", "专项审计")
    md = svc.export_report_markdown(r)
    assert "项目X" in md
    assert "高风险" in md
    assert r.high_risk_findings[0].title in md


def test_generate_rectification_notice():
    svc = AuditReportService(rag_engine=FakeRAGEngine(REPORT_ANSWER))
    r = svc.generate_audit_report("项目X", "单位Y", "2024", "专项审计")
    notice = svc.generate_rectification_notice(r, "2024-12-31")
    assert "单位Y" in notice
    assert "2024-12-31" in notice
    assert r.high_risk_findings[0].title in notice


def test_report_with_findings_data():
    """传入 findings_data 时，查询上下文应包含发现摘要。"""
    svc = AuditReportService(rag_engine=FakeRAGEngine(REPORT_ANSWER))
    findings = [
        {"title": "发现A", "description": "描述A"},
        {"title": "发现B", "description": "描述B"},
    ]
    r = svc.generate_audit_report("项目Z", "单位W", "2024", "专项审计", findings_data=findings)
    assert r.project_name == "项目Z"
    assert r.raw_content is not None
