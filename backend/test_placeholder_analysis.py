#!/usr/bin/env python3
"""
占位符分析测试脚本
测试 Agent 系统和兜底机制
"""

import asyncio
import logging
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.application.factories import create_service_orchestrator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_placeholder_analysis():
    """测试占位符分析功能"""
    
    print("=" * 60)
    print("测试占位符分析功能")
    print("=" * 60)
    
    # 创建服务编排器
    orchestrator = create_service_orchestrator("test_user_123")
    
    # 测试数据 - 模拟没有时间信息的情况
    test_data = {
        "user_id": "test_user_123",
        "placeholder_name": "period_start_date",
        "placeholder_text": "周期:统计开始日期",
        "template_id": "test_template_123",
        "template_context": "这是一个测试模板，用于统计分析",
        "data_source_info": {
            "type": "doris",
            "database": "yjg",
            "name": "测试数据源",
            "tables": ["ods_complain", "user_table"],
            "table_details": [{
                "name": "ods_complain",
                "business_category": "投诉数据",
                "columns_count": 10,
                "estimated_rows": 1000,
                "all_columns": ["id(bigint)", "create_time(datetime)", "complaint_content(text)"],
                "key_columns": ["id", "create_time", "complaint_content"]
            }]
        },
        # 注意：这里故意不提供 task_params, cron_expression, execution_time
        # 来测试固定时间信息的生成
        "task_params": {},
        "cron_expression": None,
        "execution_time": None,
        "task_type": "manual"
    }
    
    try:
        print("开始执行占位符分析...")
        print(f"占位符: {test_data['placeholder_text']}")
        print(f"模板ID: {test_data['template_id']}")
        print(f"数据源: {test_data['data_source_info']['name']}")
        
        # 执行分析
        result = await orchestrator.analyze_single_placeholder_simple(**test_data)
        
        print("\n" + "=" * 40)
        print("分析结果:")
        print("=" * 40)
        print(f"状态: {result.get('status')}")
        print(f"占位符名称: {result.get('placeholder_name')}")
        
        if result.get('status') == 'success':
            print("\n✅ 分析成功！")
            
            # 显示生成的SQL
            generated_sql = result.get('generated_sql', {})
            if isinstance(generated_sql, dict):
                sql_content = generated_sql.get('sql') or generated_sql.get(test_data['placeholder_name'], '')
            else:
                sql_content = str(generated_sql)
            
            print(f"\n生成的SQL:")
            print("-" * 40)
            print(sql_content)
            
            # 显示分析结果
            analysis_result = result.get('analysis_result', {})
            print(f"\n分析描述: {analysis_result.get('description', 'N/A')}")
            print(f"置信度: {result.get('confidence_score', 'N/A')}")
            print(f"分析时间: {result.get('analyzed_at', 'N/A')}")
            
            # 显示上下文使用情况
            context_used = result.get('context_used', {})
            print(f"\n上下文使用:")
            print(f"  - 模板上下文: {context_used.get('template_context', False)}")
            print(f"  - 数据源信息: {context_used.get('data_source_info', False)}")
            print(f"  - AI Agent: {context_used.get('ai_agent_used', False)}")
            
        else:
            print("\n❌ 分析失败！")
            error_info = result.get('error', {})
            print(f"错误消息: {error_info.get('error_message', 'Unknown error')}")
            print(f"错误类型: {error_info.get('error_type', 'Unknown type')}")
    
    except Exception as e:
        print(f"\n💥 测试执行异常: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_placeholder_analysis())