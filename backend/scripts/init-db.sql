-- AutoReportAI Database Initialization Script
-- This script sets up the PostgreSQL database with optimizations and extensions

-- Create extensions for advanced functionality
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "hstore";

-- Set up database configuration for optimal performance
ALTER DATABASE autoreport SET timezone TO 'UTC';
ALTER DATABASE autoreport SET log_statement TO 'none';
ALTER DATABASE autoreport SET log_min_duration_statement TO '1000';

-- Create custom schemas for organization
CREATE SCHEMA IF NOT EXISTS agents;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS audit;

-- Grant permissions
GRANT USAGE ON SCHEMA agents TO postgres;
GRANT USAGE ON SCHEMA analytics TO postgres;
GRANT USAGE ON SCHEMA audit TO postgres;

-- Create custom data types for agents system
DO $$ 
BEGIN
    -- Agent status enum
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'agent_status') THEN
        CREATE TYPE agent_status AS ENUM (
            'idle',
            'running', 
            'completed',
            'failed',
            'cancelled',
            'timeout'
        );
    END IF;
    
    -- Pipeline optimization levels
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'optimization_level') THEN
        CREATE TYPE optimization_level AS ENUM (
            'standard',
            'high_performance', 
            'memory_optimized'
        );
    END IF;
    
    -- Data source types
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'datasource_type') THEN
        CREATE TYPE datasource_type AS ENUM (
            'mysql',
            'postgresql',
            'doris',
            'clickhouse',
            'mongodb',
            'oracle',
            'sqlserver',
            'sqlite',
            'excel',
            'csv',
            'json',
            'api'
        );
    END IF;
    
    -- Report status types
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'report_status') THEN
        CREATE TYPE report_status AS ENUM (
            'draft',
            'processing',
            'completed',
            'failed',
            'cancelled'
        );
    END IF;
    
    -- Analysis types
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'analysis_type') THEN
        CREATE TYPE analysis_type AS ENUM (
            'descriptive',
            'diagnostic', 
            'predictive',
            'prescriptive',
            'exploratory',
            'time_series',
            'anomaly_detection'
        );
    END IF;
END $$;

-- Create indexes optimization function
CREATE OR REPLACE FUNCTION create_common_indexes() RETURNS void AS $$
BEGIN
    -- These indexes will be created by Alembic migrations
    -- This function is for reference and can be called manually if needed
    RAISE NOTICE 'Database initialization completed. Indexes will be created by Alembic migrations.';
END;
$$ LANGUAGE plpgsql;

-- Create audit trigger function for tracking changes
CREATE OR REPLACE FUNCTION audit_trigger_function() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO audit.audit_log (
            table_name,
            operation,
            old_values,
            changed_at,
            changed_by
        ) VALUES (
            TG_TABLE_NAME,
            'DELETE',
            row_to_json(OLD),
            CURRENT_TIMESTAMP,
            current_user
        );
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit.audit_log (
            table_name,
            operation,
            old_values,
            new_values,
            changed_at,
            changed_by
        ) VALUES (
            TG_TABLE_NAME,
            'UPDATE',
            row_to_json(OLD),
            row_to_json(NEW),
            CURRENT_TIMESTAMP,
            current_user
        );
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO audit.audit_log (
            table_name,
            operation,
            new_values,
            changed_at,
            changed_by
        ) VALUES (
            TG_TABLE_NAME,
            'INSERT',
            row_to_json(NEW),
            CURRENT_TIMESTAMP,
            current_user
        );
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create audit log table
CREATE TABLE IF NOT EXISTS audit.audit_log (
    id SERIAL PRIMARY KEY,
    table_name TEXT NOT NULL,
    operation TEXT NOT NULL,
    old_values JSONB,
    new_values JSONB,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    changed_by TEXT DEFAULT current_user
);

-- Create index on audit log for performance
CREATE INDEX IF NOT EXISTS idx_audit_log_table_name ON audit.audit_log(table_name);
CREATE INDEX IF NOT EXISTS idx_audit_log_changed_at ON audit.audit_log(changed_at);

-- Performance monitoring views
CREATE OR REPLACE VIEW analytics.performance_summary AS
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats 
WHERE schemaname NOT IN ('information_schema', 'pg_catalog');

-- Database maintenance functions
CREATE OR REPLACE FUNCTION analytics.get_table_sizes() 
RETURNS TABLE(
    schema_name TEXT,
    table_name TEXT,
    size_pretty TEXT,
    size_bytes BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        schemaname::TEXT,
        tablename::TEXT,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))::TEXT,
        pg_total_relation_size(schemaname||'.'||tablename)::BIGINT
    FROM pg_tables 
    WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
END;
$$ LANGUAGE plpgsql;

-- Create function to clean up old audit logs
CREATE OR REPLACE FUNCTION audit.cleanup_old_audit_logs(days_to_keep INTEGER DEFAULT 30) 
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM audit.audit_log 
    WHERE changed_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * days_to_keep;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Set up periodic maintenance (this would typically be done via cron or pg_cron)
-- For now, we'll just create the functions

-- Database optimization settings
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET track_activity_query_size = 2048;

-- Connection and performance settings
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET work_mem = '4MB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';

-- WAL and checkpoint settings for reliability
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET random_page_cost = 1.1;

-- Logging settings
ALTER SYSTEM SET log_destination = 'stderr';
ALTER SYSTEM SET logging_collector = on;
ALTER SYSTEM SET log_directory = 'pg_log';
ALTER SYSTEM SET log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log';
ALTER SYSTEM SET log_min_duration_statement = 1000;
ALTER SYSTEM SET log_checkpoints = on;
ALTER SYSTEM SET log_connections = on;
ALTER SYSTEM SET log_disconnections = on;
ALTER SYSTEM SET log_lock_waits = on;

-- Reload configuration
SELECT pg_reload_conf();

-- Success message
DO $$ 
BEGIN 
    RAISE NOTICE 'AutoReportAI database initialization completed successfully!';
    RAISE NOTICE 'Extensions created: uuid-ossp, pg_trgm, pg_stat_statements, hstore';
    RAISE NOTICE 'Custom schemas created: agents, analytics, audit';
    RAISE NOTICE 'Custom types created for agents system';
    RAISE NOTICE 'Audit system configured';
    RAISE NOTICE 'Performance monitoring views created';
    RAISE NOTICE 'Database ready for Alembic migrations';
END $$;