# Database Migrations

This directory contains database migration scripts for AutoReportAI.

## Fixed Issues

### 1. Data Source Deletion Error
**Error**: `column column_schemas.comment does not exist`

**Cause**: The `comment` column was defined in the model (`backend/app/models/table_schema.py:338`) but was missing from the actual database table.

**Fix**: Migration `001_add_comment_column_to_column_schemas.sql` adds the missing column.

### 2. Task Deletion Error
**Error**: `null value in column "task_id" of relation "task_executions" violates not-null constraint`

**Cause**: The `executions` relationship in the `Task` model was missing the `cascade="all, delete-orphan"` parameter, causing SQLAlchemy to set `task_id=None` instead of deleting related records.

**Fix**: Updated `backend/app/models/task.py:91` to include cascade deletion:
```python
executions = relationship("TaskExecution", back_populates="task", cascade="all, delete-orphan")
```

### 3. Template Placeholder Parsing Fields Missing
**Error**: `column template_placeholders.content_hash does not exist`

**Cause**: The `TemplatePlaceholder` model (`backend/app/models/template_placeholder.py:50-56`) defines parsing-related fields (`content_hash`, `original_type`, `extracted_description`, `parsing_metadata`) that were missing from the actual database table.

**Fix**:
- Migration `002_add_placeholder_parsing_fields.sql` adds the missing columns
- Updated `backend/scripts/init-db.sql` to include these fields in the initial schema

### 4. Report History File Size Missing
**Error**: `column report_history.file_size does not exist`

**Cause**: The `ReportHistory` model (`backend/app/models/report_history.py`) defines a `file_size` column that was missing from the actual database table and initialization script.

**Fix**:
- Migration `003_add_file_size_to_report_history.sql` adds the missing column
- Updated `backend/scripts/init-db.sql` to include the column with a default value

## How to Apply Migrations

### Option 1: Using Docker (Recommended)
```bash
# Start the database container
cd autorport-dev
docker-compose up -d db

# Apply the migration
docker exec -i autoreport-db-dev psql -U postgres -d autoreport < backend/migrations/001_add_comment_column_to_column_schemas.sql
```

### Option 2: Using Python Script
```bash
cd backend
python migrations/apply_migration.py 001_add_comment_column_to_column_schemas.sql
```

### Option 3: Direct psql Connection
```bash
psql -h localhost -U postgres -d autoreport -f backend/migrations/001_add_comment_column_to_column_schemas.sql
```

## Verify the Fixes

After applying the migrations and restarting your services:

1. **Test Data Source Deletion**:
   - Try deleting a data source from the UI
   - Should now succeed without errors

2. **Test Task Deletion**:
   - Try deleting a task from the UI
   - Should now succeed and properly delete all related task_executions records

## Migration Files

- `001_add_comment_column_to_column_schemas.sql` - Adds missing comment column to column_schemas
- `002_add_placeholder_parsing_fields.sql` - Adds missing parsing fields to template_placeholders
- `003_add_file_size_to_report_history.sql` - Adds missing file_size column to report_history
- `apply_migration.py` - Python helper script to apply migrations

## Quick Apply All Migrations

```bash
# Apply all migrations in order
cd autorport-dev
docker exec -i autoreport-db-dev psql -U postgres -d autoreport < backend/migrations/001_add_comment_column_to_column_schemas.sql
docker exec -i autoreport-db-dev psql -U postgres -d autoreport < backend/migrations/002_add_placeholder_parsing_fields.sql
```
