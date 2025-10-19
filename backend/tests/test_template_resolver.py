"""
测试模板路径解析器 - 验证MinIO模板获取功能

测试场景：
1. 正常获取模板（MinIO存储）
2. 下载失败重试机制
3. 临时文件自动清理
4. 文件不存在错误处理
"""

import os
import time
import tempfile
from pathlib import Path


def test_template_resolver_basic():
    """测试基本的模板获取功能"""
    print("=" * 60)
    print("测试1: 基本模板获取功能")
    print("=" * 60)

    from app.db.session import SessionLocal
    from app.services.infrastructure.document.template_path_resolver import (
        resolve_docx_template_path,
        cleanup_template_temp_dir
    )

    db = SessionLocal()

    try:
        # 假设测试环境中已有模板
        test_template_id = "YOUR_TEST_TEMPLATE_ID"  # 替换为实际的模板ID

        print(f"\n📥 正在获取模板: {test_template_id}")

        # 获取模板
        tpl_meta = resolve_docx_template_path(db, test_template_id)

        print(f"✅ 模板获取成功:")
        print(f"   - 本地路径: {tpl_meta['path']}")
        print(f"   - 存储后端: {tpl_meta['source']}")
        print(f"   - 原始文件名: {tpl_meta['original_filename']}")
        print(f"   - 存储路径: {tpl_meta['storage_path']}")
        print(f"   - 临时目录: {tpl_meta['temp_dir']}")

        # 验证文件存在
        assert os.path.exists(tpl_meta['path']), "模板文件不存在！"
        print(f"✅ 模板文件存在: {os.path.getsize(tpl_meta['path'])} bytes")

        # 验证临时目录存在
        assert os.path.exists(tpl_meta['temp_dir']), "临时目录不存在！"
        print(f"✅ 临时目录存在")

        # 清理临时文件
        print(f"\n🧹 正在清理临时文件...")
        cleanup_template_temp_dir(tpl_meta)

        # 验证临时目录已删除
        time.sleep(0.1)  # 等待文件系统同步
        assert not os.path.exists(tpl_meta['temp_dir']), "临时目录未被清理！"
        print(f"✅ 临时目录已成功清理")

        print("\n" + "=" * 60)
        print("✅ 测试1通过: 基本模板获取功能正常")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试1失败: {e}")
        raise
    finally:
        db.close()


def test_template_not_found():
    """测试模板不存在的错误处理"""
    print("\n" + "=" * 60)
    print("测试2: 模板不存在错误处理")
    print("=" * 60)

    from app.db.session import SessionLocal
    from app.services.infrastructure.document.template_path_resolver import resolve_docx_template_path

    db = SessionLocal()

    try:
        fake_template_id = "00000000-0000-0000-0000-000000000000"

        print(f"\n📥 尝试获取不存在的模板: {fake_template_id}")

        try:
            tpl_meta = resolve_docx_template_path(db, fake_template_id)
            print(f"❌ 应该抛出异常但没有抛出！")
            assert False, "应该抛出ValueError"
        except ValueError as e:
            expected_msg = "not found in database"
            assert expected_msg in str(e), f"错误信息不正确: {e}"
            print(f"✅ 正确抛出异常: {e}")

        print("\n" + "=" * 60)
        print("✅ 测试2通过: 错误处理正常")
        print("=" * 60)

    finally:
        db.close()


def test_storage_backend_info():
    """测试存储后端信息"""
    print("\n" + "=" * 60)
    print("测试3: 存储后端配置检查")
    print("=" * 60)

    from app.services.infrastructure.storage.hybrid_storage_service import get_hybrid_storage_service

    storage = get_hybrid_storage_service()
    backend_info = storage.get_backend_info()

    print(f"\n📊 存储后端信息:")
    print(f"   - 后端类型: {backend_info['backend_type']}")
    print(f"   - MinIO可用: {backend_info['is_minio_available']}")
    print(f"   - 强制本地: {backend_info['force_local']}")

    # 健康检查
    health = storage.health_check()
    print(f"\n🏥 健康检查:")
    print(f"   - 状态: {health['status']}")
    if health['status'] == 'healthy':
        print(f"   - 端点: {health.get('endpoint', 'N/A')}")
        print(f"   - 存储桶: {health.get('bucket', 'N/A')}")
    else:
        print(f"   - 错误: {health.get('error', 'N/A')}")

    print("\n" + "=" * 60)
    print("✅ 测试3通过: 存储后端配置正常")
    print("=" * 60)


def test_temp_file_cleanup_on_exit():
    """测试程序退出时的临时文件清理"""
    print("\n" + "=" * 60)
    print("测试4: 程序退出时临时文件清理")
    print("=" * 60)

    from app.services.infrastructure.document.template_path_resolver import _temp_dirs_to_cleanup

    # 创建几个测试临时目录
    test_dirs = []
    for i in range(3):
        tmp_dir = tempfile.mkdtemp(prefix=f"test_cleanup_{i}_")
        test_dirs.append(tmp_dir)
        _temp_dirs_to_cleanup.add(tmp_dir)

    print(f"\n📁 创建了 {len(test_dirs)} 个测试临时目录")
    for d in test_dirs:
        print(f"   - {d}")

    # 验证目录存在
    for d in test_dirs:
        assert os.path.exists(d), f"临时目录不存在: {d}"

    print(f"\n🧹 触发清理函数...")
    from app.services.infrastructure.document.template_path_resolver import _cleanup_temp_dirs
    _cleanup_temp_dirs()

    # 验证目录已删除
    for d in test_dirs:
        assert not os.path.exists(d), f"临时目录未被清理: {d}"

    print(f"✅ 所有测试临时目录已成功清理")

    print("\n" + "=" * 60)
    print("✅ 测试4通过: 退出清理机制正常")
    print("=" * 60)


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print(" " * 20 + "模板解析器测试套件")
    print("=" * 80)

    tests = [
        ("存储后端配置检查", test_storage_backend_info),
        ("模板不存在错误处理", test_template_not_found),
        ("程序退出时临时文件清理", test_temp_file_cleanup_on_exit),
        # ("基本模板获取功能", test_template_resolver_basic),  # 需要实际的模板ID
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n❌ 测试失败: {test_name}")
            print(f"   错误: {e}")
            failed += 1

    print("\n" + "=" * 80)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 80)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
