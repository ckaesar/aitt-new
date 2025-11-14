# AI智能自助取数平台

面向业务分析与数据取数的智能平台，支持自然语言生成只读 SQL、RAG 增强检索、动态元数据同步与文档化，以及可视化查询与分享能力。

## 项目介绍
- 自然语言到 SQL：通过提示工程与安全策略，仅生成单条只读 `SELECT`，不含分号与 DML/DDL。
- RAG 检索增强：利用 ChromaDB 存储向量化元数据与派生文档，提升表/列选择与语义理解准确性。
- 元数据动态同步：从数据源自动同步数据源/表/字段，派生文档并写入向量库，面向多源场景持续更新。
- 可视化操作：列表（创建、详情页、分享、查询等），练习场（Playground）提供交互体验与快速校验。

## 基础架构
- 前端：Vite + React（开发端口 `3000`），提供交互界面与 Playground。
- 后端：FastAPI + Uvicorn（端口 `8000`），提供 AI、RAG、元数据等 API。
- 存储：MySQL（业务数据与元数据）、Redis（缓存）、本地或持久化目录中的 ChromaDB（向量检索）。
- 访问地址：
  - 前端 Playground：`http://115.190.26.136:3000/playground`
  - 后端接口文档（JSON）：`http://115.190.26.136:3000/openapi.json`
  - Swagger 文档页：`http://115.190.26.136:3000/docs`

## 大模型应用
- 模型调用
  - SDK：OpenAI Python SDK（`openai>=1.x`）。
  - 配置：`backend/app/core/config.py` 中 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`AI_MODEL_NAME`。
  - 参数：
    - `temperature=0.0`、`top_p=0.2`、`n=1` 保证确定性与稳定性
    - 动态 `max_tokens`：根据 Prompt 长度自动在 `128–512` 之间调整
    - `stop=[";", "\n```", "\n\n```", "\n--"]` 防止生成分号、代码块与注释尾部
    - `user` 标识：使用会话 `conversation_id` 便于审计与限流
- Prompt 工程
  - 结构化 Markdown 提示词，覆盖角色定位、核心能力、工作流程、输出格式与行动建议
  - 安全与合规：
    - 仅生成只读 `SELECT`，禁止 `INSERT/UPDATE/DELETE/CREATE/DROP/ALTER/TRUNCATE`
    - 禁止 `SELECT *`，显式列/表，基于上下文选择
    - 敏感信息脱敏（如 `email/phone/address`），必要时掩码展示
    - 用户输入仅作语义参考，不直接拼接到 SQL
    - JOIN 仅基于上下文主外键或明确关联，避免笛卡尔积
- 异常与降级处理
  - 超时与重试：指数退避（最多 2 次）
  - 模型不可用：规则兜底（订单统计、详情类），否则返回占位只读 SQL
  - 调用日志：记录 tokens、延迟、RAG/元数据上下文长度与状态，便于审计与优化

## RAG 应用
- ChromaDB 使用
  - 持久化目录：`settings.CHROMA_PERSIST_DIRECTORY`
  - 集合：
    - 元数据集合：`settings.CHROMA_METADATA_COLLECTION_NAME`
    - 文档集合：派生任务文档（表/列/关联/常用字段），用于增强检索表达
- 元数据同步与文档化
  - 定时任务自动同步数据源/表/字段元数据
  - 从元数据派生面向任务的文档（主维度、指标、关联猜测、常用字段等），写入文档集合
  - 提升命中率与语义可用性，让模型更容易选择合适主表与列
- 检索接口优化
  - 查询重写：同义词与规范化（产品/商品/SKU/SPU、订单/交易、客户/用户等）
  - 结构化上下文：按表分组列、标注维度/指标，便于模型解析与选择
  - 高级技术：
    - 多源聚合上下文拼装（元数据 + 文档 RAG 合并）
    - 关联推断与主表优先策略（订单/客户/商品等主对象场景）
    - 结果缓存与近似查询归一化，降低延迟与重复检索成本

## 开发环境与启动

### 一键启动/停止脚本（跨平台）
- 启动脚本路径：`scripts/start_all.sh`
- 停止脚本路径：`scripts/stop_all.sh`
- Windows 建议使用 Git Bash 运行：
  - 启动：`bash ./scripts/start_all.sh`
  - 停止：`bash ./scripts/stop_all.sh`
- 默认端口：后端 `8000`，前端 `3000`。可通过环境变量覆盖：
  - `BACKEND_PORT=9000 FRONTEND_PORT=3100 bash ./scripts/start_all.sh`
- 日志位置：
  - 后端：`logs/backend_dev.log`
  - 前端：`logs/frontend_dev.log`

### 一键重启与健康验证

- 在项目根目录执行下列命令，可一键停止、启动并进行本机健康验证：

```
bash ./scripts/stop_all.sh && \
BACKEND_PORT=8000 FRONTEND_PORT=3000 CONDA_ENV_NAME=py311 bash ./scripts/start_all.sh && \
sleep 2 && ss -lntp | grep -E ':(8000|3000)' || true && \
curl -s http://127.0.0.1:8000/api/v1/health && echo && \
curl -s http://127.0.0.1:3000/ | head -n 3
```

参数说明：
- `BACKEND_PORT`：后端服务监听端口，默认 `8000`
- `FRONTEND_PORT`：前端 Vite 开发端口，默认 `3000`
- `CONDA_ENV_NAME`：后端使用的 Conda 环境名（如需启用 64 位 Python 与依赖），示例 `py311` 或 `aitt-py311`
- `ss -lntp`：查看端口监听状态；`grep -E ':(8000|3000)'` 过滤出关键端口；`|| true` 保证命令不会因无匹配而中断
- `curl http://127.0.0.1:8000/api/v1/health`：后端健康检查（返回 `healthy` 表示后端正常）
- `curl http://127.0.0.1:3000/ | head -n 3`：前端首页返回，取前 3 行快速确认页面正常

### 64 位 Python（强烈建议）
- 为确保 `chromadb`、`greenlet` 等依赖正常工作，推荐使用 64 位 Python（Conda 环境）。
- 两种指定方式（二选一）：
  - 指定 Conda 环境名：`CONDA_ENV_NAME=aitt-py311 bash ./scripts/start_all.sh`
  - 指定 64 位 Python 解释器绝对路径：
    - 例：`PYTHON_BIN="D:\\apps\\anaconda3\\envs\\aitt-py311\\python.exe" bash ./scripts/start_all.sh`
- 验证 64 位环境：
  - `conda run -n aitt-py311 python -c "import platform, sys; print(platform.architecture(), sys.version)"`
  - 正常输出应显示 `('64bit', 'WindowsPE')` 及 Python 3.11.x。

### 使用 Conda 配置 Python 3.11 环境并安装依赖

为避免 Windows 下 `greenlet` 等依赖的编译问题，推荐使用 64 位 Conda 环境（Anaconda 或 Miniconda）。以下步骤将创建并指定项目使用该环境，并完成依赖安装：

- 检查 Conda 是否安装：`conda --version`
- 创建环境：`conda create -n aitt-py311 python=3.11 -y`
- 预装关键包（避免 pip 轮子解析失败）：
  - `conda install -n aitt-py311 -c conda-forge -y pydantic=2.5.0 pydantic-core=2.14.1 numpy=1.24.3`
- 在新环境中安装后端依赖：
  - 一次性安装：`conda run -n aitt-py311 python -m pip install -r backend/requirements.txt`
  - 如遇解析冲突（例如 `openai` 与 `langchain-openai`）：
    - Web/数据库与工具：
      - `conda run -n aitt-py311 python -m pip install fastapi==0.104.1 uvicorn[standard]==0.24.0 pydantic==2.5.0 pydantic-settings==2.1.0 sqlalchemy==2.0.23 pymysql==1.1.0 aiomysql==0.2.0 greenlet==3.0.3 alembic==1.13.1 redis==5.0.1 python-jose[cryptography]==3.3.0 passlib[bcrypt]==1.7.4 python-multipart==0.0.6 httpx==0.25.2 aiohttp==3.9.1 python-dotenv==1.0.0 loguru==0.7.2 tenacity==8.2.3 asyncio-mqtt==0.16.1 pytest==7.4.3 pytest-asyncio==0.21.1 black==23.11.0 isort==5.12.0 flake8==6.1.0`
    - AI 相关（逐步安装，必要时允许升级 `openai` 版本以满足 `langchain-openai`）：
      - `conda run -n aitt-py311 python -m pip install openai==1.3.7`
      - `conda run -n aitt-py311 python -m pip install langchain==0.0.340 langchain-openai==0.0.2`
      - `conda run -n aitt-py311 python -m pip install chromadb==0.4.18 sentence-transformers==2.2.2 pandas==2.1.4`

说明：
- 在部分镜像源或平台上，`langchain-openai==0.0.2` 会将 `openai` 升级到较新的 `1.x` 版本，这是正常现象；若需严格版本锁定，请将 `backend/requirements.txt` 中的 `openai` 改为 `openai>=1.6,<2.0`。
- 如需更快下载，可配置企业内镜像源。

### 启动后端服务（指定 Conda 环境）
- 进入后端目录：`cd backend`
- 启动：`conda run -n aitt-py311 python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

### 选择解释器与 IDE/终端使用说明
- 终端：所有后端相关命令前加 `conda run -n aitt-py311` 前缀。
- 解释器路径（如 IDE 需手选）：指向 `…\Anaconda3\envs\aitt-py311\python.exe`（实际路径因安装位置而异）。

### 环境自检
- `conda run -n aitt-py311 python -c "import greenlet, sys; print('greenlet', greenlet.__version__, 'python', sys.version)"`
- 若能正常输出版本，说明 64 位 Python 与 `greenlet` 已正确安装。

### 使用 MySQL 作为后端数据库（概览）
- `backend/app/core/config.py` 的 `DATABASE_URL` 使用 MySQL 异步驱动：`mysql+aiomysql://<user>:<pass>@<host>:<port>/<db>?charset=utf8mb4`
- 若使用 `.env` 文件，可设置：`DATABASE_URL=mysql+aiomysql://dev:ElB8Yg5191BSoMWE@10.26.21.6:6606/aitt?charset=utf8mb4`
- 确保 MySQL 可达并创建数据库（见 `database/init.sql` 示例）。
- 确保 MySQL 可达并创建数据库（见 `database/init.sql` 示例）。

## 前端与后端访问
- 前端地址：`http://115.190.26.136:3000/playground`
- 后端接口（JSON）：`http://115.190.26.136:3000/openapi.json`
- Swagger 文档页：`http://115.190.26.136:3000/docs`

## 一键脚本
- 启动：`bash ./scripts/start_all.sh`
- 停止：`bash ./scripts/stop_all.sh`
- 重启与验证（示例见上文“一键重启与健康验证”）

## 评测与优化
- 自动评测：`backend/scripts/auto_eval_ai.py`（≥30 条用例）
- 指标：准确率、延迟、token、RAG 引用命中率等
- 优化方向：
  - 提示词工程与安全策略收敛（只读、无分号、脱敏、输入校验）
  - RAG 检索缓存与上下文归一化
  - 基于主对象（订单/客户/商品）模板化生成，缩短延迟

## 架构流程（Mermaid）

```mermaid
flowchart TD
    A[用户自然语言提问] --> B[前端 Playground]
    B --> C[后端 API: /api/v1/ai/query]
    C --> D[元数据检索\nChromaDB: metadata 集合]
    C --> E[文档RAG检索\nChromaDB: docs 集合]
    D --> F[上下文拼装\n结构化表/列 + 文档]
    E --> F
    F --> G[Prompt 工程\nMarkdown 安全规范]
    G --> H[Chat Completions\nOpenAI SDK]
    H --> I{输出校验}
    I -->|合法只读SQL| J[执行只读查询]
    I -->|不合法/空| K[降级\n规则兜底/占位SQL]
    J --> L[返回结果\n含维度/指标/选表]
    K --> L
    subgraph 数据&缓存
    M[(MySQL)]
    N[(Redis)]
    O[(ChromaDB 持久化)]
    end
    C --> M
    C --> N
    D --> O
    E --> O
    P[定时任务\n元数据同步+文档派生] --> O
```