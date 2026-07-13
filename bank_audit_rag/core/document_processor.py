"""
文档处理模块
提供文档加载、分割、元数据管理等功能
"""

import hashlib
import mimetypes
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bank_audit_rag.config.settings import Settings, get_settings
from bank_audit_rag.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DocumentChunk:
    """文档块"""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentMetadata:
    """文档元数据"""
    document_id: str
    filename: str
    file_path: str
    file_size: int = 0
    mime_type: str = ""
    document_type: str = ""
    business_line: str = ""
    custom_metadata: Dict[str, Any] = field(default_factory=dict)


class DocumentProcessor:
    """
    文档处理器
    支持多种文档格式的加载、分割和元数据提取
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        settings: Optional[Settings] = None,
    ):
        self.settings = settings or get_settings()
        self.chunk_size = chunk_size or self.settings.chunk_size
        self.chunk_overlap = chunk_overlap or self.settings.chunk_overlap
        logger.info(
            "document_processor_initialized",
            extra={"chunk_size": self.chunk_size, "chunk_overlap": self.chunk_overlap},
        )

    def validate_file(self, file_path: Path) -> Tuple[bool, str]:
        """
        验证文件是否有效

        Returns:
            (is_valid, error_message)
        """
        if not file_path.exists():
            return False, f"文件不存在: {file_path}"

        if not file_path.is_file():
            return False, f"路径不是文件: {file_path}"

        file_size = file_path.stat().st_size
        max_size = self.settings.max_file_size_mb * 1024 * 1024
        if file_size > max_size:
            return False, f"文件大小超过限制: {file_size} > {max_size}"

        return True, ""

    def detect_mime_type(self, file_path: Path) -> str:
        """检测文件 MIME 类型"""
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type is None:
            # 尝试根据扩展名判断
            ext = file_path.suffix.lower()
            ext_map = {
                ".txt": "text/plain",
                ".md": "text/markdown",
                ".pdf": "application/pdf",
                ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ".doc": "application/msword",
                ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ".csv": "text/csv",
                ".json": "application/json",
                ".html": "text/html",
            }
            mime_type = ext_map.get(ext, "application/octet-stream")
        return mime_type

    def generate_document_id(self, file_path: Path) -> str:
        """生成文档唯一 ID"""
        content = f"{file_path.name}:{file_path.stat().st_size}:{file_path.stat().st_mtime}"
        hash_str = hashlib.md5(content.encode()).hexdigest()[:12]
        return f"doc_{hash_str}"

    def load_document(self, file_path: Path) -> str:
        """加载文档内容"""
        mime_type = self.detect_mime_type(file_path)

        if mime_type.startswith("text/") or mime_type == "application/json":
            encoding = "utf-8" if mime_type != "application/json" else "utf-8"
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()

        # 对于其他格式，尝试用 langchain 加载器
        try:
            from langchain_community.document_loaders import (
                TextLoader,
                PyPDFLoader,
                Docx2txtLoader,
            )

            ext = file_path.suffix.lower()
            if ext == ".pdf":
                loader = PyPDFLoader(str(file_path))
            elif ext in (".docx", ".doc"):
                loader = Docx2txtLoader(str(file_path))
            else:
                loader = TextLoader(str(file_path))

            docs = loader.load()
            return "\n\n".join(doc.page_content for doc in docs)
        except ImportError:
            logger.warning("langchain_community not available, reading as text")
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

    def split_documents(self, documents: List[Any]) -> List[Any]:
        """
        分割文档列表

        Args:
            documents: LangChain Document 对象列表

        Returns:
            分割后的 Document 列表
        """
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
        except ImportError:
            logger.warning("langchain not available, returning original documents")
            return documents

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""],
        )

        chunks = splitter.split_documents(documents)

        # 为每个块添加 chunk_id
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_id"] = f"{chunk.metadata.get('source', 'doc')}_chunk_{i}"

        return chunks

    def split_text(self, text: str) -> List[DocumentChunk]:
        """分割纯文本"""
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
        except ImportError:
            # 简单分割
            words = text.split()
            chunks = []
            for i in range(0, len(words), self.chunk_size):
                chunk_text = " ".join(words[i:i + self.chunk_size])
                chunks.append(DocumentChunk(
                    id=f"chunk_{i}",
                    content=chunk_text,
                    metadata={"chunk_index": i},
                ))
            return chunks

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""],
        )

        texts = splitter.split_text(text)
        return [
            DocumentChunk(
                id=f"chunk_{i}",
                content=t,
                metadata={"chunk_index": i},
            )
            for i, t in enumerate(texts)
        ]

    def process_document(
        self,
        file_path: Any,
        document_type: str = "",
        business_line: str = "",
        **kwargs: Any,
    ) -> Tuple[List[DocumentChunk], DocumentMetadata]:
        """
        处理单个文档

        Args:
            file_path: 文件路径
            document_type: 文档类型
            business_line: 业务条线
            **kwargs: 额外元数据

        Returns:
            (文档块列表, 文档元数据)
        """
        file_path = Path(file_path) if not isinstance(file_path, Path) else file_path

        # 验证文件
        is_valid, error = self.validate_file(file_path)
        if not is_valid:
            raise ValueError(error)

        # 生成元数据
        doc_id = self.generate_document_id(file_path)
        mime_type = self.detect_mime_type(file_path)
        file_size = file_path.stat().st_size

        metadata = DocumentMetadata(
            document_id=doc_id,
            filename=file_path.name,
            file_path=str(file_path),
            file_size=file_size,
            mime_type=mime_type,
            document_type=document_type,
            business_line=business_line,
            custom_metadata=kwargs,
        )

        # 加载文档内容
        content = self.load_document(file_path)

        # 分割文档
        chunks = self.split_text(content)

        # 为每个块添加元数据
        for i, chunk in enumerate(chunks):
            chunk.id = f"{doc_id}_chunk_{i}"
            chunk.metadata.update({
                "document_id": doc_id,
                "filename": file_path.name,
                "chunk_index": i,
                "document_type": document_type,
                "business_line": business_line,
                **kwargs,
            })

        logger.info(
            "document_processed",
            extra={
                "document_id": doc_id,
                "doc_filename": file_path.name,
                "chunk_count": len(chunks),
                "file_size": file_size,
            },
        )

        return chunks, metadata


class DocumentStore:
    """
    文档存储管理器
    管理已处理文档的元数据和索引
    """

    def __init__(self, storage_path: str = "./data/document_store"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._documents: Dict[str, DocumentMetadata] = {}
        self._load_index()

    def _load_index(self) -> None:
        """加载文档索引"""
        index_file = self.storage_path / "index.json"
        if index_file.exists():
            import json
            with open(index_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for doc_id, doc_data in data.items():
                    self._documents[doc_id] = DocumentMetadata(**doc_data)

    def _save_index(self) -> None:
        """保存文档索引"""
        import json
        index_file = self.storage_path / "index.json"
        data = {
            doc_id: {
                "document_id": meta.document_id,
                "filename": meta.filename,
                "file_path": meta.file_path,
                "file_size": meta.file_size,
                "mime_type": meta.mime_type,
                "document_type": meta.document_type,
                "business_line": meta.business_line,
                "custom_metadata": meta.custom_metadata,
            }
            for doc_id, meta in self._documents.items()
        }
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_document(self, metadata: DocumentMetadata) -> None:
        """添加文档元数据"""
        self._documents[metadata.document_id] = metadata
        self._save_index()

    def get_document(self, document_id: str) -> Optional[DocumentMetadata]:
        """获取文档元数据"""
        return self._documents.get(document_id)

    def list_documents(self) -> List[DocumentMetadata]:
        """列出所有文档"""
        return list(self._documents.values())

    def remove_document(self, document_id: str) -> bool:
        """删除文档"""
        if document_id in self._documents:
            del self._documents[document_id]
            self._save_index()
            return True
        return False
