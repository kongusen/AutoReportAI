#!/usr/bin/env python3
"""
bcrypt 兼容性修复脚本
解决 passlib 与新版本 bcrypt 的兼容性问题
"""

def fix_bcrypt_compatibility():
    """修复 bcrypt 兼容性问题"""
    try:
        import bcrypt

        # 检查 bcrypt 版本
        if hasattr(bcrypt, '__about__'):
            print(f"✅ bcrypt 版本正常: {bcrypt.__about__.__version__}")
        else:
            print("⚠️ bcrypt 缺少 __about__ 属性，尝试修复...")

            # 为旧版本 bcrypt 添加 __about__ 属性
            class About:
                __version__ = getattr(bcrypt, '__version__', '4.0.0')

            bcrypt.__about__ = About()
            print(f"✅ bcrypt 兼容性修复完成，版本: {bcrypt.__about__.__version__}")

        # 测试 passlib 与 bcrypt 的兼容性
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        # 测试密码哈希和验证
        test_password = "test123"
        hash_result = pwd_context.hash(test_password)
        verify_result = pwd_context.verify(test_password, hash_result)

        if verify_result:
            print("✅ passlib + bcrypt 兼容性测试成功")
        else:
            print("❌ passlib + bcrypt 兼容性测试失败")

        return True

    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return False

if __name__ == "__main__":
    print("🔧 正在修复 bcrypt 兼容性...")
    success = fix_bcrypt_compatibility()
    if success:
        print("🎉 修复完成！")
    else:
        print("❌ 修复失败，请检查依赖安装")