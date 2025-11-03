#!/usr/bin/env python3
"""
检查后端是否正确连接到MinIO
在Docker容器中运行此脚本
"""

import os
import sys

print("="*80)
print("🔍 后端MinIO配置检查")
print("="*80)
print()

# 检查环境变量
print("1️⃣ 环境变量检查:")
print("-"*80)

env_vars = {
    "MINIO_ENDPOINT": os.getenv("MINIO_ENDPOINT"),
    "MINIO_ACCESS_KEY": os.getenv("MINIO_ACCESS_KEY"),
    "MINIO_SECRET_KEY": os.getenv("MINIO_SECRET_KEY"),
    "MINIO_BUCKET_NAME": os.getenv("MINIO_BUCKET_NAME"),
    "MINIO_SECURE": os.getenv("MINIO_SECURE"),
    "MINIO_ROOT_USER": os.getenv("MINIO_ROOT_USER"),
    "MINIO_ROOT_PASSWORD": os.getenv("MINIO_ROOT_PASSWORD"),
}

all_set = True
for key, value in env_vars.items():
    if value:
        # 隐藏敏感信息
        if "PASSWORD" in key or "SECRET" in key:
            display_value = value[:4] + "****" + value[-4:] if len(value) > 8 else "****"
        else:
            display_value = value
        print(f"   ✅ {key} = {display_value}")
    else:
        print(f"   ❌ {key} = 未设置")
        all_set = False

print()

if not all_set:
    print("⚠️  部分环境变量未设置！")
    print("   这会导致MinIO回退到本地存储")
else:
    print("✅ 所有环境变量已设置")

print()

# 测试MinIO连接
print("2️⃣ 测试MinIO连接:")
print("-"*80)

try:
    from app.services.infrastructure.storage.hybrid_storage_service import get_hybrid_storage_service

    storage = get_hybrid_storage_service()
    backend_info = storage.get_backend_info()

    print(f"   存储后端类型: {backend_info['backend_type']}")
    print(f"   MinIO可用: {backend_info['is_minio_available']}")
    print(f"   强制本地存储: {backend_info.get('force_local', False)}")
    print()

    if backend_info['backend_type'] == 'minio':
        print("   ✅ 正在使用MinIO存储")

        # 尝试列出文件
        print("\n   测试列出文件:")
        files = storage.list_files(file_type="reports", limit=5)
        if files:
            print(f"   ✅ 找到 {len(files)} 个文件:")
            for f in files[:3]:
                print(f"      - {f.get('file_path')} ({f.get('size', 0)} bytes)")
        else:
            print("   ⚠️  没有找到文件")

    else:
        print("   ❌ 回退到本地存储！")
        print("   原因: MinIO配置不完整或连接失败")

except Exception as e:
    print(f"   ❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

print()

# 检查最新的ReportHistory记录
print("3️⃣ 检查数据库中的ReportHistory记录:")
print("-"*80)

try:
    from app.db.session import get_db_session
    from app.models.report_history import ReportHistory

    with get_db_session() as db:
        # 获取最新的3条记录
        reports = db.query(ReportHistory).order_by(
            ReportHistory.id.desc()
        ).limit(3).all()

        if reports:
            print(f"   找到 {len(reports)} 条记录:")
            print()
            for i, report in enumerate(reports, 1):
                print(f"   [{i}] Report ID: {report.id}")
                print(f"       Task ID: {report.task_id}")
                print(f"       Status: {report.status}")
                print(f"       File Path: {report.file_path or '❌ 未设置'}")
                print(f"       File Size: {report.file_size or 0} bytes")

                if report.file_path:
                    print(f"       ✅ 有file_path")
                else:
                    print(f"       ❌ 没有file_path - 这会导致下载失败!")
                print()
        else:
            print("   ⚠️  没有找到ReportHistory记录")

except Exception as e:
    print(f"   ❌ 查询失败: {e}")
    import traceback
    traceback.print_exc()

print()
print("="*80)
print("✅ 检查完成")
print("="*80)
print()

print("📋 诊断建议:")
print("-"*80)
if not all_set:
    print("1. ⚠️  环境变量未完全设置")
    print("   -> 需要在服务器端.env文件中添加:")
    print("      MINIO_ENDPOINT=192.168.61.30:9000")
    print("      MINIO_ACCESS_KEY=minioadmin")
    print("      MINIO_SECRET_KEY=4Nfj02c9mYj6XXwHwRhgfaLn")
    print("      MINIO_SECURE=false")
    print()
    print("2. 🔄 完全重启服务（不是rebuild）:")
    print("   docker-compose down")
    print("   docker-compose up -d")
    print()
