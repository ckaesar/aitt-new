AI

基本功能：
1. 自然语言交互过程中，只返回10条数据仅供参考获取的数据对不对，如果是正确的，则将获取到的取数条件加载到规范的维度、指标、条件等设置框内
2. 模块：列表（创建、详情页、分享、查询等功能）、练习场（查询体验）

## 开发环境与启动（补充）

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





## 智能问答-核心能力

- 自然语言到SQL：用中文描述问题，自动生成并执行SQL。
- 多轮追问与澄清：在同一上下文中继续提问、细化筛选条件。
- 参数化模板：将常用问题保存为模板，下次只需填参数。
- 结果解释与校验：返回表格数据并提供简要解释，便于快速验证。
- 一键保存场景：把当前问答与SQL作为“场景”保存，复用与分享。
适用人群

- 数据分析师与BI工程师：临时分析、指标验证、报表补充。
- 产品与运营：用户行为、活动效果、转化漏斗快速问答。
- 财务与风控：账期对账、异常勾稽、阈值预警复核。
- 数据工程师：ETL上线前后验证、表结构发现、字段含义查询。
典型场景

- 数据探索与发现：快速问“近7日新增用户与留存趋势”，查看结果并细化维度。
- 指标核对与异常定位：问“昨天GMV为何环比下降？按渠道拆解并给出Top3原因”。
- 活动效果评估：分析“618大促首日转化漏斗，各环节转化率与短板”。
- A/B实验分析：比较“新结算流程A/B两组核心指标是否显著差异（t检验）”。
- 用户画像与行为：查询“付费用户的Top5常见路径，并按城市分布统计”。
- 报表补充与临时取数：生成“本月前20SKU销量、毛利、库存周转天数”列表。
- 数据字典问答：问“订单表的主键、核心字段含义、常见关联表有哪些？”。
- 运维排障与数据质量：定位“昨日流水表出现空值的字段及占比，给出影响范围”。
示例提问

- “近30天日均活跃用户、周留存率、同比环比情况，用折线图展示。”
- “按省份统计订单数量与销售额，筛选销售额>100万，按销售额倒序。”
- “2025-10-01~2025-10-31期间，渠道=抖音，计算客单价与复购率。”
- “请给出用户登录-下scm-history-item:d%3A%5CtraeApps%5Caitt?%7B%22repositoryId%22%3A%22scm0%22%2C%22historyItemId%22%3A%222ea363e4bd7c000fb5a942613f348447ae924ea3%22%2C%22historyItemParentId%22%3A%226d62dbf14f70adf30812d2f55edf5ae03d730a42%22%2C%22historyItemDisplayId%22%3A%222ea363e%22%7D单-支付的漏斗，并标注各环节转化率。”
- “列出异常订单（金额为负、退款>实付）的Top10用户及订单详情。”
使用流程

- 选择数据源与表域：在练习场页面选择目标库或业务域。
- 输入问题：自然语言描述你的需求，越具体越好（时间范围、维度、筛选条件）。
- 运行与查看：执行生成的查询，查看表格与解释，必要时调整问题。
- 细化与追问：继续提问“再按城市拆分”“筛选渠道=天猫”，系统保持上下文。
- 保存为场景：确认有复用价值时保存，命名并补充自然语言/SQL模板和参数。
- 复用与分享：后续在模板列表中选择该场景，填入不同参数快速产出。
最佳实践

- 明确时间与口径：给定统计周期、是否去重、是否含退款等，提升准确度。
- 指定维度与聚合：说明需要按“渠道/省份/SKU”分组，以及求“均值/中位数/占比”。
- 逐步细化：先跑总体，再加筛选与拆分，避免一次性过于复杂。
- 验证与比对：与既有报表或抽样SQL比对，确认指标口径一致。
- 模板参数化：把“时间/渠道/品类”等改为参数，提升复用与协作效率。
限制与建议

- 数据权限受限：仅能访问授权的数据源与表；敏感数据需遮蔽或聚合后查询。
- 复杂统计方法：如多维联合显著性检验、因果推断，建议明确方法与假设。
- 大表性能：超大范围与多维联查可能较慢，建议先限定日期或抽样。
- 字段口径差异：不同系统字段含义可能不同，先用“数据字典问答”澄清再分析。
需要我为你的业务场景定制一套可复用的智能问答模板吗？你可以提供数据源类型、核心表名、常用分析维度与指标，我来帮你拆分问题并设计参数化模板与校验规则。