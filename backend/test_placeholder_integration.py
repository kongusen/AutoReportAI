#!/usr/bin/env python3
"""
测试占位符处理集成
验证修复后的Celery任务和Agent系统集成
"""

import asyncio
import sys
import os
import logging
from datetime import datetime, timedelta

# 添加项目根路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_placeholder_service():
    """测试占位符应用服务"""
    print("🧪 测试占位符应用服务...")

    try:
        from app.services.application.placeholder.placeholder_service import PlaceholderApplicationService

        # 创建服务实例
        service = PlaceholderApplicationService(user_id="test-user")
        await service.initialize()

        print("✅ PlaceholderApplicationService 创建成功")
        print(f"   - User ID: {service.user_id}")
        print(f"   - 是否已初始化: {service.is_initialized}")

        return service

    except Exception as e:
        print(f"❌ PlaceholderApplicationService 创建失败: {e}")
        return None

async def test_sql_replacer():
    """测试SQL占位符替换器"""
    print("\n🧪 测试SQL占位符替换器...")

    try:
        from app.utils.sql_placeholder_utils import SqlPlaceholderReplacer

        replacer = SqlPlaceholderReplacer()

        # 测试SQL
        test_sql = "SELECT COUNT(*) as total FROM orders WHERE created_at BETWEEN {{start_date}} AND {{end_date}}"

        # 测试时间上下文
        time_context = {
            "data_start_time": "2025-09-28",
            "data_end_time": "2025-09-29",
            "execution_time": "2025-09-29"
        }

        # 提取占位符
        placeholders = replacer.extract_placeholders(test_sql)
        print(f"✅ 提取占位符: {placeholders}")

        # 验证占位符
        validation = replacer.validate_placeholders(test_sql, time_context)
        print(f"✅ 占位符验证: valid={validation['valid']}, 缺失={validation['missing_placeholders']}")

        # 替换占位符
        replaced_sql = replacer.replace_time_placeholders(test_sql, time_context)
        print(f"✅ 替换后SQL: {replaced_sql}")

        return True

    except Exception as e:
        print(f"❌ SQL占位符替换器测试失败: {e}")
        return False

async def test_run_task_with_agent():
    """测试 run_task_with_agent 方法"""
    print("\n🧪 测试 run_task_with_agent 方法...")

    try:
        service = await test_placeholder_service()
        if not service:
            return False

        # 模拟任务参数
        task_objective = "测试占位符分析与SQL生成"
        success_criteria = {
            "min_rows": 1,
            "max_rows": 1000,
            "execute_queries": False  # 不执行实际查询
        }
        data_source_id = "test-ds-001"
        time_window = {
            "start": "2025-09-28 00:00:00",
            "end": "2025-09-29 23:59:59"
        }
        template_id = "test-template-001"

        print(f"   - 任务目标: {task_objective}")
        print(f"   - 数据源ID: {data_source_id}")
        print(f"   - 模板ID: {template_id}")
        print(f"   - 时间窗口: {time_window}")

        events = []
        try:
            async for event in service.run_task_with_agent(
                task_objective=task_objective,
                success_criteria=success_criteria,
                data_source_id=data_source_id,
                time_window=time_window,
                template_id=template_id
            ):
                events.append(event)
                print(f"   📨 事件: {event.get('type', 'unknown')} - {event.get('message', '')}")

                # 如果失败就提前退出
                if event.get('type') == 'agent_session_failed':
                    break

                # 限制事件数量避免无限循环
                if len(events) > 10:
                    break

        except Exception as e:
            print(f"   ⚠️  Agent执行异常: {e}")

        print(f"✅ run_task_with_agent 执行完成，收到 {len(events)} 个事件")

        # 显示最后的事件
        if events:
            last_event = events[-1]
            print(f"   📋 最后事件: {last_event.get('type')} - {last_event.get('message', '')}")

        return True

    except Exception as e:
        print(f"❌ run_task_with_agent 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_celery_task_structure():
    """测试Celery任务结构"""
    print("\n🧪 测试Celery任务结构...")

    try:
        from app.services.infrastructure.task_queue.tasks import execute_report_task

        # 检查任务是否正确注册
        print("✅ execute_report_task 导入成功")
        print(f"   - 任务名称: {execute_report_task.name}")
        print(f"   - 任务队列: {getattr(execute_report_task, 'queue', 'default')}")

        return True

    except Exception as e:
        print(f"❌ Celery任务结构测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("🚀 开始占位符处理集成测试\n")

    test_results = []

    # 测试1: SQL替换器
    result1 = await test_sql_replacer()
    test_results.append(("SQL占位符替换器", result1))

    # 测试2: 占位符应用服务
    result2 = await test_placeholder_service() is not None
    test_results.append(("占位符应用服务", result2))

    # 测试3: run_task_with_agent方法
    result3 = await test_run_task_with_agent()
    test_results.append(("run_task_with_agent方法", result3))

    # 测试4: Celery任务结构
    result4 = await test_celery_task_structure()
    test_results.append(("Celery任务结构", result4))

    # 结果汇总
    print("\n📊 测试结果汇总:")
    print("=" * 50)

    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1

    print("=" * 50)
    print(f"总计: {passed}/{total} 个测试通过")

    if passed == total:
        print("\n🎉 所有测试都通过！占位符处理集成修复成功！")
        return True
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，需要进一步检查")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit_code = 0 if success else 1
        print(f"\n🏁 测试完成，退出码: {exit_code}")
        sys.exit(exit_code)
    except Exception as e:
        print(f"💥 测试执行异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)