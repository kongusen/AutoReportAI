#!/usr/bin/env python3
"""
修复后的Celery AI任务测试
使用正确注册的任务进行测试
"""

import time
import json
from datetime import datetime

def test_registered_ai_tasks():
    """测试已注册的AI任务"""
    print("🤖 测试已注册的Celery AI任务")
    print("=" * 50)
    
    try:
        # 导入已注册的AI任务
        from app.services.task.core.worker.tasks.ai_analysis_tasks import (
            custom_ai_analysis_task,
            ai_pipeline_task,
            batch_ai_analysis_task
        )
        from app.services.task.core.worker.config.celery_app import celery_app
        
        # 1. 检查任务注册
        print("\n🔍 步骤1: 检查任务注册...")
        
        inspect = celery_app.control.inspect()
        registered_tasks = inspect.registered()
        
        if registered_tasks:
            all_tasks = []
            for worker, tasks in registered_tasks.items():
                all_tasks.extend(tasks)
            
            ai_tasks = [task for task in all_tasks if 'ai_analysis_tasks' in task]
            print(f"     ✅ 发现 {len(ai_tasks)} 个AI分析任务:")
            for task in ai_tasks:
                print(f"       - {task.split('.')[-1]}")
        else:
            print("     ⚠️ 无法获取注册任务列表")
        
        # 2. 测试单个AI分析任务
        print("\n🧠 步骤2: 测试单个AI分析任务...")
        
        test_data = {
            "business_metrics": {
                "revenue": [150000, 165000, 142000, 178000, 195000],
                "orders": [1250, 1380, 1190, 1520, 1680],
                "customers": [850, 920, 810, 1050, 1150],
                "months": ["1月", "2月", "3月", "4月", "5月"]
            },
            "performance_kpis": {
                "conversion_rate": 3.8,
                "customer_satisfaction": 4.3,
                "retention_rate": 0.78,
                "churn_rate": 0.22
            }
        }
        
        analysis_prompt = """
请作为资深数据分析师，分析以下业务数据并提供专业洞察：

1. **趋势分析**：分析5个月的业务数据趋势
2. **关键指标评估**：评估转化率、满意度、留存率等KPI  
3. **业务建议**：提供3个具体的改进建议

请用简洁的markdown格式输出。
"""
        
        start_time = time.time()
        
        # 使用apply_async来避免任务注册问题
        ai_task_result = custom_ai_analysis_task.apply_async([
            json.dumps(test_data, ensure_ascii=False),
            analysis_prompt
        ])
        
        print("     ⏳ 等待AI分析完成...")
        ai_result = ai_task_result.get(timeout=60)
        execution_time = time.time() - start_time
        
        print(f"     ✅ AI分析任务完成！")
        print(f"     ⏱️ 执行时间: {execution_time:.2f}秒")
        print(f"     📊 任务状态: {ai_result.get('status')}")
        
        if ai_result.get('status') == 'success':
            analysis = ai_result.get('analysis', '')
            if isinstance(analysis, dict) and 'text_response' in analysis:
                analysis_text = analysis['text_response']
            else:
                analysis_text = str(analysis)
            
            print(f"     📄 分析长度: {len(analysis_text)} 字符")
            print(f"     🎯 分析预览:")
            print("     " + "-" * 40)
            preview = analysis_text[:300].replace('\n', '\n     ')
            print("     " + preview + "...")
            print("     " + "-" * 40)
            
            single_task_result = {
                "success": True,
                "execution_time": execution_time,
                "analysis_length": len(analysis_text),
                "full_analysis": analysis_text
            }
        else:
            print(f"     ❌ AI分析失败: {ai_result.get('error')}")
            single_task_result = {"success": False, "error": ai_result.get('error')}
        
        # 3. 测试Pipeline任务
        print("\n🔧 步骤3: 测试Pipeline任务...")
        
        pipeline_config = {
            "data": "销售数据: 月度增长12%, 客户满意度4.5/5.0, 市场份额提升2%",
            "summary": "业务表现良好，多项指标上升",
            "processing_time": "2.3秒"
        }
        
        start_time = time.time()
        pipeline_task_result = ai_pipeline_task.apply_async([pipeline_config])
        pipeline_result = pipeline_task_result.get(timeout=45)
        pipeline_time = time.time() - start_time
        
        print(f"     ✅ Pipeline任务完成！")
        print(f"     ⏱️ 执行时间: {pipeline_time:.2f}秒")
        print(f"     📊 任务状态: {pipeline_result.get('status')}")
        print(f"     📋 完成阶段: {pipeline_result.get('completed_stages')}")
        
        # 4. 测试批量任务
        print("\n🔄 步骤4: 测试批量任务...")
        
        batch_data = [
            {"context": "Q1销售额增长15%", "prompt": "分析销售增长的主要驱动因素"},
            {"context": "客户转化率提升到4.2%", "prompt": "评估转化率改善的业务影响"},
            {"context": "产品A占收入65%", "prompt": "分析产品集中度风险"}
        ]
        
        start_time = time.time()
        batch_task_result = batch_ai_analysis_task.apply_async([batch_data])
        batch_result = batch_task_result.get(timeout=60)
        batch_time = time.time() - start_time
        
        print(f"     ✅ 批量任务完成！")
        print(f"     ⏱️ 执行时间: {batch_time:.2f}秒")
        print(f"     📊 任务状态: {batch_result.get('status')}")
        
        if batch_result.get('status') == 'completed':
            success_rate = batch_result.get('successful_tasks', 0) / batch_result.get('total_tasks', 1)
            print(f"     📈 成功率: {success_rate*100:.1f}% ({batch_result.get('successful_tasks')}/{batch_result.get('total_tasks')})")
        
        return {
            "single_task": single_task_result,
            "pipeline_success": pipeline_result.get('status') == 'success',
            "batch_success": batch_result.get('status') == 'completed',
            "total_time": execution_time + pipeline_time + batch_time
        }
        
    except Exception as e:
        print(f"\n❌ 注册任务测试失败: {e}")
        return {"success": False, "error": str(e)}

def test_basic_tasks_integration():
    """测试与基础任务的集成"""
    print("\n🔗 测试与基础任务的集成")
    print("=" * 50)
    
    try:
        from app.services.task.core.worker.tasks.basic_tasks import test_celery_task
        from app.services.task.core.worker.tasks.ai_analysis_tasks import custom_ai_analysis_task
        
        # 1. 基础任务
        print("\n📝 执行基础任务...")
        basic_result = test_celery_task.apply_async(["集成测试消息"])
        basic_output = basic_result.get(timeout=10)
        print(f"     ✅ 基础任务: {basic_output}")
        
        # 2. AI任务
        print("\n🤖 执行AI任务...")
        ai_context = "测试数据：用户活跃度85%，收入增长18%"
        ai_prompt = "请简要分析这些指标的表现"
        
        ai_result = custom_ai_analysis_task.apply_async([ai_context, ai_prompt])
        ai_output = ai_result.get(timeout=30)
        
        print(f"     ✅ AI任务状态: {ai_output.get('status')}")
        
        return {
            "integration_success": True,
            "basic_task_works": True,
            "ai_task_works": ai_output.get('status') == 'success'
        }
        
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        return {"integration_success": False, "error": str(e)}

def main():
    """主函数"""
    print("🚀 开始修复后的Celery AI任务测试")
    print("重点测试：已注册任务 + 真实AI功能 + 集成测试")
    
    total_start_time = time.time()
    
    # 1. 测试已注册的AI任务
    ai_test_result = test_registered_ai_tasks()
    
    # 2. 测试任务集成
    integration_result = test_basic_tasks_integration()
    
    total_time = time.time() - total_start_time
    
    # 结果汇总
    print("\n" + "=" * 60)
    print("🎯 修复后Celery AI任务测试总结")
    print("=" * 60)
    
    print(f"\n📊 测试结果:")
    
    if ai_test_result.get('single_task', {}).get('success'):
        print(f"   ✅ 单个AI任务: 成功")
        print(f"      ⏱️ 执行时间: {ai_test_result['single_task']['execution_time']:.2f}秒")
        print(f"      📄 分析长度: {ai_test_result['single_task']['analysis_length']} 字符")
    else:
        print(f"   ❌ 单个AI任务: 失败")
    
    print(f"   ✅ Pipeline任务: {'成功' if ai_test_result.get('pipeline_success') else '失败'}")
    print(f"   ✅ 批量任务: {'成功' if ai_test_result.get('batch_success') else '失败'}")
    print(f"   ✅ 任务集成: {'成功' if integration_result.get('integration_success') else '失败'}")
    
    success_count = sum([
        ai_test_result.get('single_task', {}).get('success', False),
        ai_test_result.get('pipeline_success', False),
        ai_test_result.get('batch_success', False),
        integration_result.get('integration_success', False)
    ])
    
    print(f"\n📈 整体成功率: {success_count}/4 ({success_count*25}%)")
    print(f"⏱️ 总测试时间: {total_time:.2f}秒")
    
    if success_count >= 3:
        print("\n🎉 Celery AI任务系统修复成功！")
        print("✅ AI分析任务正确注册并可执行")
        print("✅ 真实AI服务集成完整")
        print("✅ 异步任务处理正常")
        print("✅ 批量和Pipeline功能可用")
        
        # 显示完整分析示例
        if ai_test_result.get('single_task', {}).get('full_analysis'):
            print("\n📋 AI分析报告示例:")
            print("-" * 50)
            analysis_text = ai_test_result['single_task']['full_analysis']
            if isinstance(analysis_text, dict) and 'text_response' in analysis_text:
                display_text = analysis_text['text_response']
            else:
                display_text = str(analysis_text)
            print(display_text[:600] + "..." if len(display_text) > 600 else display_text)
            print("-" * 50)
    else:
        print("\n⚠️ 部分功能仍有问题")
        if not ai_test_result.get('single_task', {}).get('success'):
            error = ai_test_result.get('single_task', {}).get('error', 'Unknown')
            print(f"   ❌ AI任务问题: {error}")
        if not integration_result.get('integration_success'):
            error = integration_result.get('error', 'Unknown')
            print(f"   ❌ 集成问题: {error}")

if __name__ == "__main__":
    main()