"""
信贷审计服务模块
提供贷款三查核查、合同合规检查、信贷风险识别等功能
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from bank_audit_rag.core.audit_prompts import BankAuditPrompts
from bank_audit_rag.core.rag_engine import RAGQueryEngine
from bank_audit_rag.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LoanReviewResult:
    """贷款三查核查结果"""
    loan_id: str
    customer_name: str

    # 分项评分
    pre_loan_score: float = 0.0
    in_loan_score: float = 0.0
    post_loan_score: float = 0.0
    risk_identification_score: float = 0.0

    # 总体评分
    total_score: float = 0.0
    risk_level: str = "未评级"

    # 审计发现
    issues: List[Dict[str, Any]] = field(default_factory=list)
    high_risk_issues: List[Dict[str, Any]] = field(default_factory=list)
    medium_risk_issues: List[Dict[str, Any]] = field(default_factory=list)
    low_risk_issues: List[Dict[str, Any]] = field(default_factory=list)

    # 整改建议
    rectification_suggestions: List[str] = field(default_factory=list)

    # 原始回答
    raw_answer: Optional[str] = None


@dataclass
class ContractComplianceResult:
    """合同合规检查结果"""
    contract_id: str
    contract_type: str

    # 合规性评分
    element_integrity_score: float = 0.0
    rate_compliance_score: float = 0.0
    guarantee_compliance_score: float = 0.0
    prohibition_compliance_score: float = 0.0
    total_compliance_score: float = 0.0

    # 合规性判断
    compliance_level: str = "未评估"

    # 违规项
    violations: List[Dict[str, Any]] = field(default_factory=list)
    regulatory_references: List[str] = field(default_factory=list)

    # 风险和建议
    risk_assessment: List[Dict[str, Any]] = field(default_factory=list)
    rectification_suggestions: List[str] = field(default_factory=list)

    raw_answer: Optional[str] = None


class CreditAuditService:
    """
    信贷审计服务
    提供贷款三查核查、信贷合同合规检查、信贷风险识别等功能
    """

    def __init__(
        self,
        rag_engine: Optional[RAGQueryEngine] = None,
        collection_name: str = "credit_audit_documents",
    ):
        self.rag_engine = rag_engine or RAGQueryEngine()
        self.collection_name = collection_name

        logger.info(
            "credit_audit_service_initialized",
            collection_name=collection_name,
        )

    def loan_three_review_check(
        self,
        loan_id: str,
        customer_name: str,
        loan_amount: float,
        loan_term: int = 12,
        guarantee_type: str = "信用",
        collection_name: Optional[str] = None,
        **kwargs: Any,
    ) -> LoanReviewResult:
        """
        贷款三查核查

        对贷款的贷前调查、贷中审查、贷后检查进行全面核查评估

        Args:
            loan_id: 贷款编号
            customer_name: 借款人名称
            loan_amount: 贷款金额（元）
            loan_term: 贷款期限（月）
            guarantee_type: 担保方式
            collection_name: 集合名称（可选）
            **kwargs: 额外参数

        Returns:
            贷款三查核查结果
        """
        logger.info(
            "starting_loan_three_review_check",
            loan_id=loan_id,
            customer_name=customer_name,
            loan_amount=loan_amount,
        )

        collection = collection_name or self.collection_name

        # 构建查询
        query = f"""
        请对贷款编号为 {loan_id} 的贷款进行三查核查：
        - 贷前调查是否完整
        - 贷中审查是否合规
        - 贷后检查是否及时
        - 风险识别是否准确
        """

        # 执行 RAG 查询，使用专用 Prompt
        result = self.rag_engine.query(
            question=query,
            collection_name=collection,
            custom_prompt=BankAuditPrompts.LOAN_THREE_REVIEW,
            prompt_variables={
                "loan_id": loan_id,
                "customer_name": customer_name,
                "loan_amount": loan_amount,
                "loan_term": loan_term,
                "guarantee_type": guarantee_type,
            },
        )

        # 解析结果
        review_result = self._parse_loan_review_result(
            result.answer,
            loan_id=loan_id,
            customer_name=customer_name,
        )

        logger.info(
            "loan_three_review_check_completed",
            loan_id=loan_id,
            total_score=review_result.total_score,
            risk_level=review_result.risk_level,
            issue_count=len(review_result.issues),
        )

        return review_result

    def _parse_loan_review_result(
        self,
        answer: str,
        loan_id: str,
        customer_name: str,
    ) -> LoanReviewResult:
        """解析贷款三查核查结果"""
        # 初始化结果对象
        result = LoanReviewResult(
            loan_id=loan_id,
            customer_name=customer_name,
            raw_answer=answer,
        )

        # 简单的评分提取（实际应用中可以使用结构化输出）
        try:
            # 提取各项评分
            import re

            # 提取贷前调查分数
            pre_match = re.search(r"贷前调查[^\d]*(\d+(?:\.\d+)?)", answer)
            if pre_match:
                result.pre_loan_score = float(pre_match.group(1))

            # 提取贷中审查分数
            in_match = re.search(r"贷中审查[^\d]*(\d+(?:\.\d+)?)", answer)
            if in_match:
                result.in_loan_score = float(in_match.group(1))

            # 提取贷后检查分数
            post_match = re.search(r"贷后检查[^\d]*(\d+(?:\.\d+)?)", answer)
            if post_match:
                result.post_loan_score = float(post_match.group(1))

            # 提取风险识别分数
            risk_match = re.search(r"风险识别[^\d]*(\d+(?:\.\d+)?)", answer)
            if risk_match:
                result.risk_identification_score = float(risk_match.group(1))

            # 计算总分
            result.total_score = (
                result.pre_loan_score
                + result.in_loan_score
                + result.post_loan_score
                + result.risk_identification_score
            ) / 4

            # 确定风险等级
            if result.total_score >= 85:
                result.risk_level = "低风险"
            elif result.total_score >= 70:
                result.risk_level = "中低风险"
            elif result.total_score >= 55:
                result.risk_level = "中风险"
            elif result.total_score >= 40:
                result.risk_level = "中高风险"
            else:
                result.risk_level = "高风险"

            # 提取问题列表
            issues = self._extract_issues(answer)
            result.issues = issues

            # 按风险等级分类
            for issue in issues:
                risk_level = issue.get("risk_level", "").lower()
                if "高" in risk_level:
                    result.high_risk_issues.append(issue)
                elif "中" in risk_level:
                    result.medium_risk_issues.append(issue)
                else:
                    result.low_risk_issues.append(issue)

            # 提取整改建议
            suggestions = self._extract_suggestions(answer)
            result.rectification_suggestions = suggestions

        except Exception as e:
            logger.warning("parse_loan_review_result_error", error=str(e))

        return result

    def contract_compliance_check(
        self,
        contract_id: str,
        contract_type: str,
        loan_amount: float,
        sign_date: str,
        collection_name: Optional[str] = None,
        **kwargs: Any,
    ) -> ContractComplianceResult:
        """
        信贷合同合规性检查

        对信贷合同的要素完整性、利率合规性、担保合规性、禁止性规定等进行全面检查

        Args:
            contract_id: 合同编号
            contract_type: 合同类型
            loan_amount: 贷款金额
            sign_date: 签订日期
            collection_name: 集合名称（可选）
            **kwargs: 额外参数

        Returns:
            合同合规检查结果
        """
        logger.info(
            "starting_contract_compliance_check",
            contract_id=contract_id,
            contract_type=contract_type,
        )

        collection = collection_name or self.collection_name

        # 执行 RAG 查询
        result = self.rag_engine.query(
            question=f"请检查合同编号为 {contract_id} 的信贷合同合规性",
            collection_name=collection,
            custom_prompt=BankAuditPrompts.CONTRACT_COMPLIANCE,
            prompt_variables={
                "contract_id": contract_id,
                "contract_type": contract_type,
                "loan_amount": loan_amount,
                "sign_date": sign_date,
            },
        )

        # 解析结果
        compliance_result = self._parse_contract_compliance_result(
            result.answer,
            contract_id=contract_id,
            contract_type=contract_type,
        )

        logger.info(
            "contract_compliance_check_completed",
            contract_id=contract_id,
            total_score=compliance_result.total_compliance_score,
            compliance_level=compliance_result.compliance_level,
            violation_count=len(compliance_result.violations),
        )

        return compliance_result

    def _parse_contract_compliance_result(
        self,
        answer: str,
        contract_id: str,
        contract_type: str,
    ) -> ContractComplianceResult:
        """解析合同合规检查结果"""
        result = ContractComplianceResult(
            contract_id=contract_id,
            contract_type=contract_type,
            raw_answer=answer,
        )

        try:
            import re

            # 提取各项评分
            patterns = [
                (r"要素完整[^\d]*(\d+(?:\.\d+)?)", "element_integrity_score"),
                (r"利率合规[^\d]*(\d+(?:\.\d+)?)", "rate_compliance_score"),
                (r"担保合规[^\d]*(\d+(?:\.\d+)?)", "guarantee_compliance_score"),
                (r"禁止性规定[^\d]*(\d+(?:\.\d+)?)", "prohibition_compliance_score"),
            ]

            for pattern, attr_name in patterns:
                match = re.search(pattern, answer)
                if match:
                    setattr(result, attr_name, float(match.group(1)))

            # 计算总分
            result.total_compliance_score = (
                result.element_integrity_score
                + result.rate_compliance_score
                + result.guarantee_compliance_score
                + result.prohibition_compliance_score
            ) / 4

            # 确定合规等级
            if result.total_compliance_score >= 90:
                result.compliance_level = "完全合规"
            elif result.total_compliance_score >= 75:
                result.compliance_level = "基本合规"
            elif result.total_compliance_score >= 60:
                result.compliance_level = "部分合规"
            else:
                result.compliance_level = "不合规"

            # 提取违规项
            violations = self._extract_violations(answer)
            result.violations = violations

            # 提取整改建议
            suggestions = self._extract_suggestions(answer)
            result.rectification_suggestions = suggestions

        except Exception as e:
            logger.warning("parse_contract_compliance_result_error", error=str(e))

        return result

    def _extract_issues(self, text: str) -> List[Dict[str, Any]]:
        """从文本中提取审计发现的问题"""
        issues = []

        # 简单的问题提取逻辑（实际应用中可以使用更复杂的 NLP 方法）
        lines = text.split("\n")
        current_issue = None

        for line in lines:
            line = line.strip()

            # 识别问题行
            if any(keyword in line for keyword in ["问题", "发现", "不足", "缺陷", "风险"]):
                if line and len(line) > 5:
                    current_issue = {
                        "description": line,
                        "risk_level": "未评估",
                    }
                    issues.append(current_issue)

            # 识别风险等级
            elif current_issue and any(
                keyword in line for keyword in ["高风险", "中风险", "低风险"]
            ):
                if "高风险" in line:
                    current_issue["risk_level"] = "高风险"
                elif "中风险" in line:
                    current_issue["risk_level"] = "中风险"
                else:
                    current_issue["risk_level"] = "低风险"

        return issues

    def _extract_violations(self, text: str) -> List[Dict[str, Any]]:
        """从文本中提取违规项"""
        violations = []

        lines = text.split("\n")
        current_violation = None

        for line in lines:
            line = line.strip()

            if any(keyword in line for keyword in ["违规", "违反", "不符合", "禁止"]):
                if line and len(line) > 5:
                    current_violation = {
                        "description": line,
                        "regulation": "",
                        "severity": "未评估",
                    }
                    violations.append(current_violation)

        return violations

    def _extract_suggestions(self, text: str) -> List[str]:
        """从文本中提取整改建议"""
        suggestions = []

        lines = text.split("\n")
        suggestion_section = False

        for line in lines:
            line = line.strip()

            if any(keyword in line for keyword in ["建议", "整改", "改进", "优化"]):
                suggestion_section = True
                continue

            if suggestion_section and line:
                # 检查是否是列表项
                if line.startswith(("- ", "• ", "* ", "1.", "2.", "3.", "4.", "5.")):
                    suggestions.append(line.lstrip("- •*12345. ").strip())
                elif line and len(line) > 10:
                    suggestions.append(line)

                # 遇到空行或新标题停止
                if not line or any(
                    keyword in line
                    for keyword in ["【", "三、", "四、", "五、", "总体", "结论"]
                ):
                    break

        return suggestions

    def index_credit_document(
        self,
        document_path: str,
        document_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        索引信贷文档

        Args:
            document_path: 文档路径
            document_type: 文档类型
            metadata: 额外元数据

        Returns:
            文档 ID 列表
        """
        from bank_audit_rag import DocumentProcessor, VectorStoreService

        processor = DocumentProcessor()
        vector_store = VectorStoreService()

        # 处理文档
        chunks, doc_metadata = processor.process_document(
            document_path,
            document_type=document_type,
            business_line="credit",
            **(metadata or {}),
        )

        # 转换为 LangChain Document
        from langchain_core.documents import Document

        langchain_docs = [
            Document(page_content=chunk.content, metadata=chunk.metadata)
            for chunk in chunks
        ]

        # 索引
        ids = vector_store.add_documents(langchain_docs, self.collection_name)

        logger.info(
            "credit_document_indexed",
            document_path=document_path,
            document_type=document_type,
            chunk_count=len(chunks),
        )

        return ids
