#!/usr/bin/env python3
"""
AutoReportAI MCP 演示工作流
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from tools.auth_tools import login
from tools.data_source_tools import create_api_data_source, list_data_sources
from tools.template_tools import create_text_template, list_templates
from tools.task_tools import create_task, list_tasks
from tools.report_tools import generate_report, list_reports

async def demo_workflow():
    """演示完整的 AutoReportAI 工作流"""
    print("🚀 AutoReportAI MCP 演示工作流")
    print("=" * 50)
    
    try:
        # 1. 登录
        print("\n1️⃣ 用户登录...")
        login_result = await login()
        print(f"   ✅ 登录成功")
        
        # 2. 创建数据源
        print("\n2️⃣ 创建API数据源...")
        ds_result = await create_api_data_source(
            name="演示数据源",
            api_url="https://jsonplaceholder.typicode.com/posts",
            description="演示用的API数据源"
        )
        print(f"   ✅ 数据源创建成功")
        
        # 3. 列出数据源
        print("\n3️⃣ 查看数据源列表...")
        ds_list = await list_data_sources()
        print(f"   📊 数据源列表获取成功")
        
        # 4. 创建模板
        print("\n4️⃣ 创建报告模板...")
        template_content = """
# 数据分析报告

## 概述
本报告基于API数据源分析生成。

## 数据统计
- 总记录数: {{total_count}}
- 分析时间: {{analysis_time}}

## 主要发现
{{main_findings}}

## 结论
{{conclusion}}
"""
        template_result = await create_text_template(
            name="演示报告模板",
            content=template_content,
            description="演示用的报告模板"
        )
        print(f"   ✅ 模板创建成功")
        
        # 5. 列出模板
        print("\n5️⃣ 查看模板列表...")
        template_list = await list_templates()
        print(f"   📝 模板列表获取成功")
        
        print("\n🎉 演示工作流完成!")
        print("\n📖 下一步操作建议:")
        print("   - 创建定时任务")
        print("   - 生成报告")
        print("   - 配置AI提供商")
        
        return True
        
    except Exception as e:
        print(f"❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(demo_workflow())
    sys.exit(0 if success else 1)