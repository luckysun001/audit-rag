"""
Bank Audit RAG - 银行审计部智能检索问答系统

专为银行审计部门设计的企业级 RAG 系统，支持信贷审计、合规审计、
财务审计、风险管理等核心审计业务场景。

主要功能:
- 信贷审计：贷款三查核查、信贷合同合规检查
- 合规审计：监管政策匹配、反洗钱合规检查
- 财务审计：财务报表真实性核查、财务异常识别
- 风险管理：信用风险评估、风险预警
- 审计报告：自动生成审计报告、审计发现归类
"""

__version__ = "2.0.0"
__author__ = "Bank Audit Tech Team"

# 导入核心模块
from bank_audit_rag.config.settings import Settings, get_settings
from bank_audit_rag.core.audit_prompts import BankAuditPrompts
from bank_audit_rag.core.audit_report import (
    AuditFinding,
    AuditReport,
    AuditReportService,
)
from bank_audit_rag.core.compliance_audit import (
    AMLComplianceResult,
    ComplianceAuditService,
    RegulatoryComplianceResult,
)
from bank_audit_rag.core.credit_audit import (
    ContractComplianceResult,
    CreditAuditService,
    LoanReviewResult,
)
from bank_audit_rag.core.document_processor import (
    DocumentChunk,
    DocumentMetadata,
    DocumentProcessor,
    DocumentStore,
)
from bank_audit_rag.core.rag_engine import RAGQueryEngine
from bank_audit_rag.core.risk_management import (
    CreditRiskAssessmentResult,
    RiskAlert,
    RiskManagementService,
)
from bank_audit_rag.core.vector_store import (
    EmbeddingService,
    RAGResult,
    VectorStoreService,
)

__all__ = [
    # Config
    "Settings",
    "get_settings",
    # Core - Document Processing
    "DocumentProcessor",
    "DocumentStore",
    "DocumentChunk",
    "DocumentMetadata",
    # Core - Vector Store
    "EmbeddingService",
    "VectorStoreService",
    "RAGResult",
    # Core - RAG Engine
    "RAGQueryEngine",
    # Core - Audit Prompts
    "BankAuditPrompts",
    # Core - Credit Audit
    "CreditAuditService",
    "LoanReviewResult",
    "ContractComplianceResult",
    # Core - Compliance Audit
    "ComplianceAuditService",
    "RegulatoryComplianceResult",
    "AMLComplianceResult",
    # Core - Risk Management
    "RiskManagementService",
    "CreditRiskAssessmentResult",
    "RiskAlert",
    # Core - Audit Report
    "AuditReportService",
    "AuditReport",
    "AuditFinding",
]
