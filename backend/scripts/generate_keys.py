#!/usr/bin/env python3
"""
密钥生成工具
用于生成安全的 SECRET_KEY 和 ENCRYPTION_KEY
"""

import secrets
import string
from cryptography.fernet import Fernet


def generate_secret_key(length=64):
    """生成随机的 SECRET_KEY"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_encryption_key():
    """生成 Fernet 加密密钥"""
    return Fernet.generate_key().decode()


def main():
    print("🔐 AutoReportAI 密钥生成器")
    print("=" * 50)
    
    print("📝 SECRET_KEY (用于会话签名):")
    secret_key = generate_secret_key()
    print(f"SECRET_KEY={secret_key}")
    
    print("\n🔒 ENCRYPTION_KEY (用于数据加密):")
    encryption_key = generate_encryption_key()
    print(f"ENCRYPTION_KEY={encryption_key}")
    
    print("\n" + "=" * 50)
    print("💡 使用方法:")
    print("1. 复制上述密钥到你的 .env 文件中")
    print("2. 确保生产环境使用不同的密钥")
    print("3. 备份你的加密密钥 - 数据恢复需要它!")
    
    # 验证生成的密钥
    try:
        f = Fernet(encryption_key.encode())
        test_data = b"test encryption"
        encrypted = f.encrypt(test_data)
        decrypted = f.decrypt(encrypted)
        assert decrypted == test_data
        print("\n✅ 加密密钥验证成功")
    except Exception as e:
        print(f"\n❌ 加密密钥验证失败: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())