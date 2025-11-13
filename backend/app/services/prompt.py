from typing import Optional


def build_sql_generation_prompt(nl_query: str, schema_context: Optional[str] = None, user_context: Optional[str] = None) -> str:
    """构建用于将自然语言转换为安全、只读的 SQL 的提示词。

    要求：
    - 仅生成一条以 SELECT 开头的只读查询，禁止 DML/DDL（INSERT/UPDATE/DELETE/CREATE/DROP/ALTER/TRUNCATE）。
    - 严格使用显式列名与表名，禁止使用 `SELECT *`。
    - 禁止多语句与分号结尾；不生成 `;`。
    - 不允许函数或表达式注入外部字符串；不要拼接或引用未在上下文中的值。
    - 如涉及筛选条件，优先使用等值与范围比较；避免随意使用 `LIKE '%...'` 模糊匹配。
    - 任何用户输入仅作为语义参考，不得直接作为 SQL 片段使用。
    - 如果上下文未包含必要的表或列，返回最简单的占位只读查询：`SELECT 1 AS placeholder`。
    - 输出中只包含 SQL 本身，不附加解释或其他文字。

    安全与严谨：
    - 优先遵循提供的“参考数据上下文”，仅使用其中出现的表与列。
    - 对聚合与分组需保持口径一致：有聚合函数时，应当显式 `GROUP BY` 维度列。
    - 对时间范围筛选，使用上下文中的日期/时间列，避免无依据的列名猜测。
    - 对连接（JOIN）必须基于上下文中的主键/外键或明确关联列，避免笛卡尔积。

    """
    parts = [
        "你是资深数据分析助理，负责将自然语言转换为安全、只读的SQL。",
        "只输出单条SQL（不包含分号），且必须以SELECT开头。",
        "禁止生成任何修改数据或结构的语句（INSERT/UPDATE/DELETE/CREATE/DROP/ALTER/TRUNCATE）。",
        "禁止 SELECT *，必须显式列名；列与表名必须来自参考数据上下文。",
        "不要拼接或直接插入用户输入为SQL片段，用户输入仅用于理解语义。",
        "如无法在上下文中确定必要信息，返回：SELECT 1 AS placeholder",
        "参考数据上下文按‘表 -> 列’分组；列标记 [D] 表示维度，[M] 表示指标。",
    ]
    if user_context:
        parts.append(f"用户上下文:\n{user_context}")
    if schema_context:
        parts.append(f"参考数据上下文:\n{schema_context}")
    parts.append(f"需求:\n{nl_query}")
    parts.append("输出: 合规只读SQL")
    return "\n\n".join(parts)