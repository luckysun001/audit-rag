"""
向量存储模块
提供 Embedding 服务和向量存储管理
"""

import functools
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from bank_audit_rag.config.settings import Settings, get_settings
from bank_audit_rag.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RAGResult:
    """RAG 查询结果"""
    question: str
    answer: str = ""
    sources: List[Dict[str, Any]] = field(default_factory=list)
    context: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0


class EmbeddingService:
    """
    Embedding 服务
    支持多种 Embedding 提供商
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._model = None
        self._embed_texts_cache: Dict[tuple, List[List[float]]] = {}
        self._initialize_model()

    def _initialize_model(self) -> None:
        """初始化 Embedding 模型"""
        provider = self.settings.embedding_provider.lower()

        try:
            if provider == "openai":
                from langchain_openai import OpenAIEmbeddings
                self._model = OpenAIEmbeddings(
                    model=self.settings.embedding_model,
                    openai_api_key=self.settings.embedding_api_key,
                    openai_api_base=self.settings.embedding_base_url or None,
                )
                logger.info("embedding_model_initialized", extra={"provider": provider, "model": self.settings.embedding_model})
            else:
                logger.warning(f"Unknown embedding provider: {provider}, using fallback")
                self._model = None
        except ImportError:
            logger.warning("langchain_openai not available, embedding service will use mock mode")
            self._model = None
        except Exception as e:
            logger.warning(f"Failed to initialize embedding model: {e}")
            self._model = None

    @functools.lru_cache(maxsize=4096)
    def embed_text(self, text: str) -> List[float]:
        """生成文本的 Embedding 向量（结果按文本缓存，避免重复计算/重复调用 API）"""
        if self._model is not None:
            try:
                return self._model.embed_query(text)
            except Exception as e:
                logger.warning(f"Embedding failed, using mock: {e}")

        # Mock embedding (deterministic hash-based)
        return self._mock_embed(text)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """批量生成 Embedding（相同文本列表直接走缓存）"""
        cache_key = tuple(texts)
        if cache_key in self._embed_texts_cache:
            return self._embed_texts_cache[cache_key]

        if self._model is not None:
            try:
                result = self._model.embed_documents(texts)
            except Exception as e:
                logger.warning(f"Batch embedding failed, using mock: {e}")
                result = [self._mock_embed(text) for text in texts]
        else:
            result = [self._mock_embed(text) for text in texts]

        if len(self._embed_texts_cache) < 1024:
            self._embed_texts_cache[cache_key] = result
        return result

    def _mock_embed(self, text: str) -> List[float]:
        """Mock embedding for fallback mode"""
        import hashlib
        import struct

        hash_bytes = hashlib.sha256(text.encode()).digest()
        # 生成 128 维的 mock 向量
        vector = []
        for i in range(0, min(len(hash_bytes), 128 * 4), 4):
            chunk = hash_bytes[i:i + 4] if i + 4 <= len(hash_bytes) else hash_bytes[i:] + b'\x00' * (4 - (len(hash_bytes) - i))
            val = struct.unpack('f', chunk)[0]
            vector.append(val)

        # 归一化
        import math
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]


class VectorStoreService:
    """
    向量存储服务
    支持 ChromaDB 和内存存储
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._store = None
        self._embedding = EmbeddingService(self.settings)
        self._initialize_store()

    def _initialize_store(self) -> None:
        """初始化向量存储"""
        store_type = self.settings.vector_store_type.lower()

        try:
            if store_type == "chroma":
                from langchain_community.vectorstores import Chroma
                self._store_type = "chroma"
                logger.info("vector_store_initialized", extra={"type": store_type, "path": self.settings.vector_store_path})
            else:
                self._store_type = "memory"
                self._memory_store: Dict[str, List[Any]] = {}
                logger.info("vector_store_initialized", extra={"type": "memory"})
        except ImportError:
            self._store_type = "memory"
            self._memory_store: Dict[str, List[Any]] = {}
            logger.warning("chromadb not available, using in-memory store")

    def add_documents(
        self,
        documents: List[Any],
        collection_name: str = "default",
    ) -> List[str]:
        """
        添加文档到向量存储

        Args:
            documents: LangChain Document 对象列表
            collection_name: 集合名称

        Returns:
            文档 ID 列表
        """
        ids = [f"doc_{i}" for i in range(len(documents))]

        if self._store_type == "chroma":
            try:
                from langchain_community.vectorstores import Chroma
                store = Chroma.from_documents(
                    documents=documents,
                    embedding=self._embedding._model or self._embedding,
                    collection_name=collection_name,
                    persist_directory=self.settings.vector_store_path,
                )
                logger.info("documents_added_to_chroma", extra={"count": len(documents), "collection": collection_name})
                return ids
            except Exception as e:
                logger.warning(f"Failed to add to Chroma, storing in memory: {e}")

        # 内存存储
        if not hasattr(self, "_memory_store"):
            self._memory_store = {}
        if collection_name not in self._memory_store:
            self._memory_store[collection_name] = []
        self._memory_store[collection_name].extend(documents)

        logger.info("documents_added_to_memory", extra={"count": len(documents), "collection": collection_name})
        return ids

    def similarity_search(
        self,
        query: str,
        collection_name: str = "default",
        top_k: Optional[int] = None,
    ) -> List[Any]:
        """
        相似度搜索

        Returns:
            匹配的 Document 列表
        """
        top_k = top_k or self.settings.retrieval_top_k

        if self._store_type == "chroma":
            try:
                from langchain_community.vectorstores import Chroma
                store = Chroma(
                    collection_name=collection_name,
                    embedding_function=self._embedding._model or self._embedding,
                    persist_directory=self.settings.vector_store_path,
                )
                results = store.similarity_search_with_score(query, k=top_k)
                return [doc for doc, score in results]
            except Exception as e:
                logger.warning(f"Chroma search failed, using memory: {e}")

        # 内存搜索（简单文本匹配）
        docs = self._memory_store.get(collection_name, []) if hasattr(self, "_memory_store") else []
        query_lower = query.lower()
        scored = []
        for doc in docs:
            content = doc.page_content if hasattr(doc, "page_content") else str(doc)
            content_lower = content.lower()
            score = sum(1 for word in query_lower.split() if word in content_lower)
            scored.append((doc, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [doc for doc, score in scored[:top_k]]

    def get_collection_stats(self, collection_name: str = "default") -> Dict[str, Any]:
        """获取集合统计信息"""
        if self._store_type == "memory" and hasattr(self, "_memory_store"):
            count = len(self._memory_store.get(collection_name, []))
        else:
            count = 0

        return {
            "collection_name": collection_name,
            "document_count": count,
            "store_type": self._store_type,
        }
