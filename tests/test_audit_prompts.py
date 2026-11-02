"""审计 Prompt 模板库单元测试（需 langchain_core）。"""

from bank_audit_rag.core.audit_prompts import BankAuditPrompts

EXPECTED_PROMPTS = [
    "LOAN_THREE_REVIEW",
    "CONTRACT_COMPLIANCE",
    "REGULATORY_COMPLIANCE",
    "AML_COMPLIANCE",
    "FINANCIAL_VERIFICATION",
    "CREDIT_RISK_ASSESSMENT",
    "AUDIT_REPORT_GENERATION",
]


def test_list_prompts_includes_all():
    prompts = BankAuditPrompts.list_prompts()
    for name in EXPECTED_PROMPTS:
        assert name in prompts


def test_get_prompt_returns_template():
    p = BankAuditPrompts.get_prompt("loan_three_review")
    assert p is not None
    assert "loan_id" in p.input_variables
    assert "customer_name" in p.input_variables


def test_get_prompt_case_insensitive():
    p = BankAuditPrompts.get_prompt("AUDIT_REPORT_GENERATION")
    assert p is not None


def test_get_prompt_unknown_returns_none():
    assert BankAuditPrompts.get_prompt("nope_x_y_z") is None


def test_financial_prompt_variables():
    p = BankAuditPrompts.get_prompt("financial_verification")
    assert "company_name" in p.input_variables
    assert "report_period" in p.input_variables
