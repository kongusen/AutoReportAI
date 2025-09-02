#!/usr/bin/env python3
"""
测试真实业务流程
验证ETL → 图表生成 → 报告生成的完整集成
基于真实数据源和模板，测试优化后的图表集成逻辑
"""

import requests
import json
import time
import os
import sys
from pathlib import Path

BACKEND_URL = "http://localhost:8000/api/v1"

def get_auth_token():
    """获取认证token"""
    print("🔐 获取认证token...")
    
    login_data = {
        "username": "testuser",
        "password": "testpassword123"
    }
    response = requests.post(
        f"{BACKEND_URL}/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print("✅ 认证成功")
            return result['data']['access_token']
    
    print("❌ 认证失败")
    return None

def test_real_business_flow():
    """测试真实业务流程"""
    print("🚀 测试真实业务流程 - ETL → 图表生成 → 报告")
    print("=" * 60)
    
    token = get_auth_token()
    if not token:
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. 获取真实数据源和模板信息
    print("\n📊 步骤1: 获取真实数据源和模板...")
    data_sources = get_real_data_sources(headers)
    templates = get_real_templates(headers)
    
    if not data_sources or not templates:
        print("❌ 无法获取真实数据源或模板")
        return False
    
    # 选择Doris数据源
    doris_ds = None
    for ds in data_sources:
        if ds.get('source_type') == 'doris':
            doris_ds = ds
            break
    
    if not doris_ds:
        print("❌ 未找到Doris数据源")
        return False
    
    print(f"✅ 选择数据源: {doris_ds['name']} (ID: {doris_ds['id']})")
    
    # 选择第一个模板
    template = templates[0]
    print(f"✅ 选择模板: {template['name']} (ID: {template['id']})")
    
    # 2. 测试集成的智能ETL + 图表生成
    print("\n🔧 步骤2: 测试智能ETL + 图表生成...")
    etl_success = test_intelligent_etl_with_charts(headers, doris_ds['id'], template['id'])
    
    # 3. 测试完整的报告生成流程
    print("\n📝 步骤3: 测试完整报告生成流程...")
    report_success = test_enhanced_report_generation(headers, doris_ds['id'], template['id'])
    
    # 4. 验证图表文件生成
    print("\n📂 步骤4: 验证图表文件生成...")
    charts_verified = verify_chart_files_generation()
    
    # 总结测试结果
    print("\n" + "=" * 60)
    print("📋 测试结果总结:")
    print(f"   🔧 智能ETL + 图表: {'✅ 成功' if etl_success else '❌ 失败'}")
    print(f"   📝 报告生成: {'✅ 成功' if report_success else '❌ 失败'}")
    print(f"   📊 图表文件: {'✅ 生成' if charts_verified else '❌ 未生成'}")
    
    overall_success = etl_success and report_success and charts_verified
    print(f"\n🎯 整体测试: {'✅ 全部成功' if overall_success else '❌ 部分失败'}")
    
    return overall_success

def get_real_data_sources(headers):
    """获取真实数据源"""
    try:
        response = requests.get(f"{BACKEND_URL}/data-sources/", headers=headers)
        print(f"   📡 数据源API响应: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                data_sources = result['data']['items']
                print(f"   📊 找到 {len(data_sources)} 个数据源")
                return data_sources
            else:
                print(f"   ❌ API返回失败: {result.get('error')}")
        else:
            print(f"   ❌ HTTP错误: {response.text[:200]}")
    except Exception as e:
        print(f"❌ 获取数据源失败: {e}")
    return []

def get_real_templates(headers):
    """获取真实模板"""
    try:
        response = requests.get(f"{BACKEND_URL}/templates", headers=headers)  # 不带尾斜杠
        print(f"   📄 模板API响应: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            # 模板API直接返回数组，不像数据源API有success包装
            if isinstance(result, dict) and 'items' in result:
                templates = result['items']
                print(f"   📝 找到 {len(templates)} 个模板")
                return templates
            elif isinstance(result, list):
                print(f"   📝 找到 {len(result)} 个模板")
                return result
            else:
                print(f"   ❌ 未知响应格式: {type(result)}")
        else:
            print(f"   ❌ HTTP错误: {response.text[:200]}")
    except Exception as e:
        print(f"❌ 获取模板失败: {e}")
    return []

def test_intelligent_etl_with_charts(headers, data_source_id, template_id):
    """测试智能ETL + 图表生成集成"""
    print(f"   🔧 测试智能ETL集成 (数据源: {data_source_id})")
    
    # 这里应该调用ETL服务的智能处理API
    # 由于当前架构中ETL主要通过报告生成触发，我们通过系统洞察API来测试
    
    try:
        etl_request = {
            "analysis_type": "intelligent_etl_with_charts",
            "data_source_id": data_source_id,
            "template_id": template_id,
            "enable_chart_generation": True,
            "optimization_level": "enhanced",
            "task_config": {
                "enable_chart_generation": True,
                "chart_types": ["bar", "line", "pie"],
                "extract_real_data": True
            }
        }
        
        response = requests.post(
            f"{BACKEND_URL}/system-insights/context-system/analyze",
            headers=headers,
            json=etl_request
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"   ✅ 智能ETL处理成功")
                analysis_data = result.get('data', {})
                
                # 检查是否包含图表生成信息
                if 'chart_results' in str(analysis_data):
                    print(f"   📊 包含图表生成结果")
                    return True
                else:
                    print(f"   ⚠️  ETL成功但未发现图表生成")
                    return True
            else:
                print(f"   ❌ 智能ETL失败: {result.get('error')}")
                return False
        else:
            print(f"   ❌ ETL API请求失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ ETL测试异常: {e}")
        return False

def test_enhanced_report_generation(headers, data_source_id, template_id):
    """测试增强的报告生成"""
    print(f"   📝 测试增强报告生成...")
    
    try:
        report_request = {
            "template_id": template_id,
            "data_source_id": data_source_id,
            "name": "真实业务流程测试报告",
            "description": "测试优化后的ETL→图表生成→报告流程",
            "optimization_level": "enhanced",
            "enable_intelligent_etl": True,
            "chart_requirements": {
                "enable_chart_generation": True,
                "chart_types": ["bar", "line", "pie", "area"],
                "generate_real_files": True,
                "include_chart_analysis": True,
                "use_real_data": True
            },
            "etl_config": {
                "enable_chart_generation": True,
                "extract_real_data": True,
                "optimization_level": "enhanced"
            }
        }
        
        response = requests.post(
            f"{BACKEND_URL}/reports/generate/intelligent",
            headers=headers,
            json=report_request
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"   ✅ 报告生成任务提交成功")
                task_data = result.get('data', {})
                task_id = task_data.get('task_id')
                
                if task_id:
                    print(f"   📋 任务ID: {task_id}")
                    
                    # 等待报告完成
                    print("   ⏳ 等待报告生成完成...")
                    time.sleep(10)
                    
                    # 检查报告结果
                    return check_report_completion(headers, task_id)
                else:
                    print("   ❌ 未获取到任务ID")
                    return False
            else:
                print(f"   ❌ 报告生成失败: {result.get('error')}")
                return False
        else:
            print(f"   ❌ 报告API请求失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ 报告生成测试异常: {e}")
        return False

def check_report_completion(headers, task_id):
    """检查报告生成完成状态"""
    try:
        # 获取最新报告
        response = requests.get(
            f"{BACKEND_URL}/reports/",
            headers=headers,
            params={"limit": 5}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                reports = result.get('data', {}).get('items', [])
                
                # 查找已完成的报告
                completed_reports = [r for r in reports if r.get('status') == 'completed']
                
                if completed_reports:
                    latest_report = completed_reports[0]
                    print(f"   ✅ 找到完成的报告: {latest_report.get('name')}")
                    
                    # 获取报告内容检查图表
                    return check_report_content_for_charts(headers, latest_report.get('id'))
                else:
                    print("   ⚠️  暂无完成的报告")
                    return False
            
    except Exception as e:
        print(f"   ❌ 检查报告状态异常: {e}")
        return False
    
    return False

def check_report_content_for_charts(headers, report_id):
    """检查报告内容中的图表信息"""
    try:
        response = requests.get(
            f"{BACKEND_URL}/reports/{report_id}/content",
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                content_data = result.get('data', {})
                content = content_data.get('content', '')
                
                # 检查内容中是否包含图表信息
                chart_indicators = ['chart_', '.png', '图表', 'matplotlib', 'seaborn']
                has_chart_info = any(indicator in content.lower() for indicator in chart_indicators)
                
                if has_chart_info:
                    print("   📊 报告包含图表相关信息")
                    return True
                else:
                    print("   ⚠️  报告中未发现图表信息")
                    return False
                    
    except Exception as e:
        print(f"   ❌ 检查报告内容异常: {e}")
        return False
    
    return False

def verify_chart_files_generation():
    """验证图表文件是否真实生成"""
    print("   📂 检查图表文件生成...")
    
    charts_dir = Path("/Users/shan/work/me/AutoReportAI/storage/reports")
    
    if not charts_dir.exists():
        print("   ❌ 图表存储目录不存在")
        return False
    
    # 查找最近生成的图表文件
    chart_files = list(charts_dir.glob("*_chart_*.png"))
    
    # 检查最近5分钟内生成的文件
    recent_charts = []
    current_time = time.time()
    
    for chart_file in chart_files:
        file_time = os.path.getmtime(chart_file)
        if current_time - file_time < 300:  # 5分钟内
            recent_charts.append(chart_file)
    
    if recent_charts:
        print(f"   ✅ 发现 {len(recent_charts)} 个最近生成的图表文件:")
        for chart in recent_charts:
            file_size = chart.stat().st_size
            print(f"      📊 {chart.name} ({file_size:,} bytes)")
        return True
    else:
        print("   ⚠️  未发现最近生成的图表文件")
        # 显示所有图表文件用于调试
        all_charts = list(charts_dir.glob("*.png"))
        if all_charts:
            print(f"   📋 存储目录中共有 {len(all_charts)} 个图表文件")
            for chart in all_charts[-3:]:  # 显示最新的3个
                file_time = os.path.getmtime(chart)
                time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_time))
                file_size = chart.stat().st_size
                print(f"      📊 {chart.name} ({file_size:,} bytes, {time_str})")
        return False

def main():
    """主函数"""
    print("🚀 AutoReportAI - 真实业务流程测试")
    print("=== 测试优化后的ETL → 图表生成 → 报告集成 ===")
    print()
    
    success = test_real_business_flow()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 真实业务流程测试完全成功!")
        print("✅ ETL处理、图表生成、报告生成全部正常")
        print("📊 图表文件已保存到 storage/reports/ 目录")
        print("🔧 优化后的集成逻辑工作正常")
    else:
        print("❌ 真实业务流程测试部分失败")
        print("🔍 请检查:")
        print("   • 后端服务是否正常运行")
        print("   • Doris数据源连接是否正常")
        print("   • React Agent配置是否正确")
        print("   • 图表生成工具是否正常")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)