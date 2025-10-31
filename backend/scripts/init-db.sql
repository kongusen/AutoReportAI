-- AutoReportAI Database Initialization Script
-- 包含所有迁移文件的特性，一次性创建完整的数据库结构
-- Version: Comprehensive (包含所有历史迁移)

-- ================================================
-- PostgreSQL Extensions and Settings
-- ================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search optimization  
CREATE EXTENSION IF NOT EXISTS "hstore";   -- For key-value storage

-- Set database timezone to UTC
-- ALTER DATABASE autoreport SET timezone TO 'UTC';

-- ================================================
-- Enum Types (All Combined)
-- ================================================
DO $$ 
BEGIN
    -- AI Provider types
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'aiprovidertype') THEN
        CREATE TYPE aiprovidertype AS ENUM ('openai', 'azure_openai', 'anthropic', 'google', 'mock');
    END IF;
    
    -- Data source types
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'datasourcetype') THEN
        CREATE TYPE datasourcetype AS ENUM ('sql', 'csv', 'api', 'push', 'doris');
    END IF;
    
    -- SQL query types
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sqlquerytype') THEN
        CREATE TYPE sqlquerytype AS ENUM ('single_table', 'multi_table', 'custom_view');
    END IF;
    
    -- Error categories
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'errorcategoryenum') THEN
        CREATE TYPE errorcategoryenum AS ENUM ('PARSING_ERROR', 'LLM_ERROR', 'FIELD_MATCHING_ERROR', 'ETL_ERROR', 'CONTENT_GENERATION_ERROR', 'VALIDATION_ERROR', 'SYSTEM_ERROR');
    END IF;
    
    -- Error severity
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'errorseverityenum') THEN
        CREATE TYPE errorseverityenum AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');
    END IF;
    
    -- Feedback types
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'feedbacktypeenum') THEN
        CREATE TYPE feedbacktypeenum AS ENUM ('CORRECTION', 'IMPROVEMENT', 'VALIDATION', 'COMPLAINT');
    END IF;
    
    -- Task status types
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'taskstatus') THEN
        CREATE TYPE taskstatus AS ENUM ('pending', 'processing', 'generating', 'completed', 'failed', 'cancelled');
    END IF;
    
    -- Processing mode
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'processingmode') THEN
        CREATE TYPE processingmode AS ENUM ('simple', 'intelligent', 'advanced');
    END IF;
    
    -- Agent workflow type
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'agentworkflowtype') THEN
        CREATE TYPE agentworkflowtype AS ENUM ('simple_report', 'complex_analysis', 'multi_stage', 'interactive');
    END IF;
    
    -- Column types
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'columntype') THEN
        CREATE TYPE columntype AS ENUM ('INT', 'BIGINT', 'FLOAT', 'DOUBLE', 'DECIMAL', 'VARCHAR', 'CHAR', 'TEXT', 'DATE', 'DATETIME', 'TIMESTAMP', 'BOOLEAN', 'JSON', 'ARRAY', 'UNKNOWN');
    END IF;
    
    -- Table types
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tabletype') THEN
        CREATE TYPE tabletype AS ENUM ('TABLE', 'VIEW', 'MATERIALIZED_VIEW', 'EXTERNAL_TABLE');
    END IF;
    
    -- Relation types
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'relationtype') THEN
        CREATE TYPE relationtype AS ENUM ('ONE_TO_ONE', 'ONE_TO_MANY', 'MANY_TO_MANY');
    END IF;
    
    -- Report period
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'reportperiod') THEN
        CREATE TYPE reportperiod AS ENUM ('daily', 'weekly', 'monthly', 'yearly');
    END IF;
    
    -- Model types (for LLM servers)
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'modeltype') THEN
        CREATE TYPE modeltype AS ENUM ('default', 'think');
    END IF;
    
    -- Provider types (for LLM servers)
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'providertype') THEN
        CREATE TYPE providertype AS ENUM ('openai', 'anthropic', 'google', 'cohere', 'huggingface', 'gpustake', 'custom');
    END IF;
    
END $$;

-- ================================================
-- Base Tables (No Dependencies)
-- ================================================

-- Users table (foundation table)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR NOT NULL,
    username VARCHAR,
    hashed_password VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    full_name VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- ================================================
-- Level 1 Dependencies (Depend only on users)
-- ================================================

-- AI Providers table
CREATE TABLE IF NOT EXISTS ai_providers (
    id SERIAL PRIMARY KEY,
    provider_name VARCHAR NOT NULL,
    provider_type aiprovidertype NOT NULL,
    api_base_url VARCHAR,
    api_key VARCHAR,
    default_model_name VARCHAR,
    is_active BOOLEAN DEFAULT TRUE,
    user_id UUID NOT NULL REFERENCES users(id)
);

-- Data Sources table  
CREATE TABLE IF NOT EXISTS data_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL,
    slug VARCHAR,
    display_name VARCHAR,
    source_type datasourcetype NOT NULL,
    connection_string VARCHAR,
    sql_query_type sqlquerytype,
    base_query TEXT,
    join_config JSON,
    column_mapping JSON,
    where_conditions JSON,
    wide_table_name VARCHAR,
    wide_table_schema JSON,
    api_url VARCHAR,
    api_method VARCHAR,
    api_headers JSON,
    api_body JSON,
    push_endpoint VARCHAR,
    push_auth_config JSON,
    doris_fe_hosts JSON,
    doris_be_hosts JSON,
    doris_http_port INTEGER,
    doris_query_port INTEGER,
    doris_database VARCHAR,
    doris_username VARCHAR,
    doris_password VARCHAR,
    is_active BOOLEAN DEFAULT TRUE,
    last_sync_time VARCHAR,
    user_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Templates table
CREATE TABLE IF NOT EXISTS templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    content TEXT,
    template_type VARCHAR(50),
    original_filename VARCHAR(255),
    file_path VARCHAR(500),  -- MinIO/storage file path for original uploaded files
    file_size INTEGER,
    is_public BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    user_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- User Profiles table
CREATE TABLE IF NOT EXISTS user_profiles (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL UNIQUE REFERENCES users(id),
    language VARCHAR(10) DEFAULT 'en',
    theme VARCHAR(20) DEFAULT 'light',
    email_notifications BOOLEAN DEFAULT TRUE,
    report_notifications BOOLEAN DEFAULT TRUE,
    system_notifications BOOLEAN DEFAULT TRUE,
    default_storage_days INTEGER DEFAULT 30,
    auto_cleanup_enabled BOOLEAN DEFAULT FALSE,
    default_report_format VARCHAR(10) DEFAULT 'pdf',
    default_ai_provider VARCHAR(100),
    custom_css TEXT,
    dashboard_layout TEXT,
    timezone VARCHAR(50) DEFAULT 'UTC',
    date_format VARCHAR(20) DEFAULT 'YYYY-MM-DD',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- LLM Servers table
CREATE TABLE IF NOT EXISTS llm_servers (
    id SERIAL PRIMARY KEY,
    server_id UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    base_url VARCHAR(512) NOT NULL,
    provider_type providertype NOT NULL DEFAULT 'openai',
    api_key TEXT,
    auth_enabled BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    is_healthy BOOLEAN DEFAULT FALSE,
    last_health_check TIMESTAMP WITH TIME ZONE,
    timeout_seconds INTEGER DEFAULT 60,
    max_retries INTEGER DEFAULT 3,
    server_version VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT llm_servers_user_base_url_key UNIQUE (user_id, base_url)
);

-- LLM Models table
CREATE TABLE IF NOT EXISTS llm_models (
    id SERIAL PRIMARY KEY,
    server_id INTEGER NOT NULL REFERENCES llm_servers(id),
    name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    model_type modeltype NOT NULL,
    provider_name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 50,
    is_healthy BOOLEAN DEFAULT FALSE,
    last_health_check TIMESTAMP WITH TIME ZONE,
    health_check_message TEXT,
    max_tokens INTEGER,
    temperature_default REAL DEFAULT 0.7,
    supports_system_messages BOOLEAN DEFAULT TRUE,
    supports_function_calls BOOLEAN DEFAULT FALSE,
    supports_thinking BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User LLM Preferences table
CREATE TABLE IF NOT EXISTS user_llm_preferences (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    default_llm_server_id INTEGER REFERENCES llm_servers(id),
    default_provider_name VARCHAR(100),
    default_model_name VARCHAR(100),
    personal_api_keys JSON DEFAULT '{}',
    preferred_temperature REAL DEFAULT 0.7,
    max_tokens_limit INTEGER DEFAULT 4000,
    daily_token_quota INTEGER DEFAULT 50000,
    monthly_cost_limit REAL DEFAULT 100.0,
    enable_caching BOOLEAN DEFAULT TRUE,
    cache_ttl_hours INTEGER DEFAULT 24,
    enable_learning BOOLEAN DEFAULT TRUE,
    provider_priorities JSON DEFAULT '{}',
    model_preferences JSON DEFAULT '{}',
    custom_settings JSON DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User LLM Usage Quotas table
CREATE TABLE IF NOT EXISTS user_llm_usage_quotas (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    quota_period VARCHAR(20) DEFAULT 'monthly',
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    tokens_used INTEGER DEFAULT 0,
    requests_made INTEGER DEFAULT 0,
    total_cost REAL DEFAULT 0.0,
    token_limit INTEGER NOT NULL,
    request_limit INTEGER DEFAULT 1000,
    cost_limit REAL NOT NULL,
    is_exceeded BOOLEAN DEFAULT FALSE,
    warning_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- LLM Call Logs table
CREATE TABLE IF NOT EXISTS llm_call_logs (
    id SERIAL PRIMARY KEY,
    request_type VARCHAR(50) NOT NULL,
    prompt_template VARCHAR(100) NOT NULL,
    input_data JSON NOT NULL,
    response_data JSON,
    model_used VARCHAR(100) NOT NULL,
    tokens_used INTEGER,
    processing_time_ms INTEGER,
    cost_estimate DECIMAL(10,6),
    success BOOLEAN NOT NULL,
    error_message TEXT,
    user_id UUID REFERENCES users(id),
    session_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ================================================
-- Level 2 Dependencies  
-- ================================================

-- Tasks table (depends on users, data_sources, templates)
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    description VARCHAR,
    schedule VARCHAR,
    recipients JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP,
    owner_id UUID NOT NULL REFERENCES users(id),
    data_source_id UUID NOT NULL REFERENCES data_sources(id),
    template_id UUID NOT NULL REFERENCES templates(id),
    -- Enhanced fields from migrations
    status taskstatus DEFAULT 'pending',
    processing_mode processingmode DEFAULT 'intelligent',
    workflow_type agentworkflowtype DEFAULT 'simple_report',
    orchestration_config JSON,
    max_context_tokens INTEGER DEFAULT 32000,
    enable_compression BOOLEAN DEFAULT TRUE,
    compression_threshold REAL DEFAULT 0.8,
    execution_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    last_execution_at TIMESTAMP,
    average_execution_time REAL,
    average_token_usage INTEGER,
    last_execution_duration REAL,
    report_period reportperiod DEFAULT 'monthly'
);

-- Databases table (multi-database support)
CREATE TABLE IF NOT EXISTS databases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL,
    display_name VARCHAR,
    description TEXT,
    data_source_id UUID NOT NULL REFERENCES data_sources(id),
    table_count INTEGER,
    total_size_mb BIGINT,
    business_domain VARCHAR,
    data_sensitivity VARCHAR,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    last_analyzed TIMESTAMP,
    CONSTRAINT unique_database_per_source UNIQUE (data_source_id, name)
);

-- Table Schemas table (schema discovery)
CREATE TABLE IF NOT EXISTS table_schemas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_source_id UUID NOT NULL REFERENCES data_sources(id),
    table_name VARCHAR NOT NULL,
    table_schema VARCHAR,
    table_catalog VARCHAR,
    columns_info JSON NOT NULL,
    primary_keys JSON,
    indexes JSON,
    constraints JSON,
    estimated_row_count BIGINT,
    table_size_bytes BIGINT,
    last_analyzed TIMESTAMP WITH TIME ZONE,
    business_category VARCHAR,
    data_freshness VARCHAR,
    update_frequency VARCHAR,
    data_quality_score REAL,
    completeness_rate REAL,
    accuracy_rate REAL,
    is_active BOOLEAN DEFAULT TRUE,
    is_analyzed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- ================================================
-- Level 3 Dependencies
-- ================================================

-- Tables table (depends on databases)
CREATE TABLE IF NOT EXISTS tables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL,
    display_name VARCHAR,
    description TEXT,
    database_id UUID NOT NULL REFERENCES databases(id),
    table_type tabletype,
    engine VARCHAR,
    charset VARCHAR,
    row_count BIGINT,
    size_mb REAL,
    column_count INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    last_analyzed TIMESTAMP,
    business_tags JSON,
    data_sensitivity VARCHAR,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT unique_table_per_database UNIQUE (database_id, name)
);

-- Task Executions table (depends on tasks)
CREATE TABLE IF NOT EXISTS task_executions (
    id SERIAL PRIMARY KEY,
    execution_id UUID,
    task_id INTEGER NOT NULL REFERENCES tasks(id),
    execution_status taskstatus,
    workflow_type agentworkflowtype,
    workflow_definition JSON,
    agent_execution_plan JSON,
    current_step VARCHAR(255),
    execution_context JSON,
    input_parameters JSON,
    processing_config JSON,
    execution_result JSON,
    output_artifacts JSON,
    error_details TEXT,
    error_trace TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    total_duration INTEGER,
    agent_execution_times JSON,
    progress_percentage INTEGER,
    progress_details JSON,
    celery_task_id VARCHAR(255),
    worker_node VARCHAR(255),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Template Placeholders table (depends on templates)
CREATE TABLE IF NOT EXISTS template_placeholders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
    placeholder_name VARCHAR(255) NOT NULL,
    placeholder_text VARCHAR(500) NOT NULL,
    placeholder_type VARCHAR(50) NOT NULL,
    content_type VARCHAR(50) NOT NULL,
    -- Agent analysis results
    agent_analyzed BOOLEAN NOT NULL DEFAULT FALSE,
    target_database VARCHAR(100),
    target_table VARCHAR(100),
    required_fields JSONB,
    generated_sql TEXT,
    sql_validated BOOLEAN NOT NULL DEFAULT FALSE,
    -- Execution configuration
    execution_order INTEGER NOT NULL DEFAULT 1,
    cache_ttl_hours INTEGER NOT NULL DEFAULT 24,
    is_required BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    -- Agent configuration
    agent_workflow_id VARCHAR(100),
    agent_config JSONB DEFAULT '{}'::jsonb,
    -- Metadata
    description TEXT,
    confidence_score REAL NOT NULL DEFAULT 0.0,
    content_hash VARCHAR(16),
    -- Parsing metadata
    original_type VARCHAR(50),
    extracted_description TEXT,
    parsing_metadata JSONB DEFAULT '{}'::jsonb,
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    analyzed_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT uq_template_placeholder_name UNIQUE (template_id, placeholder_name)
);

-- Report History table (depends on tasks and users)
CREATE TABLE IF NOT EXISTS report_history (
    id SERIAL PRIMARY KEY,
    status VARCHAR NOT NULL,
    file_path VARCHAR,
    file_size INTEGER DEFAULT 0,
    error_message TEXT,
    result TEXT,
    processing_metadata JSON,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    task_id INTEGER NOT NULL REFERENCES tasks(id),
    user_id UUID NOT NULL REFERENCES users(id)
);

-- ================================================  
-- Level 4 Dependencies
-- ================================================

-- Table Columns table (depends on tables)
CREATE TABLE IF NOT EXISTS table_columns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL,
    display_name VARCHAR,
    table_id UUID NOT NULL REFERENCES tables(id),
    data_type columntype NOT NULL,
    raw_type VARCHAR NOT NULL,
    max_length INTEGER,
    precision INTEGER,
    scale INTEGER,
    is_nullable BOOLEAN,
    is_primary_key BOOLEAN,
    is_foreign_key BOOLEAN,
    is_unique BOOLEAN,
    is_indexed BOOLEAN,
    default_value VARCHAR,
    column_comment TEXT,
    business_meaning VARCHAR,
    ordinal_position INTEGER NOT NULL,
    null_count BIGINT,
    unique_count BIGINT,
    distinct_count BIGINT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    CONSTRAINT unique_column_per_table UNIQUE (table_id, name)
);

-- Column Schemas table (depends on table_schemas) 
CREATE TABLE IF NOT EXISTS column_schemas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_schema_id UUID NOT NULL REFERENCES table_schemas(id),
    column_name VARCHAR NOT NULL,
    column_type VARCHAR NOT NULL,
    normalized_type columntype NOT NULL,
    column_size INTEGER,
    precision INTEGER,
    scale INTEGER,
    is_nullable BOOLEAN,
    is_primary_key BOOLEAN,
    is_unique BOOLEAN,
    is_indexed BOOLEAN,
    default_value VARCHAR,
    business_name VARCHAR,
    business_description TEXT,
    semantic_category VARCHAR,
    null_count BIGINT,
    unique_count BIGINT,
    distinct_count BIGINT,
    min_value VARCHAR,
    max_value VARCHAR,
    avg_value VARCHAR,
    data_patterns JSON,
    sample_values JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Table Indexes table (depends on tables)
CREATE TABLE IF NOT EXISTS table_indexes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL,
    table_id UUID NOT NULL REFERENCES tables(id),
    index_type VARCHAR,
    is_unique BOOLEAN,
    is_primary BOOLEAN,
    columns JSON NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    CONSTRAINT unique_index_per_table UNIQUE (table_id, name)
);

-- Table Relations table (depends on tables)
CREATE TABLE IF NOT EXISTS table_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL,
    parent_table_id UUID NOT NULL REFERENCES tables(id),
    child_table_id UUID NOT NULL REFERENCES tables(id),
    relation_type relationtype NOT NULL,
    parent_columns JSON NOT NULL,
    child_columns JSON NOT NULL,
    confidence_score REAL,
    is_validated BOOLEAN,
    business_meaning TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    CONSTRAINT unique_relation UNIQUE (parent_table_id, child_table_id, name)
);

-- Table Relationships table (schema discovery relationships)
CREATE TABLE IF NOT EXISTS table_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_source_id UUID NOT NULL REFERENCES data_sources(id),
    source_table_id UUID NOT NULL REFERENCES table_schemas(id),
    target_table_id UUID NOT NULL REFERENCES table_schemas(id),
    relationship_type VARCHAR NOT NULL,
    source_column VARCHAR NOT NULL,
    target_column VARCHAR NOT NULL,
    confidence_score REAL,
    business_description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Placeholder Values table (depends on template_placeholders and data_sources)
CREATE TABLE IF NOT EXISTS placeholder_values (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    placeholder_id UUID NOT NULL REFERENCES template_placeholders(id) ON DELETE CASCADE,
    data_source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    -- Execution results
    raw_query_result JSONB,
    processed_value JSONB,
    formatted_text TEXT,
    -- Execution metadata
    execution_sql TEXT,
    execution_time_ms INTEGER,
    row_count INTEGER NOT NULL DEFAULT 0,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    -- Cache management
    cache_key VARCHAR(255),
    expires_at TIMESTAMP WITH TIME ZONE,
    hit_count INTEGER NOT NULL DEFAULT 0,
    last_hit_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    -- Time-related fields (latest migration)
    execution_time TIMESTAMP WITH TIME ZONE,
    report_period VARCHAR(20),
    period_start TIMESTAMP WITH TIME ZONE,
    period_end TIMESTAMP WITH TIME ZONE,
    sql_parameters_snapshot JSON,
    execution_batch_id VARCHAR(100),
    version_hash VARCHAR(64),
    is_latest_version BOOLEAN DEFAULT TRUE
);

-- Template Execution History table
CREATE TABLE IF NOT EXISTS template_execution_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID NOT NULL REFERENCES templates(id),
    data_source_id UUID NOT NULL REFERENCES data_sources(id),
    user_id UUID REFERENCES users(id),
    -- Execution information
    execution_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    -- Phase markers
    analysis_completed BOOLEAN NOT NULL DEFAULT FALSE,
    sql_validation_completed BOOLEAN NOT NULL DEFAULT FALSE,
    data_extraction_completed BOOLEAN NOT NULL DEFAULT FALSE,
    report_generation_completed BOOLEAN NOT NULL DEFAULT FALSE,
    -- Performance metrics
    total_duration_ms INTEGER,
    analysis_duration_ms INTEGER,
    extraction_duration_ms INTEGER,
    generation_duration_ms INTEGER,
    -- Result information
    placeholders_analyzed INTEGER NOT NULL DEFAULT 0,
    placeholders_extracted INTEGER NOT NULL DEFAULT 0,
    cache_hit_rate REAL NOT NULL DEFAULT 0.0,
    output_file_path VARCHAR(500),
    output_file_size INTEGER,
    -- Error information
    error_details JSONB,
    failed_placeholders JSONB,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    end_time TIMESTAMP WITH TIME ZONE
);

-- ================================================
-- Additional Tables (Analytics, Logs, etc.)
-- ================================================

-- ETL Jobs table
CREATE TABLE IF NOT EXISTS etl_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL,
    description VARCHAR,
    data_source_id UUID NOT NULL REFERENCES data_sources(id),
    user_id UUID NOT NULL REFERENCES users(id),
    destination_table_name VARCHAR NOT NULL,
    source_query TEXT NOT NULL,
    transformation_config JSON,
    schedule VARCHAR,
    enabled BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Analytics Data table
CREATE TABLE IF NOT EXISTS analytics_data (
    id SERIAL PRIMARY KEY,
    record_id VARCHAR NOT NULL,
    data JSON NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    data_source_id UUID NOT NULL REFERENCES data_sources(id)
);

-- Error Logs table
CREATE TABLE IF NOT EXISTS error_logs (
    id SERIAL PRIMARY KEY,
    error_id VARCHAR(32) NOT NULL,
    category errorcategoryenum NOT NULL,
    severity errorseverityenum NOT NULL,
    message TEXT NOT NULL,
    placeholder_text VARCHAR(500),
    placeholder_type VARCHAR(50),
    placeholder_description TEXT,
    context_before TEXT,
    context_after TEXT,
    data_source_id UUID REFERENCES data_sources(id),
    user_id UUID REFERENCES users(id),
    session_id VARCHAR(255),
    stack_trace TEXT,
    additional_data JSON,
    resolved BOOLEAN NOT NULL,
    resolution_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Field Mapping Cache table
CREATE TABLE IF NOT EXISTS field_mapping_cache (
    id SERIAL PRIMARY KEY,
    placeholder_signature VARCHAR(255) NOT NULL,
    data_source_id UUID NOT NULL REFERENCES data_sources(id),
    matched_field VARCHAR(255) NOT NULL,
    confidence_score DECIMAL(3,2) NOT NULL,
    transformation_config JSON,
    usage_count INTEGER NOT NULL,
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Knowledge Base table
CREATE TABLE IF NOT EXISTS knowledge_base (
    id SERIAL PRIMARY KEY,
    entry_id VARCHAR(32) NOT NULL,
    placeholder_signature VARCHAR(255) NOT NULL,
    successful_mappings JSON,
    failed_mappings JSON,
    user_corrections JSON,
    pattern_analysis JSON,
    confidence_metrics JSON,
    usage_statistics JSON,
    data_source_id UUID REFERENCES data_sources(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Learning Rules table
CREATE TABLE IF NOT EXISTS learning_rules (
    id SERIAL PRIMARY KEY,
    rule_id VARCHAR(32) NOT NULL,
    placeholder_pattern VARCHAR(500) NOT NULL,
    field_mapping VARCHAR(255) NOT NULL,
    confidence_score DECIMAL(3,2) NOT NULL,
    usage_count INTEGER NOT NULL,
    success_count INTEGER NOT NULL,
    success_rate DECIMAL(3,2) NOT NULL,
    created_from_feedback BOOLEAN NOT NULL,
    data_source_id UUID NOT NULL REFERENCES data_sources(id),
    rule_metadata JSON,
    active BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Placeholder Mapping Cache table (renamed to match model)
CREATE TABLE IF NOT EXISTS placeholder_mappings (
    id SERIAL PRIMARY KEY,
    placeholder_signature VARCHAR(255) NOT NULL,
    data_source_id UUID NOT NULL REFERENCES data_sources(id),
    matched_field VARCHAR(255) NOT NULL,
    confidence_score DECIMAL(3,2) NOT NULL,
    transformation_config JSON,
    usage_count INTEGER NOT NULL,
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Placeholder Mapping Cache table (legacy name for compatibility)
CREATE TABLE IF NOT EXISTS placeholder_mapping_cache (
    id SERIAL PRIMARY KEY,
    placeholder_signature VARCHAR(255) NOT NULL,
    data_source_id UUID NOT NULL REFERENCES data_sources(id),
    matched_field VARCHAR(255) NOT NULL,
    confidence_score DECIMAL(3,2) NOT NULL,
    transformation_config JSON,
    usage_count INTEGER NOT NULL,
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Placeholder Chart Cache table (新架构两阶段图表缓存)
CREATE TABLE IF NOT EXISTS placeholder_chart_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    placeholder_id UUID NOT NULL REFERENCES template_placeholders(id),
    template_id UUID NOT NULL REFERENCES templates(id),
    data_source_id UUID NOT NULL REFERENCES data_sources(id),
    user_id UUID NOT NULL REFERENCES users(id),
    -- 阶段一：SQL和数据
    generated_sql TEXT NOT NULL,
    sql_metadata JSON,
    raw_data JSON,
    processed_data JSON,
    data_quality_score REAL DEFAULT 0.0,
    -- 阶段二：图表配置
    chart_type VARCHAR(50) NOT NULL,
    echarts_config JSON NOT NULL,
    chart_metadata JSON,
    -- 执行信息
    execution_mode VARCHAR(20) DEFAULT 'test_with_chart',
    execution_time_ms INTEGER DEFAULT 0,
    sql_execution_time_ms INTEGER DEFAULT 0,
    chart_generation_time_ms INTEGER DEFAULT 0,
    -- 状态标志
    is_valid BOOLEAN DEFAULT TRUE,
    is_preview BOOLEAN DEFAULT TRUE,
    stage_completed VARCHAR(20) DEFAULT 'chart_complete',
    -- 缓存管理
    cache_key VARCHAR(255) UNIQUE,
    cache_ttl_hours INTEGER DEFAULT 24,
    hit_count INTEGER DEFAULT 0,
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    last_accessed_at TIMESTAMP WITH TIME ZONE
);

-- Placeholder Processing History table
CREATE TABLE IF NOT EXISTS placeholder_processing_history (
    id SERIAL PRIMARY KEY,
    template_id UUID REFERENCES templates(id),
    placeholder_text VARCHAR(500) NOT NULL,
    placeholder_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    context_info JSON,
    llm_understanding JSON,
    field_mapping JSON,
    processed_value TEXT,
    processing_time_ms INTEGER,
    confidence_score DECIMAL(3,2),
    success BOOLEAN NOT NULL,
    error_message TEXT,
    user_id UUID REFERENCES users(id),
    session_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Report Quality Scores table
CREATE TABLE IF NOT EXISTS report_quality_scores (
    id SERIAL PRIMARY KEY,
    report_id VARCHAR(255) NOT NULL,
    template_id UUID REFERENCES templates(id),
    user_id UUID REFERENCES users(id),
    overall_score DECIMAL(3,2) NOT NULL,
    language_fluency_score DECIMAL(3,2),
    data_consistency_score DECIMAL(3,2),
    completeness_score DECIMAL(3,2),
    accuracy_score DECIMAL(3,2),
    formatting_score DECIMAL(3,2),
    quality_issues JSON,
    improvement_suggestions JSON,
    processing_time_ms INTEGER,
    llm_analysis_used BOOLEAN NOT NULL,
    manual_review_required BOOLEAN NOT NULL,
    reviewer_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reviewed_at TIMESTAMP WITH TIME ZONE
);

-- User Feedbacks table
CREATE TABLE IF NOT EXISTS user_feedbacks (
    id SERIAL PRIMARY KEY,
    feedback_id VARCHAR(32) NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id),
    error_id VARCHAR(32),
    feedback_type feedbacktypeenum NOT NULL,
    placeholder_text VARCHAR(500) NOT NULL,
    original_result TEXT NOT NULL,
    corrected_result TEXT,
    suggested_field VARCHAR(255),
    confidence_rating INTEGER,
    comments TEXT,
    processed BOOLEAN NOT NULL,
    processing_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);

-- ================================================
-- Indexes
-- ================================================

-- Users table indexes
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);
CREATE INDEX IF NOT EXISTS ix_users_full_name ON users (full_name);
CREATE INDEX IF NOT EXISTS ix_users_id ON users (id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username);

-- AI Providers table indexes
CREATE INDEX IF NOT EXISTS ix_ai_providers_id ON ai_providers (id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_ai_providers_provider_name ON ai_providers (provider_name);

-- Data Sources table indexes
CREATE INDEX IF NOT EXISTS ix_data_sources_display_name ON data_sources (display_name);
CREATE UNIQUE INDEX IF NOT EXISTS ix_data_sources_name ON data_sources (name);
CREATE INDEX IF NOT EXISTS ix_data_sources_slug ON data_sources (slug);

-- Templates table indexes
CREATE INDEX IF NOT EXISTS ix_templates_name ON templates (name);

-- User Profiles table indexes
CREATE INDEX IF NOT EXISTS ix_user_profiles_id ON user_profiles (id);

-- LLM Servers table indexes
CREATE INDEX IF NOT EXISTS ix_llm_servers_id ON llm_servers (id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_llm_servers_server_id ON llm_servers (server_id);
CREATE INDEX IF NOT EXISTS ix_llm_servers_name ON llm_servers (name);
CREATE INDEX IF NOT EXISTS ix_llm_servers_is_active ON llm_servers (is_active);
CREATE INDEX IF NOT EXISTS ix_llm_servers_is_healthy ON llm_servers (is_healthy);

-- LLM Models table indexes
CREATE INDEX IF NOT EXISTS ix_llm_models_id ON llm_models (id);
CREATE INDEX IF NOT EXISTS ix_llm_models_server_id ON llm_models (server_id);
CREATE INDEX IF NOT EXISTS ix_llm_models_name ON llm_models (name);
CREATE INDEX IF NOT EXISTS ix_llm_models_model_type ON llm_models (model_type);
CREATE INDEX IF NOT EXISTS ix_llm_models_provider_name ON llm_models (provider_name);
CREATE INDEX IF NOT EXISTS ix_llm_models_active_healthy ON llm_models (is_active, is_healthy);

-- User LLM Preferences table indexes
CREATE INDEX IF NOT EXISTS ix_user_llm_preferences_id ON user_llm_preferences (id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_user_llm_preferences_user_id ON user_llm_preferences (user_id);

-- User LLM Usage Quotas table indexes
CREATE INDEX IF NOT EXISTS ix_user_llm_usage_quotas_id ON user_llm_usage_quotas (id);
CREATE INDEX IF NOT EXISTS ix_user_llm_usage_quotas_user_period ON user_llm_usage_quotas (user_id, quota_period);
CREATE INDEX IF NOT EXISTS ix_user_llm_usage_quotas_period_range ON user_llm_usage_quotas (period_start, period_end);

-- LLM Call Logs table indexes
CREATE INDEX IF NOT EXISTS ix_llm_call_logs_id ON llm_call_logs (id);

-- Tasks table indexes
CREATE INDEX IF NOT EXISTS ix_tasks_id ON tasks (id);
CREATE INDEX IF NOT EXISTS ix_tasks_name ON tasks (name);

-- Databases table indexes
CREATE INDEX IF NOT EXISTS ix_databases_name ON databases (name);
CREATE INDEX IF NOT EXISTS idx_database_source_name ON databases (data_source_id, name);

-- Tables table indexes
CREATE INDEX IF NOT EXISTS ix_tables_name ON tables (name);
CREATE INDEX IF NOT EXISTS idx_table_database_name ON tables (database_id, name);

-- Table Schemas table indexes
CREATE INDEX IF NOT EXISTS ix_table_schemas_table_name ON table_schemas (table_name);

-- Table Columns table indexes
CREATE INDEX IF NOT EXISTS ix_table_columns_name ON table_columns (name);
CREATE INDEX IF NOT EXISTS idx_column_table_name ON table_columns (table_id, name);
CREATE INDEX IF NOT EXISTS idx_column_ordinal ON table_columns (table_id, ordinal_position);

-- Column Schemas table indexes
CREATE INDEX IF NOT EXISTS ix_column_schemas_column_name ON column_schemas (column_name);

-- Table Relations table indexes
CREATE INDEX IF NOT EXISTS idx_relation_parent ON table_relations (parent_table_id);
CREATE INDEX IF NOT EXISTS idx_relation_child ON table_relations (child_table_id);

-- Task Executions table indexes
CREATE UNIQUE INDEX IF NOT EXISTS ix_task_executions_execution_id ON task_executions (execution_id);
CREATE INDEX IF NOT EXISTS ix_task_executions_id ON task_executions (id);

-- Template Placeholders table indexes
CREATE INDEX IF NOT EXISTS ix_template_placeholders_template_id ON template_placeholders (template_id);
CREATE INDEX IF NOT EXISTS ix_template_placeholders_analyzed ON template_placeholders (agent_analyzed, is_active);
CREATE INDEX IF NOT EXISTS ix_template_placeholders_execution_order ON template_placeholders (template_id, execution_order);
CREATE INDEX IF NOT EXISTS ix_template_placeholders_content_hash ON template_placeholders (content_hash);

-- Placeholder Values table indexes
CREATE INDEX IF NOT EXISTS ix_placeholder_values_cache_key ON placeholder_values (cache_key);
CREATE INDEX IF NOT EXISTS ix_placeholder_values_expires_at ON placeholder_values (expires_at);
CREATE INDEX IF NOT EXISTS ix_placeholder_values_placeholder_datasource ON placeholder_values (placeholder_id, data_source_id);
-- Additional indexes for placeholder_values table (from migration 004)
CREATE INDEX IF NOT EXISTS idx_placeholder_values_batch ON placeholder_values(execution_batch_id);
CREATE INDEX IF NOT EXISTS idx_placeholder_values_cache ON placeholder_values(cache_key, expires_at) WHERE cache_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_placeholder_values_latest ON placeholder_values(placeholder_id, data_source_id, is_latest_version, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_placeholder_values_placeholder_source ON placeholder_values(placeholder_id, data_source_id);
CREATE INDEX IF NOT EXISTS idx_placeholder_values_created ON placeholder_values(created_at DESC);

-- Template Execution History table indexes
CREATE INDEX IF NOT EXISTS ix_template_execution_history_template_time ON template_execution_history (template_id, start_time);

-- ETL Jobs table indexes
CREATE INDEX IF NOT EXISTS ix_etl_jobs_destination_table_name ON etl_jobs (destination_table_name);
CREATE INDEX IF NOT EXISTS ix_etl_jobs_name ON etl_jobs (name);

-- Analytics Data table indexes
CREATE INDEX IF NOT EXISTS ix_analytics_data_id ON analytics_data (id);
CREATE INDEX IF NOT EXISTS ix_analytics_data_record_id ON analytics_data (record_id);

-- Error Logs table indexes
CREATE UNIQUE INDEX IF NOT EXISTS ix_error_logs_error_id ON error_logs (error_id);
CREATE INDEX IF NOT EXISTS ix_error_logs_id ON error_logs (id);

-- Field Mapping Cache table indexes
CREATE INDEX IF NOT EXISTS ix_field_mapping_cache_id ON field_mapping_cache (id);
CREATE INDEX IF NOT EXISTS ix_field_mapping_cache_placeholder_signature ON field_mapping_cache (placeholder_signature);

-- Knowledge Base table indexes
CREATE UNIQUE INDEX IF NOT EXISTS ix_knowledge_base_entry_id ON knowledge_base (entry_id);
CREATE INDEX IF NOT EXISTS ix_knowledge_base_id ON knowledge_base (id);
CREATE INDEX IF NOT EXISTS ix_knowledge_base_placeholder_signature ON knowledge_base (placeholder_signature);

-- Learning Rules table indexes
CREATE INDEX IF NOT EXISTS ix_learning_rules_id ON learning_rules (id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_learning_rules_rule_id ON learning_rules (rule_id);

-- Placeholder Mappings table indexes (新架构主表)
CREATE INDEX IF NOT EXISTS ix_placeholder_mappings_id ON placeholder_mappings (id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_placeholder_mappings_signature ON placeholder_mappings (placeholder_signature);
CREATE INDEX IF NOT EXISTS ix_placeholder_mappings_data_source ON placeholder_mappings (data_source_id);

-- Placeholder Mapping Cache table indexes (兼容性表)
CREATE INDEX IF NOT EXISTS ix_placeholder_mapping_cache_id ON placeholder_mapping_cache (id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_placeholder_mapping_cache_placeholder_signature ON placeholder_mapping_cache (placeholder_signature);

-- Placeholder Chart Cache table indexes (两阶段图表缓存)
CREATE INDEX IF NOT EXISTS ix_placeholder_chart_cache_id ON placeholder_chart_cache (id);
CREATE INDEX IF NOT EXISTS ix_placeholder_chart_cache_placeholder_id ON placeholder_chart_cache (placeholder_id);
CREATE INDEX IF NOT EXISTS ix_placeholder_chart_cache_template_id ON placeholder_chart_cache (template_id);
CREATE INDEX IF NOT EXISTS ix_placeholder_chart_cache_data_source_id ON placeholder_chart_cache (data_source_id);
CREATE INDEX IF NOT EXISTS ix_placeholder_chart_cache_user_id ON placeholder_chart_cache (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_placeholder_chart_cache_cache_key ON placeholder_chart_cache (cache_key);
CREATE INDEX IF NOT EXISTS ix_placeholder_chart_cache_expires_at ON placeholder_chart_cache (expires_at);
CREATE INDEX IF NOT EXISTS ix_placeholder_chart_cache_stage_valid ON placeholder_chart_cache (stage_completed, is_valid);

-- Placeholder Processing History table indexes
CREATE INDEX IF NOT EXISTS ix_placeholder_processing_history_id ON placeholder_processing_history (id);

-- Report Quality Scores table indexes
CREATE INDEX IF NOT EXISTS ix_report_quality_scores_id ON report_quality_scores (id);
CREATE INDEX IF NOT EXISTS ix_report_quality_scores_report_id ON report_quality_scores (report_id);

-- Report History table indexes
CREATE INDEX IF NOT EXISTS ix_report_history_id ON report_history (id);

-- User Feedbacks table indexes
CREATE UNIQUE INDEX IF NOT EXISTS ix_user_feedbacks_feedback_id ON user_feedbacks (feedback_id);
CREATE INDEX IF NOT EXISTS ix_user_feedbacks_id ON user_feedbacks (id);

-- ================================================
-- Success Message
-- ================================================
DO $$ 
BEGIN 
    RAISE NOTICE '=================================================';
    RAISE NOTICE 'AutoReportAI Database Initialization Finished!';
    RAISE NOTICE '=================================================';
    RAISE NOTICE 'Extensions created: uuid-ossp, pg_trgm, hstore';
    RAISE NOTICE 'Enum types created: 13 types';
    RAISE NOTICE 'Tables created: 36 tables with all relationships (includes new DDD architecture tables)';
    RAISE NOTICE 'Indexes created: All performance indexes';
    RAISE NOTICE 'Database ready for application use!';
    RAISE NOTICE '=================================================';
END $$;
