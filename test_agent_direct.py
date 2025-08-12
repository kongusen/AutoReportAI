#!/usr/bin/env python3
"""
直接测试Agent系统，不通过API
"""

import asyncio
import sys
import uuid

# 添加项目根目录到Python路径
sys.path.insert(0, '/Users/shan/work/uploads/AutoReportAI/backend')

from app.services.agents.orchestrator import orchestrator
from app.models.data_source import DataSource


async def test_direct_agent():
    """直接测试Agent系统"""
    print("🔬 直接测试Agent系统...")
    
    # 模拟占位符数据
    placeholder_input = {
        "placeholder_type": "number",
        "description": "database_count", 
        "data_source_id": "1f1b09a3-35e1-4bba-ad8e-20db33e90167",
    }
    
    # 任务上下文
    task_context = {
        "template_id": "test",
        "template_name": "测试模板",
        "data_source_name": "公司数据",
        "user_id": "test-user"
    }
    
    try:
        print("调用orchestrator._process_single_placeholder...")
        
        # 直接调用orchestrator
        result = await orchestrator._process_single_placeholder(placeholder_input, task_context)
        
        print(f"结果成功: {result.success}")
        print(f"错误信息: {result.error_message}")
        
        if result.success and result.data:
            print("工作流数据类型:", type(result.data))
            
            # 检查工作流结果
            workflow_data = result.data
            if hasattr(workflow_data, 'results'):
                print(f"工作流步骤数量: {len(workflow_data.results)}")
                
                for step_id, step_result in workflow_data.results.items():
                    print(f"\n步骤 {step_id}:")
                    print(f"  - 成功: {step_result.success}")
                    print(f"  - 错误: {step_result.error_message}")
                    
                    if step_result.success and hasattr(step_result, 'data') and step_result.data:
                        print(f"  - 数据类型: {type(step_result.data)}")
                        
                        # 特别检查数据查询结果
                        if 'fetch_data' in step_id:
                            data = step_result.data
                            print(f"  - DataQuery结果:")
                            
                            if hasattr(data, 'data'):
                                query_data = data.data
                                print(f"    查询数据类型: {type(query_data)}")
                                print(f"    查询数据内容: {query_data}")
                                
                                if isinstance(query_data, list) and query_data:
                                    print(f"    数据行数: {len(query_data)}")
                                    print(f"    第一行数据: {query_data[0]}")
                            
                            if hasattr(data, 'row_count'):
                                print(f"    行数: {data.row_count}")
                                
                            # 尝试直接打印数据对象
                            print(f"    完整数据对象: {data}")
            
            print("\n✅ Agent系统运行成功！")
            return True
        else:
            print("❌ Agent系统执行失败")
            return False
            
    except Exception as e:
        print(f"❌ Agent测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    print("🚀 开始直接Agent系统测试")
    success = await test_direct_agent()
    
    if success:
        print("\n🎉 直接Agent测试成功！")
    else:
        print("\n⚠️ Agent测试失败")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)