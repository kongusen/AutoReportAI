#!/usr/bin/env python3
"""
AutoReportAI Minio集成测试脚本
测试Docker环境中的Minio对象存储功能
"""

import os
import sys
from datetime import datetime

def test_minio_connection():
    """测试Minio连接"""
    try:
        from minio import Minio
        from minio.error import S3Error
        
        # 默认Minio配置
        client = Minio(
            "localhost:9000",
            access_key="minioadmin",
            secret_key="minioadmin123",
            secure=False
        )
        
        # 测试连接
        if client.bucket_exists("test"):
            print("✅ 默认Minio连接成功")
        else:
            # 创建测试bucket
            client.make_bucket("test")
            print("✅ 默认Minio连接成功 - 创建测试bucket")
        
        # 测试文件上传
        import io
        test_content = f"AutoReportAI测试文件 - {datetime.now()}"
        data = io.BytesIO(test_content.encode())
        client.put_object(
            "test",
            "test-file.txt",
            data=data,
            length=len(test_content.encode()),
            content_type="text/plain"
        )
        print("✅ 文件上传测试成功")
        
        # 测试文件下载
        response = client.get_object("test", "test-file.txt")
        content = response.read().decode()
        if "AutoReportAI测试文件" in content:
            print("✅ 文件下载测试成功")
        else:
            print("❌ 文件内容不匹配")
            
        return True
        
    except ImportError:
        print("❌ minio库未安装: pip install minio")
        return False
    except Exception as e:
        print(f"❌ Minio连接失败: {e}")
        return False

def test_dev_minio_connection():
    """测试开发模式Minio连接"""
    try:
        from minio import Minio
        from minio.error import S3Error
        
        # 开发模式Minio配置
        client = Minio(
            "localhost:9002",
            access_key="devuser",
            secret_key="devpassword123",
            secure=False
        )
        
        # 测试连接
        if client.bucket_exists("dev-test"):
            print("✅ 开发模式Minio连接成功")
        else:
            # 创建测试bucket
            client.make_bucket("dev-test")
            print("✅ 开发模式Minio连接成功 - 创建开发测试bucket")
        
        # 测试文件上传
        import io
        test_content = f"AutoReportAI开发模式测试 - {datetime.now()}"
        data = io.BytesIO(test_content.encode())
        client.put_object(
            "dev-test",
            "dev-test-file.txt",
            data=data,
            length=len(test_content.encode()),
            content_type="text/plain"
        )
        print("✅ 开发模式文件上传测试成功")
        
        return True
        
    except ImportError:
        print("❌ minio库未安装")
        return False
    except Exception as e:
        print(f"❌ 开发模式Minio连接失败: {e}")
        return False

def test_environment_variables():
    """测试环境变量配置"""
    print("\n🔍 检查环境变量配置:")
    
    env_vars = {
        "MINIO_ENDPOINT": "minio:9000",
        "MINIO_ACCESS_KEY": "minioadmin", 
        "MINIO_SECRET_KEY": "minioadmin123",
        "MINIO_BUCKET_NAME": "autoreport",
        "FILE_STORAGE_BACKEND": "minio"
    }
    
    all_set = True
    for var, expected in env_vars.items():
        value = os.getenv(var, "未设置")
        if value == "未设置":
            print(f"⚠️  {var}: {value}")
            all_set = False
        else:
            print(f"✅ {var}: {value}")
    
    return all_set

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