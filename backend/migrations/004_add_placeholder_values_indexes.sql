-- Migration: Add indexes to placeholder_values table for ETL persistence optimization
-- Date: 2025-10-31
-- Description: Adds performance indexes for placeholder_values table to support ETL data persistence queries

BEGIN;

-- Index for batch_id queries (查询同一批次的所有占位符值)
CREATE INDEX IF NOT EXISTS idx_placeholder_values_batch
ON placeholder_values(execution_batch_id);

-- Index for cache key queries (缓存查询优化)
CREATE INDEX IF NOT EXISTS idx_placeholder_values_cache
ON placeholder_values(cache_key, expires_at)
WHERE cache_key IS NOT NULL;

-- Index for latest version queries (查询最新版本数据)
CREATE INDEX IF NOT EXISTS idx_placeholder_values_latest
ON placeholder_values(placeholder_id, data_source_id, is_latest_version, created_at DESC);

-- Index for placeholder and data source combination (常用联合查询)
CREATE INDEX IF NOT EXISTS idx_placeholder_values_placeholder_source
ON placeholder_values(placeholder_id, data_source_id);

-- Index for created_at for time-based queries (时间范围查询)
CREATE INDEX IF NOT EXISTS idx_placeholder_values_created
ON placeholder_values(created_at DESC);

COMMIT;

-- Verify the indexes were created
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'placeholder_values'
ORDER BY indexname;
