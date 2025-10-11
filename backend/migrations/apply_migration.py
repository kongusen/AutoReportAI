#!/usr/bin/env python3
"""
Database migration script to apply SQL migrations
Usage: python apply_migration.py <migration_file.sql>
"""

import sys
import os
from pathlib import Path

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.session import get_db_session


def apply_migration(migration_file: str):
    """Apply a SQL migration file"""
    migration_path = Path(__file__).parent / migration_file

    if not migration_path.exists():
        print(f"Error: Migration file not found: {migration_path}")
        sys.exit(1)

    print(f"Applying migration: {migration_file}")

    # Read the migration SQL
    with open(migration_path, 'r') as f:
        sql = f.read()

    # Apply the migration
    try:
        with get_db_session() as db:
            # Split by semicolon and execute each statement
            statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]

            for statement in statements:
                if statement:
                    print(f"\nExecuting:\n{statement[:100]}...")
                    db.execute(text(statement))

            db.commit()
            print(f"\n✅ Migration {migration_file} applied successfully!")

    except Exception as e:
        print(f"\n❌ Error applying migration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python apply_migration.py <migration_file.sql>")
        print("\nAvailable migrations:")
        migrations_dir = Path(__file__).parent
        for sql_file in sorted(migrations_dir.glob("*.sql")):
            print(f"  - {sql_file.name}")
        sys.exit(1)

    migration_file = sys.argv[1]
    apply_migration(migration_file)
