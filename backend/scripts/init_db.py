#!/usr/bin/env python3
"""
Database initialization script for AutoReportAI
This script will create all necessary database tables and initial data
"""

import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.models.ai_provider import AIProvider
from app.models.data_source import DataSource
from app.models.enhanced_data_source import EnhancedDataSource
from app.models.etl_job import ETLJob
from app.models.report_history import ReportHistory
from app.models.task import Task
from app.models.template import Template
from app.models.user import User


def init_database():
    """Initialize database with all tables and initial data"""

    # Create database engine
    engine = create_engine(settings.DATABASE_URL)

    # Create all tables
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully!")

    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Check if admin user exists
        admin_user = db.query(User).filter(User.email == "admin@example.com").first()
        if not admin_user:
            # Create admin user
            admin_user = User(
                email="admin@example.com",
                username="admin",
                hashed_password=get_password_hash("admin123"),
                full_name="Administrator",
                is_active=True,
                is_superuser=True,
            )
            db.add(admin_user)
            db.commit()
            print("Admin user created: admin@example.com / admin123")

        # Create sample data source
        sample_source = (
            db.query(DataSource).filter(DataSource.name == "Sample CSV").first()
        )
        if not sample_source:
            sample_source = DataSource(
                name="Sample CSV", file_path="./sample_data.csv", source_type="csv"
            )
            db.add(sample_source)
            db.commit()
            print("Sample data source created")

        db.close()
        print("Database initialization completed successfully!")

    except Exception as e:
        print(f"Error during database initialization: {e}")
        db.rollback()
        db.close()
        raise


if __name__ == "__main__":
    init_database()
