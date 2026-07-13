"""
示例 2: 合规审计与风险管理演示

这个示例展示了：
1. 监管政策合规检查
2. 反洗钱合规检查
3. 信用风险评估
4. 审计报告生成
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bank_audit_rag import (
    AuditReportService,
    ComplianceAuditService,
    RAGQueryEngine,
    RiskManagementService,
)


def main():
    print("=" * 70)
    print("  银行合规审计与风险管理完整流程演示")
    print("=" * 70)

    # 初始化服务
    print("\n1. 初始化服务...")
    rag_engine = RAGQueryEngine()
    compliance_service = ComplianceAuditService(rag_engine=rag_engine)
    risk_service = RiskManagementService(rag_engine=rag_engine)
    report_service = AuditReportService(rag_engine=rag_engine)
    print("   ✓ 服务初始化完成")

    # 监管合规检查
    print("\n2. 监管政策合规检查...")
    compliance_result = compliance_service.check_regulatory_compliance(
        audit_content="""
        本次检查发现：
        1. 部分贷款审批流程未严格执行授信三查制度
        2. 个别客户授信集中度超过监管要求
        3. 贷款五级分类标准执行不够严格
        """,
        business_line="信贷业务",
        regulatory_type="credit",
    )

    print(f"   合规评分: {compliance_result.compliance_score:.2f}")
    print(f"   合规等级: {compliance_result.compliance_level}")
    print(f"   适用政策数: {len(compliance_result.applicable_policies)}")
    print(f"   发现风险数: {len(compliance_result.compliance_risks)}")

    if compliance_result.rectification_suggestions:
        print(f"\n   整改建议:")
        for i, suggestion in enumerate(compliance_result.rectification_suggestions[:3], 1):
            print(f"   {i}. {suggestion[:100]}...")

    # 反洗钱合规检查
    print("\n3. 反洗钱合规检查...")
    aml_result = compliance_service.aml_compliance_check(
        customer_name="某某贸易有限公司",
        customer_type="企业客户",
        risk_level="中风险",
        check_period="2024年1月-6月",
    )

    print(f"   客户名称: {aml_result.customer_name}")
    print(f"   客户类型: {aml_result.customer_type}")
    print(f"   总体风险等级: {aml_result.overall_risk_level}")
    print(f"   总体评分: {aml_result.overall_score:.2f}")

    print(f"\n   KYC检查评分: {aml_result.kyc_score:.2f}")
    print(f"   交易风险评分: {aml_result.transaction_risk_score:.2f}")
    print(f"   身份验证完成: {'是' if aml_result.identity_verification else '否'}")
    print(f"   可疑交易数: {len(aml_result.suspicious_transactions)}")

    # 信用风险评估
    print("\n4. 信用风险评估...")
    risk_result = risk_service.assess_credit_risk(
        customer_name="某某制造有限公司",
        customer_type="制造业企业",
        industry="装备制造",
        credit_limit=30000000,  # 3000万元
    )

    print(f"   客户名称: {risk_result.customer_name}")
    print(f"   所属行业: {risk_result.industry}")
    print(f"   总体风险等级: {risk_result.risk_level}")
    print(f"   总体评分: {risk_result.total_score:.2f}")

    print(f"\n   各维度评分:")
    print(f"   - 财务风险: {risk_result.financial_risk_score:.2f} (权重30%)")
    print(f"   - 经营风险: {risk_result.operational_risk_score:.2f} (权重25%)")
    print(f"   - 信用记录: {risk_result.credit_history_score:.2f} (权重20%)")
    print(f"   - 担保能力: {risk_result.guarantee_capacity_score:.2f} (权重15%)")
    print(f"   - 行业风险: {risk_result.industry_risk_score:.2f} (权重10%)")

    print(f"\n   识别风险点: {len(risk_result.risk_points)}")
    if risk_result.risk_points:
        print(f"\n   主要风险点:")
        for i, point in enumerate(risk_result.risk_points[:3], 1):
            severity = point.get('severity', '未评级')
            category = point.get('category', '其他')
            desc = point.get('description', '')[:60]
            print(f"   {i}. [{category}] [{severity}] {desc}...")

    if risk_result.risk_mitigation_suggestions:
        print(f"\n   风险缓释建议:")
        for i, suggestion in enumerate(risk_result.risk_mitigation_suggestions[:3], 1):
            print(f"   {i}. {suggestion[:80]}...")

    # 生成审计报告
    print("\n5. 生成审计报告...")
    report = report_service.generate_audit_report(
        project_name="2024年上半年信贷业务专项审计",
        audited_unit="某某分行",
        audit_period="2024年1月1日至2024年6月30日",
        audit_type="专项审计",
    )

    print(f"   报告编号: {report.report_id}")
    print(f"   项目名称: {report.project_name}")
    print(f"   被审计单位: {report.audited_unit}")
    print(f"   审计期间: {report.audit_period}")
    print(f"   报告日期: {report.report_date}")

    print(f"\n   审计发现统计:")
    print(f"   - 总计: {len(report.findings)} 项")
    print(f"   - 高风险: {len(report.high_risk_findings)} 项")
    print(f"   - 中风险: {len(report.medium_risk_findings)} 项")
    print(f"   - 低风险: {len(report.low_risk_findings)} 项")

    print(f"\n   审计建议数: {len(report.suggestions)}")

    # 导出 Markdown 报告
    print("\n6. 导出 Markdown 审计报告...")
    markdown_report = report_service.export_report_markdown(report)

    # 保存到文件
    output_file = "/root/opensource/audit-rag/examples/sample_audit_report.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown_report)

    print(f"   ✓ 报告已保存到: {output_file}")

    print("\n" + "=" * 70)
    print("  合规审计与风险管理流程演示完成")
    print("=" * 70)
    print(f"""
  总结:
  - 完成 1 次监管合规检查
  - 完成 1 次反洗钱合规检查
  - 完成 1 次信用风险评估
  - 生成 1 份完整审计报告

  所有功能模块运行正常！
    """)


if __name__ == "__main__":
    main()
