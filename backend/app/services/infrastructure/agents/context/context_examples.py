"""
Agent 上下文构建示例
====================

展示如何为不同类型的占位符任务构建 Agent 上下文的具体示例。
包含数据分析、报告生成、SQL 生成和商业智能等场景。
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List

from .context_builder import (
    AgentContextBuilder, ContextType, PlaceholderType, PlaceholderInfo,
    DatabaseSchemaInfo, TemplateInfo, TaskInfo, create_simple_context
)
from ..core.message_types import MessagePriority
from ..core.main import AgentCoordinator


class ContextExamples:
    """Agent 上下文构建示例集合"""
    
    def __init__(self):
        self.builder = AgentContextBuilder()
    
    def example_1_sales_report_generation(self) -> Dict[str, Any]:
        """
        示例1: 销售报告生成
        
        场景: 根据销售数据表生成月度销售报告
        占位符: 表名、日期范围、指标、图表类型
        """
        
        # 1. 定义任务信息
        task_info = TaskInfo(
            task_id="sales_report_001",
            task_name="生成月度销售报告",
            task_type="report_generation",
            description="基于销售数据表生成包含趋势分析和图表的月度销售报告",
            priority=MessagePriority.HIGH,
            requirements=[
                "包含销售趋势分析",
                "生成可视化图表",
                "计算同比增长率",
                "识别top产品"
            ],
            expected_outputs=["HTML报告", "销售趋势图表", "关键指标汇总"]
        )
        
        # 2. 定义占位符
        placeholders = [
            PlaceholderInfo(
                name="sales_table",
                type=PlaceholderType.TABLE_NAME,
                value="sales_orders",
                description="销售订单表名",
                required=True
            ),
            PlaceholderInfo(
                name="date_range",
                type=PlaceholderType.DATE_RANGE,
                value={"start_date": "2024-01-01", "end_date": "2024-01-31"},
                description="报告时间范围",
                required=True
            ),
            PlaceholderInfo(
                name="primary_metric",
                type=PlaceholderType.METRIC_NAME,
                value="total_amount",
                description="主要指标列名",
                default_value="revenue"
            ),
            PlaceholderInfo(
                name="chart_type",
                type=PlaceholderType.CHART_TYPE,
                value="line",
                description="趋势图表类型",
                default_value="bar"
            )
        ]
        
        # 3. 定义数据库表结构
        database_schemas = [
            DatabaseSchemaInfo(
                table_name="sales_orders",
                columns=[
                    {"name": "order_id", "type": "bigint", "nullable": False, "primary_key": True},
                    {"name": "customer_id", "type": "bigint", "nullable": False},
                    {"name": "product_id", "type": "bigint", "nullable": False},
                    {"name": "order_date", "type": "date", "nullable": False},
                    {"name": "total_amount", "type": "decimal(10,2)", "nullable": False},
                    {"name": "quantity", "type": "integer", "nullable": False},
                    {"name": "status", "type": "varchar(20)", "nullable": False}
                ],
                relationships=[
                    {
                        "type": "foreign_key",
                        "target_table": "customers",
                        "columns": [{"source": "customer_id", "target": "customer_id"}]
                    },
                    {
                        "type": "foreign_key", 
                        "target_table": "products",
                        "columns": [{"source": "product_id", "target": "product_id"}]
                    }
                ],
                statistics={"row_count": 50000, "avg_row_length": 128}
            ),
            DatabaseSchemaInfo(
                table_name="customers",
                columns=[
                    {"name": "customer_id", "type": "bigint", "primary_key": True},
                    {"name": "customer_name", "type": "varchar(100)"},
                    {"name": "region", "type": "varchar(50)"},
                    {"name": "segment", "type": "varchar(50)"}
                ]
            ),
            DatabaseSchemaInfo(
                table_name="products",
                columns=[
                    {"name": "product_id", "type": "bigint", "primary_key": True},
                    {"name": "product_name", "type": "varchar(100)"},
                    {"name": "category", "type": "varchar(50)"},
                    {"name": "price", "type": "decimal(8,2)"}
                ]
            )
        ]
        
        # 4. 定义报告模板
        templates = [
            TemplateInfo(
                template_id="sales_report_template",
                name="月度销售报告模板",
                template_type="report",
                content="""
                <h1>月度销售报告 - {date_range}</h1>
                
                <h2>执行摘要</h2>
                <p>本报告基于 {sales_table} 表数据，分析了 {date_range} 期间的销售表现。</p>
                
                <h2>关键指标</h2>
                <ul>
                    <li>总销售额: {total_revenue}</li>
                    <li>订单数量: {total_orders}</li>
                    <li>平均订单价值: {avg_order_value}</li>
                    <li>同比增长率: {yoy_growth}</li>
                </ul>
                
                <h2>销售趋势</h2>
                <div id="sales_trend_chart">
                    <!-- {chart_type} 图表将在这里插入 -->
                </div>
                
                <h2>产品分析</h2>
                <div id="product_performance">
                    <!-- 产品表现数据将在这里插入 -->
                </div>
                """,
                variables=["date_range", "sales_table", "total_revenue", "total_orders", 
                          "avg_order_value", "yoy_growth", "chart_type"],
                sections=["executive_summary", "key_metrics", "trend_analysis", "product_analysis"]
            )
        ]
        
        # 5. 构建上下文
        context = self.builder.build_context(
            task_info=task_info,
            placeholders=placeholders,
            templates=templates,
            database_schemas=database_schemas,
            context_type=ContextType.REPORT_GENERATION
        )
        
        return {
            "context": context,
            "description": "销售报告生成上下文示例",
            "expected_agent": "report_generator",
            "estimated_duration": "5-10分钟"
        }
    
    def example_2_data_analysis_task(self) -> Dict[str, Any]:
        """
        示例2: 客户行为数据分析
        
        场景: 分析客户购买行为，发现模式和异常
        占位符: 分析类型、过滤条件、统计指标
        """
        
        task_info = TaskInfo(
            task_id="customer_analysis_001",
            task_name="客户购买行为分析", 
            task_type="data_analysis",
            description="分析客户购买模式，识别高价值客户和潜在流失客户",
            requirements=[
                "识别购买模式",
                "计算客户生命周期价值",
                "检测异常购买行为",
                "提供业务建议"
            ]
        )
        
        placeholders = [
            PlaceholderInfo(
                name="customer_table",
                type=PlaceholderType.TABLE_NAME,
                value="customer_orders_view"
            ),
            PlaceholderInfo(
                name="analysis_type",
                type=PlaceholderType.TEMPLATE_VARIABLE,
                value="comprehensive",
                description="分析深度级别"
            ),
            PlaceholderInfo(
                name="filter_condition",
                type=PlaceholderType.FILTER_CONDITION,
                value="order_date >= '2023-01-01' AND status = 'completed'",
                description="数据过滤条件"
            ),
            PlaceholderInfo(
                name="grouping_columns",
                type=PlaceholderType.COLUMN_NAME,
                value="customer_segment,region",
                description="分组分析的列"
            )
        ]
        
        database_schemas = [
            DatabaseSchemaInfo(
                table_name="customer_orders_view",
                columns=[
                    {"name": "customer_id", "type": "bigint"},
                    {"name": "customer_name", "type": "varchar(100)"},
                    {"name": "customer_segment", "type": "varchar(50)"},
                    {"name": "region", "type": "varchar(50)"},
                    {"name": "order_date", "type": "date"},
                    {"name": "order_amount", "type": "decimal(10,2)"},
                    {"name": "product_category", "type": "varchar(50)"},
                    {"name": "status", "type": "varchar(20)"},
                    {"name": "days_since_last_order", "type": "integer"}
                ],
                statistics={"row_count": 100000}
            )
        ]
        
        context = self.builder.build_context(
            task_info=task_info,
            placeholders=placeholders,
            database_schemas=database_schemas,
            context_type=ContextType.DATA_ANALYSIS
        )
        
        return {
            "context": context,
            "description": "客户行为数据分析上下文示例",
            "expected_agent": "data_analysis_agent",
            "estimated_duration": "10-15分钟"
        }
    
    def example_3_sql_generation_task(self) -> Dict[str, Any]:
        """
        示例3: 复杂SQL查询生成
        
        场景: 根据业务需求生成优化的SQL查询
        占位符: 表名、列名、聚合函数、条件
        """
        
        task_info = TaskInfo(
            task_id="sql_gen_001",
            task_name="生成销售汇总查询",
            task_type="sql_generation", 
            description="生成按产品类别和月份汇总的销售统计查询",
            requirements=[
                "按产品类别分组",
                "按月份聚合",
                "计算销售总额和数量",
                "包含同比对比",
                "优化查询性能"
            ]
        )
        
        placeholders = [
            PlaceholderInfo(
                name="main_table",
                type=PlaceholderType.TABLE_NAME,
                value="sales_fact"
            ),
            PlaceholderInfo(
                name="date_column", 
                type=PlaceholderType.COLUMN_NAME,
                value="sale_date"
            ),
            PlaceholderInfo(
                name="amount_column",
                type=PlaceholderType.COLUMN_NAME,
                value="sale_amount"
            ),
            PlaceholderInfo(
                name="aggregation_func",
                type=PlaceholderType.AGGREGATION_FUNCTION,
                value="SUM"
            ),
            PlaceholderInfo(
                name="time_range",
                type=PlaceholderType.DATE_RANGE,
                value={"start_date": "2024-01-01", "end_date": "2024-12-31"}
            )
        ]
        
        database_schemas = [
            DatabaseSchemaInfo(
                table_name="sales_fact",
                columns=[
                    {"name": "sale_id", "type": "bigint", "primary_key": True},
                    {"name": "product_id", "type": "bigint"},
                    {"name": "customer_id", "type": "bigint"},
                    {"name": "sale_date", "type": "date", "nullable": False},
                    {"name": "sale_amount", "type": "decimal(12,2)"},
                    {"name": "quantity", "type": "integer"},
                    {"name": "discount", "type": "decimal(5,2)"}
                ],
                indexes=[
                    {"name": "idx_sale_date", "columns": ["sale_date"]},
                    {"name": "idx_product_date", "columns": ["product_id", "sale_date"]}
                ]
            ),
            DatabaseSchemaInfo(
                table_name="product_dim",
                columns=[
                    {"name": "product_id", "type": "bigint", "primary_key": True},
                    {"name": "product_name", "type": "varchar(200)"},
                    {"name": "category", "type": "varchar(100)"},
                    {"name": "subcategory", "type": "varchar(100)"}
                ]
            )
        ]
        
        templates = [
            TemplateInfo(
                template_id="sales_summary_sql",
                name="销售汇总SQL模板",
                template_type="sql_query",
                content="""
                SELECT 
                    p.category,
                    DATE_TRUNC('month', s.{date_column}) as sale_month,
                    {aggregation_func}(s.{amount_column}) as total_sales,
                    COUNT(*) as transaction_count,
                    AVG(s.{amount_column}) as avg_transaction
                FROM {main_table} s
                JOIN product_dim p ON s.product_id = p.product_id  
                WHERE s.{date_column} BETWEEN '{start_date}' AND '{end_date}'
                GROUP BY p.category, DATE_TRUNC('month', s.{date_column})
                ORDER BY sale_month, total_sales DESC
                """,
                variables=["main_table", "date_column", "amount_column", "aggregation_func", "start_date", "end_date"]
            )
        ]
        
        context = self.builder.build_context(
            task_info=task_info,
            placeholders=placeholders,
            templates=templates,
            database_schemas=database_schemas,
            context_type=ContextType.SQL_GENERATION
        )
        
        return {
            "context": context,
            "description": "SQL查询生成上下文示例",
            "expected_agent": "sql_generation_agent",
            "estimated_duration": "2-5分钟"
        }
    
    def example_4_business_intelligence_dashboard(self) -> Dict[str, Any]:
        """
        示例4: 商业智能仪表板
        
        场景: 创建高管仪表板，包含多个KPI和可视化
        """
        
        task_info = TaskInfo(
            task_id="bi_dashboard_001",
            task_name="高管仪表板创建",
            task_type="business_intelligence",
            description="创建包含关键业务指标的交互式高管仪表板",
            requirements=[
                "实时KPI监控",
                "多维度数据钻取", 
                "交互式图表",
                "移动端适配",
                "数据刷新机制"
            ]
        )
        
        placeholders = [
            PlaceholderInfo(
                name="kpi_metrics",
                type=PlaceholderType.METRIC_NAME,
                value=["revenue", "profit_margin", "customer_count", "order_volume"],
                description="关键业务指标"
            ),
            PlaceholderInfo(
                name="time_dimension",
                type=PlaceholderType.DATE_RANGE,
                value={"start_date": "2024-01-01", "end_date": "2024-12-31"},
                description="时间维度范围"
            ),
            PlaceholderInfo(
                name="chart_types",
                type=PlaceholderType.CHART_TYPE,
                value=["kpi_card", "trend_line", "donut_chart", "bar_chart"],
                description="仪表板图表类型"
            )
        ]
        
        # 多个数据源表
        database_schemas = [
            DatabaseSchemaInfo(
                table_name="financial_metrics",
                columns=[
                    {"name": "metric_date", "type": "date"},
                    {"name": "revenue", "type": "decimal(15,2)"},
                    {"name": "costs", "type": "decimal(15,2)"},
                    {"name": "profit_margin", "type": "decimal(5,4)"}
                ]
            ),
            DatabaseSchemaInfo(
                table_name="customer_metrics", 
                columns=[
                    {"name": "metric_date", "type": "date"},
                    {"name": "new_customers", "type": "integer"},
                    {"name": "active_customers", "type": "integer"},
                    {"name": "churn_rate", "type": "decimal(5,4)"}
                ]
            ),
            DatabaseSchemaInfo(
                table_name="operational_metrics",
                columns=[
                    {"name": "metric_date", "type": "date"},
                    {"name": "order_count", "type": "integer"},
                    {"name": "avg_order_value", "type": "decimal(10,2)"},
                    {"name": "fulfillment_rate", "type": "decimal(5,4)"}
                ]
            )
        ]
        
        templates = [
            TemplateInfo(
                template_id="executive_dashboard",
                name="高管仪表板模板",
                template_type="dashboard",
                content="""
                {
                  "dashboard_title": "高管业务仪表板",
                  "layout": "grid",
                  "refresh_interval": 300,
                  "widgets": [
                    {
                      "type": "kpi_card",
                      "title": "总收入",
                      "metric": "revenue",
                      "format": "currency"
                    },
                    {
                      "type": "trend_line", 
                      "title": "收入趋势",
                      "metric": "revenue",
                      "time_range": "{time_dimension}"
                    },
                    {
                      "type": "donut_chart",
                      "title": "收入分布",
                      "metric": "revenue_by_category"
                    }
                  ]
                }
                """,
                variables=["time_dimension", "kpi_metrics"]
            )
        ]
        
        context = self.builder.build_context(
            task_info=task_info,
            placeholders=placeholders,
            templates=templates,
            database_schemas=database_schemas,
            context_type=ContextType.BUSINESS_INTELLIGENCE
        )
        
        return {
            "context": context,
            "description": "商业智能仪表板上下文示例",
            "expected_agent": "business_intelligence_agent",
            "estimated_duration": "15-30分钟"
        }
    
    def example_5_simple_context_creation(self) -> Dict[str, Any]:
        """
        示例5: 使用便利函数创建简单上下文
        """
        
        # 使用便利函数快速创建上下文
        context = create_simple_context(
            task_name="客户订单统计",
            task_description="统计过去30天的客户订单数量和金额",
            placeholders_dict={
                "table_name": "orders",
                "days_back": 30,
                "status_filter": "completed"
            },
            table_schemas=[
                {
                    "table_name": "orders",
                    "columns": [
                        {"name": "order_id", "type": "bigint"},
                        {"name": "customer_id", "type": "bigint"},
                        {"name": "order_date", "type": "date"},
                        {"name": "total_amount", "type": "decimal(10,2)"},
                        {"name": "status", "type": "varchar(20)"}
                    ]
                }
            ],
            context_type=ContextType.DATA_ANALYSIS
        )
        
        return {
            "context": context,
            "description": "使用便利函数创建的简单上下文示例",
            "expected_agent": "data_analysis_agent",
            "estimated_duration": "2-5分钟"
        }


# 演示如何使用这些示例
async def demonstrate_context_usage():
    """演示如何使用上下文构建器和协调器"""
    
    examples = ContextExamples()
    
    print("=== Agent 上下文构建示例演示 ===\n")
    
    # 示例1: 销售报告生成
    example1 = examples.example_1_sales_report_generation()
    context1 = example1["context"]
    
    print("📊 示例1: 销售报告生成")
    print(f"任务ID: {context1.task_info.task_id}")
    print(f"上下文类型: {context1.context_type.value}")
    print(f"占位符数量: {len(context1.placeholders)}")
    print(f"已解析占位符: {list(context1.resolved_placeholders.keys())}")
    print(f"推荐工具: {context1.tool_preferences['preferred_tools']}")
    print()
    
    # 示例2: 数据分析
    example2 = examples.example_2_data_analysis_task()
    context2 = example2["context"]
    
    print("🔍 示例2: 客户行为数据分析")
    print(f"任务类型: {context2.task_info.task_type}")
    print(f"执行选项: {context2.execution_options}")
    print(f"查询上下文表: {context2.query_context['available_tables']}")
    print()
    
    # 示例3: SQL生成
    example3 = examples.example_3_sql_generation_task()
    context3 = example3["context"]
    
    print("🗃️ 示例3: SQL查询生成")
    print(f"模板处理结果: {len(context3.processed_templates)} 个模板已处理")
    if context3.processed_templates:
        template_id = list(context3.processed_templates.keys())[0]
        print(f"生成的SQL预览: {context3.processed_templates[template_id][:200]}...")
    print()
    
    # 创建消息并演示发送
    coordinator = AgentCoordinator()
    try:
        await coordinator.start()
        
        # 为示例1创建并发送Agent消息
        builder = AgentContextBuilder()
        message = builder.create_agent_message(
            context=context1,
            target_agent="report_generation_agent",
            from_agent="context_demo"
        )
        
        print("📨 创建的Agent消息示例:")
        print(f"消息ID: {message.message_id}")
        print(f"消息类型: {message.message_type.value}")
        print(f"目标Agent: {message.to_agent}")
        print(f"载荷大小: {len(str(message.payload))} 字符")
        print()
        
        # 显示系统状态
        status = await coordinator.get_system_status()
        print("🏗️ 协调器系统状态:")
        print(f"状态: {status['coordinator_status']}")
        print(f"已注册Agent数量: {status['registered_agents']}")
        
    finally:
        await coordinator.stop()


# 如果直接运行此脚本
if __name__ == "__main__":
    asyncio.run(demonstrate_context_usage())