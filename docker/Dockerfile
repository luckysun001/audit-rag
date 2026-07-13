# 使用官方 Python 镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Poetry
RUN pip install --no-cache-dir poetry==1.7.*

# 配置 Poetry
RUN poetry config virtualenvs.create false

# 复制依赖文件
COPY pyproject.toml ./

# 安装依赖
RUN poetry install --no-interaction --no-ansi --without dev,docs

# 复制应用代码
COPY bank_audit_rag/ ./bank_audit_rag/

# 创建数据目录
RUN mkdir -p /app/data/chroma

# 暴露端口
EXPOSE 8080 9090

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# 启动命令
CMD ["uvicorn", "bank_audit_rag.api.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4"]
