"""
风险管理服务模块
提供信用风险评估、风险预警、风险等级分类等功能
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from bank_audit_rag.core.audit_prompts import BankAuditPrompts
from bank_audit_rag.core.rag_engine import RAGQueryEngine
from bank_audit_rag.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CreditRiskAssessmentResult:
    """信用风险评估结果"""
    customer_name: str
    customer_type: str
    industry: str

    # 各维度评分
    financial_risk_score: float = 0.0
    operational_risk_score: float = 0.0
    credit_history_score: float = 0.0
    guarantee_capacity_score: float = 0.0
    industry_risk_score: float = 0.0

    # 总体评分和等级
    total_score: float = 0.0
    risk_level: str = "未评级"

    # 风险点和建议
    risk_points: List[Dict[str, Any]] = field(default_factory=list)
    risk_mitigation_suggestions: List[str] = field(default_factory=list)

    raw_answer: Optional[str] = None


@dataclass
class RiskAlert:
    """风险预警"""
    alert_id: str
    alert_type: str
    severity: str
    description: str
    related_customer: Optional[str] = None
    related_department: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)


class RiskManagementService:
    """
    风险管理服务
    提供信用风险评估、风险预警、风险等级分类等功能
    """

    # 风险等级映射
    RISK_LEVEL_MAPPING = {
        (85, 101): "低风险",
        (70, 85): "中低风险",
        (55, 70): "中风险",
        (40, 55): "中高风险",
        (0, 40): "高风险",
    }

    def __init__(
        self,
        rag_engine: Optional[RAGQueryEngine] = None,
        collection_name: str = "risk_management_documents",
    ):
        self.rag_engine = rag_engine or RAGQueryEngine()
        self.collection_name = collection_name

        logger.info(
            "risk_management_service_initialized",
            collection_name=collection_name,
        )

    def assess_credit_risk(
        self,
        customer_name: str,
        customer_type: str,
        industry: str,
        credit_limit: float,
        assessment_date: Optional[str] = None,
        collection_name: Optional[str] = None,
        **kwargs: Any,
    ) -> CreditRiskAssessmentResult:
        """
        信用风险评估

        对客户的信用风险进行多维度综合评估，包括财务风险、经营风险、
        信用记录、担保能力、行业风险等

        Args:
            customer_name: 客户名称
            customer_type: 客户类型
            industry: 所属行业
            credit_limit: 授信额度（元）
            assessment_date: 评估日期
            collection_name: 集合名称（可选）
            **kwargs: 额外参数

        Returns:
            信用风险评估结果
        """
        import datetime
        if assessment_date is None:
            assessment_date = datetime.datetime.now().strftime("%Y-%m-%d")

        logger.info(
            "starting_credit_risk_assessment",
            customer_name=customer_name,
            customer_type=customer_type,
            industry=industry,
            credit_limit=credit_limit,
        )

        collection = collection_name or self.collection_name

        # 执行 RAG 查询
        result = self.rag_engine.query(
            question=f"请对客户 {customer_name} 进行全面的信用风险评估",
            collection_name=collection,
            custom_prompt=BankAuditPrompts.CREDIT_RISK_ASSESSMENT,
            prompt_variables={
                "customer_name": customer_name,
                "customer_type": customer_type,
                "industry": industry,
                "credit_limit": credit_limit,
                "assessment_date": assessment_date,
            },
        )

        # 解析结果
        assessment_result = self._parse_credit_risk_assessment(
            result.answer,
            customer_name=customer_name,
            customer_type=customer_type,
            industry=industry,
        )

        logger.info(
            "credit_risk_assessment_completed",
            customer_name=customer_name,
            total_score=assessment_result.total_score,
            risk_level=assessment_result.risk_level,
        )

        return assessment_result

    def _parse_credit_risk_assessment(
        self,
        answer: str,
        customer_name: str,
        customer_type: str,
        industry: str,
    ) -> CreditRiskAssessmentResult:
        """解析信用风险评估结果"""
        result = CreditRiskAssessmentResult(
            customer_name=customer_name,
            customer_type=customer_type,
            industry=industry,
            raw_answer=answer,
        )

        try:
            import re

            # 提取各维度评分
            score_patterns = [
                (r"财务风险[^\d]*(\d+(?:\.\d+)?)", "financial_risk_score"),
                (r"经营风险[^\d]*(\d+(?:\.\d+)?)", "operational_risk_score"),
                (r"信用记录[^\d]*(\d+(?:\.\d+)?)", "credit_history_score"),
                (r"担保能力[^\d]*(\d+(?:\.\d+)?)", "guarantee_capacity_score"),
                (r"行业风险[^\d]*(\d+(?:\.\d+)?)", "industry_risk_score"),
            ]

            for pattern, attr_name in score_patterns:
                match = re.search(pattern, answer)
                if match:
                    setattr(result, attr_name, float(match.group(1)))

            # 提取总分
            total_match = re.search(r"[综总]体[^\d]*(\d+(?:\.\d+)?)", answer)
            if total_match:
                result.total_score = float(total_match.group(1))
            else:
                # 计算加权总分
                weights = [0.30, 0.25, 0.20, 0.15, 0.10]
                scores = [
                    result.financial_risk_score,
                    result.operational_risk_score,
                    result.credit_history_score,
                    result.guarantee_capacity_score,
                    result.industry_risk_score,
                ]
                result.total_score = sum(s * w for s, w in zip(scores, weights))

            # 确定风险等级
            result.risk_level = self._determine_risk_level(result.total_score)

            # 提取风险点
            result.risk_points = self._extract_risk_points(answer)

            # 提取风险缓释建议
            suggestions = self._extract_suggestions(answer)
            result.risk_mitigation_suggestions = suggestions

        except Exception as e:
            logger.warning("parse_credit_risk_assessment_error", error=str(e))

        return result

    def _determine_risk_level(self, score: float) -> str:
        """根据分数确定风险等级"""
        for (lower, upper), level in self.RISK_LEVEL_MAPPING.items():
            if lower <= score < upper:
                return level
        return "未评级"

    def _extract_risk_points(self, text: str) -> List[Dict[str, Any]]:
        """从文本中提取风险点"""
        risk_points = []
        lines = text.split("\n")
        current_point = None

        for line in lines:
            line = line.strip()

            # 识别风险点
            risk_keywords = ["风险", "隐患", "问题", "不足", "缺陷", "异常", "偏离"]
            if any(keyword in line for keyword in risk_keywords) and len(line) > 10:
                # 排除评分行
                if "分" in line and any(char.isdigit() for char in line):
                    continue

                current_point = {
                    "description": line,
                    "severity": "未评估",
                    "category": self._categorize_risk(line),
                }
                risk_points.append(current_point)

            # 识别严重程度
            if current_point:
                if any(word in line for word in ["严重", "重大", "高危", "高风险"]):
                    current_point["severity"] = "高"
                elif any(word in line for word in ["中等", "中度", "中风险"]):
                    current_point["severity"] = "中"
                elif any(word in line for word in ["一般", "轻微", "低风险"]):
                    current_point["severity"] = "低"

        return risk_points[:15]  # 最多返回15个风险点

    def _categorize_risk(self, description: str) -> str:
        """对风险进行分类"""
        if any(word in description for word in ["财务", "报表", "利润", "资产", "负债", "现金流"]):
            return "财务风险"
        elif any(word in description for word in ["经营", "管理", "销售", "市场", "竞争"]):
            return "经营风险"
        elif any(word in description for word in ["担保", "抵押", "质押", "保证", "代偿"]):
            return "担保风险"
        elif any(word in description for word in ["行业", "政策", "宏观", "监管"]):
            return "行业/政策风险"
        elif any(word in description for word in ["信用", "逾期", "违约", "还款"]):
            return "信用风险"
        else:
            return "其他风险"

    def _extract_suggestions(self, text: str) -> List[str]:
        """从文本中提取风险缓释建议"""
        suggestions = []
        lines = text.split("\n")
        in_suggestion_section = False

        for line in lines:
            line = line.strip()

            suggestion_keywords = [
                "建议", "措施", "缓释", "化解", "防范", "应对",
                "整改", "优化", "改进", "加强", "完善"
            ]

            if any(keyword in line for keyword in suggestion_keywords):
                in_suggestion_section = True
                continue

            if in_suggestion_section and line:
                # 检查是否是列表项
                if line.startswith(("- ", "• ", "* ", "1.", "2.", "3.", "4.", "5.")):
                    cleaned = line.lstrip("- •*12345. ").strip()
                    if cleaned and len(cleaned) > 8:
                        suggestions.append(cleaned)
                elif len(line) > 15 and not line.startswith("【") and not line.startswith("三、"):
                    suggestions.append(line)

                # 遇到新标题停止
                if any(
                    line.startswith(title)
                    for title in ["三、", "四、", "五、", "六、", "【", "总体", "结论"]
                ):
                    break

        return suggestions[:10]

    def generate_risk_alerts(
        self,
        threshold_score: float = 60.0,
        collection_name: Optional[str] = None,
    ) -> List[RiskAlert]:
        """
        生成风险预警

        基于风险评估结果，自动识别高风险客户并生成预警

        Args:
            threshold_score: 预警阈值分数（低于此分数生成预警）
            collection_name: 集合名称

        Returns:
            风险预警列表
        """
        logger.info(
            "generating_risk_alerts",
            threshold_score=threshold_score,
        )

        alerts = []

        # 这里可以添加实际的预警生成逻辑
        # 例如：扫描所有客户风险评估结果，识别低于阈值的客户

        logger.info("risk_alerts_generated", alert_count=len(alerts))
        return alerts

    def batch_risk_assessment(
        self,
        customer_list: List[Dict[str, Any]],
    ) -> List[CreditRiskAssessmentResult]:
        """
        批量信用风险评估

        Args:
            customer_list: 客户列表，每个客户包含名称、类型、行业、额度等信息

        Returns:
            评估结果列表
        """
        results = []

        for customer in customer_list:
            try:
                result = self.assess_credit_risk(
                    customer_name=customer.get("name", ""),
                    customer_type=customer.get("type", "企业"),
                    industry=customer.get("industry", "其他"),
                    credit_limit=customer.get("credit_limit", 0),
                )
                results.append(result)
            except Exception as e:
                logger.error(
                    "batch_risk_assessment_error",
                    customer=customer.get("name", ""),
                    error=str(e),
                )

        logger.info(
            "batch_risk_assessment_completed",
            total_count=len(customer_list),
            success_count=len(results),
        )

        return results
