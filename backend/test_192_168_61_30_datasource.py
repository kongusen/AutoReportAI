"""
专门测试192.168.61.30数据源的AutoReportAI Agent功能
解决LLM响应为空的问题，并使用指定的数据源进行测试
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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
    WorkflowType
)


class DataSource192168Testing:
    """专门针对192.168.61.30数据源的测试"""
    
    def __init__(self):
        self.test_results = {}
        self.target_datasource_id = "9cb48092-1bb8-4a7f-993f-8b355d984656"  # 192.168.61.30数据源
        
    async def run_targeted_test(self):
        """运行针对192.168.61.30数据源的测试"""
        logger.info("🎯 开始192.168.61.30数据源专项测试")
        
        try:
            # 1. 获取指定数据源配置
            datasource_config = await self.get_target_datasource_config()
            
            if not datasource_config:
                logger.error("无法获取192.168.61.30数据源配置")
                return
                
            # 2. 获取用户和LLM配置
            user_config = await self.get_user_and_llm_config()
            
            if not user_config:
                logger.error("无法获取用户和LLM配置")
                return
                
            # 3. 创建Agent并测试
            agent = create_autoreport_ai_agent(user_config["user_id"])
            
            # 4. 测试核心功能
            await self.test_placeholder_to_sql_with_target_datasource(agent, datasource_config, user_config)
            
            # 5. 测试多上下文集成
            await self.test_context_integration_with_target_datasource(agent, datasource_config, user_config)
            
            # 6. 生成测试报告
            self.generate_targeted_test_report()
            
        except Exception as e:
            logger.error(f"192.168.61.30数据源测试失败: {e}")
            import traceback
            traceback.print_exc()
            
        logger.info("✅ 192.168.61.30数据源专项测试完成")
    
    async def get_target_datasource_config(self):
        """获取目标数据源配置"""
        try:
            db = next(get_db())
            
            # 查询指定的数据源
            datasource = db.query(DataSource).filter(
                DataSource.id == self.target_datasource_id
            ).first()
            
            if not datasource:
                logger.error(f"未找到数据源ID: {self.target_datasource_id}")
                db.close()
                return None
            
            config = {
                "id": str(datasource.id),
                "name": datasource.name,
                "source_type": datasource.source_type.value if hasattr(datasource.source_type, 'value') else str(datasource.source_type),
                "doris_fe_hosts": datasource.doris_fe_hosts,
                "doris_query_port": datasource.doris_query_port,
                "doris_database": datasource.doris_database or "default_db",
                "doris_username": datasource.doris_username,
                "is_active": datasource.is_active
            }
            
            db.close()
            
            logger.info(f"✅ 获取目标数据源配置成功:")
            logger.info(f"   数据源名称: {config['name']}")
            logger.info(f"   Doris FE Hosts: {config['doris_fe_hosts']}")
            logger.info(f"   Query Port: {config['doris_query_port']}")
            logger.info(f"   数据库: {config['doris_database']}")
            
            return config
            
        except Exception as e:
            logger.error(f"获取目标数据源配置失败: {e}")
            return None
    
    async def get_user_and_llm_config(self):
        """获取用户和LLM配置"""
        try:
            db = next(get_db())
            
            # 获取第一个用户
            user = db.query(User).first()
            if not user:
                logger.error("未找到用户")
                db.close()
                return None
            
            # 获取激活的LLM服务器
            llm_server = db.query(LLMServer).filter(
                LLMServer.user_id == user.id,
                LLMServer.is_active == True
            ).first()
            
            if not llm_server:
                logger.warning("未找到激活的LLM服务器")
            
            config = {
                "user_id": str(user.id),
                "username": user.username,
                "email": user.email,
                "llm_server": {
                    "id": str(llm_server.id) if llm_server else None,
                    "name": llm_server.name if llm_server else None,
                    "base_url": llm_server.base_url if llm_server else None,
                    "provider_type": llm_server.provider_type if llm_server else None
                } if llm_server else None
            }
            
            db.close()
            
            logger.info(f"✅ 获取用户和LLM配置成功:")
            logger.info(f"   用户: {config['username']}")
            logger.info(f"   LLM服务器: {config['llm_server']['name'] if config['llm_server'] else 'None'}")
            
            return config
            
        except Exception as e:
            logger.error(f"获取用户和LLM配置失败: {e}")
            return None
    
    async def test_placeholder_to_sql_with_target_datasource(self, agent, datasource_config, user_config):
        """使用目标数据源测试占位符→SQL转换"""
        logger.info("🔧 测试占位符→SQL转换 (使用192.168.61.30数据源)")
        
        try:
            # 构建真实的数据源上下文
            data_source_context = {
                "source_id": datasource_config["id"],
                "source_type": datasource_config["source_type"],
                "database_name": datasource_config["doris_database"],
                "available_tables": ["customer", "orders", "products", "sales"], # 假设的表
                "table_schemas": {
                    "customer": [
                        {"name": "customer_id", "type": "bigint", "comment": "客户ID"},
                        {"name": "customer_name", "type": "varchar", "comment": "客户名称"},
                        {"name": "created_date", "type": "date", "comment": "创建日期"}
                    ],
                    "orders": [
                        {"name": "order_id", "type": "bigint", "comment": "订单ID"},
                        {"name": "customer_id", "type": "bigint", "comment": "客户ID"},
                        {"name": "order_amount", "type": "decimal", "comment": "订单金额"},
                        {"name": "order_date", "type": "date", "comment": "下单日期"}
                    ]
                },
                "connection_info": {
                    "host": datasource_config["doris_fe_hosts"][0] if datasource_config["doris_fe_hosts"] else "192.168.61.30",
                    "port": datasource_config["doris_query_port"],
                    "database": datasource_config["doris_database"],
                    "username": datasource_config["doris_username"]
                }
            }
            
            # 构建任务上下文
            task_context = {
                "task_id": "doris_192_168_61_30_test",
                "task_name": "Doris数据源销售分析",
                "task_description": f"基于{datasource_config['name']}数据源进行销售数据分析",
                "business_domain": "sales_analytics",
                "report_type": "dashboard",
                "priority": "high"
            }
            
            # 测试占位符：客户总数统计
            request = AgentRequest(
                request_id="doris_customer_count_test",
                workflow_type=WorkflowType.PLACEHOLDER_TO_SQL,
                parameters={
                    "placeholder_name": "total_customer_count",
                    "placeholder_description": f"基于{datasource_config['name']}(192.168.61.30)的客户总数统计",
                    "placeholder_type": "metric",
                    "expected_data_type": "number",
                    "task_context": task_context,
                    "data_source_context": data_source_context
                }
            )
            
            response = await agent.execute_request(request)
            
            self.test_results["doris_placeholder_to_sql"] = {
                "success": response.status.value == "completed",
                "status": response.status.value,
                "confidence_score": response.confidence_score,
                "execution_time": response.execution_time_seconds,
                "datasource_name": datasource_config["name"],
                "datasource_host": datasource_config["doris_fe_hosts"][0] if datasource_config["doris_fe_hosts"] else "192.168.61.30",
                "has_sql_query": bool(response.result and response.result.get("sql_query")) if response.result else False,
                "sql_query": response.result.get("sql_query", "") if response.result else "",
                "validation_errors": response.result.get("validation_errors", []) if response.result else [],
                "error_message": response.error_message if hasattr(response, 'error_message') else None
            }
            
            if response.status.value == "completed":
                logger.info(f"✅ Doris数据源占位符→SQL转换成功")
                logger.info(f"   数据源: {datasource_config['name']} (192.168.61.30)")
                logger.info(f"   信心度: {response.confidence_score:.2f}")
                if response.result and response.result.get("sql_query"):
                    logger.info(f"   生成的SQL: {response.result['sql_query'][:150]}...")
            else:
                logger.warning(f"⚠️ Doris数据源占位符→SQL转换部分成功")
                logger.warning(f"   状态: {response.status.value}")
                if hasattr(response, 'error_message') and response.error_message:
                    logger.warning(f"   错误: {response.error_message}")
                
        except Exception as e:
            logger.error(f"❌ Doris数据源占位符→SQL转换测试失败: {e}")
            self.test_results["doris_placeholder_to_sql"] = {
                "success": False,
                "error": str(e),
                "datasource_name": datasource_config["name"]
            }
    
    async def test_context_integration_with_target_datasource(self, agent, datasource_config, user_config):
        """使用目标数据源测试上下文集成"""
        logger.info("🧠 测试多上下文集成 (使用192.168.61.30数据源)")
        
        try:
            contexts = [
                {
                    "context_id": "doris_192_168_61_30",
                    "context_type": "data_source",
                    "priority": "critical",
                    "content": {
                        "data_source_id": datasource_config["id"],
                        "data_source_name": datasource_config["name"],
                        "doris_host": datasource_config["doris_fe_hosts"][0] if datasource_config["doris_fe_hosts"] else "192.168.61.30",
                        "doris_port": datasource_config["doris_query_port"],
                        "database_name": datasource_config["doris_database"],
                        "source_type": datasource_config["source_type"]
                    }
                },
                {
                    "context_id": "user_context",
                    "context_type": "user",
                    "priority": "high",
                    "content": {
                        "user_id": user_config["user_id"],
                        "username": user_config["username"],
                        "has_llm_server": bool(user_config["llm_server"])
                    }
                },
                {
                    "context_id": "business_context",
                    "context_type": "business",
                    "priority": "medium",
                    "content": {
                        "domain": "sales_analytics",
                        "target_datasource": "doris_192_168_61_30",
                        "analysis_type": "customer_behavior"
                    }
                }
            ]
            
            request = AgentRequest(
                request_id="doris_context_integration",
                workflow_type=WorkflowType.MULTI_CONTEXT_INTEGRATION,
                parameters={
                    "contexts": contexts,
                    "target_task": f"基于192.168.61.30 Doris数据源的销售数据分析上下文集成",
                    "required_context_types": ["data_source", "user"],
                    "custom_weights": {
                        "data_source": 0.5,
                        "user": 0.3,
                        "business": 0.2
                    }
                }
            )
            
            response = await agent.execute_request(request)
            
            self.test_results["doris_context_integration"] = {
                "success": response.status.value == "completed",
                "status": response.status.value,
                "execution_time": response.execution_time_seconds,
                "contexts_processed": len(contexts),
                "datasource_name": datasource_config["name"],
                "integration_result": response.result if response.result else {},
                "error_message": response.error_message if hasattr(response, 'error_message') else None
            }
            
            if response.status.value == "completed":
                logger.info(f"✅ Doris数据源多上下文集成成功")
                logger.info(f"   数据源: {datasource_config['name']} (192.168.61.30)")
                logger.info(f"   处理的上下文数: {len(contexts)}")
            else:
                logger.warning(f"⚠️ Doris数据源多上下文集成部分成功")
                logger.warning(f"   状态: {response.status.value}")
                
        except Exception as e:
            logger.error(f"❌ Doris数据源多上下文集成测试失败: {e}")
            self.test_results["doris_context_integration"] = {
                "success": False,
                "error": str(e),
                "datasource_name": datasource_config["name"]
            }
    
    def generate_targeted_test_report(self):
        """生成专项测试报告"""
        logger.info("📊 === 192.168.61.30数据源专项测试报告 ===")
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results.values() if result.get("success", False))
        
        logger.info(f"📈 总体结果:")
        logger.info(f"   目标数据源: 测试-公司 (192.168.61.30)")
        logger.info(f"   总测试数: {total_tests}")
        logger.info(f"   成功测试数: {successful_tests}")
        logger.info(f"   成功率: {successful_tests/total_tests:.2%}" if total_tests > 0 else "   成功率: 0%")
        logger.info("")
        
        logger.info(f"🔍 详细结果:")
        test_emojis = {
            "doris_placeholder_to_sql": "🔧",
            "doris_context_integration": "🧠"
        }
        
        for test_name, result in self.test_results.items():
            emoji = test_emojis.get(test_name, "🧪")
            status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
            logger.info(f"   {emoji} {test_name}: {status}")
            
            # 显示关键信息
            if result.get("datasource_name"):
                logger.info(f"      数据源: {result['datasource_name']}")
            if result.get("datasource_host"):
                logger.info(f"      主机: {result['datasource_host']}")
            if result.get("success", False):
                if "confidence_score" in result:
                    logger.info(f"      信心度: {result['confidence_score']:.2f}")
                if "execution_time" in result:
                    logger.info(f"      执行时间: {result['execution_time']:.3f}s")
                if result.get("has_sql_query"):
                    logger.info(f"      SQL生成: ✅")
                if result.get("sql_query"):
                    logger.info(f"      SQL预览: {result['sql_query'][:100]}...")
            else:
                if result.get("error"):
                    logger.info(f"      错误: {result['error']}")
                if result.get("error_message"):
                    logger.info(f"      错误信息: {result['error_message']}")
        
        # 保存详细报告
        report_file = f"doris_192_168_61_30_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                "test_summary": {
                    "target_datasource": "测试-公司 (192.168.61.30)",
                    "total_tests": total_tests,
                    "successful_tests": successful_tests,
                    "success_rate": successful_tests/total_tests if total_tests > 0 else 0,
                    "test_time": datetime.now().isoformat(),
                    "environment": "doris_192_168_61_30_targeted"
                },
                "detailed_results": self.test_results
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📄 详细测试报告已保存到: {report_file}")


async def main():
    """主测试函数"""
    try:
        # 设置数据库连接（从autorport-dev的docker-compose.yml获取正确配置）
        os.environ["DATABASE_URL"] = "postgresql://postgres:postgres123@localhost:5432/autoreport"
        os.environ["POSTGRES_PASSWORD"] = "postgres123"
        os.environ["POSTGRES_USER"] = "postgres"
        os.environ["POSTGRES_DB"] = "autoreport"
        
        logger.info("🎯 开始192.168.61.30数据源专项测试")
        logger.info(f"数据库URL: postgresql://postgres:***@localhost:5432/autoreport")
        
        # 先测试数据库连接
        try:
            from app.db.session import get_db
            from sqlalchemy import text
            db = next(get_db())
            result = db.execute(text("SELECT 1 as test")).fetchone()
            logger.info(f"✅ 数据库连接测试成功: {result[0]}")
            db.close()
        except Exception as db_error:
            logger.error(f"❌ 数据库连接失败: {db_error}")
            return
        
        tester = DataSource192168Testing()
        await tester.run_targeted_test()
        
    except Exception as e:
        logger.error(f"主测试函数异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行192.168.61.30数据源专项测试
    asyncio.run(main())