# 银行审计 RAG 系统

面向银行审计领域的检索增强生成系统框架。
信贷三查比对 · 合规检查 · 风险评估 · 报告生成

> **状态：Alpha (v2.0.0)** — 核心服务 Prompt 模板和结果解析逻辑已实现，RAG 引擎、向量存储等基础设施为 TODO。

---

## 已实现

- **四大核心服务的 Prompt 模板库**：信贷三查（credit_audit.py）、合规检查（compliance_audit.py）、风险评估（risk_management.py）、报告生成（audit_report.py）
- **专业的审计 Prompt 设计**：包含评分标准、法规引用、结构化输出格式
- **结果解析逻辑**：正则提取 + 关键词匹配，支持违规分级和置信度评分
- **FastAPI 入口**（api/main.py）：基础 API 框架
- **示例代码**：信贷审计演示、合规与风险演示

## 未实现（TODO）

- RAG 引擎核心：混合检索器、相关性重排
- 向量数据库集成：ChromaDB/Milvus 向量存储和相似度计算
- 知识库管理：多格式文档加载、OCR 图片识别、索引构建
- API 中间件：认证、日志、限流
- 工具函数：结构化日志、Redis 缓存、自定义异常
- 审计规则库：监管规则 YAML 文件
- 前端界面：Streamlit 审计工作台
- 测试：仅 1 个文档处理器测试，核心服务逻辑无测试

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
│   ├── __init__.py
│   ├── config/                 # 配置（仅 __init__.py）
│   ├── core/                   # 核心服务
│   │   ├── audit_prompts.py    # 审计 Prompt 模板库
│   │   ├── credit_audit.py     # 信贷三查比对
│   │   ├── compliance_audit.py # 合规检查
│   │   ├── risk_management.py  # 风险评估
│   │   └── audit_report.py     # 报告生成
│   ├── api/                    # API 层
│   │   └── main.py             # FastAPI 入口
│   └── utils/                  # 工具函数（仅 __init__.py）
│
├── docker/                     # Docker 配置
│   └── Dockerfile
├── examples/                   # 示例代码
│   ├── 01_credit_audit_demo.py
│   └── 02_compliance_and_risk_demo.py
└── tests/                      # 测试
    └── test_document_processor.py
```

---

## 快速开始

```bash
cd 03-banking-audit-suite/audit-rag
pip install -e .

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY
```

---

## 技术栈

- Python 3.10+
- LangChain（Prompt 管理、LLM 调用）
- FastAPI（API 框架）
- ChromaDB（向量数据库，TODO）

---

## 许可证

MIT
