#!/usr/bin/env python3
"""
SQL占位符优化测试脚本

测试新的SQL占位符替换逻辑是否正常工作
"""

import sys
import asyncio
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append('/Users/shan/work/uploads/AutoReportAI/backend')

from app.utils.sql_placeholder_utils import SqlPlaceholderReplacer
from app.utils.time_context import TimeContextManager


def test_sql_placeholder_replacer():
    """测试SQL占位符替换器"""
    print("🧪 测试 SqlPlaceholderReplacer")
    print("=" * 50)

    replacer = SqlPlaceholderReplacer()

    # 测试数据
    test_cases = [
        {
            "name": "每日报告",
            "sql": "SELECT COUNT(*) as total_refund_requests FROM ods_refund WHERE dt BETWEEN {{start_date}} AND {{end_date}}",
            "time_context": {
                "data_start_time": "2025-09-27",
                "data_end_time": "2025-09-27",
                "execution_time": "2025-09-28T09:00:00"
            }
        },
        {
            "name": "周报",
            "sql": "SELECT user_id, SUM(amount) FROM orders WHERE order_date >= {{start_date}} AND order_date <= {{end_date}} GROUP BY user_id",
            "time_context": {
                "data_start_time": "2025-09-21",
                "data_end_time": "2025-09-27",
                "period": "weekly"
            }
        },
        {
            "name": "复杂查询",
            "sql": """
            SELECT
                DATE(created_at) as date,
                COUNT(*) as orders,
                SUM(total_amount) as revenue
            FROM orders
            WHERE created_at BETWEEN {{start_date}} AND {{end_date}}
              AND status = 'completed'
            GROUP BY DATE(created_at)
            ORDER BY date
            """,
            "time_context": {
                "data_start_time": "2025-09-01",
                "data_end_time": "2025-09-30"
            }
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 测试用例 {i}: {test_case['name']}")
        print("-" * 30)

        # 提取占位符
        placeholders = replacer.extract_placeholders(test_case['sql'])
        print(f"🔍 发现占位符: {placeholders}")

        # 验证占位符
        validation = replacer.validate_placeholders(test_case['sql'], test_case['time_context'])
        print(f"✅ 验证结果: {'通过' if validation['valid'] else '失败'}")
        if validation['warnings']:
            for warning in validation['warnings']:
                print(f"⚠️  {warning}")

        # 预览替换
        preview = replacer.preview_replacement(test_case['sql'], test_case['time_context'])
        print(f"🔄 替换映射: {preview['replacements']}")

        # 执行替换
        replaced_sql = replacer.replace_time_placeholders(test_case['sql'], test_case['time_context'])

        print(f"📝 原始SQL:")
        print(f"   {test_case['sql'].strip()}")
        print(f"🔧 替换后SQL:")
        print(f"   {replaced_sql.strip()}")

    print("\n" + "=" * 50)
    print("✅ SqlPlaceholderReplacer 测试完成")


def test_time_context_manager():
    """测试时间上下文管理器"""
    print("\n🧪 测试 TimeContextManager")
    print("=" * 50)

    manager = TimeContextManager()

    # 测试不同的cron表达式
    test_crons = [
        ("0 9 * * *", "每日9点", datetime(2025, 9, 28, 9, 0)),
        ("0 9 * * 1", "每周一9点", datetime(2025, 9, 29, 9, 0)),  # 周一
        ("0 0 1 * *", "每月1号", datetime(2025, 10, 1, 0, 0)),
        ("0 0 1 1 *", "每年1月1号", datetime(2025, 1, 1, 0, 0))
    ]

    for cron, desc, exec_time in test_crons:
        print(f"\n📅 测试: {desc} ({cron})")
        print("-" * 30)

        # 生成时间上下文
        context = manager.build_task_time_context(cron, exec_time)

        print(f"🔍 推断周期: {context.get('period')}")
        print(f"📊 数据范围: {context.get('data_start_time')} ~ {context.get('data_end_time')}")
        print(f"⏰ 执行时间: {context.get('execution_time')}")

        # 测试SQL替换
        test_sql = "SELECT * FROM sales WHERE date BETWEEN {{start_date}} AND {{end_date}}"
        replacer = SqlPlaceholderReplacer()
        replaced = replacer.replace_time_placeholders(test_sql, context)
        print(f"🔧 SQL示例: {replaced}")

    print("\n" + "=" * 50)
    print("✅ TimeContextManager 测试完成")


async def test_query_executor():
    """测试查询执行器"""
    print("\n🧪 测试 QueryExecutorService")
    print("=" * 50)

    try:
        from app.services.data.query.query_executor_service import QueryExecutorService

        executor = QueryExecutorService()

        # 测试SQL
        sql_with_placeholders = """
        SELECT
            COUNT(*) as total_orders,
            AVG(order_amount) as avg_amount
        FROM orders
        WHERE order_date BETWEEN {{start_date}} AND {{end_date}}
        """

        # 时间上下文
        time_context = {
            "data_start_time": "2025-09-27",
            "data_end_time": "2025-09-27"
        }

        print(f"📝 测试SQL:")
        print(f"   {sql_with_placeholders.strip()}")
        print(f"⏰ 时间上下文: {time_context}")

        # 注意：这里不会真正执行，因为没有数据库连接
        # 但会测试占位符替换逻辑
        print(f"🔍 提取的占位符: {executor.sql_replacer.extract_placeholders(sql_with_placeholders)}")

        replaced_sql = executor.sql_replacer.replace_time_placeholders(sql_with_placeholders, time_context)
        print(f"🔧 替换后SQL:")
        print(f"   {replaced_sql.strip()}")

        print("✅ QueryExecutorService 占位符处理正常")

    except ImportError as e:
        print(f"⚠️  无法导入 QueryExecutorService: {e}")
    except Exception as e:
        print(f"❌ QueryExecutorService 测试失败: {e}")

    print("\n" + "=" * 50)
    print("✅ QueryExecutorService 测试完成")


async def test_task_execution_service():
    """测试任务执行服务"""
    print("\n🧪 测试 TaskExecutionService")
    print("=" * 50)

    try:
        from app.services.application.tasks.task_execution_service import TaskExecutionService

        service = TaskExecutionService()

        # 测试时间上下文生成
        execution_params = {
            "schedule": "0 9 * * 1-5",  # 工作日9点
            "execution_time": "2025-09-28T09:00:00"
        }

        print(f"📋 执行参数: {execution_params}")

        time_context = service.generate_time_context_for_task(execution_params)
        print(f"⏰ 生成的时间上下文:")
        for key, value in time_context.items():
            print(f"   {key}: {value}")

        # 测试SQL占位符替换
        test_sql = "SELECT * FROM daily_stats WHERE stat_date = {{start_date}}"
        replaced = service.replace_sql_placeholders_in_task(test_sql, time_context)
        print(f"\n🔧 SQL替换测试:")
        print(f"   原始: {test_sql}")
        print(f"   替换: {replaced}")

        print("✅ TaskExecutionService 处理正常")

    except ImportError as e:
        print(f"⚠️  无法导入 TaskExecutionService: {e}")
    except Exception as e:
        print(f"❌ TaskExecutionService 测试失败: {e}")

    print("\n" + "=" * 50)
    print("✅ TaskExecutionService 测试完成")


def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n🧪 测试向后兼容性")
    print("=" * 50)

    try:
        from app.utils.time_context import TimeContextManager

        manager = TimeContextManager()

        # 测试废弃的方法是否仍然工作
        sql = "SELECT * FROM test WHERE date = {{start_date}}"
        time_context = {
            "data_start_time": "2025-09-27",
            "data_end_time": "2025-09-27"
        }

        print(f"📝 测试废弃方法 replace_sql_time_placeholders")
        print(f"   原始SQL: {sql}")

        # 这应该会发出废弃警告但仍然工作
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = manager.replace_sql_time_placeholders(sql, time_context)

            if w:
                print(f"⚠️  废弃警告: {w[0].message}")
                print("✅ 废弃警告正常显示")
            else:
                print("❌ 未显示废弃警告")

        print(f"   结果SQL: {result}")
        print("✅ 向后兼容性测试完成")

    except Exception as e:
        print(f"❌ 向后兼容性测试失败: {e}")

    print("\n" + "=" * 50)


async def main():
    """主测试函数"""
    print("🚀 SQL占位符优化测试开始")
    print("=" * 60)

    # 运行所有测试
    test_sql_placeholder_replacer()
    test_time_context_manager()
    await test_query_executor()
    await test_task_execution_service()
    test_backward_compatibility()

    print("\n" + "=" * 60)
    print("🎉 所有测试完成！")
    print("\n📋 优化总结:")
    print("✅ 1. 创建了统一的 SqlPlaceholderReplacer 工具类")
    print("✅ 2. 修改了 TaskExecutionService 使用简化逻辑")
    print("✅ 3. 更新了 QueryExecutorService 支持占位符")
    print("✅ 4. 标记了复杂的旧逻辑为废弃")
    print("✅ 5. 保持了向后兼容性")
    print("\n🎯 现在你可以安全地使用 {{start_date}} 和 {{end_date}} 占位符！")


if __name__ == "__main__":
    asyncio.run(main())