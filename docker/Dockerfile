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
# 必须与生成 poetry.lock 的版本一致：Poetry 2.x 产出的 lock-version 2.1
# 无法被 1.7 读取，版本不匹配会直接让构建失败
RUN pip install --no-cache-dir "poetry==2.*"

# 配置 Poetry
RUN poetry config virtualenvs.create false

# 复制依赖文件（连同 lock，保证镜像构建可复现）
COPY pyproject.toml poetry.lock ./

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
