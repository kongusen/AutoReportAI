#!/usr/bin/env python3
"""
Essential startup check for AutoReportAI
Verifies database connectivity and basic system health
"""

import os
import sys
import logging
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Also add current working directory and /app for Docker environment
import os
current_dir = os.getcwd()
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if '/app' not in sys.path:
    sys.path.insert(0, '/app')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_database():
    """Check database connectivity"""
    try:
        from app.db.session import SessionLocal
        from sqlalchemy import text
        
        db = SessionLocal()
        result = db.execute(text("SELECT 1"))
        db.close()
        logger.info("✅ Database connection successful")
        return True
    except ImportError as e:
        logger.error(f"❌ Database module import failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def check_redis():
    """Check Redis connectivity"""
    try:
        import redis
        from app.core.config import settings
        from urllib.parse import urlparse
        
        parsed = urlparse(settings.REDIS_URL)
        r = redis.Redis(
            host=parsed.hostname,
            port=parsed.port or 6379,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        r.ping()
        logger.info("✅ Redis connection successful")
        return True
    except ImportError as e:
        logger.error(f"❌ Redis module import failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        return False

def check_config():
    """Check essential configuration"""
    try:
        from app.core.config import settings
        
        # Check essential settings
        essential_checks = [
            (settings.DATABASE_URL, "DATABASE_URL"),
            (settings.REDIS_URL, "REDIS_URL"),
            (settings.SECRET_KEY, "SECRET_KEY"),
            (settings.ENCRYPTION_KEY, "ENCRYPTION_KEY"),
        ]
        
        for value, name in essential_checks:
            if not value or value in ["", "your-secret-key"]:
                logger.error(f"❌ {name} not configured properly")
                return False
        
        # 特别验证 ENCRYPTION_KEY 格式
        try:
            from cryptography.fernet import Fernet
            Fernet(settings.ENCRYPTION_KEY.encode())
            logger.info("✅ ENCRYPTION_KEY format validated")
        except Exception as e:
            logger.error(f"❌ ENCRYPTION_KEY format invalid: {e}")
            logger.info("💡 Generate new key: python3 scripts/generate_keys.py")
            return False
        
        logger.info("✅ Essential configuration validated")
        return True
    except ImportError as e:
        logger.error(f"❌ Configuration import failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Configuration check failed: {e}")
        return False

def main():
    """Main startup check function"""
    logger.info("🚀 Starting comprehensive startup check...")
    
    checks = [
        ("Configuration", check_config),
        ("Database", check_database),
        ("Redis", check_redis),
    ]
    
    success = True
    for check_name, check_func in checks:
        logger.info(f"Checking {check_name}...")
        if not check_func():
            success = False
    
    if success:
        logger.info("🎉 All startup checks passed!")
        return 0
    else:
        logger.error("❌ Some startup checks failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())