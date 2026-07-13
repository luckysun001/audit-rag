"""
审计报告服务模块
提供审计报告自动生成、审计发现归类、报告模板管理等功能
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from bank_audit_rag.core.audit_prompts import BankAuditPrompts
from bank_audit_rag.core.rag_engine import RAGQueryEngine
from bank_audit_rag.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AuditFinding:
    """审计发现"""
    finding_id: str
    title: str
    description: str
    risk_level: str = "未评级"
    category: str = "其他"
    violation: Optional[str] = None
    evidence: List[str] = field(default_factory=list)
    rectification_deadline: Optional[str] = None
    responsible_department: Optional[str] = None


@dataclass
class AuditReport:
    """审计报告"""
    report_id: str
    project_name: str
    audited_unit: str
    audit_period: str
    audit_type: str

    # 报告日期和版本
    report_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    version: str = "1.0"

    # 审计概况
    audit_scope: List[str] = field(default_factory=list)
    audit_methods: List[str] = field(default_factory=list)
    audit_basis: List[str] = field(default_factory=list)

    # 审计发现
    findings: List[AuditFinding] = field(default_factory=list)
    high_risk_findings: List[AuditFinding] = field(default_factory=list)
    medium_risk_findings: List[AuditFinding] = field(default_factory=list)
    low_risk_findings: List[AuditFinding] = field(default_factory=list)

    # 风险评估
    overall_risk_assessment: str = ""
    risk_trend_analysis: str = ""

    # 审计建议
    suggestions: List[str] = field(default_factory=list)

    # 审计结论
    audit_conclusion: str = ""

    # 原始生成内容
    raw_content: Optional[str] = None


class AuditReportService:
    """
    审计报告服务
    提供审计报告自动生成、审计发现归类、报告模板管理等功能
    """

    def __init__(
        self,
        rag_engine: Optional[RAGQueryEngine] = None,
        collection_name: str = "audit_documents",
    ):
        self.rag_engine = rag_engine or RAGQueryEngine()
        self.collection_name = collection_name

        logger.info(
            "audit_report_service_initialized",
            collection_name=collection_name,
        )

    def generate_audit_report(
        self,
        project_name: str,
        audited_unit: str,
        audit_period: str,
        audit_type: str = "专项审计",
        findings_data: Optional[List[Dict[str, Any]]] = None,
        collection_name: Optional[str] = None,
        **kwargs: Any,
    ) -> AuditReport:
        """
        生成审计报告

        基于审计发现和相关文档，自动生成完整、规范的审计报告

        Args:
            project_name: 审计项目名称
            audited_unit: 被审计单位
            audit_period: 审计期间
            audit_type: 审计类型
            findings_data: 审计发现数据（可选）
            collection_name: 集合名称
            **kwargs: 额外参数

        Returns:
            审计报告对象
        """
        logger.info(
            "generating_audit_report",
            project_name=project_name,
            audited_unit=audited_unit,
            audit_period=audit_period,
            audit_type=audit_type,
        )

        collection = collection_name or self.collection_name

        # 构建查询上下文
        context_parts = [
            f"审计项目：{project_name}",
            f"被审计单位：{audited_unit}",
            f"审计期间：{audit_period}",
            f"审计类型：{audit_type}",
        ]

        if findings_data:
            context_parts.append("\n审计发现摘要：")
            for i, finding in enumerate(findings_data, 1):
                context_parts.append(f"{i}. {finding.get('title', '')}")
                context_parts.append(f"   {finding.get('description', '')}")

        context = "\n".join(context_parts)

        # 执行 RAG 查询
        result = self.rag_engine.query(
            question=f"请基于以下信息生成完整的审计报告\n\n{context}",
            collection_name=collection,
            custom_prompt=BankAuditPrompts.AUDIT_REPORT_GENERATION,
            prompt_variables={
                "audit_project_name": project_name,
                "audited_unit": audited_unit,
                "audit_period": audit_period,
                "audit_type": audit_type,
            },
        )

        # 解析报告
        report = self._parse_audit_report_content(
            result.answer,
            project_name=project_name,
            audited_unit=audited_unit,
            audit_period=audit_period,
            audit_type=audit_type,
        )

        logger.info(
            "audit_report_generated",
            project_name=project_name,
            finding_count=len(report.findings),
            high_risk_count=len(report.high_risk_findings),
        )

        return report

    def _parse_audit_report_content(
        self,
        content: str,
        project_name: str,
        audited_unit: str,
        audit_period: str,
        audit_type: str,
    ) -> AuditReport:
        """解析审计报告内容"""
        import uuid

        report = AuditReport(
            report_id=f"RPT-{uuid.uuid4().hex[:8].upper()}",
            project_name=project_name,
            audited_unit=audited_unit,
            audit_period=audit_period,
            audit_type=audit_type,
            raw_content=content,
        )

        try:
            # 分章节解析
            sections = self._split_into_sections(content)

            # 解析审计概况
            if "审计概况" in sections:
                self._parse_overview_section(sections["审计概况"], report)

            # 解析审计发现
            if "审计发现" in sections or "主要问题" in sections:
                findings_section = sections.get("审计发现", sections.get("主要问题", ""))
                self._parse_findings_section(findings_section, report)

            # 解析风险评估
            if "风险评估" in sections:
                self._parse_risk_assessment_section(sections["风险评估"], report)

            # 解析审计建议
            if "审计建议" in sections or "整改建议" in sections:
                suggestions_section = sections.get("审计建议", sections.get("整改建议", ""))
                self._parse_suggestions_section(suggestions_section, report)

            # 解析审计结论
            if "审计结论" in sections or "总体评价" in sections:
                conclusion_section = sections.get("审计结论", sections.get("总体评价", ""))
                report.audit_conclusion = conclusion_section.strip()

            # 按风险等级分类审计发现
            self._categorize_findings_by_risk(report)

        except Exception as e:
            logger.warning("parse_audit_report_error", error=str(e))

        return report

    def _split_into_sections(self, content: str) -> Dict[str, str]:
        """将报告内容按章节分割"""
        sections = {}
        current_section = "前言"
        current_content = []

        lines = content.split("\n")

        for line in lines:
            stripped = line.strip()

            # 检查是否是章节标题
            if self._is_section_title(stripped):
                # 保存上一个章节
                sections[current_section] = "\n".join(current_content)
                current_section = stripped.strip(" 　、：:")
                current_content = []
            else:
                current_content.append(line)

        # 保存最后一个章节
        sections[current_section] = "\n".join(current_content)

        return sections

    def _is_section_title(self, line: str) -> bool:
        """判断是否是章节标题"""
        if not line:
            return False

        # 常见的章节标题格式
        title_patterns = [
            r"^[一二三四五六七八九十]+、",
            r"^[（(][一二三四五六七八九十]+[)）]",
            r"^【.*】$",
            r"^第[一二三四五六七八九十]+部分",
            r"^第[一二三四五六七八九十]+章",
        ]

        import re
        for pattern in title_patterns:
            if re.match(pattern, line):
                return True

        # 常见的审计报告章节关键词
        section_keywords = [
            "审计概况", "审计范围", "审计发现", "主要问题", "风险评估",
            "审计建议", "整改建议", "审计结论", "总体评价", "整改要求",
            "审计意见", "一、", "二、", "三、", "四、", "五、",
        ]

        for keyword in section_keywords:
            if line.startswith(keyword) and len(line) < 30:
                return True

        return False

    def _parse_overview_section(self, content: str, report: AuditReport) -> None:
        """解析审计概况章节"""
        lines = content.split("\n")

        for line in lines:
            line = line.strip()

            # 识别审计方法
            if "方法" in line and any(keyword in line for keyword in ["检查", "抽样", "访谈", "分析", "复核"]):
                report.audit_methods.append(line)

            # 识别审计依据
            if "依据" in line or "根据" in line:
                if any(keyword in line for keyword in ["法规", "制度", "规定", "办法", "指引"]):
                    report.audit_basis.append(line)

    def _parse_findings_section(self, content: str, report: AuditReport) -> None:
        """解析审计发现章节"""
        lines = content.split("\n")
        current_finding = None

        import uuid

        for line in lines:
            line = line.strip()

            # 识别新的审计发现
            if self._is_finding_start(line):
                if current_finding:
                    report.findings.append(current_finding)

                current_finding = AuditFinding(
                    finding_id=f"FND-{uuid.uuid4().hex[:6].upper()}",
                    title=line.lstrip("- •*1234567890. ").strip(),
                    description="",
                )
            elif current_finding and line:
                # 追加到当前发现的描述中
                if current_finding.description:
                    current_finding.description += " " + line
                else:
                    current_finding.description = line

                # 识别风险等级
                if "高风险" in line or "严重" in line or "重大" in line:
                    current_finding.risk_level = "高风险"
                elif "中风险" in line or "中等" in line:
                    current_finding.risk_level = "中风险"
                elif "低风险" in line or "一般" in line or "轻微" in line:
                    current_finding.risk_level = "低风险"

                # 识别违规条款
                if "违反" in line or "不符合" in line or "违规" in line:
                    current_finding.violation = line

        # 添加最后一个发现
        if current_finding:
            report.findings.append(current_finding)

    def _is_finding_start(self, line: str) -> bool:
        """判断是否是审计发现的开始"""
        if not line or len(line) < 5:
            return False

        # 列表项格式
        if line.startswith(("- ", "• ", "* ")):
            return True

        # 数字编号格式
        import re
        if re.match(r"^\d+[.、）)]", line):
            return True

        # 包含问题关键词
        finding_keywords = ["存在", "发现", "问题", "不足", "缺陷", "违规", "风险", "隐患"]
        if any(keyword in line for keyword in finding_keywords) and len(line) < 100:
            return True

        return False

    def _parse_risk_assessment_section(self, content: str, report: AuditReport) -> None:
        """解析风险评估章节"""
        report.overall_risk_assessment = content.strip()

    def _parse_suggestions_section(self, content: str, report: AuditReport) -> None:
        """解析审计建议章节"""
        lines = content.split("\n")

        for line in lines:
            line = line.strip()
            if line and len(line) > 10:
                if line.startswith(("- ", "• ", "* ", "1.", "2.", "3.", "4.", "5.")):
                    cleaned = line.lstrip("- •*12345. ").strip()
                    if cleaned:
                        report.suggestions.append(cleaned)
                elif not line.startswith("【") and not line.startswith("("):
                    report.suggestions.append(line)

    def _categorize_findings_by_risk(self, report: AuditReport) -> None:
        """按风险等级对审计发现进行分类"""
        for finding in report.findings:
            if finding.risk_level == "高风险":
                report.high_risk_findings.append(finding)
            elif finding.risk_level == "中风险":
                report.medium_risk_findings.append(finding)
            else:
                report.low_risk_findings.append(finding)

    def generate_rectification_notice(
        self,
        report: AuditReport,
        deadline: str,
    ) -> str:
        """
        生成整改通知书

        Args:
            report: 审计报告
            deadline: 整改截止日期

        Returns:
            整改通知书内容
        """
        notice = f"""
整改通知书

编号：{report.report_id}-ZG
通知日期：{datetime.now().strftime('%Y年%m月%d日')}

致：{report.audited_unit}

根据《{report.project_name}》审计报告（报告编号：{report.report_id}），
现将审计发现的问题及整改要求通知如下：

一、需整改的主要问题
"""

        for i, finding in enumerate(report.high_risk_findings + report.medium_risk_findings, 1):
            notice += f"\n{i}. {finding.title}\n   {finding.description}\n"

        notice += f"""

二、整改要求
1. 请于 {deadline} 前完成所有问题的整改
2. 请制定详细的整改方案，明确整改责任人、整改措施和时间节点
3. 整改完成后请提交书面整改报告及相关证明材料

三、联系方式
联系人：审计部
联系电话：

特此通知。

审计部
{datetime.now().strftime('%Y年%m月%d日')}
"""

        return notice.strip()

    def export_report_markdown(self, report: AuditReport) -> str:
        """
        导出 Markdown 格式的审计报告

        Args:
            report: 审计报告对象

        Returns:
            Markdown 格式的报告内容
        """
        md = f"""# {report.project_name} - 审计报告

**报告编号：** {report.report_id}
**报告日期：** {report.report_date}
**报告版本：** {report.version}

---

## 一、审计概况

| 项目 | 内容 |
|------|------|
| 审计项目 | {report.project_name} |
| 被审计单位 | {report.audited_unit} |
| 审计期间 | {report.audit_period} |
| 审计类型 | {report.audit_type} |

### 1.1 审计范围

"""

        if report.audit_scope:
            for scope in report.audit_scope:
                md += f"- {scope}\n"
        else:
            md += "- 详见审计方案及相关文档\n"

        md += "\n### 1.2 审计方法\n\n"
        if report.audit_methods:
            for method in report.audit_methods:
                md += f"- {method}\n"
        else:
            md += "- 查阅资料、抽样检查、访谈了解、数据分析、穿行测试等\n"

        md += "\n### 1.3 审计依据\n\n"
        if report.audit_basis:
            for basis in report.audit_basis:
                md += f"- {basis}\n"
        else:
            md += "- 国家相关法律法规\n- 监管部门规章制度\n- 银行内部管理制度\n"

        md += "\n## 二、审计发现\n\n"

        # 高风险发现
        if report.high_risk_findings:
            md += "### 2.1 高风险问题\n\n"
            for i, finding in enumerate(report.high_risk_findings, 1):
                md += f"**{i}. {finding.title}**\n\n"
                md += f"{finding.description}\n\n"
                if finding.violation:
                    md += f"*违反条款：{finding.violation}*\n\n"

        # 中风险发现
        if report.medium_risk_findings:
            md += "### 2.2 中风险问题\n\n"
            for i, finding in enumerate(report.medium_risk_findings, 1):
                md += f"**{i}. {finding.title}**\n\n"
                md += f"{finding.description}\n\n"

        # 低风险发现
        if report.low_risk_findings:
            md += "### 2.3 低风险问题\n\n"
            for i, finding in enumerate(report.low_risk_findings, 1):
                md += f"{i}. {finding.title}\n\n"

        # 风险评估
        md += "\n## 三、风险评估\n\n"
        if report.overall_risk_assessment:
            md += f"{report.overall_risk_assessment}\n\n"
        else:
            md += "基于本次审计发现的问题，整体风险评估如下：\n\n"
            md += f"- 高风险问题：{len(report.high_risk_findings)} 项\n"
            md += f"- 中风险问题：{len(report.medium_risk_findings)} 项\n"
            md += f"- 低风险问题：{len(report.low_risk_findings)} 项\n"

        # 审计建议
        md += "\n## 四、审计建议\n\n"
        if report.suggestions:
            for i, suggestion in enumerate(report.suggestions, 1):
                md += f"{i}. {suggestion}\n\n"
        else:
            md += "针对上述审计发现，提出以下整改建议：\n\n"
            md += "- 高度重视高风险问题，立即制定整改方案\n"
            md += "- 完善内部控制制度，堵塞管理漏洞\n"
            md += "- 加强员工培训，提高合规意识\n"
            md += "- 建立长效机制，防止问题屡查屡犯\n"

        # 审计结论
        md += "\n## 五、审计结论\n\n"
        if report.audit_conclusion:
            md += f"{report.audit_conclusion}\n\n"
        else:
            md += "本次审计按照规定程序和方法实施，审计报告所附资料真实、完整。\n\n"
            md += "请被审计单位认真落实整改要求，并在规定时限内提交整改报告。\n"

        # 附录
        md += "\n---\n\n"
        md += "**本报告仅用于内部审计目的，请注意保密。**\n"

        return md
