"""
示例 1: 信贷审计流程演示

这个示例展示了银行信贷审计的完整流程：
1. 初始化信贷审计服务
2. 贷款三查核查
3. 信贷合同合规检查
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bank_audit_rag import CreditAuditService, RAGQueryEngine


def main():
    print("=" * 60)
    print("  银行信贷审计流程演示")
    print("=" * 60)

    # 初始化服务
    print("\n1. 初始化服务...")
    rag_engine = RAGQueryEngine()
    credit_service = CreditAuditService(rag_engine=rag_engine)
    print("   ✓ 服务初始化完成")

    # 贷款三查核查
    print("\n2. 贷款三查核查...")
    loan_review_result = credit_service.loan_three_review_check(
        loan_id="LOAN-2024-001",
        customer_name="某某科技有限公司",
        loan_amount=5000000,  # 500万元
        loan_term=12,
        guarantee_type="抵押",
    )

    print(f"   贷款编号: {loan_review_result.loan_id}")
    print(f"   客户名称: {loan_review_result.customer_name}")
    print(f"   总体评分: {loan_review_result.total_score:.2f}")
    print(f"   风险等级: {loan_review_result.risk_level}")

    print(f"\n   分项评分:")
    print(f"   - 贷前调查: {loan_review_result.pre_loan_score:.2f}")
    print(f"   - 贷中审查: {loan_review_result.in_loan_score:.2f}")
    print(f"   - 贷后检查: {loan_review_result.post_loan_score:.2f}")
    print(f"   - 风险识别: {loan_review_result.risk_identification_score:.2f}")

    print(f"\n   发现问题数: {len(loan_review_result.issues)}")
    print(f"   高风险问题: {len(loan_review_result.high_risk_issues)}")
    print(f"   中风险问题: {len(loan_review_result.medium_risk_issues)}")
    print(f"   低风险问题: {len(loan_review_result.low_risk_issues)}")

    if loan_review_result.rectification_suggestions:
        print(f"\n   整改建议:")
        for i, suggestion in enumerate(loan_review_result.rectification_suggestions[:5], 1):
            print(f"   {i}. {suggestion[:80]}...")

    # 信贷合同合规检查
    print("\n3. 信贷合同合规检查...")
    contract_result = credit_service.contract_compliance_check(
        contract_id="CONT-2024-001",
        contract_type="流动资金借款合同",
        loan_amount=5000000,
        sign_date="2024-01-15",
    )

    print(f"   合同编号: {contract_result.contract_id}")
    print(f"   合同类型: {contract_result.contract_type}")
    print(f"   总体合规评分: {contract_result.total_compliance_score:.2f}")
    print(f"   合规等级: {contract_result.compliance_level}")

    print(f"\n   分项评分:")
    print(f"   - 要素完整性: {contract_result.element_integrity_score:.2f}")
    print(f"   - 利率合规性: {contract_result.rate_compliance_score:.2f}")
    print(f"   - 担保合规性: {contract_result.guarantee_capacity_score:.2f}")

    print(f"\n   违规项数: {len(contract_result.violations)}")

    if contract_result.violations:
        print(f"\n   主要违规项:")
        for i, violation in enumerate(contract_result.violations[:3], 1):
            print(f"   {i}. {violation.get('description', '')[:80]}...")

    print("\n" + "=" * 60)
    print("  信贷审计流程演示完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
