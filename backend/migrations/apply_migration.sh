#!/bin/bash
# Database migration script using psql
# Usage: ./apply_migration.sh <migration_file.sql>

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if migration file is provided
if [ $# -eq 0 ]; then
    echo -e "${RED}❌ Error: No migration file specified${NC}"
    echo "Usage: $0 <migration_file.sql>"
    echo ""
    echo "Available migrations:"
    ls -1 "${SCRIPT_DIR}"/*.sql 2>/dev/null || echo "  No migration files found"
    exit 1
fi

MIGRATION_FILE="$1"
MIGRATION_PATH="${SCRIPT_DIR}/${MIGRATION_FILE}"

# Check if migration file exists
if [ ! -f "${MIGRATION_PATH}" ]; then
    echo -e "${RED}❌ Error: Migration file not found: ${MIGRATION_PATH}${NC}"
    exit 1
fi

echo -e "${YELLOW}📦 Applying migration: ${MIGRATION_FILE}${NC}"
echo ""

# Load database configuration from .env file
ENV_FILE="${SCRIPT_DIR}/../.env"
if [ -f "${ENV_FILE}" ]; then
    # Export DATABASE_URL if it exists in .env
    export $(grep -v '^#' "${ENV_FILE}" | grep DATABASE_URL | xargs)
fi

# If DATABASE_URL is not set, try to construct it from individual variables
if [ -z "${DATABASE_URL}" ]; then
    if [ -f "${ENV_FILE}" ]; then
        export $(grep -v '^#' "${ENV_FILE}" | grep -E 'POSTGRES_|DB_' | xargs)
    fi

    # Set defaults
    DB_HOST="${POSTGRES_HOST:-${DB_HOST:-localhost}}"
    DB_PORT="${POSTGRES_PORT:-${DB_PORT:-5432}}"
    DB_USER="${POSTGRES_USER:-${DB_USER:-postgres}}"
    DB_PASSWORD="${POSTGRES_PASSWORD:-${DB_PASSWORD}}"
    DB_NAME="${POSTGRES_DB:-${DB_NAME:-autoreport}}"

    if [ -n "${DB_PASSWORD}" ]; then
        DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
    else
        DATABASE_URL="postgresql://${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
    fi
fi

echo -e "${YELLOW}Database: ${DATABASE_URL%%:*}://****@****${NC}"
echo ""

# Apply the migration using psql
if psql "${DATABASE_URL}" -f "${MIGRATION_PATH}"; then
    echo ""
    echo -e "${GREEN}✅ Migration ${MIGRATION_FILE} applied successfully!${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}❌ Error applying migration${NC}"
    exit 1
fi
