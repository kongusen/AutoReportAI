"""
AutoReportAI Agent 真实数据测试脚本

测试内容：
1. 占位符→SQL转换功能测试
2. 任务补充机制测试
3. 图表生成测试
4. SQL测试验证流程
5. 多上下文集成测试
6. 完整流水线测试

使用真实的Doris数据源和模板数据进行端到端测试
"""

import asyncio
import sys
import os
import logging
from datetime import datetime, timedelta
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
        logging.FileHandler('agent_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 导入Agent系统
from app.services.infrastructure.ai.agents.autoreport_ai_agent import (
    create_autoreport_ai_agent,
    AgentRequest,
    WorkflowType,
    process_placeholder_to_sql,
    supplement_placeholders,
    run_full_pipeline
)
from app.services.infrastructure.ai.agents.multi_context_integrator import (
    ContextType,
    ContextPriority
)

# 测试数据
TEST_USER_ID = "test_user_001"

# 真实的Doris数据源配置
DORIS_DATA_SOURCE = {
    "source_id": "doris_test_001",
    "source_type": "doris",
    "database_name": "test_db",
    "available_tables": [
        "user_behavior",
        "sales_order",
        "product_info",
        "user_profile"
    ],
    "table_schemas": {
        "user_behavior": [
            {"name": "user_id", "type": "bigint", "comment": "用户ID"},
            {"name": "event_time", "type": "datetime", "comment": "事件时间"},
            {"name": "event_type", "type": "varchar(50)", "comment": "事件类型"},
            {"name": "page_path", "type": "varchar(500)", "comment": "页面路径"},
            {"name": "session_id", "type": "varchar(100)", "comment": "会话ID"}
        ],
        "sales_order": [
            {"name": "order_id", "type": "bigint", "comment": "订单ID"},
            {"name": "user_id", "type": "bigint", "comment": "用户ID"},
            {"name": "order_time", "type": "datetime", "comment": "订单时间"},
            {"name": "amount", "type": "decimal(10,2)", "comment": "订单金额"},
            {"name": "status", "type": "varchar(20)", "comment": "订单状态"},
            {"name": "product_id", "type": "bigint", "comment": "商品ID"}
        ],
        "product_info": [
            {"name": "product_id", "type": "bigint", "comment": "商品ID"},
            {"name": "product_name", "type": "varchar(200)", "comment": "商品名称"},
            {"name": "category", "type": "varchar(100)", "comment": "商品分类"},
            {"name": "price", "type": "decimal(10,2)", "comment": "商品价格"}
        ],
        "user_profile": [
            {"name": "user_id", "type": "bigint", "comment": "用户ID"},
            {"name": "age", "type": "int", "comment": "年龄"},
            {"name": "gender", "type": "varchar(10)", "comment": "性别"},
            {"name": "city", "type": "varchar(50)", "comment": "城市"},
            {"name": "registration_time", "type": "datetime", "comment": "注册时间"}
        ]
    },
    "connection_info": {
        "host": "localhost",
        "port": 9030,
        "username": "root",
        "password": "password"
    }
}

# 测试任务上下文
TASK_CONTEXT = {
    "task_id": "task_001", 
    "task_name": "销售数据分析报告",
    "task_description": "分析最近30天的销售数据，包括销售额趋势、用户行为分析和商品分类统计",
    "business_domain": "sales",
    "report_type": "dashboard",
    "priority": "high"
}

# 测试占位符
TEST_PLACEHOLDERS = [
    {
        "placeholder_name": "total_sales_amount",
        "placeholder_description": "最近30天的总销售额",
        "placeholder_type": "metric",
        "expected_data_type": "number",
        "current_value": None,
        "is_empty": True
    },
    {
        "placeholder_name": "daily_sales_trend",
        "placeholder_description": "每日销售额趋势数据",
        "placeholder_type": "metric",
        "expected_data_type": "list",
        "current_value": None,
        "is_empty": True
    },
    {
        "placeholder_name": "top_products",
        "placeholder_description": "销售额排名前10的商品",
        "placeholder_type": "dimension",
        "expected_data_type": "list",
        "current_value": None,
        "is_empty": True
    },
    {
        "placeholder_name": "user_age_distribution",
        "placeholder_description": "用户年龄分布统计",
        "placeholder_type": "chart",
        "expected_data_type": "list",
        "current_value": None,
        "is_empty": True
    }
]


class AutoReportAIAgentTester:
    """AutoReportAI Agent测试类"""
    
    def __init__(self):
        self.agent = create_autoreport_ai_agent(TEST_USER_ID)
        self.test_results = {}
        
    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("开始AutoReportAI Agent系统测试")
        
        try:
            # 测试1: 占位符→SQL转换
            await self.test_placeholder_to_sql_conversion()
            
            # 测试2: 任务补充机制
            await self.test_task_supplement_mechanism()
            
            # 测试3: SQL测试验证
            await self.test_sql_validation()
            
            # 测试4: 多上下文集成
            await self.test_multi_context_integration()
            
            # 测试5: 完整流水线
            await self.test_full_pipeline()
            
            # 测试6: Agent统计和健康检查
            await self.test_agent_statistics()
            
            # 输出测试报告
            self.generate_test_report()
            
        except Exception as e:
            logger.error(f"测试执行失败: {e}")
        
        logger.info("AutoReportAI Agent系统测试完成")
    
    async def test_placeholder_to_sql_conversion(self):
        """测试占位符→SQL转换功能"""
        logger.info("=== 测试1: 占位符→SQL转换功能 ===")
        
        test_results = []
        
        for placeholder in TEST_PLACEHOLDERS:
            try:
                logger.info(f"测试占位符: {placeholder['placeholder_name']}")
                
                # 使用便捷函数进行转换
                result = await process_placeholder_to_sql(
                    user_id=TEST_USER_ID,
                    placeholder_name=placeholder["placeholder_name"],
                    placeholder_description=placeholder["placeholder_description"],
                    task_context=TASK_CONTEXT,
                    data_source_context=DORIS_DATA_SOURCE,
                    placeholder_type=placeholder["placeholder_type"],
                    expected_data_type=placeholder["expected_data_type"]
                )
                
                test_results.append({
                    "placeholder_name": placeholder["placeholder_name"],
                    "success": True,
                    "sql_query": result.get("sql_query", ""),
                    "confidence_score": result.get("confidence_score", 0.0),
                    "explanation": result.get("explanation", ""),
                    "used_tables": result.get("used_tables", []),
                    "correction_attempts": result.get("correction_attempts", 0)
                })
                
                logger.info(f"✅ {placeholder['placeholder_name']} 转换成功，信心度: {result.get('confidence_score', 0.0):.2f}")
                
            except Exception as e:
                logger.error(f"❌ {placeholder['placeholder_name']} 转换失败: {e}")
                test_results.append({
                    "placeholder_name": placeholder["placeholder_name"],
                    "success": False,
                    "error": str(e)
                })
        
        self.test_results["placeholder_to_sql"] = {
            "total_tests": len(TEST_PLACEHOLDERS),
            "successful_tests": sum(1 for r in test_results if r["success"]),
            "results": test_results
        }
        
        success_rate = self.test_results["placeholder_to_sql"]["successful_tests"] / len(TEST_PLACEHOLDERS)
        logger.info(f"占位符→SQL转换测试完成，成功率: {success_rate:.2%}")
    
    async def test_task_supplement_mechanism(self):
        """测试任务补充机制"""
        logger.info("=== 测试2: 任务补充机制 ===")
        
        try:
            # 使用便捷函数进行补充
            result = await supplement_placeholders(
                user_id=TEST_USER_ID,
                template_id="template_001",
                placeholders=TEST_PLACEHOLDERS,
                task_context=TASK_CONTEXT,
                data_source_context=DORIS_DATA_SOURCE
            )
            
            self.test_results["task_supplement"] = {
                "success": True,
                "total_requests": result.get("total_requests", 0),
                "successful_supplements": result.get("successful_supplements", 0),
                "failed_supplements": result.get("failed_supplements", 0),
                "overall_confidence": result.get("overall_confidence", 0.0),
                "processing_time": result.get("processing_time_seconds", 0.0)
            }
            
            logger.info(f"✅ 任务补充测试成功: {result.get('successful_supplements', 0)}/{result.get('total_requests', 0)}")
            
        except Exception as e:
            logger.error(f"❌ 任务补充测试失败: {e}")
            self.test_results["task_supplement"] = {
                "success": False,
                "error": str(e)
            }
    
    async def test_sql_validation(self):
        """测试SQL验证功能"""
        logger.info("=== 测试3: SQL测试验证流程 ===")
        
        # 测试SQL查询
        test_sql = """
        SELECT 
            DATE(order_time) as order_date,
            SUM(amount) as daily_sales,
            COUNT(DISTINCT user_id) as unique_users
        FROM sales_order 
        WHERE order_time >= '2024-01-01'
            AND order_time < '2024-02-01'
            AND status = 'completed'
        GROUP BY DATE(order_time)
        ORDER BY order_date
        """
        
        try:
            request = AgentRequest(
                request_id="sql_validation_test",
                workflow_type=WorkflowType.SQL_TESTING,
                parameters={
                    "sql_query": test_sql,
                    "data_source_context": DORIS_DATA_SOURCE,
                    "validation_level": "comprehensive"
                }
            )
            
            response = await self.agent.execute_request(request)
            
            if response.status.value == "completed":
                result = response.result
                self.test_results["sql_validation"] = {
                    "success": True,
                    "validation_status": result.get("status", "unknown"),
                    "errors_count": len(result.get("errors", [])),
                    "warnings_count": len(result.get("warnings", [])),
                    "corrected_sql": result.get("corrected_sql"),
                    "correction_attempts": result.get("correction_attempts", 0),
                    "confidence_score": result.get("confidence_score", 0.0)
                }
                
                logger.info(f"✅ SQL验证测试成功，状态: {result.get('status', 'unknown')}")
                
            else:
                raise Exception(f"SQL验证失败: {response.error_message}")
                
        except Exception as e:
            logger.error(f"❌ SQL验证测试失败: {e}")
            self.test_results["sql_validation"] = {
                "success": False,
                "error": str(e)
            }
    
    async def test_multi_context_integration(self):
        """测试多上下文集成"""
        logger.info("=== 测试4: 多上下文集成系统 ===")
        
        try:
            # 准备多个上下文
            contexts = [
                {
                    "context_id": "data_source_ctx",
                    "context_type": "data_source",
                    "priority": "critical",
                    "content": DORIS_DATA_SOURCE
                },
                {
                    "context_id": "task_ctx", 
                    "context_type": "task",
                    "priority": "high",
                    "content": TASK_CONTEXT
                },
                {
                    "context_id": "time_ctx",
                    "context_type": "time",
                    "priority": "medium",
                    "content": {
                        "report_start_date": "2024-01-01",
                        "report_end_date": "2024-01-31",
                        "time_granularity": "day"
                    }
                },
                {
                    "context_id": "business_ctx",
                    "context_type": "business",
                    "priority": "medium",
                    "content": {
                        "business_rules": ["只统计已完成订单", "排除测试用户数据"],
                        "kpi_targets": {"monthly_sales": 1000000, "user_retention": 0.8}
                    }
                }
            ]
            
            request = AgentRequest(
                request_id="context_integration_test",
                workflow_type=WorkflowType.MULTI_CONTEXT_INTEGRATION,
                parameters={
                    "contexts": contexts,
                    "target_task": "生成销售数据分析报告",
                    "required_context_types": ["data_source", "task"],
                    "custom_weights": {
                        "data_source": 0.4,
                        "task": 0.3,
                        "time": 0.2,
                        "business": 0.1
                    }
                }
            )
            
            response = await self.agent.execute_request(request)
            
            if response.status.value == "completed":
                result = response.result
                self.test_results["multi_context"] = {
                    "success": True,
                    "integration_confidence": result.get("integration_confidence", 0.0),
                    "used_contexts": result.get("used_contexts", []),
                    "context_weights": result.get("context_weights", {}),
                    "processing_time": result.get("processing_time_seconds", 0.0),
                    "warnings_count": len(result.get("warnings", []))
                }
                
                logger.info(f"✅ 多上下文集成测试成功，信心度: {result.get('integration_confidence', 0.0):.2f}")
                
            else:
                raise Exception(f"多上下文集成失败: {response.error_message}")
                
        except Exception as e:
            logger.error(f"❌ 多上下文集成测试失败: {e}")
            self.test_results["multi_context"] = {
                "success": False,
                "error": str(e)
            }
    
    async def test_full_pipeline(self):
        """测试完整流水线"""
        logger.info("=== 测试5: 完整流水线测试 ===")
        
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
                            "context_id": "pipeline_data_source",
                            "context_type": "data_source",
                            "priority": "critical",
                            "content": DORIS_DATA_SOURCE
                        },
                        {
                            "context_id": "pipeline_task",
                            "context_type": "task", 
                            "priority": "high",
                            "content": TASK_CONTEXT
                        }
                    ],
                    "target_task": "完整流水线测试",
                    "required_context_types": ["data_source", "task"]
                },
                
                # 任务补充参数
                "task_supplement_params": {
                    "template_id": "pipeline_template",
                    "placeholders": TEST_PLACEHOLDERS[:2],  # 只测试前两个占位符
                    "task_context": TASK_CONTEXT,
                    "data_source_context": DORIS_DATA_SOURCE,
                    "max_concurrent": 2
                },
                
                # 占位符SQL参数
                "placeholder_sql_params": {
                    "placeholder_name": "pipeline_test_metric",
                    "placeholder_description": "流水线测试指标：最近7天的订单总数",
                    "placeholder_type": "metric",
                    "expected_data_type": "number",
                    "task_context": TASK_CONTEXT,
                    "data_source_context": DORIS_DATA_SOURCE
                },
                
                # SQL测试参数
                "sql_testing_params": {
                    "data_source_context": DORIS_DATA_SOURCE,
                    "validation_level": "standard"
                }
            }
            
            # 使用便捷函数执行完整流水线
            result = await run_full_pipeline(
                user_id=TEST_USER_ID,
                pipeline_config=pipeline_config
            )
            
            self.test_results["full_pipeline"] = {
                "success": True,
                "steps_completed": result.get("steps_completed", 0),
                "overall_confidence": result.get("overall_confidence", 0.0),
                "pipeline_results": result.get("pipeline_results", {})
            }
            
            logger.info(f"✅ 完整流水线测试成功，步骤完成: {result.get('steps_completed', 0)}, 信心度: {result.get('overall_confidence', 0.0):.2f}")
            
        except Exception as e:
            logger.error(f"❌ 完整流水线测试失败: {e}")
            self.test_results["full_pipeline"] = {
                "success": False,
                "error": str(e)
            }
    
    async def test_agent_statistics(self):
        """测试Agent统计和健康检查"""
        logger.info("=== 测试6: Agent统计和健康检查 ===")
        
        try:
            # 获取统计信息
            stats = self.agent.get_agent_statistics()
            
            # 健康检查
            health = await self.agent.health_check()
            
            self.test_results["agent_statistics"] = {
                "success": True,
                "total_requests": stats["execution_statistics"]["total_requests"],
                "success_rate": stats["execution_statistics"]["success_rate"],
                "average_execution_time": stats["performance_metrics"]["average_execution_time"],
                "average_confidence": stats["performance_metrics"]["average_confidence_score"],
                "health_status": health["status"]
            }
            
            logger.info(f"✅ Agent统计测试成功，健康状态: {health['status']}")
            logger.info(f"   总请求数: {stats['execution_statistics']['total_requests']}")
            logger.info(f"   成功率: {stats['execution_statistics']['success_rate']:.2%}")
            
        except Exception as e:
            logger.error(f"❌ Agent统计测试失败: {e}")
            self.test_results["agent_statistics"] = {
                "success": False,
                "error": str(e)
            }
    
    def generate_test_report(self):
        """生成测试报告"""
        logger.info("=== 测试报告 ===")
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results.values() if result.get("success", False))
        
        logger.info(f"总测试数: {total_tests}")
        logger.info(f"成功测试数: {successful_tests}")
        logger.info(f"总体成功率: {successful_tests/total_tests:.2%}")
        
        # 详细结果
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
            logger.info(f"{test_name}: {status}")
            
            if not result.get("success", False) and result.get("error"):
                logger.info(f"  错误信息: {result['error']}")
        
        # 保存详细报告到文件
        report_file = f"agent_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                "test_summary": {
                    "total_tests": total_tests,
                    "successful_tests": successful_tests,
                    "success_rate": successful_tests/total_tests,
                    "test_time": datetime.now().isoformat()
                },
                "detailed_results": self.test_results
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"详细测试报告已保存到: {report_file}")


async def main():
    """主测试函数"""
    try:
        tester = AutoReportAIAgentTester()
        await tester.run_all_tests()
    except Exception as e:
        logger.error(f"测试主函数异常: {e}")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())