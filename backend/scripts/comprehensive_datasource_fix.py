#!/usr/bin/env python3
"""
综合数据源问题诊断和修复脚本

解决以下问题:
1. ENCRYPTION_KEY 不一致导致的密码解密失败
2. 数据源连接配置问题
3. Doris用户权限问题诊断

使用方法:
    python scripts/comprehensive_datasource_fix.py --diagnose     # 诊断问题
    python scripts/comprehensive_datasource_fix.py --fix          # 修复密码
    python scripts/comprehensive_datasource_fix.py --test         # 测试连接
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import json

# 添加项目路径
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.data_source import DataSource
from cryptography.fernet import Fernet, InvalidToken
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def diagnose_environment():
    """诊断环境配置"""
    print("\n" + "=" * 60)
    print("环境诊断")
    print("=" * 60)

    # 检查加密密钥
    current_key = settings.ENCRYPTION_KEY
    default_key = "DO2E-DOAveBMXpu1xMTl9fRjehX_1pbDnVZkuFRDA14="
    docker_env_key = "ixd0gr5Ntuy8PSOOJsFl4DY1R2fFgFVc34_vu4Yzr1c="

    print(f"\n当前 ENCRYPTION_KEY: {current_key[:20]}...{current_key[-10:]}")
    print(f"默认密钥 (config.py):  {default_key[:20]}...{default_key[-10:]}")
    print(f"Docker .env 密钥:      {docker_env_key[:20]}...{docker_env_key[-10:]}")

    if current_key == default_key:
        print("⚠️  使用默认密钥 (可能是本地开发模式)")
    elif current_key == docker_env_key:
        print("✅ 使用 Docker .env 中的密钥")
    else:
        print("⚠️  使用自定义密钥")

    # 检查环境类型
    print(f"\n环境类型: {settings.ENVIRONMENT_TYPE}")
    print(f"数据库 URL: {settings.DATABASE_URL[:50]}...")

    # 检查是否可以初始化 Fernet
    try:
        cipher = Fernet(current_key.encode())
        print("✅ ENCRYPTION_KEY 格式正确")
    except Exception as e:
        print(f"❌ ENCRYPTION_KEY 格式错误: {e}")
        return False

    return True


def diagnose_datasources():
    """诊断数据源配置"""
    print("\n" + "=" * 60)
    print("数据源诊断")
    print("=" * 60)

    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        data_sources = db.query(DataSource).filter(
            DataSource.source_type == "doris"
        ).all()

        print(f"\n找到 {len(data_sources)} 个 Doris 数据源\n")

        results = []
        for ds in data_sources:
            info = {
                "id": str(ds.id),
                "name": ds.name,
                "host": ds.doris_fe_hosts[0] if ds.doris_fe_hosts else "N/A",
                "port": ds.doris_query_port,
                "database": ds.doris_database,
                "username": ds.doris_username,
                "password_length": len(ds.doris_password) if ds.doris_password else 0,
                "password_prefix": ds.doris_password[:10] if ds.doris_password else "None",
                "is_encrypted": False,
                "can_decrypt": False,
                "decryption_error": None
            }

            # 检查密码是否加密
            if ds.doris_password and ds.doris_password.startswith('gAAAA'):
                info["is_encrypted"] = True

                # 尝试用当前密钥解密
                try:
                    from app.core.security_utils import decrypt_data
                    decrypted = decrypt_data(ds.doris_password)
                    info["can_decrypt"] = True
                    info["decrypted_length"] = len(decrypted)
                except Exception as e:
                    info["can_decrypt"] = False
                    info["decryption_error"] = str(e)

            results.append(info)

            # 打印诊断结果
            print(f"数据源: {info['name']} (ID: {info['id'][:8]}...)")
            print(f"  连接: {info['username']}@{info['host']}:{info['port']}/{info['database']}")
            print(f"  密码长度: {info['password_length']} 字符")
            print(f"  密码前缀: {info['password_prefix']}...")

            if info["is_encrypted"]:
                if info["can_decrypt"]:
                    print(f"  ✅ 密码已加密，可以正常解密 (解密后长度: {info['decrypted_length']})")
                else:
                    print(f"  ❌ 密码已加密，但无法解密!")
                    print(f"     错误: {info['decryption_error']}")
                    print(f"     可能原因: ENCRYPTION_KEY 不匹配")
            else:
                print(f"  ⚠️  密码未加密 (明文)")

            print()

        return results

    except Exception as e:
        logger.error(f"诊断失败: {e}")
        return []
    finally:
        db.close()


def fix_datasource_passwords_interactive():
    """交互式修复数据源密码"""
    print("\n" + "=" * 60)
    print("交互式密码修复")
    print("=" * 60)

    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        data_sources = db.query(DataSource).filter(
            DataSource.source_type == "doris"
        ).all()

        print(f"\n找到 {len(data_sources)} 个数据源需要检查\n")

        for ds in data_sources:
            print(f"\n数据源: {ds.name}")
            print(f"  Host: {ds.doris_fe_hosts[0] if ds.doris_fe_hosts else 'N/A'}")
            print(f"  当前密码长度: {len(ds.doris_password) if ds.doris_password else 0}")

            # 检查是否可以解密
            can_decrypt = False
            decrypted_password = None

            if ds.doris_password and ds.doris_password.startswith('gAAAA'):
                try:
                    from app.core.security_utils import decrypt_data
                    decrypted_password = decrypt_data(ds.doris_password)
                    can_decrypt = True
                    print(f"  ✅ 当前密码可以解密 (解密后长度: {len(decrypted_password)})")
                except Exception as e:
                    print(f"  ❌ 当前密码无法解密: {e}")
            else:
                print(f"  ℹ️  当前密码未加密")

            # 询问操作
            print("\n  选择操作:")
            print("    1. 保持不变")
            print("    2. 输入新的明文密码 (不加密)")
            print("    3. 输入新的明文密码并加密")
            if can_decrypt:
                print(f"    4. 使用已解密的密码重新加密 (推荐)")

            choice = input("  请选择 (1/2/3/4): ").strip()

            if choice == "1":
                print("  ⏭️  跳过")
                continue

            elif choice == "2":
                new_password = input("  请输入明文密码: ").strip()
                if new_password:
                    ds.doris_password = new_password
                    db.commit()
                    print("  ✅ 已更新为明文密码")

            elif choice == "3":
                new_password = input("  请输入明文密码: ").strip()
                if new_password:
                    from app.core.security_utils import encrypt_data
                    encrypted = encrypt_data(new_password)
                    ds.doris_password = encrypted
                    db.commit()
                    print("  ✅ 已加密并更新密码")

            elif choice == "4" and can_decrypt:
                from app.core.security_utils import encrypt_data
                re_encrypted = encrypt_data(decrypted_password)
                ds.doris_password = re_encrypted
                db.commit()
                print("  ✅ 已使用当前密钥重新加密密码")

            else:
                print("  ⏭️  无效选择，跳过")

        print("\n✅ 密码修复完成")

    except Exception as e:
        logger.error(f"修复失败: {e}")
        db.rollback()
    finally:
        db.close()


def fix_all_passwords_auto():
    """自动修复所有密码 - 尝试解密并重新加密"""
    print("\n" + "=" * 60)
    print("自动密码修复 (尝试解密并重新加密)")
    print("=" * 60)

    # 尝试多个可能的密钥
    possible_keys = [
        settings.ENCRYPTION_KEY,  # 当前密钥
        "DO2E-DOAveBMXpu1xMTl9fRjehX_1pbDnVZkuFRDA14=",  # 默认密钥
        "ixd0gr5Ntuy8PSOOJsFl4DY1R2fFgFVc34_vu4Yzr1c=",  # Docker env 密钥
    ]

    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        data_sources = db.query(DataSource).filter(
            DataSource.source_type == "doris"
        ).all()

        print(f"\n找到 {len(data_sources)} 个数据源")
        print(f"将尝试 {len(possible_keys)} 个不同的解密密钥\n")

        for ds in data_sources:
            print(f"\n处理: {ds.name}")

            if not ds.doris_password:
                print("  ⚠️  密码为空，跳过")
                continue

            # 如果不是加密密码，跳过
            if not ds.doris_password.startswith('gAAAA'):
                print("  ℹ️  密码未加密，跳过")
                continue

            # 尝试用不同的密钥解密
            decrypted = None
            used_key_index = None

            for i, key in enumerate(possible_keys):
                try:
                    cipher = Fernet(key.encode())
                    decrypted = cipher.decrypt(ds.doris_password.encode()).decode()
                    used_key_index = i
                    print(f"  ✅ 使用密钥 #{i+1} 成功解密")
                    break
                except InvalidToken:
                    continue
                except Exception as e:
                    logger.warning(f"  尝试密钥 #{i+1} 失败: {e}")
                    continue

            if decrypted:
                # 使用当前密钥重新加密
                from app.core.security_utils import encrypt_data
                re_encrypted = encrypt_data(decrypted)
                ds.doris_password = re_encrypted
                db.commit()
                print(f"  ✅ 已使用当前密钥重新加密")
            else:
                print(f"  ❌ 无法用任何密钥解密，请手动处理")

        print("\n✅ 自动修复完成")

    except Exception as e:
        logger.error(f"自动修复失败: {e}")
        db.rollback()
    finally:
        db.close()


def test_connections():
    """测试数据源连接"""
    print("\n" + "=" * 60)
    print("数据源连接测试")
    print("=" * 60)

    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        data_sources = db.query(DataSource).filter(
            DataSource.source_type == "doris"
        ).all()

        print(f"\n测试 {len(data_sources)} 个数据源连接\n")

        for ds in data_sources:
            print(f"数据源: {ds.name}")
            print(f"  连接: {ds.doris_username}@{ds.doris_fe_hosts[0] if ds.doris_fe_hosts else 'N/A'}:{ds.doris_query_port}")

            try:
                from app.services.data.connectors.doris_connector import DorisConnector
                from app.core.data_source_utils import DataSourcePasswordManager
                import asyncio

                # 显示解密后的密码长度
                decrypted_pwd = DataSourcePasswordManager.get_password(ds.doris_password)
                print(f"  解密后密码长度: {len(decrypted_pwd)}")

                connector = DorisConnector.from_data_source(ds)

                async def test():
                    await connector.connect()
                    result = await connector.test_connection()
                    await connector.disconnect()
                    return result

                result = asyncio.run(test())

                if result.get("success"):
                    print(f"  ✅ 连接成功")
                    print(f"     方法: {result.get('method')}")
                else:
                    print(f"  ❌ 连接失败")
                    error = result.get('error', 'Unknown error')
                    print(f"     错误: {error}")

                    # 分析错误原因
                    if "Access denied" in error:
                        if "@192.168.34.121" in error or "@192.168" in error:
                            print(f"     💡 可能原因: Doris用户权限限制")
                            print(f"        Docker容器IP被Doris服务器拒绝")
                            print(f"        建议: 在Doris中执行以下SQL:")
                            print(f"        GRANT ALL ON *.* TO '{ds.doris_username}'@'%' IDENTIFIED BY 'password';")
                    elif "password" in error.lower():
                        print(f"     💡 可能原因: 密码错误或解密失败")

            except Exception as e:
                print(f"  ❌ 连接测试异常: {e}")
                import traceback
                traceback.print_exc()

            print()

    except Exception as e:
        logger.error(f"测试失败: {e}")
    finally:
        db.close()


def print_doris_grant_commands():
    """打印Doris权限授予命令"""
    print("\n" + "=" * 60)
    print("Doris 用户权限修复命令")
    print("=" * 60)

    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        data_sources = db.query(DataSource).filter(
            DataSource.source_type == "doris"
        ).all()

        print("\n如果遇到 IP 访问限制问题，在 Doris 中执行以下命令:\n")

        for ds in data_sources:
            print(f"-- 数据源: {ds.name}")
            print(f"-- 1. 删除旧的用户 (如果存在)")
            print(f"DROP USER IF EXISTS '{ds.doris_username}'@'%';")
            print(f"")
            print(f"-- 2. 创建允许任意IP访问的用户")
            print(f"CREATE USER '{ds.doris_username}'@'%' IDENTIFIED BY 'YOUR_PASSWORD_HERE';")
            print(f"")
            print(f"-- 3. 授予权限")
            print(f"GRANT ALL ON {ds.doris_database}.* TO '{ds.doris_username}'@'%';")
            print(f"")
            print(f"-- 4. 刷新权限")
            print(f"FLUSH PRIVILEGES;")
            print("\n" + "-" * 60 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="综合数据源问题诊断和修复")
    parser.add_argument("--diagnose", action="store_true", help="诊断环境和数据源配置")
    parser.add_argument("--fix", action="store_true", help="交互式修复密码")
    parser.add_argument("--auto-fix", action="store_true", help="自动修复密码 (尝试多个密钥)")
    parser.add_argument("--test", action="store_true", help="测试数据源连接")
    parser.add_argument("--grant-sql", action="store_true", help="生成Doris权限授予SQL")

    args = parser.parse_args()

    if args.diagnose:
        diagnose_environment()
        diagnose_datasources()

    elif args.fix:
        fix_datasource_passwords_interactive()

    elif args.auto_fix:
        fix_all_passwords_auto()

    elif args.test:
        test_connections()

    elif args.grant_sql:
        print_doris_grant_commands()

    else:
        print("请指定操作:")
        print("  --diagnose   : 诊断问题")
        print("  --fix        : 交互式修复密码")
        print("  --auto-fix   : 自动修复密码")
        print("  --test       : 测试连接")
        print("  --grant-sql  : 生成Doris权限SQL")
        print("\n示例:")
        print("  python scripts/comprehensive_datasource_fix.py --diagnose")
        print("  python scripts/comprehensive_datasource_fix.py --auto-fix")
        print("  python scripts/comprehensive_datasource_fix.py --test")
