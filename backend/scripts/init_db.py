#!/usr/bin/env python3
"""
AutoReportAI Database Initialization Script
一键初始化数据库，包含所有表结构、索引和数据
适配新的 DDD 架构和依赖注入系统
"""

import os
import sys
import logging
import psycopg2
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
            try:
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
                logger.info(f"✅ 创建管理员用户: {settings.FIRST_SUPERUSER_EMAIL}")
                print(f"✅ 创建管理员用户: {settings.FIRST_SUPERUSER_EMAIL}")
            except Exception as e:
                logger.error(f"创建管理员用户失败: {e}")
                print(f"⚠️  创建管理员用户失败: {e}")
        else:
            print(f"ℹ️  已存在 {superuser_count} 个管理员用户")
        
        # 创建默认LLM服务器和模型（如果不存在）
        print("🤖 检查默认LLM服务器...")
        cur.execute("SELECT COUNT(*) FROM llm_servers")
        server_count = cur.fetchone()[0]
        
        if server_count == 0:
            print("🛠️  创建默认LLM服务器配置...")
            
            # 创建本地OpenAI兼容服务器
            cur.execute("""
                INSERT INTO llm_servers (name, description, base_url, auth_enabled, is_active, server_version)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                "Local OpenAI Compatible",
                "本地OpenAI兼容API服务器",
                "http://localhost:11434/v1",
                False,
                True,
                "v1.0"
            ))
            local_server_id = cur.fetchone()[0]
            
            # 创建OpenAI官方服务器
            cur.execute("""
                INSERT INTO llm_servers (name, description, base_url, auth_enabled, is_active, server_version)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                "OpenAI Official",
                "OpenAI官方API服务",
                "https://api.openai.com/v1",
                True,
                False,  # 默认不激活，需要用户配置API密钥
                "v1.0"
            ))
            openai_server_id = cur.fetchone()[0]
            
            # 为本地服务器添加默认模型
            default_models = [
                ("llama3.2:3b", "Llama 3.2 3B", "小型聊天模型，适合日常对话", "chat", "ollama", True, 10, False),
                ("qwen2.5:7b", "Qwen 2.5 7B", "中等规模聊天模型，平衡性能与质量", "chat", "ollama", True, 20, False),
                ("deepseek-coder-v2:16b", "DeepSeek Coder V2 16B", "专业代码生成模型", "chat", "ollama", True, 30, False),
                ("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet (Think)", "支持思考模式的高级模型", "think", "anthropic", True, 5, True),
            ]
            
            for name, display_name, description, model_type, provider, is_active, priority, supports_thinking in default_models:
                server_id = local_server_id if provider == "ollama" else openai_server_id
                cur.execute("""
                    INSERT INTO llm_models (
                        server_id, name, display_name, description, model_type, provider_name, 
                        is_active, priority, supports_thinking, supports_function_calls, max_tokens
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    server_id, name, display_name, description, model_type, provider,
                    is_active, priority, supports_thinking, False, 32000
                ))
            
            conn.commit()
            print(f"✅ 创建了2个LLM服务器和{len(default_models)}个模型")
        else:
            print(f"ℹ️  已存在 {server_count} 个LLM服务器")
        
        cur.close()
        conn.close()
        
        # 初始化新架构相关配置
        print("🏗️  初始化 DDD 架构相关配置...")
        try:
            # 创建默认的分析配置
            cur.execute("""
                INSERT INTO analytics_data (name, data_type, configuration, is_active)
                VALUES ('default_analysis', 'system', '{}', true)
                ON CONFLICT (name) DO NOTHING
            """)
            
            # 初始化占位符映射缓存
            cur.execute("""
                SELECT COUNT(*) FROM placeholder_mappings
            """)
            placeholder_count = cur.fetchone()[0]
            if placeholder_count == 0:
                logger.info("创建默认占位符映射")
            
            conn.commit()
            logger.info("✅ DDD 架构配置初始化完成")
        except Exception as e:
            logger.warning(f"DDD 架构配置初始化失败: {e}")
            # 不影响主要初始化流程
        
        print("\n🎉 数据库初始化完成!")
        print("=" * 50)
        print(f"📊 创建表数量: {len(tables)}")
        print(f"👤 管理员邮箱: {settings.FIRST_SUPERUSER_EMAIL}")
        print(f"🤖 LLM服务器数: {server_count}+(新增2个)" if server_count == 0 else f"🤖 LLM服务器数: {server_count}")
        print(f"🔗 数据库连接: {settings.DATABASE_URL.replace(settings.DATABASE_URL.split('@')[0].split(':')[-1], '***')}")
        print(f"🏗️  DDD 架构: Application → Domain → Infrastructure → Data")
        print("=" * 50)
        print("🚀 现在可以启动应用服务了!")
        
        return True
        
    except psycopg2.Error as e:
        logger.error(f"数据库错误: {e}")
        print(f"❌ 数据库错误: {e}")
        return False
    except Exception as e:
        logger.error(f"初始化失败: {e}", exc_info=True)
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

def validate_new_architecture():
    """验证新架构相关组件"""
    try:
        logger.info("🔍 验证新 DDD 架构组件...")
        
        # 验证核心配置
        from app.core.config import settings
        from app.core.dependencies import get_current_user
        
        # 验证应用层工厂
        from app.services.application.factories import create_intelligent_placeholder_workflow
        
        # 验证领域服务
        from app.services.domain.template.intelligent_template_service import IntelligentTemplateService
        from app.services.domain.placeholder.intelligent_placeholder_service import IntelligentPlaceholderService
        
        # 验证基础设施层
        from app.services.infrastructure.cache.unified_cache_system import UnifiedCacheSystem
        
        logger.info("✅ 新架构组件验证通过")
        print("✅ 新 DDD 架构组件验证通过")
        return True
        
    except ImportError as e:
        logger.error(f"架构组件导入失败: {e}")
        print(f"⚠️  架构组件导入失败: {e}")
        return False
    except Exception as e:
        logger.error(f"架构验证失败: {e}")
        print(f"⚠️  架构验证失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("🚀 AutoReportAI 数据库初始化开始")
    
    # 验证新架构
    if not validate_new_architecture():
        logger.warning("架构验证失败，但继续初始化...")
    
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        print("🔄 重置数据库模式")
        if reset_database():
            print("📝 开始初始化...")
            success = init_database()
            sys.exit(0 if success else 1)
    else:
        print("🆕 初始化数据库模式")
        success = init_database()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()