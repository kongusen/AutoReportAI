-- Migration: Add missing file_size column to report_history table
-- Date: 2025-10-23
-- Description: Ensures report_history records store the generated file size in bytes

BEGIN;

ALTER TABLE report_history
ADD COLUMN IF NOT EXISTS file_size INTEGER DEFAULT 0;

COMMIT;

-- Verify the column exists with the expected default
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'report_history'
  AND column_name = 'file_size';
