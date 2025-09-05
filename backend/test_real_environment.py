"""
AutoReportAI Agent 真实环境测试脚本

基于实际的venv环境、Docker数据库和真实的模板、LLM配置进行测试
"""

import asyncio
import sys
import os
import logging
from datetime import datetime
import json
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('real_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 导入项目模块
from app.core.config import settings
from app.db.session import get_db
from app.models.data_source import DataSource
from app.models.template import Template
from app.models.llm_server import LLMServer
from app.models.user import User
from app.services.infrastructure.ai.agents.autoreport_ai_agent import (
    create_autoreport_ai_agent,
    AgentRequest,
    WorkflowType,
    process_placeholder_to_sql,
    run_full_pipeline
)

from sqlalchemy.orm import Session
from sqlalchemy import text


class RealEnvironmentTester:
    """真实环境测试器"""
    
    def __init__(self):
        self.test_results = {}
        
    async def run_all_tests(self):
        """运行所有真实环境测试"""
        logger.info("开始真实环境测试")
        
        try:
            # 1. 测试数据库连接
            await self.test_database_connection()
            
            # 2. 获取真实数据
            real_data = await self.get_real_data_from_database()
            
            # 3. 测试真实Agent功能
            if real_data:
                await self.test_real_agent_functionality(real_data)
            
            # 4. 生成测试报告
            self.generate_real_test_report()
            
        except Exception as e:
            logger.error(f"真实环境测试失败: {e}")
            
        logger.info("真实环境测试完成")
    
    async def test_database_connection(self):
        """测试数据库连接"""
        logger.info("=== 测试数据库连接 ===")
        
        try:
            # 获取数据库会话
            db = next(get_db())
            
            # 测试基本查询
            result = db.execute(text("SELECT version()")).fetchone()
            db_version = result[0] if result else "未知"
            
            # 测试表是否存在
            tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
            """
            tables_result = db.execute(text(tables_query)).fetchall()
            table_names = [row[0] for row in tables_result]
            
            self.test_results["database_connection"] = {
                "success": True,
                "database_url": str(settings.DATABASE_URL).replace(settings.DATABASE_URL.split('@')[0].split('//')[-1] + '@', '***@'),
                "database_version": db_version,
                "available_tables": table_names,
                "tables_count": len(table_names)
            }
            
            logger.info(f"✅ 数据库连接成功")
            logger.info(f"   数据库版本: {db_version}")
            logger.info(f"   可用表数量: {len(table_names)}")
            logger.info(f"   主要表: {', '.join(table_names[:5])}")
            
            db.close()
            
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            self.test_results["database_connection"] = {
                "success": False,
                "error": str(e)
            }
    
    async def get_real_data_from_database(self):
        """从数据库获取真实数据"""
        logger.info("=== 获取真实数据 ===")
        
        try:
            db = next(get_db())
            
            # 获取用户数据
            users = db.query(User).limit(5).all()
            
            # 获取数据源
            data_sources = db.query(DataSource).limit(10).all()
            
            # 获取模板
            templates = db.query(Template).limit(10).all()
            
            # 获取LLM服务器
            llm_servers = db.query(LLMServer).limit(10).all()
            
            real_data = {
                "users": [
                    {
                        "id": str(user.id),
                        "username": user.username,
                        "email": user.email
                    } for user in users
                ],
                "data_sources": [
                    {
                        "id": str(ds.id),
                        "name": ds.name,
                        "source_type": ds.source_type,
                        "is_active": ds.is_active,
                        "created_at": ds.created_at.isoformat() if ds.created_at else None
                    } for ds in data_sources
                ],
                "templates": [
                    {
                        "id": str(template.id),
                        "name": template.name,
                        "description": template.description,
                        "template_type": template.template_type,
                        "is_active": template.is_active
                    } for template in templates
                ],
                "llm_servers": [
                    {
                        "id": str(llm.id),
                        "name": llm.name,
                        "provider_type": llm.provider_type,
                        "is_active": getattr(llm, 'is_active', True),
                        "base_url": llm.base_url
                    } for llm in llm_servers
                ]
            }
            
            self.test_results["real_data"] = {
                "success": True,
                "users_count": len(real_data["users"]),
                "data_sources_count": len(real_data["data_sources"]),
                "templates_count": len(real_data["templates"]),
                "llm_servers_count": len(real_data["llm_servers"])
            }
            
            logger.info(f"✅ 真实数据获取成功")
            logger.info(f"   用户数量: {len(real_data['users'])}")
            logger.info(f"   数据源数量: {len(real_data['data_sources'])}")
            logger.info(f"   模板数量: {len(real_data['templates'])}")
            logger.info(f"   LLM服务器数量: {len(real_data['llm_servers'])}")
            
            db.close()
            return real_data
            
        except Exception as e:
            logger.error(f"❌ 获取真实数据失败: {e}")
            self.test_results["real_data"] = {
                "success": False,
                "error": str(e)
            }
            return None
    
    async def test_real_agent_functionality(self, real_data):
        """测试真实Agent功能"""
        logger.info("=== 测试真实Agent功能 ===")
        
        if not real_data["users"]:
            logger.warning("没有找到用户数据，跳过Agent测试")
            return
        
        # 使用第一个用户进行测试
        test_user = real_data["users"][0]
        user_id = test_user["id"]
        
        try:
            # 创建Agent实例
            agent = create_autoreport_ai_agent(user_id)
            
            # 测试1: Agent健康检查
            health_result = await agent.health_check()
            
            self.test_results["agent_health"] = {
                "success": health_result["status"] == "healthy",
                "status": health_result["status"],
                "details": health_result
            }
            
            logger.info(f"✅ Agent健康检查: {health_result['status']}")
            
            # 测试2: 如果有真实数据源，测试占位符→SQL转换
            if real_data["data_sources"]:
                await self.test_real_placeholder_to_sql(agent, real_data)
            
            # 测试3: 如果有真实模板，测试模板相关功能
            if real_data["templates"]:
                await self.test_real_template_functionality(agent, real_data)
            
            # 测试4: Agent统计信息
            stats = agent.get_agent_statistics()
            
            self.test_results["agent_statistics"] = {
                "success": True,
                "total_requests": stats["execution_statistics"]["total_requests"],
                "success_rate": stats["execution_statistics"]["success_rate"],
                "sub_agents_count": len(stats["sub_agent_statistics"])
            }
            
            logger.info(f"✅ Agent统计信息获取成功")
            logger.info(f"   总请求数: {stats['execution_statistics']['total_requests']}")
            
        except Exception as e:
            logger.error(f"❌ Agent功能测试失败: {e}")
            self.test_results["agent_functionality"] = {
                "success": False,
                "error": str(e)
            }
    
    async def test_real_placeholder_to_sql(self, agent, real_data):
        """测试真实的占位符→SQL转换"""
        logger.info("测试真实占位符→SQL转换")
        
        try:
            # 使用第一个数据源
            data_source = real_data["data_sources"][0]
            
            # 构建真实的数据源上下文
            data_source_context = {
                "source_id": data_source["id"],
                "source_type": data_source["source_type"],
                "database_name": "autoreport",  # 使用实际数据库名
                "available_tables": ["users", "templates", "data_sources", "llm_providers"],
                "table_schemas": {
                    "users": [
                        {"name": "id", "type": "uuid", "comment": "用户ID"},
                        {"name": "username", "type": "varchar", "comment": "用户名"},
                        {"name": "email", "type": "varchar", "comment": "邮箱"}
                    ],
                    "templates": [
                        {"name": "id", "type": "uuid", "comment": "模板ID"}, 
                        {"name": "name", "type": "varchar", "comment": "模板名称"},
                        {"name": "template_type", "type": "varchar", "comment": "模板类型"}
                    ]
                },
                "connection_info": {
                    "host": "localhost",
                    "port": 5432,
                    "database": "autoreport"
                }
            }
            
            # 构建任务上下文
            task_context = {
                "task_id": "real_test_001",
                "task_name": "真实环境用户统计分析",
                "task_description": f"基于{data_source['name']}数据源，分析用户注册情况和模板使用统计",
                "business_domain": "analytics",
                "report_type": "dashboard",
                "priority": "high"
            }
            
            # 测试占位符转换
            test_placeholder = {
                "placeholder_name": "total_users_count",
                "placeholder_description": "系统中的用户总数",
                "placeholder_type": "metric",
                "expected_data_type": "number"
            }
            
            request = AgentRequest(
                request_id="real_placeholder_test",
                workflow_type=WorkflowType.PLACEHOLDER_TO_SQL,
                parameters={
                    **test_placeholder,
                    "task_context": task_context,
                    "data_source_context": data_source_context
                }
            )
            
            response = await agent.execute_request(request)
            
            self.test_results["real_placeholder_to_sql"] = {
                "success": response.status.value == "completed",
                "status": response.status.value,
                "confidence_score": response.confidence_score,
                "execution_time": response.execution_time_seconds,
                "result": response.result
            }
            
            if response.status.value == "completed":
                logger.info(f"✅ 真实占位符→SQL转换成功")
                logger.info(f"   信心度: {response.confidence_score:.2f}")
                if response.result and response.result.get("sql_query"):
                    logger.info(f"   生成的SQL: {response.result['sql_query'][:100]}...")
            else:
                logger.warning(f"⚠️ 真实占位符→SQL转换未完全成功: {response.error_message}")
                
        except Exception as e:
            logger.error(f"❌ 真实占位符→SQL转换测试失败: {e}")
            self.test_results["real_placeholder_to_sql"] = {
                "success": False,
                "error": str(e)
            }
    
    async def test_real_template_functionality(self, agent, real_data):
        """测试真实模板功能"""
        logger.info("测试真实模板功能")
        
        try:
            # 使用第一个模板
            template = real_data["templates"][0]
            
            # 模拟模板中的占位符
            template_placeholders = [
                {
                    "placeholder_name": f"template_{template['id']}_metric1",
                    "placeholder_description": f"模板{template['name']}的主要指标",
                    "placeholder_type": "metric",
                    "expected_data_type": "number",
                    "current_value": None,
                    "is_empty": True
                }
            ]
            
            # 任务补充测试
            task_context = {
                "task_id": f"template_test_{template['id']}",
                "task_name": f"模板{template['name']}分析",
                "task_description": template.get("description", "模板分析任务"),
                "business_domain": "template_analysis",
                "report_type": template.get("template_type", "dashboard")
            }
            
            data_source_context = {
                "source_id": "real_db_source",
                "source_type": "postgresql",
                "database_name": "autoreport",
                "available_tables": ["templates", "users"],
                "table_schemas": {
                    "templates": [
                        {"name": "id", "type": "uuid", "comment": "模板ID"},
                        {"name": "name", "type": "varchar", "comment": "模板名称"}
                    ]
                }
            }
            
            request = AgentRequest(
                request_id="real_template_test",
                workflow_type=WorkflowType.TASK_SUPPLEMENT,
                parameters={
                    "template_id": template["id"],
                    "placeholders": template_placeholders,
                    "task_context": task_context,
                    "data_source_context": data_source_context
                }
            )
            
            response = await agent.execute_request(request)
            
            self.test_results["real_template_functionality"] = {
                "success": response.status.value == "completed",
                "status": response.status.value,
                "template_id": template["id"],
                "template_name": template["name"],
                "execution_time": response.execution_time_seconds,
                "result": response.result
            }
            
            if response.status.value == "completed":
                logger.info(f"✅ 真实模板功能测试成功")
                logger.info(f"   模板: {template['name']}")
            else:
                logger.warning(f"⚠️ 真实模板功能测试未完全成功: {response.error_message}")
                
        except Exception as e:
            logger.error(f"❌ 真实模板功能测试失败: {e}")
            self.test_results["real_template_functionality"] = {
                "success": False,
                "error": str(e)
            }
    
    def generate_real_test_report(self):
        """生成真实测试报告"""
        logger.info("=== 真实环境测试报告 ===")
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results.values() if result.get("success", False))
        
        logger.info(f"总测试数: {total_tests}")
        logger.info(f"成功测试数: {successful_tests}")
        logger.info(f"成功率: {successful_tests/total_tests:.2%}")
        
        # 详细结果
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
            logger.info(f"{test_name}: {status}")
            
            if not result.get("success", False) and result.get("error"):
                logger.info(f"  错误: {result['error']}")
        
        # 保存详细报告
        report_file = f"real_environment_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                "test_summary": {
                    "total_tests": total_tests,
                    "successful_tests": successful_tests,
                    "success_rate": successful_tests/total_tests,
                    "test_time": datetime.now().isoformat(),
                    "environment": "real_venv_docker"
                },
                "detailed_results": self.test_results
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"详细测试报告已保存到: {report_file}")


async def test_database_connection_direct():
    """直接测试数据库连接"""
    logger.info("直接测试数据库连接...")
    
    try:
        db = next(get_db())
        
        # 测试简单查询
        result = db.execute(text("SELECT 1 as test")).fetchone()
        logger.info(f"✅ 数据库连接正常，测试查询结果: {result[0]}")
        
        # 检查用户表
        user_count = db.execute(text("SELECT COUNT(*) FROM users")).fetchone()
        logger.info(f"📊 用户表记录数: {user_count[0]}")
        
        # 检查数据源表
        ds_count = db.execute(text("SELECT COUNT(*) FROM data_sources")).fetchone()  
        logger.info(f"📊 数据源表记录数: {ds_count[0]}")
        
        # 检查模板表
        template_count = db.execute(text("SELECT COUNT(*) FROM templates")).fetchone()
        logger.info(f"📊 模板表记录数: {template_count[0]}")
        
        db.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        return False


async def main():
    """主测试函数"""
    try:
        logger.info("开始真实环境测试")
        logger.info(f"数据库URL: {str(settings.DATABASE_URL).replace(str(settings.DATABASE_URL).split('@')[0].split('//')[-1] + '@', '***@')}")
        
        # 首先测试数据库连接
        if not await test_database_connection_direct():
            logger.error("数据库连接失败，停止测试")
            return
        
        # 运行完整测试
        tester = RealEnvironmentTester()
        await tester.run_all_tests()
        
    except Exception as e:
        logger.error(f"主测试函数异常: {e}")


if __name__ == "__main__":
    # 使用venv环境运行
    asyncio.run(main())