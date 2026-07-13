"""
合规审计服务模块
提供监管政策匹配、反洗钱合规检查、内部控制审计等功能
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from bank_audit_rag.core.audit_prompts import BankAuditPrompts
from bank_audit_rag.core.rag_engine import RAGQueryEngine
from bank_audit_rag.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RegulatoryComplianceResult:
    """监管合规评估结果"""
    audit_content: str
    business_line: str

    # 适用政策
    applicable_policies: List[Dict[str, str]] = field(default_factory=list)

    # 合规性评估
    compliance_level: str = "未评估"
    compliance_score: float = 0.0

    # 风险和建议
    compliance_risks: List[Dict[str, Any]] = field(default_factory=list)
    rectification_suggestions: List[str] = field(default_factory=list)

    raw_answer: Optional[str] = None


@dataclass
class AMLComplianceResult:
    """反洗钱合规检查结果"""
    customer_name: str
    customer_type: str

    # KYC 检查
    kyc_score: float = 0.0
    identity_verification: bool = False
    risk_rating_accuracy: bool = False
    beneficial_owner_identified: bool = False

    # 交易监测
    transaction_risk_score: float = 0.0
    suspicious_transactions: List[Dict[str, Any]] = field(default_factory=list)

    # 制裁筛查
    sanctions_screening_result: str = "未筛查"
    sanctions_matches: List[str] = field(default_factory=list)

    # 总体评估
    overall_risk_level: str = "未评估"
    overall_score: float = 0.0

    recommendations: List[str] = field(default_factory=list)
    raw_answer: Optional[str] = None


class ComplianceAuditService:
    """
    合规审计服务
    提供监管政策匹配、反洗钱合规检查、内部控制审计等功能
    """

    def __init__(
        self,
        rag_engine: Optional[RAGQueryEngine] = None,
        collection_name: str = "compliance_documents",
        regulatory_collection: str = "regulatory_policies",
    ):
        self.rag_engine = rag_engine or RAGQueryEngine()
        self.collection_name = collection_name
        self.regulatory_collection = regulatory_collection

        logger.info(
            "compliance_audit_service_initialized",
            collection_name=collection_name,
            regulatory_collection=regulatory_collection,
        )

    def check_regulatory_compliance(
        self,
        audit_content: str,
        business_line: str,
        regulatory_type: str = "all",
        collection_name: Optional[str] = None,
        **kwargs: Any,
    ) -> RegulatoryComplianceResult:
        """
        监管政策合规性检查

        基于监管政策库，对审计内容进行合规性匹配和评估

        Args:
            audit_content: 审计内容
            business_line: 业务条线
            regulatory_type: 监管类型（信贷/风险/内控/消保/all）
            collection_name: 集合名称（可选）
            **kwargs: 额外参数

        Returns:
            监管合规评估结果
        """
        logger.info(
            "starting_regulatory_compliance_check",
            audit_content=audit_content[:100],
            business_line=business_line,
            regulatory_type=regulatory_type,
        )

        collection = collection_name or self.regulatory_collection

        # 执行 RAG 查询
        result = self.rag_engine.query(
            question=f"请评估以下内容的监管合规性：{audit_content}",
            collection_name=collection,
            custom_prompt=BankAuditPrompts.REGULATORY_COMPLIANCE,
            prompt_variables={
                "audit_content": audit_content,
                "business_line": business_line,
                "regulatory_type": regulatory_type,
            },
        )

        # 解析结果
        compliance_result = self._parse_regulatory_compliance_result(
            result.answer,
            audit_content=audit_content,
            business_line=business_line,
        )

        logger.info(
            "regulatory_compliance_check_completed",
            compliance_level=compliance_result.compliance_level,
            compliance_score=compliance_result.compliance_score,
            risk_count=len(compliance_result.compliance_risks),
        )

        return compliance_result

    def _parse_regulatory_compliance_result(
        self,
        answer: str,
        audit_content: str,
        business_line: str,
    ) -> RegulatoryComplianceResult:
        """解析监管合规评估结果"""
        result = RegulatoryComplianceResult(
            audit_content=audit_content,
            business_line=business_line,
            raw_answer=answer,
        )

        try:
            import re

            # 提取合规性评分
            score_match = re.search(r"[综总]体[^\d]*(\d+(?:\.\d+)?)分", answer)
            if score_match:
                result.compliance_score = float(score_match.group(1))

            # 提取合规等级
            if "完全合规" in answer:
                result.compliance_level = "完全合规"
            elif "基本合规" in answer:
                result.compliance_level = "基本合规"
            elif "部分合规" in answer:
                result.compliance_level = "部分合规"
            elif "不合规" in answer:
                result.compliance_level = "不合规"

            # 提取适用政策
            result.applicable_policies = self._extract_policies(answer)

            # 提取合规风险
            result.compliance_risks = self._extract_compliance_risks(answer)

            # 提取整改建议
            suggestions = self._extract_suggestions(answer)
            result.rectification_suggestions = suggestions

        except Exception as e:
            logger.warning("parse_regulatory_compliance_result_error", error=str(e))

        return result

    def aml_compliance_check(
        self,
        customer_name: str,
        customer_type: str,
        risk_level: str = "未评级",
        check_period: str = "近一年",
        collection_name: Optional[str] = None,
        **kwargs: Any,
    ) -> AMLComplianceResult:
        """
        反洗钱合规检查

        对客户进行 KYC、交易监测、制裁筛查等反洗钱合规检查

        Args:
            customer_name: 客户名称
            customer_type: 客户类型
            risk_level: 风险等级
            check_period: 检查期间
            collection_name: 集合名称（可选）
            **kwargs: 额外参数

        Returns:
            反洗钱合规检查结果
        """
        logger.info(
            "starting_aml_compliance_check",
            customer_name=customer_name,
            customer_type=customer_type,
            risk_level=risk_level,
        )

        collection = collection_name or self.collection_name

        # 执行 RAG 查询
        result = self.rag_engine.query(
            question=f"请对客户 {customer_name} 进行反洗钱合规检查",
            collection_name=collection,
            custom_prompt=BankAuditPrompts.AML_COMPLIANCE,
            prompt_variables={
                "customer_name": customer_name,
                "customer_type": customer_type,
                "risk_level": risk_level,
                "check_period": check_period,
            },
        )

        # 解析结果
        aml_result = self._parse_aml_compliance_result(
            result.answer,
            customer_name=customer_name,
            customer_type=customer_type,
        )

        logger.info(
            "aml_compliance_check_completed",
            customer_name=customer_name,
            overall_risk_level=aml_result.overall_risk_level,
            suspicious_transaction_count=len(aml_result.suspicious_transactions),
        )

        return aml_result

    def _parse_aml_compliance_result(
        self,
        answer: str,
        customer_name: str,
        customer_type: str,
    ) -> AMLComplianceResult:
        """解析反洗钱合规检查结果"""
        result = AMLComplianceResult(
            customer_name=customer_name,
            customer_type=customer_type,
            raw_answer=answer,
        )

        try:
            import re

            # 提取 KYC 评分
            kyc_match = re.search(r"KYC[^\d]*(\d+(?:\.\d+)?)", answer)
            if kyc_match:
                result.kyc_score = float(kyc_match.group(1))

            # 提取交易风险评分
            trans_match = re.search(r"交易风险[^\d]*(\d+(?:\.\d+)?)", answer)
            if trans_match:
                result.transaction_risk_score = float(trans_match.group(1))

            # 提取总体评分
            overall_match = re.search(r"[综总]体[^\d]*(\d+(?:\.\d+)?)", answer)
            if overall_match:
                result.overall_score = float(overall_match.group(1))

            # 身份验证检查
            result.identity_verification = "身份验证已完成" in answer or "身份信息完整" in answer

            # 受益所有人识别
            result.beneficial_owner_identified = "受益所有人已识别" in answer or "受益所有人信息完整" in answer

            # 总体风险等级
            if "低风险" in answer:
                result.overall_risk_level = "低风险"
            elif "中风险" in answer:
                result.overall_risk_level = "中风险"
            elif "高风险" in answer:
                result.overall_risk_level = "高风险"

            # 提取可疑交易
            result.suspicious_transactions = self._extract_suspicious_transactions(answer)

            # 提取建议
            recommendations = self._extract_suggestions(answer)
            result.recommendations = recommendations

        except Exception as e:
            logger.warning("parse_aml_compliance_result_error", error=str(e))

        return result

    def _extract_policies(self, text: str) -> List[Dict[str, str]]:
        """从文本中提取适用的监管政策"""
        policies = []

        # 常见的政策关键词
        policy_keywords = [
            "商业银行法", "贷款通则", "授信工作尽职指引",
            "固定资产贷款管理暂行办法", "流动资金贷款管理暂行办法",
            "个人贷款管理暂行办法", "商业银行风险管理指引",
            "商业银行资本管理办法", "商业银行内部控制指引",
            "反洗钱法", "商业银行合规风险管理指引",
        ]

        for keyword in policy_keywords:
            if keyword in text:
                policies.append({
                    "name": keyword,
                    "applicable": True,
                })

        return policies

    def _extract_compliance_risks(self, text: str) -> List[Dict[str, Any]]:
        """从文本中提取合规风险"""
        risks = []

        lines = text.split("\n")
        current_risk = None

        for line in lines:
            line = line.strip()

            if any(keyword in line for keyword in ["风险", "违规", "问题", "不符合"]):
                if line and len(line) > 10:
                    current_risk = {
                        "description": line,
                        "severity": "未评估",
                    }
                    risks.append(current_risk)

            if current_risk and any(keyword in line for keyword in ["严重", "重大", "中等", "一般", "高", "中", "低"]):
                if "严重" in line or "重大" in line or "高" in line:
                    current_risk["severity"] = "高风险"
                elif "中等" in line or "中" in line:
                    current_risk["severity"] = "中风险"
                elif "一般" in line or "低" in line:
                    current_risk["severity"] = "低风险"

        return risks

    def _extract_suspicious_transactions(self, text: str) -> List[Dict[str, Any]]:
        """从文本中提取可疑交易"""
        transactions = []

        lines = text.split("\n")
        current_transaction = None

        for line in lines:
            line = line.strip()

            if any(keyword in line for keyword in ["交易", "可疑", "异常"]):
                if line and len(line) > 15:
                    current_transaction = {
                        "description": line,
                        "risk_level": "未评估",
                    }
                    transactions.append(current_transaction)

        return transactions

    def _extract_suggestions(self, text: str) -> List[str]:
        """从文本中提取整改建议"""
        suggestions = []

        lines = text.split("\n")
        in_suggestion_section = False

        for line in lines:
            line = line.strip()

            if any(keyword in line for keyword in ["建议", "整改", "改进", "措施", "优化"]):
                in_suggestion_section = True
                continue

            if in_suggestion_section and line:
                if line.startswith(("- ", "• ", "* ", "1.", "2.", "3.", "4.", "5.")):
                    cleaned = line.lstrip("- •*12345. ").strip()
                    if cleaned and len(cleaned) > 5:
                        suggestions.append(cleaned)
                elif len(line) > 10 and not line.startswith("【"):
                    suggestions.append(line)

                # 遇到新的标题停止
                if any(
                    line.startswith(title)
                    for title in ["三、", "四、", "五、", "六、", "【", "总体", "结论"]
                ):
                    break

        return suggestions[:10]  # 最多返回10条建议
