"""
RAG 查询引擎
整合向量检索和大语言模型，提供端到端的 RAG 查询能力
"""

import time
from typing import Any, Dict, List, Optional

from bank_audit_rag.config.settings import Settings, get_settings
from bank_audit_rag.core.vector_store import RAGResult, VectorStoreService
from bank_audit_rag.utils.logger import get_logger

logger = get_logger(__name__)


class RAGQueryEngine:
    """
    RAG 查询引擎

    整合向量存储检索和 LLM 生成，提供完整的 RAG 问答能力。
    支持 mock 模式（无 API Key 时自动降级）。
    """

    def __init__(
        self,
        vector_store: Optional[VectorStoreService] = None,
        settings: Optional[Settings] = None,
    ):
        self.settings = settings or get_settings()
        self.vector_store = vector_store or VectorStoreService(self.settings)
        self._llm = None
        self._initialize_llm()

    def _initialize_llm(self) -> None:
        """初始化 LLM"""
        provider = self.settings.llm_provider.lower()

        try:
            if provider == "openai":
                from langchain_openai import ChatOpenAI
                self._llm = ChatOpenAI(
                    model=self.settings.llm_model,
                    openai_api_key=self.settings.llm_api_key,
                    openai_api_base=self.settings.llm_base_url or None,
                    temperature=self.settings.llm_temperature,
                    max_tokens=self.settings.llm_max_tokens,
                )
                logger.info("llm_initialized", extra={"provider": provider, "model": self.settings.llm_model})
            else:
                logger.warning(f"Unknown LLM provider: {provider}, using mock mode")
                self._llm = None
        except ImportError:
            logger.warning("langchain_openai not available, LLM will use mock mode")
            self._llm = None
        except Exception as e:
            logger.warning(f"Failed to initialize LLM: {e}")
            self._llm = None

    @property
    def is_mock_mode(self) -> bool:
        """是否处于 mock 模式"""
        return self._llm is None

    def query(
        self,
        question: str,
        collection_name: str = "default",
        custom_prompt: Optional[Any] = None,
        prompt_variables: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None,
    ) -> RAGResult:
        """
        执行 RAG 查询

        Args:
            question: 用户问题
            collection_name: 向量集合名称
            custom_prompt: 自定义 Prompt 模板
            prompt_variables: Prompt 变量
            top_k: 检索结果数量

        Returns:
            RAG 查询结果
        """
        start_time = time.perf_counter()

        logger.info(
            "rag_query_started",
            extra={"question": question[:100], "collection": collection_name},
        )

        # 1. 检索相关文档
        sources = self.vector_store.similarity_search(
            query=question,
            collection_name=collection_name,
            top_k=top_k,
        )

        # 2. 构建上下文
        context = self._build_context(sources)

        # 3. 生成回答
        if self._llm is not None:
            answer = self._generate_with_llm(
                question=question,
                context=context,
                custom_prompt=custom_prompt,
                prompt_variables=prompt_variables,
            )
        else:
            answer = self._generate_mock_answer(question, context, sources)

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        result = RAGResult(
            question=question,
            answer=answer,
            sources=[
                {
                    "content": doc.page_content[:200] if hasattr(doc, "page_content") else str(doc)[:200],
                    "metadata": doc.metadata if hasattr(doc, "metadata") else {},
                }
                for doc in sources
            ],
            context=context,
            metadata={
                "collection_name": collection_name,
                "source_count": len(sources),
                "mock_mode": self.is_mock_mode,
            },
            latency_ms=round(elapsed_ms, 2),
        )

        logger.info(
            "rag_query_completed",
            extra={
                "source_count": len(sources),
                "latency_ms": result.latency_ms,
                "mock_mode": self.is_mock_mode,
            },
        )

        return result

    def _build_context(self, sources: List[Any]) -> str:
        """构建上下文文本"""
        if not sources:
            return "（暂无相关文档）"

        context_parts = []
        for i, doc in enumerate(sources, 1):
            content = doc.page_content if hasattr(doc, "page_content") else str(doc)
            context_parts.append(f"[文档{i}]\n{content}")

        return "\n\n".join(context_parts)

    def _generate_with_llm(
        self,
        question: str,
        context: str,
        custom_prompt: Optional[Any] = None,
        prompt_variables: Optional[Dict[str, Any]] = None,
    ) -> str:
        """使用 LLM 生成回答"""
        prompt_variables = prompt_variables or {}

        try:
            if custom_prompt is not None:
                # 使用自定义 Prompt 模板
                variables = {"context": context, "question": question, **prompt_variables}
                # 过滤掉模板中不存在的变量
                input_variables = set()
                if hasattr(custom_prompt, "input_variables"):
                    input_variables = set(custom_prompt.input_variables)
                filtered = {k: v for k, v in variables.items() if k in input_variables}
                messages = custom_prompt.format_messages(**filtered)
            else:
                # 使用默认 Prompt
                from langchain_core.prompts import ChatPromptTemplate
                default_prompt = ChatPromptTemplate.from_messages([
                    ("system", "你是一位银行审计专家。请基于以下文档信息回答问题。\n\n【文档信息】\n{context}"),
                    ("human", "{question}"),
                ])
                messages = default_prompt.format_messages(context=context, question=question)

            response = self._llm.invoke(messages)
            return response.content if hasattr(response, "content") else str(response)

        except Exception as e:
            logger.warning(f"LLM generation failed, using mock: {e}")
            return self._generate_mock_answer(question, context, [])

    def _generate_mock_answer(
        self,
        question: str,
        context: str,
        sources: List[Any],
    ) -> str:
        """生成 mock 回答（无 LLM 时的降级方案）"""
        source_count = len(sources)

        answer = f"""[Mock 模式 - 未配置 LLM API Key]

问题: {question}

基于检索到的 {source_count} 个相关文档，以下是分析结果:

【检索上下文摘要】
{context[:500]}...

注意: 当前运行在 Mock 模式，未接入真实 LLM。请配置 OPENAI_API_KEY 环境变量以启用完整的 RAG 问答功能。
"""
        return answer

    def index_documents(
        self,
        documents: List[Any],
        collection_name: str = "default",
    ) -> List[str]:
        """索引文档到向量存储"""
        return self.vector_store.add_documents(documents, collection_name)

    def get_stats(self) -> Dict[str, Any]:
        """获取引擎统计信息"""
        return {
            "mock_mode": self.is_mock_mode,
            "llm_provider": self.settings.llm_provider,
            "llm_model": self.settings.llm_model,
            "embedding_provider": self.settings.embedding_provider,
            "vector_store_type": self.settings.vector_store_type,
        }
