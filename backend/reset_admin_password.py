#!/usr/bin/env python3
"""
管理员密码重置脚本
用于解决 bcrypt 兼容性问题后重置管理员密码
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy.exc import SQLAlchemyError

def reset_admin_password():
    """重置管理员密码"""
    db = SessionLocal()

    try:
        # 查找管理员用户
        admin_user = db.query(User).filter(
            User.email == 'admin@example.com'
        ).first()

        if not admin_user:
            print("❌ 未找到管理员用户 (admin@example.com)")
            print("正在创建管理员用户...")

            # 创建新的管理员用户
            admin_user = User(
                email='admin@example.com',
                username='admin',
                full_name='System Administrator',
                hashed_password=get_password_hash('password'),
                is_active=True,
                is_superuser=True
            )
            db.add(admin_user)
            db.commit()
            print("✅ 管理员用户创建成功")
        else:
            print(f"✅ 找到管理员用户: {admin_user.email}")

            # 重置密码
            new_password_hash = get_password_hash('password')
            admin_user.hashed_password = new_password_hash
            db.commit()
            print("✅ 管理员密码重置成功")

        print(f"管理员登录信息:")
        print(f"  邮箱: admin@example.com")
        print(f"  密码: password")

        # 验证密码
        from app.core.security import verify_password
        if verify_password('password', admin_user.hashed_password):
            print("✅ 密码验证成功")
        else:
            print("❌ 密码验证失败")

    except SQLAlchemyError as e:
        print(f"❌ 数据库错误: {e}")
        db.rollback()
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🔧 正在重置管理员密码...")
    reset_admin_password()
    print("🎉 完成！")