-- Migration: Add source, confidence_score, and analysis_metadata fields to placeholder_values
-- Description: Adds fields required for tracking data source and analysis metadata in placeholder values
-- Date: 2025-10-31

-- Add source field (data source: agent, rule, cache, run_report, etc.)
ALTER TABLE placeholder_values
ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'agent';

-- Add confidence_score field (confidence score of the analysis)
ALTER TABLE placeholder_values
ADD COLUMN IF NOT EXISTS confidence_score REAL DEFAULT 0.0;

-- Add analysis_metadata field (stores analysis-related metadata as JSON)
ALTER TABLE placeholder_values
ADD COLUMN IF NOT EXISTS analysis_metadata JSONB DEFAULT '{}'::jsonb;

-- Add index for source field for better query performance
CREATE INDEX IF NOT EXISTS idx_placeholder_values_source
ON placeholder_values(source);

-- Add comment for documentation
COMMENT ON COLUMN placeholder_values.source IS '数据来源：agent, rule, cache, run_report, run_report_chart';
COMMENT ON COLUMN placeholder_values.confidence_score IS '置信度分数 (0.0-1.0)';
COMMENT ON COLUMN placeholder_values.analysis_metadata IS '分析元数据，包含 content_type, placeholder_type, formatting_applied 等信息';
