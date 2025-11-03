#!/usr/bin/env python3
"""
直接测试MinIO下载功能
"""

try:
    from minio import Minio
    from minio.error import S3Error
except ImportError:
    print("❌ 需要安装minio库: pip install minio")
    exit(1)

# MinIO配置 - 你的外部服务器
MINIO_ENDPOINT = "192.168.61.30:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "4Nfj02c9mYj6XXwHwRhgfaLn"
MINIO_BUCKET_NAME = "autoreport"
MINIO_SECURE = False

print("="*80)
print("🧪 MinIO下载测试工具")
print("="*80)
print(f"服务器: {MINIO_ENDPOINT}")
print(f"Bucket: {MINIO_BUCKET_NAME}")
print(f"使用HTTPS: {MINIO_SECURE}")
print()

# 初始化MinIO客户端
try:
    client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE
    )
    print("✅ MinIO客户端初始化成功")
except Exception as e:
    print(f"❌ MinIO客户端初始化失败: {e}")
    exit(1)

# 1. 检查bucket是否存在
print("\n" + "="*80)
print("1️⃣ 检查Bucket是否存在")
print("="*80)
try:
    exists = client.bucket_exists(MINIO_BUCKET_NAME)
    if exists:
        print(f"✅ Bucket '{MINIO_BUCKET_NAME}' 存在")
    else:
        print(f"❌ Bucket '{MINIO_BUCKET_NAME}' 不存在")
        print("   尝试创建bucket...")
        client.make_bucket(MINIO_BUCKET_NAME)
        print(f"✅ Bucket '{MINIO_BUCKET_NAME}' 创建成功")
except S3Error as e:
    print(f"❌ 检查Bucket失败: {e}")
    exit(1)

# 2. 列出reports目录下的文件
print("\n" + "="*80)
print("2️⃣ 列出reports目录下的文件")
print("="*80)
try:
    objects = client.list_objects(MINIO_BUCKET_NAME, prefix="reports/", recursive=True)

    files = []
    for obj in objects:
        files.append(obj)
        print(f"   📄 {obj.object_name}")
        print(f"      大小: {obj.size} bytes")
        print(f"      修改时间: {obj.last_modified}")
        print()

    if not files:
        print("⚠️  没有找到任何文件")
        print("\n让我们上传一个测试文件...")

        # 上传测试文件
        test_content = b"Hello MinIO! This is a test file."
        from io import BytesIO
        test_file = BytesIO(test_content)

        test_object_name = "reports/test/test_file.txt"
        client.put_object(
            MINIO_BUCKET_NAME,
            test_object_name,
            test_file,
            len(test_content),
            content_type="text/plain"
        )
        print(f"✅ 上传测试文件成功: {test_object_name}")
        files = [(test_object_name, len(test_content))]

    # 3. 测试下载第一个文件
    if files:
        print("\n" + "="*80)
        print("3️⃣ 测试下载文件")
        print("="*80)

        # 选择第一个文件进行测试
        test_object = files[0] if isinstance(files[0], tuple) else files[0].object_name
        object_name = test_object[0] if isinstance(test_object, tuple) else test_object

        print(f"测试下载: {object_name}")

        try:
            # 方法1: 直接下载
            response = client.get_object(MINIO_BUCKET_NAME, object_name)
            data = response.read()
            response.close()
            response.release_conn()

            print(f"✅ 下载成功!")
            print(f"   文件大小: {len(data)} bytes")

            # 检查文件内容
            if len(data) > 0:
                print(f"   文件头部(前50字节): {data[:50]}")

                # 检查是否是DOCX文件
                if data[:2] == b'PK':
                    print("   ✅ 这是有效的ZIP/DOCX文件格式")
                elif data[:5] == b'Hello':
                    print("   ✅ 这是我们的测试文件")
                else:
                    print(f"   ⚠️  文件格式: {data[:10]}")
            else:
                print("   ❌ 文件为空!")

        except S3Error as e:
            print(f"❌ 下载失败: {e}")
            print(f"   错误代码: {e.code}")
            print(f"   错误消息: {e.message}")

        # 方法2: 生成预签名URL
        print("\n" + "="*80)
        print("4️⃣ 生成预签名下载URL")
        print("="*80)

        try:
            from datetime import timedelta
            url = client.presigned_get_object(
                MINIO_BUCKET_NAME,
                object_name,
                expires=timedelta(hours=1)
            )
            print(f"✅ 预签名URL生成成功:")
            print(f"   {url}")
            print(f"\n   你可以在浏览器中直接访问这个URL来测试下载")

        except S3Error as e:
            print(f"❌ 生成预签名URL失败: {e}")

except S3Error as e:
    print(f"❌ 操作失败: {e}")
    exit(1)

# 5. 测试从后端日志中看到的实际文件路径
print("\n" + "="*80)
print("5️⃣ 测试你的实际报告文件")
print("="*80)

# 从你的日志中看到的路径
actual_report_path = "reports/aa18bc60-06e0-4305-96b5-3a205a91d94e/团队监管/report_20251103_082601.docx"

print(f"测试路径: {actual_report_path}")

try:
    # 检查文件是否存在
    stat = client.stat_object(MINIO_BUCKET_NAME, actual_report_path)
    print(f"✅ 文件存在!")
    print(f"   大小: {stat.size} bytes")
    print(f"   Content-Type: {stat.content_type}")
    print(f"   最后修改: {stat.last_modified}")

    # 尝试下载
    print("\n   正在下载...")
    response = client.get_object(MINIO_BUCKET_NAME, actual_report_path)
    data = response.read()
    response.close()
    response.release_conn()

    print(f"✅ 下载成功! 文件大小: {len(data)} bytes")

    # 检查文件格式
    if data[:2] == b'PK':
        print("   ✅ 有效的DOCX文件格式!")

        # 保存到本地测试
        local_file = "/tmp/test_download.docx"
        with open(local_file, 'wb') as f:
            f.write(data)
        print(f"   ✅ 文件已保存到: {local_file}")
        print(f"   请尝试打开这个文件验证内容是否正确")
    else:
        print(f"   ⚠️  文件头部不是标准DOCX格式: {data[:10]}")

except S3Error as e:
    if e.code == 'NoSuchKey':
        print(f"❌ 文件不存在: {actual_report_path}")
        print("\n   让我列出该目录下的所有文件:")

        # 尝试列出父目录
        parent_prefix = "/".join(actual_report_path.split("/")[:-1]) + "/"
        print(f"   搜索目录: {parent_prefix}")

        try:
            objects = client.list_objects(MINIO_BUCKET_NAME, prefix=parent_prefix, recursive=True)
            found = False
            for obj in objects:
                found = True
                print(f"      📄 {obj.object_name} ({obj.size} bytes)")

            if not found:
                print("      ⚠️  目录为空")
        except Exception as list_error:
            print(f"      ❌ 列出目录失败: {list_error}")
    else:
        print(f"❌ 操作失败: {e}")
        print(f"   错误代码: {e.code}")
        print(f"   错误消息: {e.message}")

print("\n" + "="*80)
print("✅ 测试完成!")
print("="*80)
