#!/usr/bin/env python3
"""
AutoReportAI Database Initialization Script
一键初始化数据库，包含所有表结构、索引和数据
"""

import os
import sys
import psycopg2
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings

def init_database():
    """初始化数据库"""
    print("🚀 开始初始化 AutoReportAI 数据库...")
    
    try:
        # 连接数据库
        print(f"📡 连接数据库: {settings.DATABASE_URL}")
        conn = psycopg2.connect(settings.DATABASE_URL)
        cur = conn.cursor()
        
        # 读取完整初始化脚本
        script_path = Path(__file__).parent / "init-db.sql"
        if not script_path.exists():
            print(f"❌ 初始化脚本不存在: {script_path}")
            return False
            
        print("📄 读取数据库初始化脚本...")
        with open(script_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        print("🔧 执行数据库初始化...")
        cur.execute(sql_content)
        conn.commit()
        
        # 验证表创建情况
        print("✅ 验证表创建情况...")
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        
        tables = [row[0] for row in cur.fetchall()]
        print(f"📊 成功创建 {len(tables)} 个表:")
        
        # 按类别显示表
        core_tables = [t for t in tables if t in ['users', 'ai_providers', 'data_sources', 'templates', 'tasks']]
        schema_tables = [t for t in tables if 'schema' in t or t in ['databases', 'tables', 'table_columns']]
        template_tables = [t for t in tables if 'template' in t or 'placeholder' in t]
        other_tables = [t for t in tables if t not in core_tables + schema_tables + template_tables]
        
        if core_tables:
            print("  📋 核心表:", ", ".join(core_tables))
        if schema_tables:
            print("  🗄️  架构表:", ", ".join(schema_tables))
        if template_tables:
            print("  📝 模板表:", ", ".join(template_tables))
        if other_tables:
            print("  🔧 其他表:", ", ".join(other_tables))
        
        # 检查关键表
        key_tables = ['users', 'data_sources', 'templates', 'tasks']
        missing_tables = [t for t in key_tables if t not in tables]
        
        if missing_tables:
            print(f"⚠️  缺少关键表: {missing_tables}")
            return False
        
        print("✅ 所有关键表创建成功!")
        
        # 创建默认管理员用户（如果不存在）
        print("👤 检查默认管理员用户...")
        cur.execute("SELECT COUNT(*) FROM users WHERE is_superuser = true")
        superuser_count = cur.fetchone()[0]
        
        if superuser_count == 0:
            print("🔑 创建默认管理员用户...")
            from app.core.security import get_password_hash
            
            hashed_password = get_password_hash(settings.FIRST_SUPERUSER_PASSWORD)
            cur.execute("""
                INSERT INTO users (email, username, hashed_password, is_active, is_superuser, full_name)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (email) DO NOTHING
            """, (
                settings.FIRST_SUPERUSER_EMAIL,
                settings.FIRST_SUPERUSER,
                hashed_password,
                True,
                True,
                "System Administrator"
            ))
            conn.commit()
            print(f"✅ 创建管理员用户: {settings.FIRST_SUPERUSER_EMAIL}")
        else:
            print(f"ℹ️  已存在 {superuser_count} 个管理员用户")
        
        cur.close()
        conn.close()
        
        print("\n🎉 数据库初始化完成!")
        print("=" * 50)
        print(f"📊 创建表数量: {len(tables)}")
        print(f"👤 管理员邮箱: {settings.FIRST_SUPERUSER_EMAIL}")
        print(f"🔗 数据库连接: {settings.DATABASE_URL.replace(settings.DATABASE_URL.split('@')[0].split(':')[-1], '***')}")
        print("=" * 50)
        print("🚀 现在可以启动应用服务了!")
        
        return True
        
    except psycopg2.Error as e:
        print(f"❌ 数据库错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def reset_database():
    """重置数据库（危险操作）"""
    print("⚠️  警告：即将重置数据库，所有数据将被删除！")
    confirm = input("请输入 'RESET' 确认重置: ")
    
    if confirm != 'RESET':
        print("❌ 操作已取消")
        return False
    
    try:
        # 解析数据库URL获取连接参数
        db_url = settings.DATABASE_URL
        parts = db_url.split('://')
        user_pass, host_port_db = parts[1].split('@')
        user, password = user_pass.split(':')
        host_port, db_name = host_port_db.split('/')
        host, port = (host_port.split(':') + ['5432'])[:2]
        
        # 连接到postgres数据库
        conn = psycopg2.connect(
            host=host, port=port, database='postgres',
            user=user, password=password
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        print(f"🗑️  删除数据库: {db_name}")
        
        # 强制断开所有连接
        cur.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{db_name}'
              AND pid <> pg_backend_pid();
        """)
        
        # 删除数据库
        cur.execute(f'DROP DATABASE IF EXISTS {db_name}')
        
        # 重新创建数据库
        cur.execute(f'CREATE DATABASE {db_name} WITH OWNER = {user} ENCODING = "UTF8" LC_COLLATE = "C" LC_CTYPE = "C"')
        
        cur.close()
        conn.close()
        
        print(f"✅ 数据库 {db_name} 重置完成")
        return True
        
    except Exception as e:
        print(f"❌ 重置失败: {e}")
        return False

def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        print("🔄 重置数据库模式")
        if reset_database():
            print("📝 开始初始化...")
            init_database()
    else:
        print("🆕 初始化数据库模式")
        init_database()

if __name__ == "__main__":
    main()