#!/usr/bin/env python3
"""
AutoReportAI Minio集成测试脚本
测试Docker环境中的Minio对象存储功能
"""

import os
import sys
from datetime import datetime

def test_minio_connection():
    """测试MinIO连接"""
    print("\n🔗 测试MinIO连接...")
    
    try:
        # 测试连接
        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_USE_SSL
        )
        
        # 检查连接
        buckets = client.list_buckets()
        bucket_names = [bucket.name for bucket in buckets]
        
        print(f"✅ MinIO连接成功")
        print(f"   📦 可用存储桶: {bucket_names}")
        
        # 检查必要的存储桶
        required_buckets = ['reports', 'charts', 'templates']
        missing_buckets = [bucket for bucket in required_buckets if bucket not in bucket_names]
        
        if missing_buckets:
            print(f"⚠️  缺少必要存储桶: {missing_buckets}")
            print("   正在创建...")
            
            for bucket in missing_buckets:
                try:
                    client.make_bucket(bucket)
                    print(f"   ✅ 创建存储桶: {bucket}")
                except Exception as e:
                    print(f"   ❌ 创建存储桶失败 {bucket}: {e}")
        else:
            print("✅ 所有必要存储桶已存在")
        
        assert True, "MinIO连接应该成功"
        
    except Exception as e:
        print(f"❌ MinIO连接失败: {e}")
        assert False, f"MinIO连接应该成功: {e}"

def test_dev_minio_connection():
    """测试开发环境MinIO连接"""
    print("\n🔗 测试开发环境MinIO连接...")
    
    try:
        # 使用开发环境配置
        dev_client = Minio(
            "localhost:9000",
            access_key="minioadmin",
            secret_key="minioadmin",
            secure=False
        )
        
        # 检查连接
        buckets = dev_client.list_buckets()
        bucket_names = [bucket.name for bucket in buckets]
        
        print(f"✅ 开发环境MinIO连接成功")
        print(f"   📦 可用存储桶: {bucket_names}")
        
        assert True, "开发环境MinIO连接应该成功"
        
    except Exception as e:
        print(f"❌ 开发环境MinIO连接失败: {e}")
        print("   这可能是正常的，如果开发环境MinIO未启动")
        assert False, f"开发环境MinIO连接应该成功: {e}"

def test_environment_variables():
    """测试环境变量配置"""
    print("\n🔧 测试环境变量配置...")
    
    try:
        # 检查必要的环境变量
        required_vars = [
            'MINIO_ENDPOINT',
            'MINIO_ACCESS_KEY', 
            'MINIO_SECRET_KEY',
            'MINIO_USE_SSL'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ 缺少环境变量: {missing_vars}")
            assert False, f"应该设置所有必要的环境变量: {missing_vars}"
        else:
            print("✅ 所有必要的环境变量已设置")
            print(f"   📍 端点: {os.getenv('MINIO_ENDPOINT')}")
            print(f"   🔑 访问密钥: {os.getenv('MINIO_ACCESS_KEY')[:8]}...")
            print(f"   🔒 使用SSL: {os.getenv('MINIO_USE_SSL')}")
            assert True, "环境变量配置应该完整"
        
    except Exception as e:
        print(f"❌ 环境变量检查失败: {e}")
        assert False, f"环境变量检查应该成功: {e}"

if __name__ == "__main__":
    print("🚀 AutoReportAI Minio集成测试")
    print("=" * 50)
    
    # 测试环境变量
    env_ok = test_environment_variables()
    
    print("\n📡 测试Minio连接:")
    print("-" * 30)
    
    # 测试默认Minio
    default_ok = test_minio_connection()
    
    print("\n🛠️ 测试开发模式Minio:")
    print("-" * 30)
    
    # 测试开发模式Minio
    dev_ok = test_dev_minio_connection()
    
    print("\n📊 测试结果总结:")
    print("-" * 30)
    print(f"环境变量配置: {'✅ 正常' if env_ok else '⚠️ 部分缺失'}")
    print(f"默认Minio服务: {'✅ 正常' if default_ok else '❌ 失败'}")
    print(f"开发模式Minio: {'✅ 正常' if dev_ok else '❌ 失败'}")
    
    if default_ok and dev_ok:
        print("\n🎉 所有Minio服务测试通过!")
        print("💡 可以通过以下地址访问:")
        print("   - 默认Minio控制台: http://localhost:9001")
        print("   - 开发Minio控制台: http://localhost:9003")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败，请检查Minio服务状态")
        sys.exit(1)