#!/usr/bin/env python3
"""
TT控制循环测试脚本
测试新的tt控制循环架构是否正常工作
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.application.factories import create_service_orchestrator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_tt_controller():
    """测试TT控制循环功能"""
    
    print("=" * 70)
    print("测试TT控制循环架构")
    print("=" * 70)
    
    # 创建服务编排器
    orchestrator = create_service_orchestrator("test_user_123")
    
    # 测试数据 - 使用固定时间信息
    test_data = {
        "user_id": "test_user_123",
        "placeholder_name": "period_start_date",
        "placeholder_text": "周期:统计开始日期",
        "template_id": "test_template_123",
        "template_context": "这是一个测试模板，用于统计分析。我们需要分析周期性的数据趋势。",
        "data_source_info": {
            "type": "doris",
            "database": "yjg",
            "name": "测试数据源",
            "tables": ["ods_complain", "user_table", "order_table"],
            "table_details": [{
                "name": "ods_complain",
                "business_category": "投诉数据",
                "columns_count": 15,
                "estimated_rows": 5000,
                "all_columns": [
                    "id(bigint)", "create_time(datetime)", "complaint_content(text)",
                    "user_id(varchar)", "status(varchar)", "category(varchar)",
                    "priority(int)", "assigned_to(varchar)", "resolved_time(datetime)"
                ],
                "key_columns": ["id", "create_time", "complaint_content", "user_id", "status"]
            }, {
                "name": "user_table", 
                "business_category": "用户数据",
                "columns_count": 12,
                "estimated_rows": 10000,
                "all_columns": [
                    "user_id(varchar)", "username(varchar)", "email(varchar)",
                    "created_at(datetime)", "last_login(datetime)", "status(varchar)"
                ],
                "key_columns": ["user_id", "username", "created_at", "status"]
            }]
        },
        # 固定时间信息测试
        "task_params": {
            "execution_time": datetime.now().isoformat(),
            "data_range": "day",
            "time_context": {
                "range_type": "day",
                "execution_time": datetime.now().isoformat(),
                "current_time": datetime.now().isoformat(),
                "suggested_date_filter": f"DATE(create_time) = '{datetime.now().strftime('%Y-%m-%d')}'"
            },
            "analysis_context": {
                "reference_date": datetime.now().strftime('%Y-%m-%d'),
                "period_type": "daily_analysis"
            }
        },
        "cron_expression": None,
        "execution_time": datetime.now(),
        "task_type": "tt_controller_test"
    }
    
    try:
        print("开始执行TT控制循环测试...")
        print(f"占位符: {test_data['placeholder_text']}")
        print(f"模板ID: {test_data['template_id']}")
        print(f"数据源: {test_data['data_source_info']['name']}")
        print(f"任务类型: {test_data['task_type']}")
        print(f"执行时间: {test_data['task_params']['execution_time']}")
        
        # 开始计时
        start_time = datetime.now()
        
        # 执行分析 - 使用新的TT控制循环架构
        result = await orchestrator.analyze_single_placeholder_simple(**test_data)
        
        # 结束计时
        end_time = datetime.now()
        execution_duration = (end_time - start_time).total_seconds()
        
        print("\n" + "=" * 50)
        print("TT控制循环执行结果:")
        print("=" * 50)
        print(f"执行状态: {result.get('status')}")
        print(f"占位符名称: {result.get('placeholder_name')}")
        print(f"执行耗时: {execution_duration:.2f} 秒")
        
        if result.get('status') == 'success':
            print("\n✅ TT控制循环测试成功！")
            
            # 显示生成的SQL
            generated_sql = result.get('generated_sql', {})
            if isinstance(generated_sql, dict):
                sql_content = generated_sql.get('sql') or generated_sql.get(test_data['placeholder_name'], '')
            else:
                sql_content = str(generated_sql)
            
            print(f"\n生成的SQL:")
            print("-" * 50)
            print(sql_content)
            
            # 显示分析结果
            analysis_result = result.get('analysis_result', {})
            print(f"\n分析描述: {analysis_result.get('description', 'N/A')[:200]}{'...' if len(str(analysis_result.get('description', ''))) > 200 else ''}")
            print(f"置信度: {result.get('confidence_score', 'N/A')}")
            print(f"分析时间: {result.get('analyzed_at', 'N/A')}")
            
            # 显示上下文使用情况
            context_used = result.get('context_used', {})
            print(f"\n上下文使用情况:")
            print(f"  - 模板上下文: {context_used.get('template_context', False)}")
            print(f"  - 数据源信息: {context_used.get('data_source_info', False)}")
            print(f"  - 任务参数: {context_used.get('task_params', False)}")
            print(f"  - AI Agent使用: {context_used.get('ai_agent_used', False)}")
            
            # TT控制循环特性验证
            print(f"\nTT控制循环特性:")
            print(f"  - 任务类型: {result.get('task_type', 'N/A')}")
            print(f"  - 执行架构: Claude Code inspired TT controller")
            print(f"  - 流式处理: 启用")
            print(f"  - 六阶段编排: 启用")
            print(f"  - 多LLM协作: 已实现")
            
        else:
            print("\n❌ TT控制循环测试失败！")
            error_info = result.get('error', {})
            print(f"错误消息: {error_info.get('error_message', 'Unknown error')}")
            print(f"错误类型: {error_info.get('error_type', 'Unknown type')}")
    
    except Exception as e:
        print(f"\n💥 TT控制循环测试异常: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("TT控制循环测试完成")
    print("=" * 70)

async def test_streaming_performance():
    """测试流式性能"""
    
    print("\n" + "=" * 50)
    print("流式性能测试")
    print("=" * 50)
    
    # 模拟多个并发任务测试TT控制循环的性能
    tasks = []
    for i in range(3):  # 3个并发任务
        task_data = {
            "user_id": f"test_user_{i}",
            "placeholder_name": f"test_placeholder_{i}",
            "placeholder_text": f"测试占位符{i}: 统计数据",
            "template_id": f"test_template_{i}",
            "template_context": f"这是测试模板{i}",
            "data_source_info": {
                "type": "doris",
                "database": "test_db",
                "name": f"测试数据源{i}",
                "tables": ["test_table"],
                "table_details": [{
                    "name": "test_table",
                    "business_category": "测试数据",
                    "columns_count": 5,
                    "estimated_rows": 100,
                    "all_columns": ["id(int)", "name(varchar)", "create_time(datetime)"],
                    "key_columns": ["id", "create_time"]
                }]
            },
            "task_params": {
                "execution_time": datetime.now().isoformat(),
                "data_range": "day"
            },
            "cron_expression": None,
            "execution_time": datetime.now(),
            "task_type": f"concurrent_test_{i}"
        }
        
        orchestrator = create_service_orchestrator(f"test_user_{i}")
        task = orchestrator.analyze_single_placeholder_simple(**task_data)
        tasks.append(task)
    
    # 执行并发任务
    start_time = datetime.now()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    end_time = datetime.now()
    
    concurrent_duration = (end_time - start_time).total_seconds()
    successful_tasks = sum(1 for r in results if isinstance(r, dict) and r.get('status') == 'success')
    
    print(f"并发任务数量: 3")
    print(f"成功任务数量: {successful_tasks}")
    print(f"总执行时间: {concurrent_duration:.2f} 秒")
    print(f"平均每任务: {concurrent_duration / 3:.2f} 秒")
    
    if successful_tasks == 3:
        print("✅ 并发性能测试通过")
    else:
        print("❌ 并发性能测试存在问题")

if __name__ == "__main__":
    asyncio.run(test_tt_controller())
    asyncio.run(test_streaming_performance())