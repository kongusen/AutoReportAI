-- Migration: Add missing 'comment' column to column_schemas table
-- Date: 2025-10-11
-- Description: Fix missing comment column that exists in the model but not in the database

-- Add the comment column to column_schemas table
-- Note: The column already exists in the model at backend/app/models/table_schema.py:338
ALTER TABLE column_schemas ADD COLUMN IF NOT EXISTS comment TEXT;

-- Add a comment to document the column
COMMENT ON COLUMN column_schemas.comment IS 'Database field comment/description';
