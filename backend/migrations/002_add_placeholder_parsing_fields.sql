-- Migration: Add missing parsing-related fields to template_placeholders table
-- Date: 2025-10-18
-- Description: Adds content_hash, original_type, extracted_description, and parsing_metadata columns

BEGIN;

-- Add content_hash column with index for deduplication
ALTER TABLE template_placeholders
ADD COLUMN IF NOT EXISTS content_hash VARCHAR(16);

CREATE INDEX IF NOT EXISTS ix_template_placeholders_content_hash
ON template_placeholders(content_hash);

-- Add original_type column (stores the original parsed type)
ALTER TABLE template_placeholders
ADD COLUMN IF NOT EXISTS original_type VARCHAR(50);

-- Add extracted_description column (stores extracted description from parsing)
ALTER TABLE template_placeholders
ADD COLUMN IF NOT EXISTS extracted_description TEXT;

-- Add parsing_metadata column (stores metadata from parsing process)
ALTER TABLE template_placeholders
ADD COLUMN IF NOT EXISTS parsing_metadata JSONB DEFAULT '{}'::jsonb;

COMMIT;

-- Verify the changes
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'template_placeholders'
AND column_name IN ('content_hash', 'original_type', 'extracted_description', 'parsing_metadata')
ORDER BY column_name;
