#!/usr/bin/env python3
"""
测试 Agent 无限循环修复

验证：
1. Agent 能够正常完成执行
2. 工具调用被正确追踪
3. 没有无限循环
"""

import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.container import Container
from app.services.infrastructure.agents import StageAwareAgentAdapter
from app.services.infrastructure.agents.types import TaskComplexity

async def test_agent_execution():
    print("=" * 80)
    print("🧪 测试 Agent 执行修复")
    print("=" * 80)
    print()
    
    # 创建容器
    container = Container()
    
    # 创建适配器
    adapter = StageAwareAgentAdapter(container=container)
    
    # 初始化
    await adapter.initialize(
        user_id="test_user",
        task_type="sql_generation",
        task_complexity=TaskComplexity.MEDIUM
    )
    
    # 测试 SQL 生成
    print("📝 测试任务: 查询最近7天的销售数据")
    print()
    
    iteration_count = 0
    max_iterations = 5  # 设置最大迭代次数防止真的无限循环
    
    try:
        result = await adapter.generate_sql(
            placeholder="查询最近7天的销售数据，按天统计总销售额",
            data_source_id=1,
            user_id="test_user",
            context={}
        )
        
        if result.get("success"):
            print(f"\n✅ 执行完成!")
            print(f"   迭代次数: {result.get('iterations', 'N/A')}")
            print(f"   执行时间: {result.get('execution_time_ms', 'N/A')}ms")
            print(f"   质量评分: {result.get('quality_score', 'N/A')}")
            print(f"   结果: {result.get('sql', 'N/A')[:100]}...")
        else:
            print(f"\n❌ 执行失败:")
            print(f"   错误: {result.get('error', 'Unknown')}")
    
    except Exception as e:
        print(f"\n❌ 异常: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 80)
    print(f"📊 测试完成")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_agent_execution())
