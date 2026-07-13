"""
Document Processor 单元测试
"""

import tempfile
from pathlib import Path

import pytest

from bank_audit_rag import DocumentProcessor


@pytest.fixture
def document_processor():
    """创建文档处理器实例"""
    return DocumentProcessor()


@pytest.fixture
def temp_text_file():
    """创建临时文本文件"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("""
这是一个测试文档。
包含多行文本内容。

用于验证文档加载和分割功能。

第一部分：这是第一部分的内容，主要介绍项目背景和目标。
我们的目标是创建一个高质量的 RAG 系统。

第二部分：这是第二部分的内容，介绍技术实现方案。
使用 LangChain 作为基础框架，集成多种向量数据库。

第三部分：这是第三部分的内容，介绍部署和运维方案。
支持 Docker 容器化部署，提供完整的监控和日志系统。
""")
        file_path = Path(f.name)

    yield file_path

    # 清理
    if file_path.exists():
        file_path.unlink()


class TestDocumentProcessor:
    """文档处理器测试"""

    def test_initialization(self, document_processor):
        """测试初始化"""
        assert document_processor.chunk_size == 1000
        assert document_processor.chunk_overlap == 200

    def test_validate_file_success(self, document_processor, temp_text_file):
        """测试文件验证 - 成功"""
        is_valid, error = document_processor.validate_file(temp_text_file)
        assert is_valid
        assert error == ""

    def test_validate_file_not_exists(self, document_processor):
        """测试文件验证 - 文件不存在"""
        is_valid, error = document_processor.validate_file(Path("/nonexistent/file.txt"))
        assert not is_valid
        assert "不存在" in error

    def test_detect_mime_type(self, document_processor, temp_text_file):
        """测试 MIME 类型检测"""
        mime_type = document_processor.detect_mime_type(temp_text_file)
        # text/plain 或 application/octet-stream 都可以接受
        assert "text" in mime_type or "octet-stream" in mime_type

    def test_generate_document_id(self, document_processor, temp_text_file):
        """测试文档 ID 生成"""
        doc_id = document_processor.generate_document_id(temp_text_file)
        assert doc_id.startswith("doc_")
        assert len(doc_id) > 5  # doc_ + hash

    def test_split_documents(self, document_processor):
        """测试文档分割"""
        from langchain_core.documents import Document

        # 创建长文档（超过 chunk_size=1000）
        long_text = "这是第一句话。" * 200
        docs = [Document(page_content=long_text, metadata={"source": "test"})]

        chunks = document_processor.split_documents(docs)
        assert len(chunks) > 1
        assert all("chunk_id" in chunk.metadata for chunk in chunks)

    def test_process_document(self, document_processor, temp_text_file):
        """测试处理单个文档"""
        chunks, metadata = document_processor.process_document(temp_text_file)

        assert len(chunks) > 0
        assert metadata.filename == temp_text_file.name
        assert metadata.document_id.startswith("doc_")

        # 验证每个块
        for chunk in chunks:
            assert len(chunk.content) > 0
            assert chunk.id is not None


class TestDocumentMetadata:
    """文档元数据测试"""

    def test_custom_metadata(self, document_processor, temp_text_file):
        """测试自定义元数据"""
        custom_meta = {
            "department": "审计部",
            "year": 2024,
            "audit_type": "财务审计",
        }

        chunks, metadata = document_processor.process_document(
            temp_text_file,
            **custom_meta
        )

        # 验证自定义元数据被正确传递
        assert metadata.custom_metadata["department"] == "审计部"
        assert metadata.custom_metadata["year"] == 2024
        assert metadata.custom_metadata["audit_type"] == "财务审计"

        # 验证文档块中也包含元数据
        assert chunks[0].metadata.get("department") == "审计部"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
