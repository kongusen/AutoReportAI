"""
完整的AutoReportAI Agent真实环境测试

使用真实的:
- venv环境
- Docker PostgreSQL数据库
- 真实的LLM服务器配置 (xiaoai)
- 真实的Doris数据源
- 真实的用户和模板数据

完整测试Agent的三大核心功能和五大流程
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


class CompleteRealAgentTester:
    """完整真实Agent测试器"""
    
    def __init__(self):
        self.test_results = {}
        
    async def run_complete_test(self):
        """运行完整的真实环境测试"""
        logger.info("🚀 开始完整的AutoReportAI Agent真实环境测试")
        
        try:
            # 1. 获取真实配置数据
            real_config = await self.get_real_database_config()
            
            if not real_config:
                logger.error("无法获取真实数据库配置，停止测试")
                return
                
            # 2. 使用真实用户创建Agent
            user_id = real_config["user"]["id"]
            agent = create_autoreport_ai_agent(user_id)
            
            # 3. 测试核心功能1：占位符→SQL转换
            await self.test_real_placeholder_to_sql(agent, real_config)
            
            # 4. 测试核心功能2：任务补充机制
            await self.test_real_task_supplement(agent, real_config)
            
            # 5. 测试核心功能3：多上下文集成
            await self.test_real_context_integration(agent, real_config)
            
            # 6. 测试完整流水线
            await self.test_complete_pipeline(agent, real_config)
            
            # 7. 生成测试报告
            self.generate_complete_test_report()
            
        except Exception as e:
            logger.error(f"完整测试失败: {e}")
            import traceback
            traceback.print_exc()
            
        logger.info("✅ 完整的AutoReportAI Agent真实环境测试完成")
    
    async def get_real_database_config(self):
        """获取真实数据库配置"""
        try:
            db = next(get_db())
            
            # 获取用户
            user = db.query(User).first()
            if not user:
                logger.error("数据库中没有用户数据")
                return None
                
            # 获取LLM服务器
            llm_server = db.query(LLMServer).filter(
                LLMServer.user_id == user.id,
                LLMServer.is_active == True
            ).first()
            
            if not llm_server:
                logger.error("没有找到激活的LLM服务器")
                return None
            
            # 获取数据源
            data_sources = db.query(DataSource).filter(
                DataSource.is_active == True
            ).all()
            
            if not data_sources:
                logger.error("没有找到激活的数据源")
                return None
            
            # 获取模板
            templates = db.query(Template).filter(
                Template.is_active == True
            ).limit(2).all()
            
            config = {
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "email": user.email
                },
                "llm_server": {
                    "id": str(llm_server.id),
                    "name": llm_server.name,
                    "provider_type": llm_server.provider_type,
                    "base_url": llm_server.base_url,
                    "has_api_key": bool(getattr(llm_server, 'api_key', None))
                },
                "data_sources": [
                    {
                        "id": str(ds.id),
                        "name": ds.name,
                        "source_type": ds.source_type.value if hasattr(ds.source_type, 'value') else str(ds.source_type),
                        "config": ds.config if hasattr(ds, 'config') else {}
                    } for ds in data_sources
                ],
                "templates": [
                    {
                        "id": str(t.id),
                        "name": t.name,
                        "description": t.description,
                        "template_type": t.template_type.value if hasattr(t.template_type, 'value') else str(t.template_type)
                    } for t in templates
                ]
            }
            
            db.close()
            
            logger.info(f"✅ 获取真实配置成功:")
            logger.info(f"   用户: {config['user']['username']}")
            logger.info(f"   LLM服务器: {config['llm_server']['name']} ({config['llm_server']['provider_type']})")
            logger.info(f"   数据源数量: {len(config['data_sources'])}")
            logger.info(f"   模板数量: {len(config['templates'])}")
            
            return config
            
        except Exception as e:
            logger.error(f"获取真实配置失败: {e}")
            return None
    
    async def test_real_placeholder_to_sql(self, agent, real_config):
        """测试真实的占位符→SQL转换"""
        logger.info("🔧 测试核心功能1：占位符→SQL转换")
        
        try:
            # 使用第一个数据源
            data_source = real_config["data_sources"][0]
            
            # 构建真实的占位符转换请求
            request = AgentRequest(
                request_id="real_sql_conversion",
                workflow_type=WorkflowType.PLACEHOLDER_TO_SQL,
                parameters={
                    "placeholder_name": "user_total_count",
                    "placeholder_description": f"系统中{data_source['name']}数据源的用户总数统计",
                    "placeholder_type": "metric",
                    "expected_data_type": "number",
                    "task_context": {
                        "task_id": "real_analysis_001",
                        "task_name": "用户数据分析",
                        "task_description": f"基于{data_source['name']}进行用户数据统计分析",
                        "business_domain": "analytics",
                        "report_type": "dashboard",
                        "priority": "high"
                    },
                    "data_source_context": {
                        "source_id": data_source["id"],
                        "source_type": data_source["source_type"],
                        "database_name": "default_db",
                        "available_tables": ["users", "user_behavior", "user_profiles"],
                        "table_schemas": {
                            "users": [
                                {"name": "user_id", "type": "bigint", "comment": "用户ID"},
                                {"name": "username", "type": "varchar", "comment": "用户名"},
                                {"name": "created_at", "type": "datetime", "comment": "创建时间"}
                            ]
                        },
                        "connection_info": {
                            "host": "localhost",
                            "port": 9030,
                            "database": "default_db"
                        }
                    }
                }
            )
            
            response = await agent.execute_request(request)
            
            self.test_results["real_placeholder_to_sql"] = {
                "success": response.status.value == "completed",
                "status": response.status.value,
                "confidence_score": response.confidence_score,
                "execution_time": response.execution_time_seconds,
                "has_sql_query": bool(response.result and response.result.get("sql_query")),
                "sql_preview": response.result.get("sql_query", "")[:200] + "..." if response.result and response.result.get("sql_query") else "",
                "validation_errors_count": len(response.result.get("validation_errors", [])) if response.result else 0
            }
            
            if response.status.value == "completed":
                logger.info(f"✅ 占位符→SQL转换成功")
                logger.info(f"   信心度: {response.confidence_score:.2f}")
                if response.result and response.result.get("sql_query"):
                    logger.info(f"   生成SQL: {response.result['sql_query'][:100]}...")
            else:
                logger.warning(f"⚠️ 占位符→SQL转换部分成功: {response.error_message}")
                
        except Exception as e:
            logger.error(f"❌ 占位符→SQL转换测试失败: {e}")
            self.test_results["real_placeholder_to_sql"] = {
                "success": False,
                "error": str(e)
            }
    
    async def test_real_task_supplement(self, agent, real_config):
        """测试真实的任务补充机制"""
        logger.info("🔄 测试核心功能2：任务补充机制")
        
        try:
            # 使用真实模板和数据源
            template = real_config["templates"][0] if real_config["templates"] else None
            data_source = real_config["data_sources"][0]
            
            if not template:
                logger.warning("没有可用模板，跳过任务补充测试")
                self.test_results["real_task_supplement"] = {"success": False, "error": "no_template"}
                return
            
            # 模拟需要补充的占位符
            placeholders = [
                {
                    "placeholder_name": f"{template['name']}_key_metric",
                    "placeholder_description": f"模板{template['name']}的关键指标",
                    "placeholder_type": "metric",
                    "expected_data_type": "number",
                    "current_value": None,
                    "is_empty": True
                }
            ]
            
            request = AgentRequest(
                request_id="real_task_supplement",
                workflow_type=WorkflowType.TASK_SUPPLEMENT,
                parameters={
                    "template_id": template["id"],
                    "placeholders": placeholders,
                    "task_context": {
                        "task_id": f"supplement_{template['id']}",
                        "task_name": f"补充{template['name']}模板",
                        "task_description": template["description"],
                        "business_domain": "template_management",
                        "report_type": template["template_type"]
                    },
                    "data_source_context": {
                        "source_id": data_source["id"],
                        "source_type": data_source["source_type"],
                        "database_name": "default_db",
                        "available_tables": ["templates", "users", "data_sources"],
                        "table_schemas": {
                            "templates": [
                                {"name": "id", "type": "uuid", "comment": "模板ID"},
                                {"name": "name", "type": "varchar", "comment": "模板名称"}
                            ]
                        },
                        "connection_info": {"host": "localhost", "port": 9030}
                    }
                }
            )
            
            response = await agent.execute_request(request)
            
            self.test_results["real_task_supplement"] = {
                "success": response.status.value == "completed",
                "status": response.status.value,
                "execution_time": response.execution_time_seconds,
                "template_id": template["id"],
                "template_name": template["name"],
                "processed_placeholders": len(placeholders),
                "result_summary": response.result if response.result else {}
            }
            
            if response.status.value == "completed":
                logger.info(f"✅ 任务补充机制成功")
                logger.info(f"   处理模板: {template['name']}")
                logger.info(f"   处理占位符数: {len(placeholders)}")
            else:
                logger.warning(f"⚠️ 任务补充机制部分成功: {response.error_message}")
                
        except Exception as e:
            logger.error(f"❌ 任务补充机制测试失败: {e}")
            self.test_results["real_task_supplement"] = {
                "success": False,
                "error": str(e)
            }
    
    async def test_real_context_integration(self, agent, real_config):
        """测试真实的多上下文集成"""
        logger.info("🧠 测试核心功能3：多上下文集成")
        
        try:
            contexts = [
                {
                    "context_id": "real_data_source",
                    "context_type": "data_source",
                    "priority": "critical",
                    "content": {
                        "data_sources": real_config["data_sources"],
                        "total_sources": len(real_config["data_sources"]),
                        "primary_source": real_config["data_sources"][0]["name"]
                    }
                },
                {
                    "context_id": "real_user",
                    "context_type": "user",
                    "priority": "high",
                    "content": {
                        "user_id": real_config["user"]["id"],
                        "username": real_config["user"]["username"],
                        "has_llm_config": real_config["llm_server"]["has_api_key"]
                    }
                },
                {
                    "context_id": "real_templates",
                    "context_type": "business",
                    "priority": "medium",
                    "content": {
                        "templates": real_config["templates"],
                        "template_count": len(real_config["templates"])
                    }
                }
            ]
            
            request = AgentRequest(
                request_id="real_context_integration",
                workflow_type=WorkflowType.MULTI_CONTEXT_INTEGRATION,
                parameters={
                    "contexts": contexts,
                    "target_task": f"为用户{real_config['user']['username']}进行数据分析任务的上下文集成",
                    "required_context_types": ["data_source", "user"],
                    "custom_weights": {
                        "data_source": 0.4,
                        "user": 0.3,
                        "business": 0.3
                    }
                }
            )
            
            response = await agent.execute_request(request)
            
            self.test_results["real_context_integration"] = {
                "success": response.status.value == "completed",
                "status": response.status.value,
                "execution_time": response.execution_time_seconds,
                "contexts_processed": len(contexts),
                "integration_confidence": response.result.get("integration_confidence", 0.0) if response.result else 0.0,
                "used_contexts": response.result.get("used_contexts", []) if response.result else []
            }
            
            if response.status.value == "completed":
                logger.info(f"✅ 多上下文集成成功")
                logger.info(f"   集成信心度: {self.test_results['real_context_integration']['integration_confidence']:.2f}")
                logger.info(f"   使用的上下文: {len(self.test_results['real_context_integration']['used_contexts'])}")
            else:
                logger.warning(f"⚠️ 多上下文集成部分成功: {response.error_message}")
                
        except Exception as e:
            logger.error(f"❌ 多上下文集成测试失败: {e}")
            self.test_results["real_context_integration"] = {
                "success": False,
                "error": str(e)
            }
    
    async def test_complete_pipeline(self, agent, real_config):
        """测试完整流水线"""
        logger.info("🏭 测试完整流水线集成")
        
        try:
            # 构建完整的流水线配置
            pipeline_config = {
                "enable_context_integration": True,
                "enable_task_supplement": True,
                "enable_placeholder_sql": True,
                "enable_sql_testing": True,
                "enable_chart_generation": False,  # 图表生成可能需要额外依赖
                
                # 上下文集成参数
                "context_integration_params": {
                    "contexts": [
                        {
                            "context_id": "pipeline_user",
                            "context_type": "user",
                            "priority": "critical",
                            "content": real_config["user"]
                        },
                        {
                            "context_id": "pipeline_data_source",
                            "context_type": "data_source",
                            "priority": "critical",
                            "content": real_config["data_sources"][0]
                        }
                    ],
                    "target_task": f"完整流水线测试 - 用户{real_config['user']['username']}的数据分析",
                    "required_context_types": ["user", "data_source"]
                },
                
                # 占位符SQL参数
                "placeholder_sql_params": {
                    "placeholder_name": "pipeline_test_metric",
                    "placeholder_description": f"流水线测试：基于{real_config['data_sources'][0]['name']}的核心指标",
                    "placeholder_type": "metric",
                    "expected_data_type": "number",
                    "task_context": {
                        "task_id": "pipeline_test",
                        "task_name": "完整流水线测试",
                        "task_description": "测试完整的Agent流水线功能",
                        "business_domain": "system_test",
                        "report_type": "dashboard"
                    },
                    "data_source_context": {
                        "source_id": real_config["data_sources"][0]["id"],
                        "source_type": real_config["data_sources"][0]["source_type"],
                        "database_name": "test_db",
                        "available_tables": ["users", "metrics", "analytics"],
                        "table_schemas": {
                            "users": [{"name": "id", "type": "bigint", "comment": "ID"}],
                            "metrics": [{"name": "value", "type": "decimal", "comment": "指标值"}]
                        },
                        "connection_info": {"host": "localhost", "port": 9030}
                    }
                },
                
                # SQL测试参数
                "sql_testing_params": {
                    "data_source_context": {
                        "source_id": real_config["data_sources"][0]["id"],
                        "source_type": real_config["data_sources"][0]["source_type"],
                        "available_tables": ["users", "metrics"],
                        "table_schemas": {}
                    },
                    "validation_level": "standard"
                }
            }
            
            request = AgentRequest(
                request_id="complete_pipeline_test",
                workflow_type=WorkflowType.FULL_PIPELINE,
                parameters=pipeline_config
            )
            
            response = await agent.execute_request(request)
            
            pipeline_results = response.result.get("pipeline_results", {}) if response.result else {}
            
            self.test_results["complete_pipeline"] = {
                "success": response.status.value == "completed",
                "status": response.status.value,
                "execution_time": response.execution_time_seconds,
                "steps_completed": response.result.get("steps_completed", 0) if response.result else 0,
                "overall_confidence": response.result.get("overall_confidence", 0.0) if response.result else 0.0,
                "pipeline_steps": list(pipeline_results.keys()),
                "context_integration_success": "context_integration" in pipeline_results,
                "placeholder_sql_success": "placeholder_to_sql" in pipeline_results,
                "sql_testing_success": "sql_testing" in pipeline_results
            }
            
            if response.status.value == "completed":
                logger.info(f"✅ 完整流水线测试成功")
                logger.info(f"   完成步骤数: {self.test_results['complete_pipeline']['steps_completed']}")
                logger.info(f"   总体信心度: {self.test_results['complete_pipeline']['overall_confidence']:.2f}")
                logger.info(f"   执行的步骤: {', '.join(self.test_results['complete_pipeline']['pipeline_steps'])}")
            else:
                logger.warning(f"⚠️ 完整流水线部分成功: {response.error_message}")
                
        except Exception as e:
            logger.error(f"❌ 完整流水线测试失败: {e}")
            self.test_results["complete_pipeline"] = {
                "success": False,
                "error": str(e)
            }
    
    def generate_complete_test_report(self):
        """生成完整测试报告"""
        logger.info("📊 === 完整真实环境测试报告 ===")
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results.values() if result.get("success", False))
        
        logger.info(f"📈 总体结果:")
        logger.info(f"   总测试数: {total_tests}")
        logger.info(f"   成功测试数: {successful_tests}")
        logger.info(f"   成功率: {successful_tests/total_tests:.2%}")
        logger.info("")
        
        logger.info(f"🔍 详细结果:")
        test_emojis = {
            "real_placeholder_to_sql": "🔧",
            "real_task_supplement": "🔄", 
            "real_context_integration": "🧠",
            "complete_pipeline": "🏭"
        }
        
        for test_name, result in self.test_results.items():
            emoji = test_emojis.get(test_name, "🧪")
            status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
            logger.info(f"   {emoji} {test_name}: {status}")
            
            # 显示关键指标
            if result.get("success", False):
                if "confidence_score" in result:
                    logger.info(f"      信心度: {result['confidence_score']:.2f}")
                if "execution_time" in result:
                    logger.info(f"      执行时间: {result['execution_time']:.3f}s")
                if "steps_completed" in result:
                    logger.info(f"      完成步骤: {result['steps_completed']}")
            else:
                if result.get("error"):
                    logger.info(f"      错误: {result['error']}")
        
        # 保存详细报告
        report_file = f"complete_real_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                "test_summary": {
                    "total_tests": total_tests,
                    "successful_tests": successful_tests,
                    "success_rate": successful_tests/total_tests,
                    "test_time": datetime.now().isoformat(),
                    "environment": "complete_real_venv_docker_llm"
                },
                "detailed_results": self.test_results
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📄 详细测试报告已保存到: {report_file}")


async def main():
    """主测试函数"""
    try:
        tester = CompleteRealAgentTester()
        await tester.run_complete_test()
    except Exception as e:
        logger.error(f"主测试函数异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 设置数据库连接
    os.environ["DATABASE_URL"] = "postgresql://postgres:postgres123@localhost:5432/autoreport"
    
    # 运行完整测试
    asyncio.run(main())