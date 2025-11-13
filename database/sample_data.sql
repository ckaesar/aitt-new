-- 示例数据插入脚本
USE ai_data_platform;

-- 插入示例用户
INSERT INTO aitt_users (username, email, password_hash, full_name, department, role) VALUES
('admin', 'admin@company.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3bp.Gm.F5W', '系统管理员', 'IT部门', 'admin'),
('analyst1', 'analyst1@company.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3bp.Gm.F5W', '数据分析师1', '数据部门', 'analyst'),
('analyst2', 'analyst2@company.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3bp.Gm.F5W', '数据分析师2', '业务部门', 'analyst'),
('viewer1', 'viewer1@company.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3bp.Gm.F5W', '业务查看者', '销售部门', 'viewer');

-- 插入示例数据源
INSERT INTO aitt_data_sources (name, type, host, port, database_name, username, description, created_by) VALUES
('主数据库', 'mysql', 'localhost', 3306, 'business_db', 'root', '主要业务数据库', 1),
('数据仓库', 'mysql', 'localhost', 3306, 'warehouse_db', 'root', '数据仓库', 1);

-- 插入示例数据表
INSERT INTO aitt_data_tables (data_source_id, table_name, display_name, description, category, row_count, size_mb) VALUES
(1, 'sales_orders', '销售订单表', '记录所有销售订单信息', '销售', 150000, 25.6),
(1, 'customers', '客户表', '客户基本信息', '客户', 5000, 2.1),
(1, 'products', '产品表', '产品基本信息', '产品', 1200, 0.8),
(1, 'order_items', '订单明细表', '订单商品明细', '销售', 300000, 45.2),
(2, 'sales_summary', '销售汇总表', '按日期汇总的销售数据', '报表', 365, 0.1),
(2, 'customer_analysis', '客户分析表', '客户行为分析数据', '分析', 5000, 3.2);

-- 插入示例字段信息
INSERT INTO aitt_table_columns (table_id, column_name, display_name, data_type, is_nullable, description, is_dimension, is_metric, column_order) VALUES
-- sales_orders表字段
(1, 'order_id', '订单ID', 'BIGINT', FALSE, '订单唯一标识', FALSE, FALSE, 1),
(1, 'customer_id', '客户ID', 'BIGINT', FALSE, '客户标识', TRUE, FALSE, 2),
(1, 'order_date', '订单日期', 'DATE', FALSE, '下单日期', TRUE, FALSE, 3),
(1, 'total_amount', '订单总金额', 'DECIMAL(10,2)', FALSE, '订单总金额', FALSE, TRUE, 4),
(1, 'status', '订单状态', 'VARCHAR(20)', FALSE, '订单状态', TRUE, FALSE, 5),
(1, 'created_at', '创建时间', 'TIMESTAMP', FALSE, '记录创建时间', TRUE, FALSE, 6),

-- customers表字段
(2, 'customer_id', '客户ID', 'BIGINT', FALSE, '客户唯一标识', FALSE, FALSE, 1),
(2, 'customer_name', '客户姓名', 'VARCHAR(100)', FALSE, '客户姓名', TRUE, FALSE, 2),
(2, 'email', '邮箱', 'VARCHAR(100)', TRUE, '客户邮箱', TRUE, FALSE, 3),
(2, 'phone', '电话', 'VARCHAR(20)', TRUE, '客户电话', TRUE, FALSE, 4),
(2, 'city', '城市', 'VARCHAR(50)', TRUE, '所在城市', TRUE, FALSE, 5),
(2, 'registration_date', '注册日期', 'DATE', FALSE, '客户注册日期', TRUE, FALSE, 6),

-- products表字段
(3, 'product_id', '产品ID', 'BIGINT', FALSE, '产品唯一标识', FALSE, FALSE, 1),
(3, 'product_name', '产品名称', 'VARCHAR(200)', FALSE, '产品名称', TRUE, FALSE, 2),
(3, 'category', '产品分类', 'VARCHAR(50)', FALSE, '产品分类', TRUE, FALSE, 3),
(3, 'price', '产品价格', 'DECIMAL(8,2)', FALSE, '产品单价', FALSE, TRUE, 4),
(3, 'stock_quantity', '库存数量', 'INT', FALSE, '当前库存', FALSE, TRUE, 5),

-- order_items表字段
(4, 'item_id', '明细ID', 'BIGINT', FALSE, '明细唯一标识', FALSE, FALSE, 1),
(4, 'order_id', '订单ID', 'BIGINT', FALSE, '关联订单ID', TRUE, FALSE, 2),
(4, 'product_id', '产品ID', 'BIGINT', FALSE, '关联产品ID', TRUE, FALSE, 3),
(4, 'quantity', '数量', 'INT', FALSE, '购买数量', FALSE, TRUE, 4),
(4, 'unit_price', '单价', 'DECIMAL(8,2)', FALSE, '商品单价', FALSE, TRUE, 5),
(4, 'total_price', '小计', 'DECIMAL(10,2)', FALSE, '明细小计', FALSE, TRUE, 6),

-- sales_summary表字段
(5, 'summary_date', '汇总日期', 'DATE', FALSE, '汇总日期', TRUE, FALSE, 1),
(5, 'total_orders', '订单总数', 'INT', FALSE, '当日订单总数', FALSE, TRUE, 2),
(5, 'total_revenue', '总收入', 'DECIMAL(12,2)', FALSE, '当日总收入', FALSE, TRUE, 3),
(5, 'avg_order_value', '平均订单价值', 'DECIMAL(8,2)', FALSE, '平均订单价值', FALSE, TRUE, 4),
(5, 'new_customers', '新客户数', 'INT', FALSE, '当日新客户数', FALSE, TRUE, 5),

-- customer_analysis表字段
(6, 'customer_id', '客户ID', 'BIGINT', FALSE, '客户ID', TRUE, FALSE, 1),
(6, 'total_orders', '总订单数', 'INT', FALSE, '客户总订单数', FALSE, TRUE, 2),
(6, 'total_spent', '总消费金额', 'DECIMAL(12,2)', FALSE, '客户总消费', FALSE, TRUE, 3),
(6, 'avg_order_value', '平均订单价值', 'DECIMAL(8,2)', FALSE, '平均订单价值', FALSE, TRUE, 4),
(6, 'last_order_date', '最后订单日期', 'DATE', TRUE, '最后一次下单日期', TRUE, FALSE, 5),
(6, 'customer_segment', '客户分群', 'VARCHAR(20)', TRUE, '客户分群标签', TRUE, FALSE, 6);

-- 插入示例查询模板
INSERT INTO aitt_query_templates (name, description, category, natural_language_template, sql_template, parameters, created_by) VALUES
('销售趋势查询', '查询指定时间段的销售趋势', '销售分析', 
'查询{start_date}到{end_date}的销售趋势', 
'SELECT order_date, COUNT(*) as order_count, SUM(total_amount) as total_revenue FROM sales_orders WHERE order_date BETWEEN ''{start_date}'' AND ''{end_date}'' GROUP BY order_date ORDER BY order_date',
'{"start_date": {"type": "date", "description": "开始日期"}, "end_date": {"type": "date", "description": "结束日期"}}',
1),

('客户消费排行', '查询客户消费排行榜', '客户分析',
'查询消费金额前{limit}名的客户',
'SELECT c.customer_name, SUM(o.total_amount) as total_spent FROM customers c JOIN sales_orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id, c.customer_name ORDER BY total_spent DESC LIMIT {limit}',
'{"limit": {"type": "integer", "description": "返回记录数", "default": 10}}',
1),

('产品销量统计', '统计产品销量情况', '产品分析',
'统计{category}分类产品的销量情况',
'SELECT p.product_name, SUM(oi.quantity) as total_sold FROM products p JOIN order_items oi ON p.product_id = oi.product_id WHERE p.category = ''{category}'' GROUP BY p.product_id, p.product_name ORDER BY total_sold DESC',
'{"category": {"type": "string", "description": "产品分类"}}',
1);

-- 插入系统配置
INSERT INTO aitt_system_configs (config_key, config_value, description) VALUES
('ai_model_provider', 'openai', 'AI模型提供商'),
('ai_model_name', 'gpt-4', 'AI模型名称'),
('max_query_rows', '1000', '查询结果最大行数'),
('query_timeout_seconds', '30', '查询超时时间（秒）'),
('enable_query_cache', 'true', '是否启用查询缓存'),
('cache_expire_minutes', '60', '缓存过期时间（分钟）');

-- 插入示例权限
INSERT INTO aitt_permissions (user_id, resource_type, resource_id, permission_type, granted_by) VALUES
-- 管理员拥有所有权限
(1, 'data_source', 1, 'admin', 1),
(1, 'data_source', 2, 'admin', 1),
-- 分析师权限
(2, 'data_source', 1, 'read', 1),
(2, 'data_source', 2, 'read', 1),
(3, 'data_source', 1, 'read', 1),
-- 查看者权限
(4, 'table', 1, 'read', 1),
(4, 'table', 2, 'read', 1),
(4, 'table', 5, 'read', 1);