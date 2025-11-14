-- AI智能自助取数平台数据库初始化脚本
-- 创建数据库
CREATE DATABASE IF NOT EXISTS smart_finance_area DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smart_finance_area;

-- 用户表
CREATE TABLE aitt_users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    email VARCHAR(100) NOT NULL UNIQUE COMMENT '邮箱',
    password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希',
    full_name VARCHAR(100) COMMENT '全名',
    department VARCHAR(100) COMMENT '部门',
    role ENUM('admin', 'analyst', 'viewer') DEFAULT 'viewer' COMMENT '角色',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_email (email)
) COMMENT '用户表';

-- 数据源表
CREATE TABLE aitt_data_sources (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL COMMENT '数据源名称',
    type ENUM('mysql', 'postgresql', 'clickhouse', 'hive') NOT NULL COMMENT '数据源类型',
    host VARCHAR(255) NOT NULL COMMENT '主机地址',
    port INT NOT NULL COMMENT '端口',
    database_name VARCHAR(100) NOT NULL COMMENT '数据库名',
    username VARCHAR(100) COMMENT '用户名',
    password_encrypted TEXT COMMENT '加密密码',
    description TEXT COMMENT '描述',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    created_by BIGINT NOT NULL COMMENT '创建人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES aitt_users(id),
    INDEX idx_name (name),
    INDEX idx_type (type)
) COMMENT '数据源表';

-- 数据表元信息
CREATE TABLE aitt_data_tables (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    data_source_id BIGINT NOT NULL COMMENT '数据源ID',
    table_name VARCHAR(100) NOT NULL COMMENT '表名',
    display_name VARCHAR(100) COMMENT '显示名称',
    description TEXT COMMENT '表描述',
    category VARCHAR(50) COMMENT '分类',
    tags JSON COMMENT '标签',
    row_count BIGINT DEFAULT 0 COMMENT '行数',
    size_mb DECIMAL(10,2) DEFAULT 0 COMMENT '大小MB',
    last_updated TIMESTAMP COMMENT '最后更新时间',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (data_source_id) REFERENCES aitt_data_sources(id),
    UNIQUE KEY uk_source_table (data_source_id, table_name),
    INDEX idx_table_name (table_name),
    INDEX idx_category (category)
) COMMENT '数据表元信息';

-- 字段元信息
CREATE TABLE aitt_table_columns (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    table_id BIGINT NOT NULL COMMENT '表ID',
    column_name VARCHAR(100) NOT NULL COMMENT '字段名',
    display_name VARCHAR(100) COMMENT '显示名称',
    data_type VARCHAR(50) NOT NULL COMMENT '数据类型',
    is_nullable BOOLEAN DEFAULT TRUE COMMENT '是否可空',
    default_value VARCHAR(255) COMMENT '默认值',
    description TEXT COMMENT '字段描述',
    is_dimension BOOLEAN DEFAULT FALSE COMMENT '是否维度',
    is_metric BOOLEAN DEFAULT FALSE COMMENT '是否指标',
    is_primary_key BOOLEAN DEFAULT FALSE COMMENT '是否主键',
    is_foreign_key BOOLEAN DEFAULT FALSE COMMENT '是否外键',
    column_order INT DEFAULT 0 COMMENT '字段顺序',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (table_id) REFERENCES aitt_data_tables(id),
    UNIQUE KEY uk_table_column (table_id, column_name),
    INDEX idx_column_name (column_name),
    INDEX idx_is_dimension (is_dimension),
    INDEX idx_is_metric (is_metric)
) COMMENT '字段元信息';

-- 查询历史表
CREATE TABLE aitt_query_history (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL COMMENT '用户ID',
    query_name VARCHAR(200) COMMENT '查询名称',
    natural_language_query TEXT NOT NULL COMMENT '自然语言查询',
    generated_sql TEXT NOT NULL COMMENT '生成的SQL',
    executed_sql TEXT COMMENT '实际执行的SQL',
    query_result JSON COMMENT '查询结果',
    execution_time_ms INT COMMENT '执行时间毫秒',
    row_count INT COMMENT '结果行数',
    status ENUM('success', 'error', 'timeout') NOT NULL COMMENT '执行状态',
    error_message TEXT COMMENT '错误信息',
    is_saved BOOLEAN DEFAULT FALSE COMMENT '是否保存',
    is_shared BOOLEAN DEFAULT FALSE COMMENT '是否分享',
    tags JSON COMMENT '标签',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES aitt_users(id),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    INDEX idx_is_saved (is_saved),
    INDEX idx_is_shared (is_shared)
) COMMENT '查询历史表';

-- 权限表
CREATE TABLE aitt_permissions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL COMMENT '用户ID',
    resource_type ENUM('data_source', 'table', 'column') NOT NULL COMMENT '资源类型',
    resource_id BIGINT NOT NULL COMMENT '资源ID',
    permission_type ENUM('read', 'write', 'admin') NOT NULL COMMENT '权限类型',
    row_filter JSON COMMENT '行级过滤条件',
    column_mask JSON COMMENT '列级脱敏规则',
    granted_by BIGINT NOT NULL COMMENT '授权人',
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP COMMENT '过期时间',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    FOREIGN KEY (user_id) REFERENCES aitt_users(id),
    FOREIGN KEY (granted_by) REFERENCES aitt_users(id),
    UNIQUE KEY uk_user_resource (user_id, resource_type, resource_id, permission_type),
    INDEX idx_user_id (user_id),
    INDEX idx_resource (resource_type, resource_id)
) COMMENT '权限表';

-- AI对话记录表
CREATE TABLE aitt_ai_conversations (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL COMMENT '用户ID',
    session_id VARCHAR(100) NOT NULL COMMENT '会话ID',
    message_type ENUM('user', 'assistant') NOT NULL COMMENT '消息类型',
    content TEXT NOT NULL COMMENT '消息内容',
    metadata JSON COMMENT '元数据',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES aitt_users(id),
    INDEX idx_user_session (user_id, session_id),
    INDEX idx_created_at (created_at)
) COMMENT 'AI对话记录表';

-- 大模型调用日志表
CREATE TABLE aitt_ai_call_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    conversation_id BIGINT NULL COMMENT '关联会话ID',
    model_name VARCHAR(100) COMMENT '模型名称',
    endpoint VARCHAR(100) COMMENT '调用端点',
    prompt_tokens INT DEFAULT 0 COMMENT '提示词Token',
    completion_tokens INT DEFAULT 0 COMMENT '生成Token',
    total_tokens INT DEFAULT 0 COMMENT '总Token',
    latency_ms INT DEFAULT 0 COMMENT '调用耗时毫秒',
    use_rag BOOLEAN DEFAULT FALSE COMMENT '是否启用RAG',
    rag_context_len INT DEFAULT 0 COMMENT 'RAG上下文长度',
    metadata_context_len INT DEFAULT 0 COMMENT '元数据上下文长度',
    rag_chunks JSON COMMENT '检索片段',
    status ENUM('success','error','timeout') NOT NULL DEFAULT 'success' COMMENT '调用状态',
    error_message TEXT COMMENT '错误信息',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (conversation_id) REFERENCES aitt_ai_conversations(id),
    INDEX idx_model_name (model_name),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) COMMENT '大模型调用日志表';

-- 查询模板表
CREATE TABLE aitt_query_templates (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(200) NOT NULL COMMENT '模板名称',
    description TEXT COMMENT '模板描述',
    category VARCHAR(50) COMMENT '分类',
    natural_language_template TEXT NOT NULL COMMENT '自然语言模板',
    sql_template TEXT NOT NULL COMMENT 'SQL模板',
    parameters JSON COMMENT '参数定义',
    usage_count INT DEFAULT 0 COMMENT '使用次数',
    is_public BOOLEAN DEFAULT FALSE COMMENT '是否公开',
    created_by BIGINT NOT NULL COMMENT '创建人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES aitt_users(id),
    INDEX idx_name (name),
    INDEX idx_category (category),
    INDEX idx_is_public (is_public)
) COMMENT '查询模板表';

-- 系统配置表
CREATE TABLE aitt_system_configs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    config_key VARCHAR(100) NOT NULL UNIQUE COMMENT '配置键',
    config_value TEXT COMMENT '配置值',
    description TEXT COMMENT '描述',
    is_encrypted BOOLEAN DEFAULT FALSE COMMENT '是否加密',
    updated_by BIGINT COMMENT '更新人',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (updated_by) REFERENCES aitt_users(id),
    INDEX idx_config_key (config_key)
) COMMENT '系统配置表';

-- 审计日志表
CREATE TABLE aitt_audit_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT COMMENT '用户ID',
    action VARCHAR(100) NOT NULL COMMENT '操作',
    resource_type VARCHAR(50) COMMENT '资源类型',
    resource_id BIGINT COMMENT '资源ID',
    details JSON COMMENT '详细信息',
    ip_address VARCHAR(45) COMMENT 'IP地址',
    user_agent TEXT COMMENT '用户代理',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES aitt_users(id),
    INDEX idx_user_id (user_id),
    INDEX idx_action (action),
    INDEX idx_created_at (created_at)
) COMMENT '审计日志表';

-- 元数据最近同步摘要表（支持历史记录）
CREATE TABLE aitt_metadata_sync_summaries (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    sources_total INT NOT NULL DEFAULT 0 COMMENT '数据源总数',
    tables_total INT NOT NULL DEFAULT 0 COMMENT '数据表总数',
    columns_total INT NOT NULL DEFAULT 0 COMMENT '字段总数',
    deleted_sources INT NOT NULL DEFAULT 0 COMMENT '删除的数据源数',
    deleted_tables INT NOT NULL DEFAULT 0 COMMENT '删除的数据表数',
    deleted_columns INT NOT NULL DEFAULT 0 COMMENT '删除的字段数',
    upserted_sources INT NOT NULL DEFAULT 0 COMMENT '新增/更新的数据源数',
    upserted_tables INT NOT NULL DEFAULT 0 COMMENT '新增/更新的数据表数',
    upserted_columns INT NOT NULL DEFAULT 0 COMMENT '新增/更新的字段数',
    last_sync_time TIMESTAMP NULL COMMENT '最近同步时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    INDEX idx_last_sync_time (last_sync_time),
    INDEX idx_created_at (created_at)
) COMMENT '元数据最近同步摘要';