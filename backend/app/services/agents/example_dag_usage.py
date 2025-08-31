"""
DAG编排架构使用示例
展示如何使用Background Controller和Execution Engine处理placeholder任务
"""

import asyncio
import logging
from typing import Dict, Any

# 导入DAG编排组件
from .core.placeholder_task_context import (
    PlaceholderTaskContext,
    create_task_context_from_placeholder_analysis
)
from .core.background_controller import BackgroundController
from .core.execution_engine import ExecutionEngine

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_placeholder_processing():
    """
    示例：完整的占位符处理流程
    演示从placeholder上下文工程分析结果到最终结果的完整DAG流程
    """
    
    print("=" * 60)
    print("DAG编排架构 - 占位符处理示例")
    print("=" * 60)
    
    # 1. 模拟来自placeholder上下文工程的分析结果
    context_analysis = {
        "confidence_score": 0.75,
        "processing_time_ms": 150,
        "integrated_context": {
            "placeholder_type": "统计",
            "description": "Q1销售额统计",
            "business_dimension": {
                "domain": "sales",
                "entities": ["销售额", "Q1"],
                "rules": ["按季度统计", "包含所有部门"]
            },
            "time_dimension": {
                "detected_periods": ["Q1"],
                "granularity": "quarterly",
                "confidence": 0.8
            },
            "data_dimension": {
                "sources": ["sales_table", "department_table"],
                "fields": ["amount", "date", "department"],
                "quality_requirements": "high"
            },
            "semantic_dimension": {
                "keywords": ["销售额", "统计", "季度"],
                "concepts": ["财务指标", "时间维度", "汇总分析"]
            },
            "constraints": {
                "data_constraints": ["date >= '2024-01-01'", "date < '2024-04-01'"],
                "business_constraints": ["只包含已确认订单"],
                "temporal_constraints": ["Q1时间范围"],
                "quality_constraints": ["数据完整性检查"]
            }
        }
    }
    
    # 2. 创建占位符任务上下文
    print("\n1. 创建占位符任务上下文...")
    task_context = create_task_context_from_placeholder_analysis(
        placeholder_text="{{统计：Q1销售额}}",
        statistical_type="统计",
        description="Q1销售额统计",
        context_analysis=context_analysis,
        user_id="demo_user"
    )
    
    print(f"   任务ID: {task_context.task_id}")
    print(f"   复杂度: {task_context.complexity.value}")
    print(f"   置信度: {task_context.confidence_score}")
    print(f"   计划步骤数: {len(task_context.execution_steps)}")
    
    # 3. 显示执行计划
    print("\n2. DAG执行计划:")
    for i, step in enumerate(task_context.execution_steps):
        dependencies = f" (依赖: {', '.join(step.dependencies)})" if step.dependencies else ""
        print(f"   步骤 {i+1}: {step.step_type.value} [{step.model_requirement.value}]{dependencies}")
    
    # 4. 创建执行引擎
    print("\n3. 初始化执行引擎...")
    execution_engine = ExecutionEngine()
    
    # 注册模拟的Think和Default模型
    think_model = MockThinkModel()
    default_model = MockDefaultModel()
    execution_engine.register_models(think_model, default_model)
    
    # 注册模拟工具
    tools_registry = {
        "placeholder_parser": MockPlaceholderParser(),
        "context_analyzer": MockContextAnalyzer(),
        "sql_generator": MockSQLGenerator(),
        "schema_analyzer": MockSchemaAnalyzer(),
        "data_executor": MockDataExecutor(),
        "business_processor": MockBusinessProcessor(),
        "calculator": MockCalculator(),
        "result_validator": MockResultValidator(),
        "formatter": MockFormatter()
    }
    execution_engine.register_tools(tools_registry)
    
    # 5. 执行占位符任务
    print("\n4. 开始DAG执行流程...")
    print("-" * 40)
    
    result = await execution_engine.execute_placeholder_task(task_context)
    
    print("-" * 40)
    print("5. 执行结果:")
    print(f"   状态: {result['status']}")
    print(f"   执行时间: {result['execution_time']:.2f}秒")
    print(f"   步骤数: {result['steps_executed']}")
    print(f"   最终结果: {result.get('result', 'N/A')}")
    
    # 6. 显示执行历史
    if result.get('execution_history'):
        print("\n6. 执行决策历史:")
        for i, decision in enumerate(result['execution_history']):
            print(f"   决策 {i+1}: {decision['decision']} (置信度: {decision.get('quality_assessment', {}).get('confidence_level', 'unknown')})")
    
    # 7. 显示性能指标
    if result.get('performance_metrics'):
        print("\n7. 性能指标:")
        for metric, value in result['performance_metrics'].items():
            print(f"   {metric}: {value}")
    
    print("\n" + "=" * 60)
    print("示例执行完成")
    print("=" * 60)
    
    return result


# 模拟模型类
class MockThinkModel:
    """模拟Think模型 - 复杂推理"""
    
    async def achat(self, messages):
        # 模拟复杂推理处理
        await asyncio.sleep(0.1)  # 模拟思考时间
        
        content = messages[0].content if messages else ""
        
        if "SQL生成" in content:
            result = """
            SELECT 
                SUM(amount) as total_sales
            FROM sales_table s
            JOIN department_table d ON s.dept_id = d.id
            WHERE s.date >= '2024-01-01' 
                AND s.date < '2024-04-01'
                AND s.status = 'confirmed'
            """
        elif "业务逻辑" in content:
            result = "应用业务规则：只包含已确认订单，按季度汇总，所有部门参与"
        elif "验证" in content:
            result = "数据验证通过：格式正确，业务逻辑合理，结果可信"
        else:
            result = f"Think模型复杂推理结果: {content[:50]}..."
        
        return MockChatResponse(result)


class MockDefaultModel:
    """模拟Default模型 - 快速处理"""
    
    async def achat(self, messages):
        # 模拟快速处理
        await asyncio.sleep(0.05)  # 模拟快速响应
        
        content = messages[0].content if messages else ""
        
        if "解析" in content:
            result = "占位符解析结果: 统计类型=统计, 描述=Q1销售额"
        elif "格式化" in content:
            result = "1,250,000.00"  # 格式化的销售额
        elif "数据查询" in content:
            result = "查询执行完成，返回数据: 1250000.00"
        else:
            result = f"Default模型快速处理结果: {content[:50]}..."
        
        return MockChatResponse(result)


class MockChatResponse:
    """模拟聊天响应"""
    def __init__(self, content):
        self.message = MockMessage(content)


class MockMessage:
    """模拟消息"""
    def __init__(self, content):
        self.content = content


# 模拟工具类
class MockPlaceholderParser:
    async def execute(self, input_data):
        return {
            "type": "统计",
            "description": "Q1销售额",
            "parameters": {"time_range": "Q1"}
        }


class MockContextAnalyzer:
    async def execute(self, input_data):
        return {
            "enhanced_analysis": "增强的上下文理解",
            "confidence": 0.85
        }


class MockSQLGenerator:
    async def execute(self, input_data):
        return {
            "sql": "SELECT SUM(amount) FROM sales WHERE date BETWEEN '2024-01-01' AND '2024-03-31'",
            "complexity": "medium"
        }


class MockSchemaAnalyzer:
    async def execute(self, input_data):
        return {
            "tables": ["sales_table", "department_table"],
            "relationships": ["sales.dept_id = department.id"]
        }


class MockDataExecutor:
    async def execute(self, input_data):
        return {
            "data": [{"total_sales": 1250000.00}],
            "row_count": 1
        }


class MockBusinessProcessor:
    async def execute(self, input_data):
        return {
            "processed_data": 1250000.00,
            "business_rules_applied": ["confirmed_orders_only", "quarterly_aggregation"]
        }


class MockCalculator:
    async def execute(self, input_data):
        return {
            "result": 1250000.00,
            "calculation_type": "sum"
        }


class MockResultValidator:
    async def execute(self, input_data):
        return {
            "is_valid": True,
            "confidence": 0.9,
            "quality_score": 0.85
        }


class MockFormatter:
    async def execute(self, input_data):
        return "1,250,000.00"


# 图表生成工具Mock类（六种统计图）
class MockChartGenerator:
    """Mock图表生成器 - 支持六种统计图"""
    
    async def generate_bar_chart(self, data, config):
        """生成柱状图"""
        return {
            "success": True,
            "chart_type": "bar_chart",
            "chart_name": "柱状图",
            "echarts_config": {
                "title": {"text": config.get("title", "柱状图")},
                "xAxis": {"type": "category", "data": ["类别1", "类别2", "类别3"]},
                "yAxis": {"type": "value"},
                "series": [{"data": [120, 200, 150], "type": "bar"}]
            },
            "generation_info": {"tool": "mock_chart_generator", "complexity": "simple"}
        }
    
    async def generate_pie_chart(self, data, config):
        """生成饼图"""
        return {
            "success": True,
            "chart_type": "pie_chart", 
            "chart_name": "饼图",
            "echarts_config": {
                "title": {"text": config.get("title", "饼图")},
                "series": [{
                    "type": "pie",
                    "data": [
                        {"value": 335, "name": "直接访问"},
                        {"value": 310, "name": "邮件营销"}, 
                        {"value": 234, "name": "联盟广告"}
                    ]
                }]
            },
            "generation_info": {"tool": "mock_chart_generator", "complexity": "simple"}
        }
    
    async def generate_line_chart(self, data, config):
        """生成折线图"""
        return {
            "success": True,
            "chart_type": "line_chart",
            "chart_name": "折线图", 
            "echarts_config": {
                "title": {"text": config.get("title", "折线图")},
                "xAxis": {"type": "category", "data": ["1月", "2月", "3月", "4月", "5月"]},
                "yAxis": {"type": "value"},
                "series": [{"data": [820, 932, 901, 934, 1290], "type": "line"}]
            },
            "generation_info": {"tool": "mock_chart_generator", "complexity": "medium"}
        }
    
    async def generate_scatter_chart(self, data, config):
        """生成散点图"""
        return {
            "success": True,
            "chart_type": "scatter_chart",
            "chart_name": "散点图",
            "echarts_config": {
                "title": {"text": config.get("title", "散点图")},
                "xAxis": {"type": "value"},
                "yAxis": {"type": "value"},
                "series": [{
                    "type": "scatter",
                    "data": [[10, 20], [15, 25], [20, 30], [25, 35], [30, 40]]
                }]
            },
            "generation_info": {"tool": "mock_chart_generator", "complexity": "medium"}
        }
    
    async def generate_radar_chart(self, data, config):
        """生成雷达图"""
        return {
            "success": True,
            "chart_type": "radar_chart",
            "chart_name": "雷达图",
            "echarts_config": {
                "title": {"text": config.get("title", "雷达图")},
                "radar": {
                    "indicator": [
                        {"name": "销售", "max": 6500},
                        {"name": "管理", "max": 16000}, 
                        {"name": "信息技术", "max": 30000},
                        {"name": "客服", "max": 38000},
                        {"name": "研发", "max": 52000},
                        {"name": "市场", "max": 25000}
                    ]
                },
                "series": [{
                    "type": "radar",
                    "data": [{"value": [4300, 10000, 28000, 35000, 50000, 19000]}]
                }]
            },
            "generation_info": {"tool": "mock_chart_generator", "complexity": "complex"}
        }
    
    async def generate_funnel_chart(self, data, config):
        """生成漏斗图"""
        return {
            "success": True,
            "chart_type": "funnel_chart",
            "chart_name": "漏斗图",
            "echarts_config": {
                "title": {"text": config.get("title", "漏斗图")},
                "series": [{
                    "type": "funnel",
                    "data": [
                        {"value": 100, "name": "访问"},
                        {"value": 80, "name": "咨询"},
                        {"value": 60, "name": "订单"},
                        {"value": 40, "name": "点击"},
                        {"value": 20, "name": "成交"}
                    ]
                }]
            },
            "generation_info": {"tool": "mock_chart_generator", "complexity": "medium"}
        }
    
    async def execute(self, task_type, input_data):
        """通用执行接口"""
        config = input_data.get("config", {})
        data = input_data.get("data", [])
        
        if task_type == "bar_chart":
            return await self.generate_bar_chart(data, config)
        elif task_type == "pie_chart":
            return await self.generate_pie_chart(data, config)
        elif task_type == "line_chart":
            return await self.generate_line_chart(data, config)
        elif task_type == "scatter_chart":
            return await self.generate_scatter_chart(data, config)
        elif task_type == "radar_chart":
            return await self.generate_radar_chart(data, config)
        elif task_type == "funnel_chart":
            return await self.generate_funnel_chart(data, config)
        else:
            return {
                "success": False,
                "error": f"不支持的图表类型: {task_type}"
            }


class MockDataAnalyzer:
    """Mock数据分析器"""
    async def execute(self, input_data):
        return {
            "analysis_type": "descriptive",
            "data_summary": {
                "total_records": 1000,
                "columns": ["name", "value", "category"],
                "data_quality": 0.95
            },
            "recommended_charts": ["bar_chart", "pie_chart", "line_chart"]
        }


class MockVisualizationOptimizer:
    """Mock可视化优化器"""
    async def execute(self, input_data):
        return {
            "optimization_applied": True,
            "improvements": [
                "调整颜色搭配提升可读性",
                "优化图表尺寸和布局", 
                "添加数据标签增强理解"
            ],
            "quality_score": 0.92
        }


# SQL生成和验证工具Mock类
class MockSQLGeneratorAdvanced:
    """Mock高级SQL生成器 - 支持迭代验证"""
    
    async def generate_sql_with_validation(self, context):
        """生成SQL并验证"""
        # 模拟SQL生成和验证过程
        await asyncio.sleep(0.1)  # 模拟处理时间
        
        placeholder_text = context.get("placeholder_text", "")
        
        # 模拟不同复杂度的SQL生成
        if "简单" in placeholder_text or "统计" in placeholder_text:
            sql_query = "SELECT category, SUM(amount) as total FROM sales_data GROUP BY category"
            complexity = "simple"
        elif "趋势" in placeholder_text:
            sql_query = """
                SELECT 
                    DATE_FORMAT(date, '%Y-%m') as month,
                    SUM(amount) as total,
                    LAG(SUM(amount), 1) OVER (ORDER BY DATE_FORMAT(date, '%Y-%m')) as prev_total
                FROM sales_data 
                GROUP BY DATE_FORMAT(date, '%Y-%m') 
                ORDER BY month
            """
            complexity = "medium"
        elif "对比" in placeholder_text or "占比" in placeholder_text:
            sql_query = """
                SELECT 
                    category,
                    SUM(amount) as total,
                    SUM(amount) / (SELECT SUM(amount) FROM sales_data) * 100 as percentage
                FROM sales_data 
                GROUP BY category 
                ORDER BY total DESC
            """
            complexity = "complex"
        else:
            sql_query = "SELECT * FROM sales_data LIMIT 100"
            complexity = "simple"
        
        return {
            "success": True,
            "sql_query": sql_query,
            "validation_result": {
                "is_valid": True,
                "status": "valid",
                "execution_time_ms": 45.2,
                "affected_rows": 150,
                "quality_score": 0.85
            },
            "iteration_count": 1,
            "total_processing_time": 0.15,
            "complexity": complexity,
            "generation_method": "iterative_validation"
        }
    
    async def execute(self, task_type, input_data):
        """通用执行接口"""
        if task_type == "sql_generation":
            return await self.generate_sql_with_validation(input_data)
        else:
            return {
                "success": False,
                "error": f"不支持的任务类型: {task_type}"
            }


class MockSQLValidator:
    """Mock SQL验证器 - 基于数据源连接测试"""
    
    async def validate_sql_with_datasource(self, sql_query, data_source_info):
        """验证SQL并连接数据源测试"""
        await asyncio.sleep(0.05)  # 模拟验证时间
        
        # 模拟不同的验证场景
        if "SELEC " in sql_query:  # 拼写错误
            return {
                "is_valid": False,
                "status": "syntax_error",
                "error_message": "语法错误: SELECT关键字拼写错误",
                "suggestions": ["检查SELECT关键字拼写"]
            }
        
        if "nonexistent_table" in sql_query:
            return {
                "is_valid": False,
                "status": "schema_error",
                "error_message": "表不存在: nonexistent_table",
                "suggestions": ["检查表名是否正确", "确认表是否存在于当前数据库"]
            }
        
        if "permission_test_table" in sql_query:
            return {
                "is_valid": False,
                "status": "permission_error", 
                "error_message": "权限不足: 无法访问表 permission_test_table",
                "suggestions": ["联系管理员获取权限"]
            }
        
        # 模拟成功验证
        data_source_type = data_source_info.get("source_type", "unknown")
        
        return {
            "is_valid": True,
            "status": "valid",
            "execution_time_ms": 35.8,
            "affected_rows": 200,
            "result_columns": ["category", "total", "percentage"],
            "sample_data": [
                {"category": "产品A", "total": 15000, "percentage": 45.5},
                {"category": "产品B", "total": 12000, "percentage": 36.4},
                {"category": "产品C", "total": 6000, "percentage": 18.1}
            ],
            "quality_score": 0.88,
            "data_source_type": data_source_type,
            "validation_details": {
                "connection_test": "success",
                "query_analysis": "optimized",
                "performance_check": "good"
            }
        }
    
    async def execute(self, input_data):
        """通用执行接口"""
        sql_query = input_data.get("sql_query", "")
        data_source_info = input_data.get("data_source_info", {})
        
        return await self.validate_sql_with_datasource(sql_query, data_source_info)


class MockSQLOptimizer:
    """Mock SQL优化器 - 基于验证错误进行迭代优化"""
    
    async def optimize_sql_based_on_error(self, sql_query, error_info):
        """基于错误信息优化SQL"""
        await asyncio.sleep(0.03)  # 模拟优化时间
        
        optimized_sql = sql_query
        optimization_applied = []
        
        error_type = error_info.get("status", "")
        error_message = error_info.get("error_message", "")
        
        if error_type == "syntax_error":
            if "SELECT关键字拼写错误" in error_message:
                optimized_sql = sql_query.replace("SELEC ", "SELECT ")
                optimization_applied.append("修复SELECT关键字拼写")
        
        elif error_type == "schema_error":
            if "nonexistent_table" in error_message:
                optimized_sql = sql_query.replace("nonexistent_table", "sales_data")
                optimization_applied.append("替换不存在的表名为有效表名")
            
            if "nonexistent_column" in error_message:
                optimized_sql = sql_query.replace("nonexistent_column", "amount")
                optimization_applied.append("替换不存在的字段名为有效字段名")
        
        elif error_type == "execution_error":
            if "除零错误" in error_message:
                optimized_sql = optimized_sql.replace("/ ", "/ NULLIF(")
                optimization_applied.append("添加除零保护")
        
        return {
            "success": len(optimization_applied) > 0,
            "optimized_sql": optimized_sql,
            "original_sql": sql_query,
            "optimizations_applied": optimization_applied,
            "optimization_count": len(optimization_applied),
            "error_type_handled": error_type
        }
    
    async def execute(self, input_data):
        """通用执行接口"""
        sql_query = input_data.get("sql_query", "")
        error_info = input_data.get("error_info", {})
        
        return await self.optimize_sql_based_on_error(sql_query, error_info)


class MockDataSourceConnector:
    """Mock数据源连接器 - 模拟不同数据源连接测试"""
    
    async def test_connection(self, data_source_info):
        """测试数据源连接"""
        await asyncio.sleep(0.08)  # 模拟连接时间
        
        source_type = data_source_info.get("source_type", "unknown")
        
        # 模拟不同数据源的连接测试
        if source_type == "doris":
            return await self._test_doris_connection(data_source_info)
        elif source_type == "mysql":
            return await self._test_mysql_connection(data_source_info)
        elif source_type == "postgresql":
            return await self._test_postgresql_connection(data_source_info)
        else:
            return await self._test_generic_connection(data_source_info)
    
    async def _test_doris_connection(self, data_source_info):
        """测试Apache Doris连接"""
        return {
            "success": True,
            "connection_type": "doris",
            "host": data_source_info.get("doris_fe_hosts", ["localhost"])[0],
            "port": data_source_info.get("doris_query_port", 9030),
            "database": data_source_info.get("doris_database", "default"),
            "connection_time_ms": 120,
            "available_tables": ["sales_data", "customer_data", "product_data"],
            "server_version": "Apache Doris 1.2.0"
        }
    
    async def _test_mysql_connection(self, data_source_info):
        """测试MySQL连接"""
        return {
            "success": True,
            "connection_type": "mysql",
            "host": data_source_info.get("host", "localhost"),
            "port": data_source_info.get("port", 3306),
            "database": data_source_info.get("database", "test"),
            "connection_time_ms": 85,
            "available_tables": ["orders", "customers", "products"],
            "server_version": "MySQL 8.0.25"
        }
    
    async def _test_postgresql_connection(self, data_source_info):
        """测试PostgreSQL连接"""
        return {
            "success": True,
            "connection_type": "postgresql",
            "host": data_source_info.get("host", "localhost"),
            "port": data_source_info.get("port", 5432),
            "database": data_source_info.get("database", "postgres"),
            "connection_time_ms": 95,
            "available_tables": ["transactions", "users", "categories"],
            "server_version": "PostgreSQL 13.4"
        }
    
    async def _test_generic_connection(self, data_source_info):
        """测试通用数据源连接"""
        return {
            "success": True,
            "connection_type": "generic",
            "connection_time_ms": 100,
            "available_tables": ["data_table"],
            "server_version": "Generic DB 1.0"
        }
    
    async def execute(self, input_data):
        """通用执行接口"""
        data_source_info = input_data.get("data_source_info", {})
        return await self.test_connection(data_source_info)


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_placeholder_processing())