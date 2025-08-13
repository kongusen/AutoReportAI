#!/usr/bin/env python3
"""
打印Settings配置值的脚本
用于排查配置问题和验证环境变量加载
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings

def print_settings():
    """打印所有Settings配置值"""
    print("=" * 80)
    print("🔧 AutoReportAI Settings 配置值")
    print("=" * 80)
    print()
    
    # 获取Settings类的所有属性
    settings_dict = {}
    for attr_name in dir(settings):
        # 跳过私有属性和方法
        if not attr_name.startswith('_') and not callable(getattr(settings, attr_name)):
            try:
                value = getattr(settings, attr_name)
                # 如果是敏感信息，部分隐藏
                if any(sensitive in attr_name.lower() for sensitive in ['password', 'key', 'secret', 'token']):
                    if isinstance(value, str) and len(value) > 8:
                        display_value = value[:4] + '*' * (len(value) - 8) + value[-4:]
                    else:
                        display_value = '*' * len(str(value)) if value else 'None'
                else:
                    display_value = value
                
                settings_dict[attr_name] = display_value
            except Exception as e:
                settings_dict[attr_name] = f"Error: {e}"
    
    # 按分类打印配置
    categories = {
        "基础配置": ["PROJECT_NAME", "API_V1_STR", "ENVIRONMENT", "DEBUG"],
        "数据库配置": ["db_user", "db_password", "db_host", "db_port", "db_name", "DATABASE_URL"],
        "Redis配置": ["REDIS_URL"],
        "邮件配置": ["SMTP_SERVER", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_USE_TLS", "SENDER_EMAIL", "SENDER_NAME"],
        "安全配置": ["SECRET_KEY", "ACCESS_TOKEN_EXPIRE_MINUTES", "ALGORITHM", "ENCRYPTION_KEY"],
        "Celery配置": ["CELERY_BROKER_URL", "CELERY_RESULT_BACKEND", "CELERY_TASK_SERIALIZER", "CELERY_RESULT_SERIALIZER"],
        "监控配置": ["ENABLE_MONITORING", "MONITORING_CHECK_INTERVAL"],
        "AI配置": ["DEFAULT_AI_MODEL", "AI_REQUEST_TIMEOUT", "AI_MAX_RETRIES"],
        "文件存储": ["UPLOAD_DIR", "REPORT_OUTPUT_DIR", "MAX_UPLOAD_SIZE", "LOCAL_STORAGE_PATH"],
        "MinIO配置": ["MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY", "MINIO_BUCKET_NAME"],
        "其他配置": []
    }
    
    # 将未分类的配置项添加到"其他配置"
    categorized_keys = set()
    for category_keys in categories.values():
        categorized_keys.update(category_keys)
    
    for key in settings_dict.keys():
        if key not in categorized_keys:
            categories["其他配置"].append(key)
    
    # 打印分类配置
    for category_name, keys in categories.items():
        if keys:
            print(f"📋 {category_name}")
            print("-" * 60)
            for key in keys:
                if key in settings_dict:
                    value = settings_dict[key]
                    print(f"  {key:<30} = {value}")
            print()
    
    # 打印环境变量信息
    print("🌍 环境变量信息")
    print("-" * 60)
    print(f"  当前工作目录: {os.getcwd()}")
    print(f"  脚本所在目录: {backend_dir}")
    
    # 检查.env文件
    env_file = backend_dir / '.env'
    if env_file.exists():
        print(f"  .env文件存在: {env_file}")
        print(f"  .env文件大小: {env_file.stat().st_size} 字节")
    else:
        print(f"  .env文件不存在: {env_file}")
    
    # 检查env.example文件
    env_example = backend_dir / 'env.example'
    if env_example.exists():
        print(f"  env.example文件存在: {env_example}")
    else:
        print(f"  env.example文件不存在: {env_example}")
    
    print()
    
    # 打印关键环境变量
    print("🔑 关键环境变量")
    print("-" * 60)
    key_env_vars = [
        "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB",
        "REDIS_URL", "SECRET_KEY", "ENCRYPTION_KEY", "ENVIRONMENT", "DEBUG"
    ]
    
    for env_var in key_env_vars:
        value = os.getenv(env_var)
        if value:
            # 隐藏敏感信息
            if any(sensitive in env_var.lower() for sensitive in ['password', 'key', 'secret']):
                if len(value) > 8:
                    display_value = value[:4] + '*' * (len(value) - 8) + value[-4:]
                else:
                    display_value = '*' * len(value)
            else:
                display_value = value
            print(f"  {env_var:<20} = {display_value}")
        else:
            print(f"  {env_var:<20} = 未设置")
    
    print()
    print("=" * 80)
    print("✅ 配置打印完成")
    print("=" * 80)

if __name__ == "__main__":
    print_settings()
