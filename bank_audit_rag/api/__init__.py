"""
FastAPI 应用入口 - 银行审计版
提供 RESTful API 接口
"""

import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from bank_audit_rag.config.settings import Settings, get_settings
from bank_audit_rag.core.audit_report import AuditReport, AuditReportService
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
from bank_audit_rag.core.risk_management import (
    CreditRiskAssessmentResult,
    RiskManagementService,
)
from bank_audit_rag.utils.logger import RequestLogger, get_logger, root_logger

logger = get_logger(__name__)
request_logger = RequestLogger(root_logger)


# Pydantic 模型
class QueryRequest(BaseModel):
    """查询请求"""
    question: str = Field(..., description="问题")
    collection_name: Optional[str] = Field(None, description="集合名称")
    k: Optional[int] = Field(None, description="返回结果数量")
    stream: bool = Field(False, description="是否流式输出")
    use_cache: bool = Field(True, description="是否使用缓存")
    chat_history: Optional[List[Dict[str, str]]] = Field(None, description="对话历史")


class LoanReviewRequest(BaseModel):
    """贷款三查核查请求"""
    loan_id: str = Field(..., description="贷款编号")
    customer_name: str = Field(..., description="借款人名称")
    loan_amount: float = Field(..., description="贷款金额（元）")
    loan_term: int = Field(12, description="贷款期限（月）")
    guarantee_type: str = Field("信用", description="担保方式")
    collection_name: Optional[str] = Field(None, description="集合名称")


class ContractComplianceRequest(BaseModel):
    """合同合规检查请求"""
    contract_id: str = Field(..., description="合同编号")
    contract_type: str = Field(..., description="合同类型")
    loan_amount: float = Field(..., description="贷款金额")
    sign_date: str = Field(..., description="签订日期")
    collection_name: Optional[str] = Field(None, description="集合名称")


class RegulatoryComplianceRequest(BaseModel):
    """监管合规检查请求"""
    audit_content: str = Field(..., description="审计内容")
    business_line: str = Field(..., description="业务条线")
    regulatory_type: str = Field("all", description="监管类型")
    collection_name: Optional[str] = Field(None, description="集合名称")


class AMLComplianceRequest(BaseModel):
    """反洗钱合规检查请求"""
    customer_name: str = Field(..., description="客户名称")
    customer_type: str = Field(..., description="客户类型")
    risk_level: str = Field("未评级", description="风险等级")
    check_period: str = Field("近一年", description="检查期间")
    collection_name: Optional[str] = Field(None, description="集合名称")


class CreditRiskRequest(BaseModel):
    """信用风险评估请求"""
    customer_name: str = Field(..., description="客户名称")
    customer_type: str = Field(..., description="客户类型")
    industry: str = Field(..., description="所属行业")
    credit_limit: float = Field(..., description="授信额度（元）")
    assessment_date: Optional[str] = Field(None, description="评估日期")
    collection_name: Optional[str] = Field(None, description="集合名称")


class AuditReportRequest(BaseModel):
    """审计报告生成请求"""
    project_name: str = Field(..., description="审计项目名称")
    audited_unit: str = Field(..., description="被审计单位")
    audit_period: str = Field(..., description="审计期间")
    audit_type: str = Field("专项审计", description="审计类型")
    findings_data: Optional[List[Dict[str, Any]]] = Field(None, description="审计发现数据")
    collection_name: Optional[str] = Field(None, description="集合名称")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    timestamp: str
    services: Dict[str, bool]


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """
    创建 FastAPI 应用实例

    Args:
        settings: 配置实例

    Returns:
        FastAPI 应用实例
    """
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """应用生命周期管理"""
        # 启动时初始化
        logger.info("starting_bank_audit_rag_service")

        # 初始化核心服务
        app.state.document_processor = __import__('bank_audit_rag').DocumentProcessor(settings)
        app.state.vector_store_service = __import__('bank_audit_rag').VectorStoreService(settings)
        app.state.rag_engine = __import__('bank_audit_rag').RAGQueryEngine(settings)

        # 初始化审计专用服务
        app.state.credit_audit_service = CreditAuditService(app.state.rag_engine)
        app.state.compliance_audit_service = ComplianceAuditService(app.state.rag_engine)
        app.state.risk_management_service = RiskManagementService(app.state.rag_engine)
        app.state.audit_report_service = AuditReportService(app.state.rag_engine)

        logger.info("bank_audit_rag_service_started")
        yield
        # 关闭时清理
        logger.info("shutting_down_bank_audit_rag_service")

    app = FastAPI(
        title="Bank Audit RAG Service",
        description="银行审计部智能检索问答系统 API",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # CORS 配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 请求日志中间件
    @app.middleware("http")
    async def log_requests(request, call_next):
        start_time = time.time()
        request_id = str(uuid.uuid4())

        # 添加请求 ID 到响应头
        response = await call_next(request)
        duration = time.time() - start_time

        # 记录请求日志
        request_logger.log_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=duration,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            request_id=request_id,
        )

        response.headers["X-Request-ID"] = request_id
        return response

    # 依赖注入
    def get_credit_audit_service() -> CreditAuditService:
        return app.state.credit_audit_service

    def get_compliance_audit_service() -> ComplianceAuditService:
        return app.state.compliance_audit_service

    def get_risk_management_service() -> RiskManagementService:
        return app.state.risk_management_service

    def get_audit_report_service() -> AuditReportService:
        return app.state.audit_report_service

    # 健康检查
    @app.get("/health", response_model=HealthResponse, tags=["System"])
    async def health_check() -> HealthResponse:
        """健康检查端点"""
        import datetime

        services = {
            "vector_store": True,
            "embedding_service": True,
            "credit_audit_service": True,
            "compliance_audit_service": True,
            "risk_management_service": True,
            "audit_report_service": True,
        }

        return HealthResponse(
            status="healthy",
            version="2.0.0",
            timestamp=datetime.datetime.now().isoformat(),
            services=services,
        )

    # ========================================================================
    # 信贷审计接口
    # ========================================================================

    @app.post(
        "/api/v1/credit/loan-review",
        response_model=LoanReviewResult,
        tags=["信贷审计"],
        summary="贷款三查核查",
        description="对贷款的贷前调查、贷中审查、贷后检查情况进行全面核查评估",
    )
    async def loan_review_check(
        request: LoanReviewRequest,
        service: CreditAuditService = Depends(get_credit_audit_service),
    ) -> LoanReviewResult:
        try:
            return service.loan_three_review_check(
                loan_id=request.loan_id,
                customer_name=request.customer_name,
                loan_amount=request.loan_amount,
                loan_term=request.loan_term,
                guarantee_type=request.guarantee_type,
                collection_name=request.collection_name,
            )
        except Exception as e:
            logger.error("loan_review_check_failed", error=str(e))
            raise HTTPException(status_code=500, detail=f"贷款三查核查失败: {str(e)}")

    @app.post(
        "/api/v1/credit/contract-compliance",
        response_model=ContractComplianceResult,
        tags=["信贷审计"],
        summary="信贷合同合规检查",
        description="对信贷合同的要素完整性、利率合规性、担保合规性等进行检查",
    )
    async def contract_compliance_check(
        request: ContractComplianceRequest,
        service: CreditAuditService = Depends(get_credit_audit_service),
    ) -> ContractComplianceResult:
        try:
            return service.contract_compliance_check(
                contract_id=request.contract_id,
                contract_type=request.contract_type,
                loan_amount=request.loan_amount,
                sign_date=request.sign_date,
                collection_name=request.collection_name,
            )
        except Exception as e:
            logger.error("contract_compliance_check_failed", error=str(e))
            raise HTTPException(status_code=500, detail=f"合同合规检查失败: {str(e)}")

    # ========================================================================
    # 合规审计接口
    # ========================================================================

    @app.post(
        "/api/v1/compliance/regulatory",
        response_model=RegulatoryComplianceResult,
        tags=["合规审计"],
        summary="监管合规检查",
        description="基于监管政策库，对审计内容进行合规性匹配和评估",
    )
    async def regulatory_compliance_check(
        request: RegulatoryComplianceRequest,
        service: ComplianceAuditService = Depends(get_compliance_audit_service),
    ) -> RegulatoryComplianceResult:
        try:
            return service.check_regulatory_compliance(
                audit_content=request.audit_content,
                business_line=request.business_line,
                regulatory_type=request.regulatory_type,
                collection_name=request.collection_name,
            )
        except Exception as e:
            logger.error("regulatory_compliance_check_failed", error=str(e))
            raise HTTPException(status_code=500, detail=f"监管合规检查失败: {str(e)}")

    @app.post(
        "/api/v1/compliance/aml",
        response_model=AMLComplianceResult,
        tags=["合规审计"],
        summary="反洗钱合规检查",
        description="对客户进行 KYC、交易监测、制裁筛查等反洗钱合规检查",
    )
    async def aml_compliance_check(
        request: AMLComplianceRequest,
        service: ComplianceAuditService = Depends(get_compliance_audit_service),
    ) -> AMLComplianceResult:
        try:
            return service.aml_compliance_check(
                customer_name=request.customer_name,
                customer_type=request.customer_type,
                risk_level=request.risk_level,
                check_period=request.check_period,
                collection_name=request.collection_name,
            )
        except Exception as e:
            logger.error("aml_compliance_check_failed", error=str(e))
            raise HTTPException(status_code=500, detail=f"反洗钱合规检查失败: {str(e)}")

    # ========================================================================
    # 风险管理接口
    # ========================================================================

    @app.post(
        "/api/v1/risk/credit-assessment",
        response_model=CreditRiskAssessmentResult,
        tags=["风险管理"],
        summary="信用风险评估",
        description="对客户的信用风险进行多维度综合评估",
    )
    async def credit_risk_assessment(
        request: CreditRiskRequest,
        service: RiskManagementService = Depends(get_risk_management_service),
    ) -> CreditRiskAssessmentResult:
        try:
            return service.assess_credit_risk(
                customer_name=request.customer_name,
                customer_type=request.customer_type,
                industry=request.industry,
                credit_limit=request.credit_limit,
                assessment_date=request.assessment_date,
                collection_name=request.collection_name,
            )
        except Exception as e:
            logger.error("credit_risk_assessment_failed", error=str(e))
            raise HTTPException(status_code=500, detail=f"信用风险评估失败: {str(e)}")

    # ========================================================================
    # 审计报告接口
    # ========================================================================

    @app.post(
        "/api/v1/report/generate",
        response_model=AuditReport,
        tags=["审计报告"],
        summary="生成审计报告",
        description="基于审计发现和相关文档，自动生成完整的审计报告",
    )
    async def generate_audit_report(
        request: AuditReportRequest,
        service: AuditReportService = Depends(get_audit_report_service),
    ) -> AuditReport:
        try:
            return service.generate_audit_report(
                project_name=request.project_name,
                audited_unit=request.audited_unit,
                audit_period=request.audit_period,
                audit_type=request.audit_type,
                findings_data=request.findings_data,
                collection_name=request.collection_name,
            )
        except Exception as e:
            logger.error("generate_audit_report_failed", error=str(e))
            raise HTTPException(status_code=500, detail=f"审计报告生成失败: {str(e)}")

    @app.post(
        "/api/v1/report/export-markdown",
        tags=["审计报告"],
        summary="导出 Markdown 格式审计报告",
    )
    async def export_report_markdown(
        report: AuditReport,
        service: AuditReportService = Depends(get_audit_report_service),
    ) -> Dict[str, str]:
        try:
            markdown_content = service.export_report_markdown(report)
            return {
                "report_id": report.report_id,
                "markdown": markdown_content,
            }
        except Exception as e:
            logger.error("export_report_markdown_failed", error=str(e))
            raise HTTPException(status_code=500, detail=f"导出 Markdown 失败: {str(e)}")

    # ========================================================================
    # 文档管理接口
    # ========================================================================

    @app.post("/api/v1/documents/upload", tags=["文档管理"])
    async def upload_document(
        file: UploadFile = File(...),
        document_type: str = Form("通用文档"),
        collection_name: Optional[str] = Form(None),
    ) -> Dict[str, Any]:
        """上传审计文档"""
        start_time = time.time()

        try:
            # 这里实现实际的文件上传和索引逻辑
            duration = time.time() - start_time

            return {
                "success": True,
                "filename": file.filename,
                "document_type": document_type,
                "collection": collection_name or "default",
                "duration_ms": round(duration * 1000, 2),
            }

        except Exception as e:
            logger.error("document_upload_failed", error=str(e))
            raise HTTPException(status_code=500, detail=f"文档上传失败: {str(e)}")

    # ========================================================================
    # 通用查询接口
    # ========================================================================

    @app.post("/api/v1/query", tags=["通用查询"])
    async def query(request: QueryRequest) -> Dict[str, Any]:
        """
        通用 RAG 查询接口

        - **question**: 问题（必填）
        - **collection_name**: 集合名称（可选）
        - **k**: 返回结果数量（可选）
        """
        try:
            # 这里实现实际的查询逻辑
            return {
                "answer": f"已收到您的查询: {request.question}",
                "question": request.question,
                "sources": [],
                "confidence": 0.95,
                "latency_ms": 100,
            }

        except Exception as e:
            logger.error("query_failed", error=str(e))
            raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

    # 错误处理器
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        logger.error(
            "http_exception",
            path=request.url.path,
            status_code=exc.status_code,
            detail=exc.detail,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "error": type(exc).__name__},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        logger.error(
            "unhandled_exception",
            path=request.url.path,
            error=str(exc),
            exc_info=exc,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "服务器内部错误", "error": type(exc).__name__},
        )

    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "bank_audit_rag.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        reload=settings.api_reload,
        log_level="info" if settings.is_production else "debug",
    )
