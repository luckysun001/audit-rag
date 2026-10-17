# 银行审计 RAG 系统

面向银行审计领域的检索增强生成（RAG）系统。
信贷三查比对 · 合规检查 · 风险评估 · 报告生成

[![CI](https://github.com/luckysun001/audit-rag/actions/workflows/ci.yml/badge.svg)](https://github.com/luckysun001/audit-rag/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)

> **状态：Beta (v2.0.0)** — 检索 → 上下文构建 → 生成的完整 RAG 链路已跑通，
> 向量存储支持 ChromaDB 持久化并可在无 API Key / 无依赖时自动降级到内存与 mock 向量。

---

## 已实现

### 检索与生成

- **RAG 查询引擎**（`core/rag_engine.py`）：`检索 → 构建上下文 → LLM 生成` 端到端链路，
  返回 `answer / sources / context / metadata / latency_ms` 完整结果对象
- **双模式生成**：配置 API Key 时调用 `ChatOpenAI`；未配置或依赖缺失时自动降级为 mock 回答
  （`is_mock_mode` 可查询，结果 `metadata.mock_mode` 会标记），**无需 Key 也能跑通示例**
- **自定义 Prompt 注入**：可传入审计专用模板，引擎会按模板 `input_variables` 自动过滤变量

### 向量存储（`core/vector_store.py`）

- **双后端**：ChromaDB 持久化（`./data/chroma`）优先，导入失败自动回退内存存储
- **Embedding 服务**：`OpenAIEmbeddings` 主路径 + 确定性哈希 mock 向量（128 维、归一化）兜底
- **两级缓存**：单条文本 `lru_cache(4096)`、批量文本结果缓存，避免重复调用计费接口
- 支持 `add_documents` / `similarity_search`（Chroma 带相似度分，内存按词频打分）/ `get_collection_stats`

### 文档处理（`core/document_processor.py`）

- **多格式加载**：纯文本与 JSON 直接读取，PDF 走 `PyPDFLoader`，`.doc/.docx` 走 `Docx2txtLoader`；
  无 `langchain_community` 时回退为文本读取
- **中文友好分块**：`RecursiveCharacterTextSplitter`，分隔符覆盖中英文句读；
  依赖缺失时有等价的简易切分回退（默认 chunk 1000 / overlap 200）
- **元数据与索引**：文件校验（存在性、类型、50MB 上限）、MIME 检测、内容哈希生成文档 ID、
  每个分块携带 `document_id/filename/chunk_index/document_type/business_line`
- **DocumentStore**：文档元数据以 `index.json` 落盘，支持 `add / get / list / remove`

### 审计能力

- **7 个专业 Prompt 模板**（`core/audit_prompts.py`）：贷款三查、信贷合同合规、监管政策匹配、
  反洗钱、财务报表真实性、信用风险评估、审计报告生成；可通过 `BankAuditPrompts.get_prompt()` 取用
- **四大核心服务**：信贷三查比对、合规检查、风险评估、报告生成
  （`credit_audit.py` / `compliance_audit.py` / `risk_management.py` / `audit_report.py`）
- **结构化结果解析**：正则提取 + 关键词匹配，输出违规分级与置信度评分

### 工程能力

- **配置中心**（`config/settings.py`）：dataclass + `.env` 自动加载（无 `python-dotenv` 时内置简易解析），
  覆盖 LLM / Embedding / 向量库 / 分块 / 检索 / 日志 / API 七组参数，单例 `get_settings()`
- **结构化日志**（`utils/logger.py`）：`StructuredFormatter`、`Timer`、`LoggingContext`、`RequestLogger`
- **FastAPI 入口**（`api/main.py`）：应用工厂 + CORS + `/health` + `/api/v1/stats`，依赖缺失时优雅降级

## 未实现（TODO）

- 混合检索（BM25 + 向量）与相关性重排（rerank）
- OCR：扫描件 / 图片型 PDF 的文字识别
- 知识库增量更新：文档删除后向量库中对应向量的清理与索引重建
- API 层扩充：认证鉴权、限流中间件，以及审计业务端点（当前仅 health / stats）
- Redis 缓存接入（依赖已声明，代码未使用）
- 审计规则库：监管规则 YAML（条款、阈值、处罚依据）
- 其他向量库后端（Milvus 等，`settings` 已预留 host/port 但未接线）
- 前端界面：Streamlit 审计工作台
- 测试覆盖：目前仅 `test_document_processor.py`，RAG 引擎 / 向量存储 / 四大服务缺测试

---

## 项目结构

```text
audit-rag/
├── pyproject.toml              # Poetry 依赖配置
├── .env.example                # 环境变量示例
├── docker-compose.yml          # Docker Compose 编排
├── Makefile                    # 常用命令
├── start.sh                    # 启动脚本
│
├── bank_audit_rag/             # 核心代码
│   ├── config/
│   │   └── settings.py         # 配置中心（dataclass + dotenv）
│   ├── core/
│   │   ├── rag_engine.py       # RAG 查询引擎（检索 → 上下文 → 生成）
│   │   ├── vector_store.py     # Embedding 服务 + Chroma/内存双后端
│   │   ├── document_processor.py # 文档加载、分块、DocumentStore 索引
│   │   ├── audit_prompts.py    # 7 个银行审计 Prompt 模板
│   │   ├── credit_audit.py     # 信贷三查比对
│   │   ├── compliance_audit.py # 合规检查
│   │   ├── risk_management.py  # 风险评估
│   │   └── audit_report.py     # 报告生成
│   ├── api/
│   │   └── main.py             # FastAPI 入口
│   └── utils/
│       └── logger.py           # 结构化日志工具
│
├── docker/                     # Docker 配置
├── examples/
│   ├── 01_credit_audit_demo.py
│   └── 02_compliance_and_risk_demo.py
└── tests/
    └── test_document_processor.py
```

---

## 快速开始

```bash
cd 03-banking-audit-suite/audit-rag
poetry install          # 按 poetry.lock 安装（如需重新解析用 poetry lock）
cp .env.example .env    # 可选：填入 OPENAI_API_KEY 切换到真实 LLM
python examples/01_credit_audit_demo.py
```

不配置 API Key 也可以直接运行示例：引擎会输出 mock 回答，便于先跑通链路再接真实模型。

> **依赖锁定**：本项目是带 API 与 Docker 镜像的应用型项目，因此**提交 `poetry.lock`**
> （库项目才应忽略它）。lock 由 Poetry 2.x 生成（`lock-version 2.1`），
> 若改动 `pyproject.toml` 的依赖约束，请一并执行 `poetry lock` 并提交新的 lock，
> 否则 CI 与镜像构建会报 lock 与 pyproject 不一致。

常用环境变量（前缀 `ATRAG_`）：

| 变量 | 说明 | 默认值 |
|---|---|---|
| `ATRAG_OPENAI_API_KEY` | LLM / Embedding 的 API Key（留空则 mock） | 空 |
| `ATRAG_OPENAI_BASE_URL` | 兼容 OpenAI 协议的中转地址 | 空 |
| `ATRAG_LLM_MODEL` | 生成模型 | `gpt-4` |
| `ATRAG_EMBEDDING_MODEL` | Embedding 模型 | `text-embedding-ada-002` |
| `ATRAG_DOCUMENT_CHUNK_SIZE` | 分块大小 | `1000` |
| `ATRAG_RETRIEVER_TOP_K` | 检索返回条数 | `5` |

---

## 🔗 相关项目

本仓库解决「审计知识怎么被准确检索和引用」。

如果你关心「**多个 Agent 如何分工协作跑完一整套审计流程**」，推荐作者的另一个开源项目：

> ### 🤖 [银行审计多智能体平台（bank-audit-agents）](https://github.com/luckysun001/bank-audit-agents)
> 5 个角色 Agent + 编排器 + 三种审计流水线，同样支持真实 LLM 与 mock 双模式。

| | 本仓库（audit-rag） | bank-audit-agents |
|---|---|---|
| **核心问题** | 审计知识检索与引用 | 审计任务的多角色协同 |
| **关键组件** | 向量库、Embedding、RAG 引擎 | BaseAgent、Orchestrator、流水线 |
| **典型用法** | 提问 → 检索法规/合同 → 生成结论 | 拆解审计项目 → 分派 Agent → 汇总报告 |

想系统学习背后的原理，另见 [AI-Learning-Playground](https://github.com/luckysun001/AI-Learning-Playground)。

---

## 技术栈

- Python 3.11+（3.10 已 EOL，且 chromadb 依赖的 onnxruntime 自 1.24.4 起不再发布 cp310 轮子）
- LangChain（Prompt 模板、文本切分、Embedding 接口）
- ChromaDB（向量持久化，失败回退内存）
- FastAPI（API 框架）
- Pydantic / dataclass（配置与数据模型）

---

## 许可证

MIT
