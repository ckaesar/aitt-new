from typing import Optional


def build_sql_generation_prompt(nl_query: str, schema_context: Optional[str] = None, user_context: Optional[str] = None) -> str:
    parts = [
        "你是资深数据分析助理，负责将自然语言转换为正确的SQL。",
        "请只输出SQL，不要附加解释。",
        "参考数据上下文按‘表 -> 列’分组；列标记 [D] 表示维度，[M] 表示指标。",
    ]
    if user_context:
        parts.append(f"用户上下文:\n{user_context}")
    if schema_context:
        parts.append(f"参考数据上下文:\n{schema_context}")
    parts.append(f"需求:\n{nl_query}")
    parts.append("输出: 合规SQL")
    return "\n\n".join(parts)