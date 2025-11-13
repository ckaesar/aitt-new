#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
根据 database/sample_data.sql 中 aitt_data_tables 与 aitt_table_columns 的示例数据，
生成对应示例业务表的 CREATE TABLE 语句，写入 database/generated_example_tables.sql。

假设：
- aitt_data_tables 的插入顺序即表的自增 ID 映射（示例中 columns 使用的 table_id 与插入顺序一致）。
- 数据类型直接采用示例中的字符串（如 BIGINT, DATE, DECIMAL(10,2), VARCHAR(20), TIMESTAMP, INT）。
- is_nullable 为 FALSE 则生成 NOT NULL；TRUE 则允许 NULL。
"""

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'database' / 'sample_data.sql'
OUTPUT = ROOT / 'database' / 'generated_example_tables.sql'


def parse_tables(sql_text: str):
    """解析 aitt_data_tables 的插入块，返回按插入顺序的表名列表。"""
    m = re.search(r"INSERT INTO\s+aitt_data_tables\s*\([^)]+\)\s*VALUES\s*(.+?);", sql_text, flags=re.S | re.I)
    if not m:
        return []
    values_blob = m.group(1)
    table_names = []
    for line in values_blob.splitlines():
        line = line.strip()
        if not line or line.startswith('--'):
            continue
        if not line.startswith('('):
            continue
        # 形如：  (1, 'sales_orders', '销售订单表', ...)
        m2 = re.search(r"^\(\s*\d+\s*,\s*'([^']+)'\s*,", line)
        if m2:
            table_names.append(m2.group(1))
    return table_names


def parse_columns(sql_text: str):
    """解析 aitt_table_columns 的插入块，返回 {table_id: [列信息...]}"""
    m = re.search(r"INSERT INTO\s+aitt_table_columns\s*\([^)]+\)\s*VALUES\s*(.+?);", sql_text, flags=re.S | re.I)
    if not m:
        return {}
    values_blob = m.group(1)
    by_table = {}
    for line in values_blob.splitlines():
        line = line.strip()
        if not line or line.startswith('--'):
            continue
        if not line.startswith('('):
            continue
        # 去掉行尾逗号
        if line.endswith(','):
            line = line[:-1]
        # 形如：(1, 'order_id', '订单ID', 'BIGINT', FALSE, '订单唯一标识', FALSE, TRUE, 1)
        m2 = re.match(
            r"^\(\s*(\d+)\s*,\s*'([^']+)'\s*,\s*'([^']*)'\s*,\s*'([^']+)'\s*,\s*(TRUE|FALSE)\s*,\s*'([^']*)'\s*,\s*(TRUE|FALSE)\s*,\s*(TRUE|FALSE)\s*,\s*(\d+)\s*\)$",
            line,
        )
        if not m2:
            continue
        table_id = int(m2.group(1))
        column_name = m2.group(2)
        display_name = m2.group(3)
        data_type = m2.group(4)
        is_nullable = (m2.group(5).upper() == 'TRUE')
        description = m2.group(6)
        # is_dimension = (m2.group(7).upper() == 'TRUE')
        # is_metric = (m2.group(8).upper() == 'TRUE')
        column_order = int(m2.group(9))

        by_table.setdefault(table_id, []).append({
            'column_name': column_name,
            'display_name': display_name,
            'data_type': data_type,
            'is_nullable': is_nullable,
            'description': description,
            'column_order': column_order,
        })

    # 按 column_order 排序
    for t in by_table.values():
        t.sort(key=lambda x: x.get('column_order', 0))
    return by_table


def generate_ddl(table_names, columns_by_table):
    lines = []
    lines.append('-- 自动生成的示例表建表语句')
    lines.append('-- 来源：database/sample_data.sql 的 aitt_data_tables 与 aitt_table_columns')
    lines.append('')
    for idx, tbl in enumerate(table_names, start=1):
        cols = columns_by_table.get(idx, [])
        if not cols:
            # 若没有字段信息，跳过或生成空表结构
            lines.append(f"-- 跳过无字段的表 {tbl}")
            lines.append('')
            continue
        lines.append(f"CREATE TABLE IF NOT EXISTS `{tbl}` (")
        # 选择主键列：优先选择以 _id 结尾且类型为 INT/BIGINT 的第一列
        def choose_pk(columns):
            for cc in columns:
                nm = cc['column_name']
                dt = cc['data_type'].upper()
                if nm.endswith('_id') and ('INT' in dt or 'BIGINT' in dt):
                    return nm
            return None

        pk_col = choose_pk(cols)
        add_synthetic_pk = pk_col is None

        col_lines = []
        if add_synthetic_pk:
            col_lines.append("  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键'")

        for c in cols:
            name = c['column_name']
            dtype = c['data_type']
            nullable = c['is_nullable']
            desc = c['description']
            parts = [f"  `{name}` {dtype}"]
            if name == pk_col:
                # 主键列：强制 NOT NULL + AUTO_INCREMENT + PRIMARY KEY
                parts.append('NOT NULL')
                parts.append('AUTO_INCREMENT')
                parts.append('PRIMARY KEY')
            else:
                parts.append('NULL' if nullable else 'NOT NULL')
            if desc:
                d = desc.replace("'", "''")
                parts.append(f"COMMENT '{d}'")
            col_lines.append(' '.join(parts))
        lines.extend(',\n'.join(col_lines).split('\n'))
        lines.append(');')
        lines.append('')
    return '\n'.join(lines)


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f'未找到输入文件: {INPUT}')
    sql_text = INPUT.read_text(encoding='utf-8')
    table_names = parse_tables(sql_text)
    columns_by_table = parse_columns(sql_text)
    ddl = generate_ddl(table_names, columns_by_table)
    OUTPUT.write_text(ddl, encoding='utf-8')
    print(f'生成完成: {OUTPUT}')


if __name__ == '__main__':
    main()