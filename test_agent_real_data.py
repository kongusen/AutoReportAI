#!/usr/bin/env python3
"""
测试Agent系统与真实Doris数据的集成
"""

import requests
import json
import time
import sys
from datetime import datetime


# API配置
BASE_URL = "http://localhost:8000/api/v1"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTQ5NjgzNzQsInN1YiI6IjJmZjkzNmY3LTg4YWItNDVhYS1hMDU2LTIyOWQ5YTFjNjcxZCJ9.Ah2EplbqNxyhPr_nRkq9fPfZQfs0Fjsl7djsvbZ06Vw"

HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}


def test_data_source_connection():
    """测试数据源连接"""
    print("1️⃣ 测试数据源连接...")
    
    # 获取数据源列表
    response = requests.get(f"{BASE_URL}/data-sources/", headers=HEADERS)
    if response.status_code != 200:
        print(f"❌ 获取数据源失败: {response.text}")
        return None
    
    data_sources = response.json()["data"]["items"]
    print(f"✅ 找到 {len(data_sources)} 个数据源")
    
    # 找到Doris数据源
    doris_sources = [ds for ds in data_sources if ds["source_type"] == "doris"]
    if not doris_sources:
        print("❌ 没有找到Doris数据源")
        return None
    
    # 使用第一个Doris数据源
    data_source = doris_sources[0]
    print(f"✅ 使用数据源: {data_source['name']} (ID: {data_source['id']})")
    
    return data_source


def test_template_creation():
    """创建用于测试的模板"""
    print("\n2️⃣ 创建测试模板...")
    
    template_data = {
        "name": "Doris数据库统计报告",
        "description": "测试Agent系统与真实Doris数据的集成",
        "content": """# Doris数据库统计报告

## 系统概况
- 当前数据库数量: {{database_count}}
- 总表数量: {{total_tables}}
- 数据库列表: {{database_list}}

## 数据库详情
{{#each databases}}
- 数据库名: {{name}}
- 表数量: {{table_count}}
{{/each}}

## 报告生成时间
{{current_time}}
""",
        "category": "database_analysis",
        "is_active": True
    }
    
    response = requests.post(f"{BASE_URL}/templates/", headers=HEADERS, json=template_data)
    if response.status_code != 201:
        print(f"❌ 创建模板失败: {response.text}")
        return None
    
    template = response.json()
    print(f"✅ 模板创建成功: {template['name']} (ID: {template['id']})")
    return template


def test_intelligent_placeholder_analysis(template_id):
    """测试智能占位符分析"""
    print("\n3️⃣ 测试智能占位符分析...")
    
    response = requests.post(
        f"{BASE_URL}/intelligent-placeholders/analyze?template_id={template_id}",
        headers=HEADERS
    )
    
    if response.status_code != 200:
        print(f"❌ 占位符分析失败: {response.text}")
        return None
    
    data = response.json()["data"]
    placeholders = data["placeholders"]
    print(f"✅ 识别到 {len(placeholders)} 个占位符:")
    for p in placeholders:
        print(f"   - {p['placeholder_name']}: {p['description']}")
    
    return placeholders


def test_real_data_report_generation(template_id, data_source_id):
    """测试使用真实数据生成报告"""
    print("\n4️⃣ 测试真实数据报告生成...")
    
    # 生成报告
    response = requests.post(
        f"{BASE_URL}/intelligent-placeholders/generate-report?template_id={template_id}&data_source_id={data_source_id}",
        headers=HEADERS
    )
    
    if response.status_code != 200:
        print(f"❌ 报告生成请求失败: {response.text}")
        return None
    
    task_info = response.json()["data"]
    task_id = task_info["task_id"]
    print(f"✅ 报告生成任务启动: {task_id}")
    
    # 等待任务完成
    print("⏳ 等待任务完成...")
    max_retries = 30
    retry_count = 0
    
    while retry_count < max_retries:
        response = requests.get(
            f"{BASE_URL}/intelligent-placeholders/task/{task_id}/status",
            headers=HEADERS
        )
        
        if response.status_code != 200:
            print(f"❌ 获取任务状态失败: {response.text}")
            return None
        
        task_status = response.json()["data"]
        status = task_status["status"]
        
        print(f"   状态: {status}")
        
        if status == "completed":
            print("✅ 任务完成!")
            return task_status
        elif status == "failed":
            print(f"❌ 任务失败: {task_status.get('error', '未知错误')}")
            return task_status
        
        time.sleep(2)
        retry_count += 1
    
    print("⏰ 任务超时")
    return None


def analyze_report_content(task_status):
    """分析报告内容"""
    print("\n5️⃣ 分析报告内容...")
    
    if not task_status or task_status.get("status") != "completed":
        print("❌ 任务未完成，无法分析报告内容")
        return False
    
    result = task_status.get("result", {})
    generated_content = result.get("generated_content", "")
    placeholder_data = result.get("placeholder_data", {})
    
    print("📊 报告内容:")
    print("=" * 50)
    print(generated_content)
    print("=" * 50)
    
    print("\n📋 占位符数据:")
    for key, value in placeholder_data.items():
        print(f"   {key}: {value}")
    
    # 检查是否使用了真实数据
    has_real_data = False
    
    # 检查是否有实际的数据库信息
    if placeholder_data.get("database_count") and placeholder_data.get("database_count") != "模拟数据":
        has_real_data = True
        print("✅ 发现真实数据库统计数据")
    
    if placeholder_data.get("database_list") and "mysql" in str(placeholder_data.get("database_list")):
        has_real_data = True
        print("✅ 发现真实数据库列表")
    
    if has_real_data:
        print("🎉 成功！报告使用了真实Doris数据！")
        return True
    else:
        print("⚠️ 报告可能仍在使用模拟数据")
        return False


def main():
    """主函数"""
    print(f"🚀 开始Agent系统与真实Doris数据集成测试")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        # 1. 测试数据源连接
        data_source = test_data_source_connection()
        if not data_source:
            return False
        
        # 2. 创建测试模板
        template = test_template_creation()
        if not template:
            return False
        
        # 3. 测试智能占位符分析
        placeholders = test_intelligent_placeholder_analysis(template["id"])
        if not placeholders:
            return False
        
        # 4. 测试真实数据报告生成
        task_status = test_real_data_report_generation(template["id"], data_source["id"])
        
        # 5. 分析报告内容
        success = analyze_report_content(task_status)
        
        print("\n" + "=" * 60)
        if success:
            print("🎉 集成测试通过！Agent系统成功使用真实Doris数据！")
        else:
            print("⚠️ 集成测试部分成功，但可能仍需要进一步优化")
        
        return success
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)