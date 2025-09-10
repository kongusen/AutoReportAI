-- 添加 placeholder_values 表缺失的字段
-- 这些字段在模型中定义但数据库中缺失

BEGIN;

-- 添加 source 字段
ALTER TABLE placeholder_values 
ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'agent';

-- 添加 confidence_score 字段  
ALTER TABLE placeholder_values 
ADD COLUMN IF NOT EXISTS confidence_score FLOAT DEFAULT 0.0;

-- 添加 analysis_metadata 字段
ALTER TABLE placeholder_values 
ADD COLUMN IF NOT EXISTS analysis_metadata JSON DEFAULT '{}';

-- 更新注释
COMMENT ON COLUMN placeholder_values.source IS '数据来源：agent, rule, cache';
COMMENT ON COLUMN placeholder_values.confidence_score IS '置信度分数 0-1';
COMMENT ON COLUMN placeholder_values.analysis_metadata IS '分析元数据';

COMMIT;