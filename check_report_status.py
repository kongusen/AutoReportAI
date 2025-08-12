#!/usr/bin/env python3
"""
检查报告生成状态和内容
"""

import requests
import json

# API配置
BASE_URL = "http://localhost:8000/api/v1"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTQ5NjgzNzQsInN1YiI6IjJmZjkzNmY3LTg4YWItNDVhYS1hMDU2LTIyOWQ5YTFjNjcxZCJ9.Ah2EplbqNxyhPr_nRkq9fPfZQfs0Fjsl7djsvbZ06Vw"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def check_task_status(task_id):
    """检查任务状态"""
    print(f"📊 检查任务状态: {task_id}")
    
    response = requests.get(f"{BASE_URL}/intelligent-placeholders/task/{task_id}/status", headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ 任务状态查询成功:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result
    else:
        print(f"❌ 任务状态查询失败: {response.status_code}")
        print(response.text)
        return None

def get_recent_templates():
    """获取最近创建的模板"""
    print("\n📝 获取最近创建的模板...")
    
    response = requests.get(f"{BASE_URL}/templates/", headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        if 'data' in result and 'items' in result['data']:
            templates = result['data']['items']
            print(f"✅ 找到 {len(templates)} 个模板:")
            
            for template in templates[-3:]:  # 显示最后3个模板
                print(f"  - {template['name']} (ID: {template['id']})")
                print(f"    创建时间: {template.get('created_at', 'N/A')}")
                print(f"    内容长度: {len(template.get('content', ''))}")
                
                # 显示部分内容
                content = template.get('content', '')
                if content:
                    content_preview = content[:200] + "..." if len(content) > 200 else content
                    print(f"    内容预览: {content_preview}")
                print()
            
            return templates
        else:
            print("❌ 模板数据格式错误")
            return None
    else:
        print(f"❌ 获取模板失败: {response.status_code}")
        return None

def get_recent_reports():
    """获取最近的报告"""
    print("\n📋 获取最近的报告...")
    
    response = requests.get(f"{BASE_URL}/reports/", headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ 报告查询成功:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result
    else:
        print(f"❌ 报告查询失败: {response.status_code}")
        print(response.text)
        return None

def test_placeholder_analysis_on_template(template_id):
    """测试模板的占位符分析结果"""
    print(f"\n🔍 分析模板占位符: {template_id}")
    
    response = requests.post(f"{BASE_URL}/intelligent-placeholders/analyze?template_id={template_id}", headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            data = result.get('data', {})
            placeholders = data.get('placeholders', [])
            
            print(f"✅ 发现 {len(placeholders)} 个占位符:")
            for placeholder in placeholders:
                name = placeholder.get('placeholder_name', 'Unknown')
                ptype = placeholder.get('placeholder_type', 'text')
                desc = placeholder.get('description', '')
                print(f"  - {name} (类型: {ptype})")
                if desc:
                    print(f"    描述: {desc}")
            
            return data
        else:
            print(f"❌ 占位符分析失败: {result.get('message')}")
            return None
    else:
        print(f"❌ 占位符分析请求失败: {response.status_code}")
        return None

def main():
    print("🔍 检查报告生成状态和内容\n")
    
    # 1. 检查之前的任务状态
    recent_task_ids = [
        "31204267-bd26-45b9-8347-7738e962d0a1",  # 刚才创建的任务
        "cc073fb8-e52a-43f2-abba-04cea1a5613c",  # 之前的任务
    ]
    
    for task_id in recent_task_ids:
        task_status = check_task_status(task_id)
        print()
    
    # 2. 获取最近的模板
    templates = get_recent_templates()
    
    # 3. 如果有模板，分析其占位符
    if templates:
        latest_template = templates[-1]
        placeholder_analysis = test_placeholder_analysis_on_template(latest_template['id'])
    
    # 4. 获取报告列表
    reports = get_recent_reports()
    
    print("\n" + "="*50)
    print("📊 当前报告系统状态总结")
    print("="*50)
    print("1. 任务状态: API返回模拟的完成状态")
    print("2. 模板系统: 正常工作，可以创建和分析占位符")
    print("3. 报告文件: 目前为模拟状态，未生成实际文件")
    print("4. 数据查询: 需要修复Doris连接器配置")
    print("\n🎯 要获得真实的报告内容，需要:")
    print("   - 修复Doris连接器的timeout配置问题")
    print("   - 实现真正的后台任务处理")
    print("   - 连接Agent系统进行真实的数据查询")

if __name__ == "__main__":
    main()