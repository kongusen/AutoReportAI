"""
测试样例数据
提供各种测试场景所需的标准化测试数据
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
import json

class SampleData:
    """测试样例数据生成器"""
    
    # 用户数据
    USERS = [
        {
            "username": "admin",
            "email": "admin@autoreport.ai",
            "full_name": "系统管理员",
            "is_active": True,
            "is_superuser": True
        },
        {
            "username": "testuser", 
            "email": "test@example.com",
            "full_name": "测试用户",
            "is_active": True,
            "is_superuser": False
        }
    ]
    
    # 数据源配置
    DATA_SOURCES = [
        {
            "name": "测试Doris数据源",
            "source_type": "doris",
            "doris_fe_hosts": ["192.168.61.30"],
            "doris_query_port": 9030,
            "doris_username": "root",
            "doris_password": "yjg@123456",
            "doris_database": "doris",
            "is_active": True
        },
        {
            "name": "本地Doris测试",
            "source_type": "doris", 
            "doris_fe_hosts": ["localhost"],
            "doris_query_port": 9030,
            "doris_username": "root",
            "doris_database": "test_db",
            "is_active": False
        }
    ]
    
    # 模板数据
    TEMPLATES = [
        {
            "name": "销售报告模板",
            "description": "月度销售数据分析报告",
            "content": """
# 销售报告

## 数据概览
本月销售总额: {total_sales}
同比增长: {growth_rate}%

## 详细分析
{sales_analysis}

## 图表展示
{chart_placeholder}
            """,
            "variables": ["total_sales", "growth_rate", "sales_analysis", "chart_placeholder"],
            "is_active": True
        },
        {
            "name": "用户行为分析",
            "description": "用户访问和行为分析报告",
            "content": """
# 用户行为分析报告

## 访问统计
总访问量: {total_visits}
独立用户: {unique_users}
平均停留时间: {avg_duration}

## 行为分析
{behavior_analysis}
            """,
            "variables": ["total_visits", "unique_users", "avg_duration", "behavior_analysis"],
            "is_active": True
        }
    ]
    
    # 图表数据
    CHART_DATA = {
        "bar_chart": {
            "title": "城市销售数据",
            "x_data": ["北京", "上海", "深圳", "广州"],
            "y_data": [1200, 1500, 980, 1100],
            "x_label": "城市",
            "y_label": "销售额 (万元)"
        },
        "line_chart": {
            "title": "月度增长趋势",
            "x_data": ["1月", "2月", "3月", "4月", "5月", "6月"],
            "y_data": [100, 120, 140, 135, 165, 180],
            "x_label": "月份",
            "y_label": "增长率 (%)"
        },
        "pie_chart": {
            "title": "产品类别分布",
            "labels": ["电子产品", "服装", "食品", "其他"],
            "values": [35, 25, 20, 20]
        }
    }
    
    # SQL查询示例
    SQL_QUERIES = {
        "sales_summary": """
            SELECT 
                DATE_FORMAT(order_date, '%Y-%m') as month,
                SUM(amount) as total_sales,
                COUNT(*) as order_count
            FROM orders 
            WHERE order_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
            GROUP BY DATE_FORMAT(order_date, '%Y-%m')
            ORDER BY month DESC
        """,
        "user_stats": """
            SELECT 
                COUNT(DISTINCT user_id) as total_users,
                COUNT(*) as total_visits,
                AVG(session_duration) as avg_duration
            FROM user_sessions 
            WHERE visit_date >= CURDATE() - INTERVAL 30 DAY
        """,
        "product_performance": """
            SELECT 
                product_category,
                SUM(quantity) as total_quantity,
                SUM(revenue) as total_revenue,
                AVG(rating) as avg_rating
            FROM product_sales ps
            JOIN products p ON ps.product_id = p.id
            GROUP BY product_category
            ORDER BY total_revenue DESC
        """
    }
    
    # Agent工具调用示例
    AGENT_TOOL_CALLS = [
        {
            "tool_name": "sql_executor",
            "parameters": {
                "sql": "SELECT COUNT(*) FROM users",
                "datasource_id": 1
            },
            "expected_result": {
                "success": True,
                "data": [{"count": 150}]
            }
        },
        {
            "tool_name": "chart_generator",
            "parameters": {
                "chart_type": "bar",
                "title": "测试图表",
                "x_data": ["A", "B", "C"],
                "y_data": [10, 20, 15]
            },
            "expected_result": {
                "success": True,
                "chart_path": "storage/charts/test_chart.png"
            }
        }
    ]
    
    # 报告示例
    REPORTS = [
        {
            "title": "月度业务报告",
            "template_id": 1,
            "datasource_id": 1,
            "status": "completed",
            "content": """
# 月度业务报告

## 关键指标
- 总销售额: ¥1,250,000
- 订单数量: 2,345
- 客户满意度: 4.6/5.0

## 趋势分析
本月销售额较上月增长15%，主要增长来自电子产品类别。

## 图表分析
[图表已生成: storage/reports/monthly_chart.png]
            """,
            "generated_at": datetime.now() - timedelta(days=1)
        }
    ]
    
    # 任务示例
    TASKS = [
        {
            "title": "生成月度销售报告",
            "template_id": 1,
            "datasource_id": 1,
            "status": "pending",
            "scheduled_at": datetime.now() + timedelta(hours=1),
            "parameters": {
                "month": "2024-01",
                "include_charts": True
            }
        },
        {
            "title": "用户行为分析任务",
            "template_id": 2,
            "datasource_id": 1, 
            "status": "running",
            "started_at": datetime.now() - timedelta(minutes=30),
            "parameters": {
                "date_range": "last_30_days"
            }
        }
    ]
    
    @classmethod
    def get_user(cls, index: int = 0) -> Dict[str, Any]:
        """获取用户数据"""
        return cls.USERS[index].copy()
    
    @classmethod
    def get_datasource(cls, index: int = 0) -> Dict[str, Any]:
        """获取数据源配置"""
        return cls.DATA_SOURCES[index].copy()
    
    @classmethod
    def get_template(cls, index: int = 0) -> Dict[str, Any]:
        """获取模板数据"""
        return cls.TEMPLATES[index].copy()
    
    @classmethod
    def get_chart_data(cls, chart_type: str = "bar_chart") -> Dict[str, Any]:
        """获取图表数据"""
        return cls.CHART_DATA[chart_type].copy()
    
    @classmethod
    def get_sql_query(cls, query_type: str = "sales_summary") -> str:
        """获取SQL查询"""
        return cls.SQL_QUERIES[query_type]
    
    @classmethod
    def get_agent_tool_call(cls, index: int = 0) -> Dict[str, Any]:
        """获取Agent工具调用示例"""
        return cls.AGENT_TOOL_CALLS[index].copy()
    
    @classmethod
    def get_report(cls, index: int = 0) -> Dict[str, Any]:
        """获取报告数据"""
        return cls.REPORTS[index].copy()
    
    @classmethod
    def get_task(cls, index: int = 0) -> Dict[str, Any]:
        """获取任务数据"""
        return cls.TASKS[index].copy()
    
    @classmethod
    def get_all_sample_data(cls) -> Dict[str, Any]:
        """获取所有样例数据"""
        return {
            "users": cls.USERS,
            "data_sources": cls.DATA_SOURCES,
            "templates": cls.TEMPLATES,
            "chart_data": cls.CHART_DATA,
            "sql_queries": cls.SQL_QUERIES,
            "agent_tool_calls": cls.AGENT_TOOL_CALLS,
            "reports": cls.REPORTS,
            "tasks": cls.TASKS
        }

# 便捷访问实例
sample_data = SampleData()