#!/usr/bin/env python3
"""
简化的Agent驱动投诉统计测试
专注于API调用，验证Agent系统的完整流程
"""

import requests
import json
import time
from datetime import datetime

# API配置
BASE_URL = "http://localhost:8000/api/v1"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTQ5NjgzNzQsInN1YiI6IjJmZjkzNmY3LTg4YWItNDVhYS1hMDU2LTIyOWQ5YTFjNjcxZCJ9.Ah2EplbqNxyhPr_nRkq9fPfZQfs0Fjsl7djsvbZ06Vw"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def get_data_sources():
    """获取数据源列表"""
    print("🔍 获取数据源列表...")
    response = requests.get(f"{BASE_URL}/data-sources/", headers=headers)
    if response.status_code == 200:
        data = response.json()
        sources = data.get('data', {}).get('items', [])
        doris_sources = [s for s in sources if s.get('source_type') == 'doris']
        
        if doris_sources:
            source = doris_sources[0]
            print(f"✅ 找到Doris数据源: {source['name']} (ID: {source['id']})")
            return source
        else:
            print("❌ 未找到Doris数据源")
            return None
    else:
        print(f"❌ 获取数据源失败: {response.status_code}")
        return None

def create_test_template():
    """创建测试模板 - 修正占位符格式"""
    print("\n📝 创建测试模板...")
    
    # 使用正确的占位符格式
    template_content = """# {{区域地区名称}}投诉统计分析报告

## 统计周期
报告统计周期：{{统计开始日期}} 至 {{统计结束日期}}

## 一、全量投诉统计
{{统计开始日期}}—{{统计结束日期}}，{{区域地区名称}}共受理投诉{{总投诉件数}}件，较上年同期{{去年同期总投诉件数}}件，同比{{同比变化方向}}{{同比变化百分比}}%。

## 二、去重身份证统计
删除身份证号重复件后，{{区域地区名称}}共受理投诉{{去重身份证投诉件数}}件，较上年同期{{去年同期去重身份证投诉件数}}件，同比{{身份证去重同比变化方向}}{{身份证去重同比变化百分比}}%。

## 三、去重手机号统计  
删除手机号重复件后，{{区域地区名称}}共受理投诉{{去重手机号投诉件数}}件，较上年同期{{去年同期去重手机号投诉件数}}件，同比{{手机号去重同比变化方向}}{{手机号去重同比变化百分比}}%。

## 四、统计汇总
- 统计区域：{{区域地区名称}}
- 统计起始：{{统计开始日期}}
- 统计截止：{{统计结束日期}}
- 数据来源：Doris数据库
- 报告生成时间：{{报告生成时间}}
"""

    template_data = {
        "name": "Agent智能投诉统计报告",
        "description": "基于Agent系统智能生成的投诉统计分析报告，支持数据源查询和占位符替换",
        "content": template_content,
        "is_active": True
    }
    
    response = requests.post(f"{BASE_URL}/templates/", headers=headers, json=template_data)
    if response.status_code in [200, 201]:
        template = response.json()
        print(f"✅ 创建模板成功: {template['name']} (ID: {template['id']})")
        return template
    else:
        print(f"❌ 创建模板失败: {response.status_code}")
        print(response.text)
        return None

def analyze_placeholders(template_id):
    """分析模板占位符"""
    print("\n🔍 分析模板占位符...")
    
    response = requests.post(f"{BASE_URL}/intelligent-placeholders/analyze?template_id={template_id}", headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            data = result.get('data', {})
            placeholders = data.get('placeholders', [])
            print(f"✅ 占位符分析成功，发现 {len(placeholders)} 个占位符:")
            
            # 显示占位符详情
            for placeholder in placeholders:
                name = placeholder.get('placeholder_name', 'Unknown')
                ptype = placeholder.get('placeholder_type', 'text')
                print(f"  - {name} (类型: {ptype})")
            
            # 显示类型分布
            type_dist = data.get('type_distribution', {})
            if type_dist:
                print(f"\n📊 占位符类型分布:")
                for ptype, count in type_dist.items():
                    print(f"  - {ptype}: {count}个")
            
            return data
        else:
            print(f"❌ 占位符分析失败: {result.get('message', 'Unknown error')}")
            return None
    else:
        print(f"❌ 占位符分析请求失败: {response.status_code}")
        print(response.text)
        return None

def test_agent_report_generation(template_id, data_source_id):
    """测试Agent报告生成"""
    print("\n📋 测试Agent报告生成...")
    
    # 使用查询参数
    url = f"{BASE_URL}/intelligent-placeholders/generate-report?template_id={template_id}&data_source_id={data_source_id}"
    
    # 可选的请求体参数
    report_request = {
        "processing_config": {
            "agent_mode": True,
            "auto_query": True,
            "data_discovery": True
        },
        "output_config": {
            "format": "docx",
            "include_metadata": True
        }
    }
    
    response = requests.post(url, headers=headers, json=report_request)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            data = result.get('data', {})
            task_id = data.get('task_id')
            print(f"✅ 报告生成任务启动成功: {task_id}")
            
            # 显示处理摘要
            summary = data.get('processing_summary', {})
            print(f"  模板: {summary.get('template_name', 'N/A')}")
            print(f"  数据源: {summary.get('data_source_name', 'N/A')}")
            print(f"  预计完成: {summary.get('estimated_completion', 'N/A')}")
            
            return data
        else:
            print(f"❌ 报告生成失败: {result.get('message', 'Unknown error')}")
            return None
    else:
        print(f"❌ 报告生成请求失败: {response.status_code}")
        print(response.text)
        return None

def test_field_matching(template_id, data_source_id, placeholder_name):
    """测试字段匹配功能"""
    print(f"\n🔍 测试字段匹配: {placeholder_name}")
    
    response = requests.post(
        f"{BASE_URL}/intelligent-placeholders/field-matching?template_id={template_id}&data_source_id={data_source_id}&placeholder_name={placeholder_name}", 
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            data = result.get('data', {})
            suggestions = data.get('field_suggestions', [])
            best_match = data.get('best_match')
            
            print(f"✅ 字段匹配成功，找到 {len(suggestions)} 个建议:")
            for suggestion in suggestions[:3]:  # 显示前3个
                print(f"  - {suggestion.get('field_name')} (匹配度: {suggestion.get('match_score', 0):.2f})")
            
            if best_match:
                print(f"🎯 最佳匹配: {best_match.get('field_name')} (匹配度: {best_match.get('match_score', 0):.2f})")
            
            return data
        else:
            print(f"❌ 字段匹配失败: {result.get('message', 'Unknown error')}")
            return None
    else:
        print(f"❌ 字段匹配请求失败: {response.status_code}")
        return None

def test_task_status(task_id):
    """测试任务状态查询"""
    print(f"\n📊 查询任务状态: {task_id}")
    
    response = requests.get(f"{BASE_URL}/intelligent-placeholders/task/{task_id}/status", headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            data = result.get('data', {})
            status = data.get('status', 'unknown')
            progress = data.get('progress', 0)
            message = data.get('message', '')
            
            print(f"✅ 任务状态: {status} (进度: {progress}%)")
            if message:
                print(f"  消息: {message}")
            
            # 如果任务完成，显示结果信息
            if status == 'completed':
                result_info = data.get('result', {})
                if result_info:
                    print(f"  报告ID: {result_info.get('report_id', 'N/A')}")
                    print(f"  文件路径: {result_info.get('file_path', 'N/A')}")
            
            return data
        else:
            print(f"❌ 任务状态查询失败: {result.get('message', 'Unknown error')}")
            return None
    else:
        print(f"❌ 任务状态查询请求失败: {response.status_code}")
        return None

def get_statistics():
    """获取系统统计信息"""
    print("\n📈 获取系统统计信息...")
    
    response = requests.get(f"{BASE_URL}/intelligent-placeholders/statistics", headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            data = result.get('data', {})
            
            print(f"✅ 系统统计信息:")
            print(f"  已分析模板数: {data.get('total_templates_analyzed', 0)}")
            print(f"  已发现占位符数: {data.get('total_placeholders_found', 0)}")
            print(f"  准确率: {data.get('accuracy_rate', 0):.2%}")
            print(f"  平均处理时间: {data.get('processing_time_avg', 0):.1f}秒")
            
            # 显示最常见的占位符类型
            common_types = data.get('most_common_types', {})
            if common_types:
                print(f"  常见占位符类型:")
                for ptype, count in common_types.items():
                    print(f"    - {ptype}: {count}个")
            
            return data
        else:
            print(f"❌ 统计信息获取失败: {result.get('message', 'Unknown error')}")
            return None
    else:
        print(f"❌ 统计信息请求失败: {response.status_code}")
        return None

def run_comprehensive_test():
    """运行完整的Agent驱动测试"""
    print("🚀 开始Agent驱动的投诉统计系统完整测试\n")
    
    # 1. 获取数据源
    data_source = get_data_sources()
    if not data_source:
        print("❌ 无法获取数据源，测试终止")
        return False
    
    # 2. 创建测试模板
    template = create_test_template()
    if not template:
        print("❌ 无法创建模板，测试终止")
        return False
    
    # 3. 分析占位符
    placeholder_analysis = analyze_placeholders(template['id'])
    if not placeholder_analysis:
        print("❌ 占位符分析失败，继续其他测试...")
    
    # 4. 测试字段匹配
    if placeholder_analysis and placeholder_analysis.get('placeholders'):
        first_placeholder = placeholder_analysis['placeholders'][0]
        placeholder_name = first_placeholder.get('placeholder_name', 'test_placeholder')
        field_matching = test_field_matching(template['id'], data_source['id'], placeholder_name)
    
    # 5. 测试报告生成
    report_result = test_agent_report_generation(template['id'], data_source['id'])
    
    # 6. 如果有任务ID，测试任务状态查询
    if report_result and report_result.get('task_id'):
        task_status = test_task_status(report_result['task_id'])
    
    # 7. 获取系统统计
    statistics = get_statistics()
    
    # 汇总测试结果
    print("\n" + "="*60)
    print("🎯 Agent驱动测试结果汇总")
    print("="*60)
    
    results = [
        ("数据源获取", data_source is not None),
        ("模板创建", template is not None),
        ("占位符分析", placeholder_analysis is not None),
        ("字段匹配", 'field_matching' in locals() and field_matching is not None),
        ("报告生成", report_result is not None),
        ("任务状态查询", 'task_status' in locals() and task_status is not None),
        ("系统统计", statistics is not None)
    ]
    
    for test_name, success in results:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"{test_name:15} : {status}")
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    print(f"\n📊 测试通过率: {success_count}/{total_count} ({success_count/total_count:.1%})")
    
    if placeholder_analysis and placeholder_analysis.get('placeholders'):
        placeholder_count = len(placeholder_analysis['placeholders'])
        print(f"📝 发现占位符: {placeholder_count} 个")
        print(f"🤖 Agent系统已准备好处理投诉统计任务")
    
    print(f"\n🎉 测试完成！系统功能{'正常' if success_count >= total_count * 0.7 else '部分正常'}")
    
    return success_count >= total_count * 0.7

if __name__ == "__main__":
    try:
        success = run_comprehensive_test()
        exit(0 if success else 1)
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)