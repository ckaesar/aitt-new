-- 示例数据插入脚本（基于 generated_example_tables.sql 定义）
-- 说明：为了便于联动测试，部分主键使用显式编号，保持引用一致。

-- customers 表示例数据
INSERT INTO `customers` (`customer_id`, `customer_name`, `email`, `phone`, `city`, `registration_date`) VALUES
  (1, 'Alice Zhang', 'alice@example.com', '13800000001', '北京', '2023-12-15'),
  (2, 'Bob Li',    'bob@example.com',   '13800000002', '上海', '2023-12-20'),
  (3, 'Carol Wang','carol@example.com', '13800000003', '深圳', '2024-01-05');

-- products 表示例数据
INSERT INTO `products` (`product_id`, `product_name`, `category`, `price`, `stock_quantity`) VALUES
  (101, 'Laptop',       '电子', 4999.00, 50),
  (102, 'Mouse',        '电子',   99.00, 200),
  (103, 'Office Chair', '家具',  799.00, 30),
  (104, 'Notebook',     '文具',   12.50, 1000);

-- sales_orders 表示例数据
INSERT INTO `sales_orders` (`order_id`, `customer_id`, `order_date`, `total_amount`, `status`, `created_at`) VALUES
  (1001, 1, '2024-01-01', 5197.00, 'PAID',    '2024-01-01 10:00:00'),
  (1002, 2, '2024-01-02',  924.00, 'PAID',    '2024-01-02 11:00:00'),
  (1003, 1, '2024-01-03',  161.50, 'PENDING', '2024-01-03 12:00:00');

-- order_items 表示例数据（与订单和产品联动）
INSERT INTO `order_items` (`item_id`, `order_id`, `product_id`, `quantity`, `unit_price`, `total_price`) VALUES
  (1, 1001, 101, 1, 4999.00, 4999.00),
  (2, 1001, 102, 2,   99.00,  198.00),
  (3, 1002, 103, 1,  799.00,  799.00),
  (4, 1002, 104,10,   12.50,  125.00),
  (5, 1003, 102, 1,   99.00,   99.00),
  (6, 1003, 104, 5,   12.50,   62.50);

-- sales_summary 表示例数据（按日汇总）
INSERT INTO `sales_summary` (`id`, `summary_date`, `total_orders`, `total_revenue`, `avg_order_value`, `new_customers`) VALUES
  (1, '2024-01-01', 1, 5197.00, 5197.00, 0),
  (2, '2024-01-02', 1,  924.00,  924.00, 0),
  (3, '2024-01-03', 1,  161.50,  161.50, 0);

-- customer_analysis 表示例数据（按客户分析）
INSERT INTO `customer_analysis` (`customer_id`, `total_orders`, `total_spent`, `avg_order_value`, `last_order_date`, `customer_segment`) VALUES
  (1, 2, 5358.50, 2679.25, '2024-01-03', 'VIP'),
  (2, 1,  924.00,  924.00, '2024-01-02', 'Regular'),
  (3, 0,    0.00,    0.00, NULL,          'Prospect');

-- 备注：如需清空并重置数据，可在执行前添加 TRUNCATE 语句。