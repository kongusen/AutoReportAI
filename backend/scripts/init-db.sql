-- AutoReportAI Database Initialization Script
-- Essential database setup for AutoReportAI system

-- Create required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search optimization
CREATE EXTENSION IF NOT EXISTS "hstore";   -- For key-value storage

-- Set database timezone to UTC
ALTER DATABASE autoreport SET timezone TO 'UTC';

-- Create custom data types for the application
DO $$ 
BEGIN
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
    
    -- Task status types
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'taskstatus') THEN
        CREATE TYPE taskstatus AS ENUM (
            'pending',
            'processing', 
            'generating',
            'completed',
            'failed',
            'cancelled'
        );
    END IF;
    
    -- AI Provider types
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'aiprovidertype') THEN
        CREATE TYPE aiprovidertype AS ENUM (
            'openai',
            'azure_openai',
            'anthropic',
            'google',
            'mock'
        );
    END IF;
END $$;

-- Success message
DO $$ 
BEGIN 
    RAISE NOTICE 'AutoReportAI database initialization completed successfully!';
    RAISE NOTICE 'Extensions created: uuid-ossp, pg_trgm, hstore';
    RAISE NOTICE 'Custom types created: datasource_type, taskstatus, aiprovidertype';
    RAISE NOTICE 'Database ready for Alembic migrations and application use';
END $$;