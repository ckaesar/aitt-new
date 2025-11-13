-- 自动生成的示例表建表语句
-- 来源：database/sample_data.sql 的 aitt_data_tables 与 aitt_table_columns

CREATE TABLE IF NOT EXISTS `sales_orders` (
  `order_id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY COMMENT '订单唯一标识',
  `customer_id` BIGINT NOT NULL COMMENT '客户标识',
  `order_date` DATE NOT NULL COMMENT '下单日期',
  `total_amount` DECIMAL(10,2) NOT NULL COMMENT '订单总金额',
  `status` VARCHAR(20) NOT NULL COMMENT '订单状态',
  `created_at` TIMESTAMP NOT NULL COMMENT '记录创建时间'
);

CREATE TABLE IF NOT EXISTS `customers` (
  `customer_id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY COMMENT '客户唯一标识',
  `customer_name` VARCHAR(100) NOT NULL COMMENT '客户姓名',
  `email` VARCHAR(100) NULL COMMENT '客户邮箱',
  `phone` VARCHAR(20) NULL COMMENT '客户电话',
  `city` VARCHAR(50) NULL COMMENT '所在城市',
  `registration_date` DATE NOT NULL COMMENT '客户注册日期'
);

CREATE TABLE IF NOT EXISTS `products` (
  `product_id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY COMMENT '产品唯一标识',
  `product_name` VARCHAR(200) NOT NULL COMMENT '产品名称',
  `category` VARCHAR(50) NOT NULL COMMENT '产品分类',
  `price` DECIMAL(8,2) NOT NULL COMMENT '产品单价',
  `stock_quantity` INT NOT NULL COMMENT '当前库存'
);

CREATE TABLE IF NOT EXISTS `order_items` (
  `item_id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY COMMENT '明细唯一标识',
  `order_id` BIGINT NOT NULL COMMENT '关联订单ID',
  `product_id` BIGINT NOT NULL COMMENT '关联产品ID',
  `quantity` INT NOT NULL COMMENT '购买数量',
  `unit_price` DECIMAL(8,2) NOT NULL COMMENT '商品单价',
  `total_price` DECIMAL(10,2) NOT NULL COMMENT '明细小计'
);

CREATE TABLE IF NOT EXISTS `sales_summary` (
  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
  `summary_date` DATE NOT NULL COMMENT '汇总日期',
  `total_orders` INT NOT NULL COMMENT '当日订单总数',
  `total_revenue` DECIMAL(12,2) NOT NULL COMMENT '当日总收入',
  `avg_order_value` DECIMAL(8,2) NOT NULL COMMENT '平均订单价值',
  `new_customers` INT NOT NULL COMMENT '当日新客户数'
);

CREATE TABLE IF NOT EXISTS `customer_analysis` (
  `customer_id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY COMMENT '客户ID',
  `total_orders` INT NOT NULL COMMENT '客户总订单数',
  `total_spent` DECIMAL(12,2) NOT NULL COMMENT '客户总消费',
  `avg_order_value` DECIMAL(8,2) NOT NULL COMMENT '平均订单价值',
  `last_order_date` DATE NULL COMMENT '最后一次下单日期',
  `customer_segment` VARCHAR(20) NULL COMMENT '客户分群标签'
);
