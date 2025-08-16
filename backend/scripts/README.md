# AutoReportAI Scripts

This directory contains essential scripts for AutoReportAI initialization and maintenance.

## Scripts Overview

### Database Initialization

#### `init-db.sql`
Basic PostgreSQL database setup script that:
- Creates required extensions (uuid-ossp, pg_trgm, hstore)
- Sets database timezone to UTC
- Creates custom data types (datasource_type, taskstatus, aiprovidertype)

**Usage:**
```bash
# Run as postgres user or database administrator
psql -d autoreport -f scripts/init-db.sql
```

#### `init_db.py`
Python script for application-level database initialization:
- Creates superuser account
- Sets up AI providers based on environment configuration
- Only creates providers if API keys are configured

**Usage:**
```bash
# From backend directory
python scripts/init_db.py
```

**Environment Variables:**
- `FIRST_SUPERUSER`: Username for admin user (default: admin)
- `FIRST_SUPERUSER_EMAIL`: Admin email (default: admin@autoreportai.com)
- `FIRST_SUPERUSER_PASSWORD`: Admin password (default: password)
- `OPENAI_API_KEY`: OpenAI API key (optional)
- `OPENAI_BASE_URL`: OpenAI API base URL (default: https://api.openai.com/v1)
- `AZURE_OPENAI_API_KEY`: Azure OpenAI API key (optional)
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI endpoint (optional)

### Health Check

#### `healthcheck_backend.sh`
Simple health check script for Docker containers and monitoring:
- Checks if backend API is responding on port 8000
- Returns exit code 0 for success, 1 for failure

**Usage:**
```bash
./scripts/healthcheck_backend.sh
```

### Configuration

#### `redis.conf`
Redis configuration optimized for AutoReportAI workloads:
- Memory management settings
- Persistence configuration
- Performance optimizations

## Setup Process

1. **Database Setup**: Run `init-db.sql` first to prepare PostgreSQL
2. **Run Migrations**: Use Alembic to create tables
   ```bash
   alembic upgrade head
   ```
3. **Initialize Data**: Run `init_db.py` to create admin user and AI providers
   ```bash
   python scripts/init_db.py
   ```

## Notes

- Scripts are designed to be idempotent (safe to run multiple times)
- No mock or test data is created during initialization
- AI providers are only created if valid API keys are provided
- All scripts include proper error handling and logging