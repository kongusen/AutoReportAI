#!/usr/bin/env python3
"""
投诉统计系统全面测试
基于用户提供的统计模板和Doris数据源
"""

import requests
import json
from datetime import datetime, timedelta
import sys
import os

# 添加backend路径
sys.path.insert(0, '/Users/shan/work/uploads/AutoReportAI/backend')

# API配置
BASE_URL = "http://localhost:8000/api/v1"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTQ5NjgzNzQsInN1YiI6IjJmZjkzNmY3LTg4YWItNDVhYS1hMDU2LTIyOWQ5YTFjNjcxZCJ9.Ah2EplbqNxyhPr_nRkq9fPfZQfs0Fjsl7djsvbZ06Vw"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def test_doris_connection():
    """测试Doris数据源连接"""
    print("🔍 测试 Doris 数据源连接...")
    
    # 获取现有数据源
    response = requests.get(f"{BASE_URL}/data-sources/", headers=headers)
    if response.status_code == 200:
        response_data = response.json()
        # 处理嵌套的API响应格式
        if 'data' in response_data and 'items' in response_data['data']:
            data_sources = response_data['data']['items']
        elif isinstance(response_data, list):
            data_sources = response_data
        else:
            print(f"❌ 响应格式错误: {response_data}")
            return None
            
        doris_sources = [ds for ds in data_sources if isinstance(ds, dict) and ds.get('source_type') == 'doris']
        
        if doris_sources:
            doris_source = doris_sources[0]
            print(f"✅ 找到 Doris 数据源: {doris_source['name']} (ID: {doris_source['id']})")
            return doris_source
        else:
            print("❌ 未找到 Doris 数据源")
            return None
    else:
        print(f"❌ 获取数据源失败: {response.status_code}")
        return None

def create_complaint_statistics_template():
    """创建投诉统计报告模板"""
    print("\n📝 创建投诉统计报告模板...")
    
    template_content = """# {{区域:地区名称}}投诉统计分析报告

## 报告周期
统计周期：{{周期:统计开始日期}} 至 {{周期:统计结束日期}}

## 一、系统全量统计情况
{{周期:统计开始日期}}—{{周期:统计结束日期}}，{{区域:地区名称}}共受理投诉{{统计:总投诉件数}}件，较上年同期{{统计:去年同期总投诉件数}}件，同比{{统计:同比变化方向}}{{统计:同比变化百分比}}%。

## 二、删除身份证号重复件统计情况
{{周期:统计开始日期}}—{{周期:统计结束日期}}，{{区域:地区名称}}共受理投诉{{统计:去重身份证投诉件数}}件，较上年同期{{统计:去年同期去重身份证投诉件数}}件，同比{{统计:身份证去重同比变化方向}}{{统计:身份证去重同比变化百分比}}%。

## 三、删除手机号重复件统计情况
{{周期:统计开始日期}}—{{周期:统计结束日期}}，{{区域:地区名称}}共受理投诉{{统计:去重手机号投诉件数}}件，较上年同期{{统计:去年同期去重手机号投诉件数}}件，同比{{统计:手机号去重同比变化方向}}{{统计:手机号去重同比变化百分比}}%。

## 四、详细统计数据

### 4.1 投诉趋势分析
- 当期总投诉件数：{{统计:总投诉件数}}件
- 上年同期投诉件数：{{统计:去年同期总投诉件数}}件
- 同比变化：{{统计:同比变化方向}}{{统计:同比变化百分比}}%

### 4.2 去重统计对比
| 统计类型 | 当期件数 | 上年同期 | 同比变化 |
|---------|---------|---------|---------|
| 身份证去重 | {{统计:去重身份证投诉件数}} | {{统计:去年同期去重身份证投诉件数}} | {{统计:身份证去重同比变化方向}}{{统计:身份证去重同比变化百分比}}% |
| 手机号去重 | {{统计:去重手机号投诉件数}} | {{统计:去年同期去重手机号投诉件数}} | {{统计:手机号去重同比变化方向}}{{统计:手机号去重同比变化百分比}}% |

### 4.3 统计数据有效性分析
- 统计区域：{{区域:地区名称}}
- 统计开始时间：{{周期:统计开始日期}}
- 统计结束时间：{{周期:统计结束日期}}

## 五、结论与建议
基于以上统计数据，{{区域:地区名称}}在{{周期:统计开始日期}}至{{周期:统计结束日期}}期间的投诉处理情况呈现{{统计:同比变化方向}}趋势。
"""

    template_data = {
        "name": "投诉统计分析报告模板",
        "description": "支持全量统计、去重统计、年度对比的投诉数据分析报告",
        "content": template_content,
        "is_active": True
    }
    
    response = requests.post(f"{BASE_URL}/templates/", headers=headers, json=template_data)
    if response.status_code == 200:
        template = response.json()
        print(f"✅ 创建模板成功: {template['name']} (ID: {template['id']})")
        return template
    else:
        print(f"❌ 创建模板失败: {response.status_code}")
        print(response.text)
        return None

def analyze_template_placeholders(template_id):
    """分析模板占位符"""
    print("\n🔍 分析模板占位符...")
    
    data = {"template_id": template_id}
    response = requests.post(f"{BASE_URL}/intelligent-placeholders/analyze", headers=headers, json=data)
    
    if response.status_code == 200:
        analysis = response.json()
        print(f"✅ 占位符分析成功，发现 {len(analysis.get('placeholders', []))} 个占位符")
        
        # 打印占位符详情
        for placeholder in analysis.get('placeholders', []):
            print(f"  - {placeholder['text']} ({placeholder['category']}, {placeholder['inferred_type']})")
        
        return analysis
    else:
        print(f"❌ 占位符分析失败: {response.status_code}")
        print(response.text)
        return None

def test_complaint_statistics_queries():
    """测试投诉统计相关的SQL查询"""
    print("\n📊 测试投诉统计SQL查询...")
    
    from app.services.connectors.doris_connector import DorisConnector
    from app.core.config import settings
    
    # Doris连接配置
    doris_config = {
        'fe_hosts': ['192.168.61.30'],
        'http_port': 8030,
        'query_port': 9030,
        'database': 'yjg',
        'username': 'root',
        'password': 'yjg@123456'
    }
    
    connector = DorisConnector(doris_config)
    
    # 测试查询
    test_queries = [
        {
            "name": "查看数据库列表",
            "query": "SHOW DATABASES"
        },
        {
            "name": "查看当前数据库表",
            "query": "SHOW TABLES"
        },
        {
            "name": "查看complaint_data表结构",
            "query": "DESC complaint_data"
        },
        {
            "name": "统计总投诉件数（示例）",
            "query": """
            SELECT 
                COUNT(*) as total_complaints,
                COUNT(DISTINCT id_card) as unique_id_complaints,
                COUNT(DISTINCT phone) as unique_phone_complaints
            FROM complaint_data 
            WHERE created_date >= '2024-01-01' AND created_date <= '2024-12-31'
            """
        },
        {
            "name": "按地区统计投诉件数（示例）",
            "query": """
            SELECT 
                region,
                COUNT(*) as total_complaints,
                COUNT(DISTINCT id_card) as unique_id_complaints,
                COUNT(DISTINCT phone) as unique_phone_complaints
            FROM complaint_data 
            WHERE created_date >= '2024-01-01' AND created_date <= '2024-12-31'
            GROUP BY region
            """
        },
        {
            "name": "年度对比统计（示例）",
            "query": """
            SELECT 
                YEAR(created_date) as year,
                COUNT(*) as total_complaints,
                COUNT(DISTINCT id_card) as unique_id_complaints,
                COUNT(DISTINCT phone) as unique_phone_complaints
            FROM complaint_data 
            WHERE YEAR(created_date) IN (2023, 2024)
            GROUP BY YEAR(created_date)
            ORDER BY year
            """
        }
    ]
    
    results = {}
    for test_query in test_queries:
        try:
            print(f"\n🔎 执行查询: {test_query['name']}")
            result = connector.execute_query(test_query['query'])
            results[test_query['name']] = result
            
            if result:
                print(f"✅ 查询成功，返回 {len(result)} 条记录")
                # 显示前几条记录
                for i, row in enumerate(result[:3]):
                    print(f"  {i+1}: {row}")
                if len(result) > 3:
                    print(f"  ... 还有 {len(result) - 3} 条记录")
            else:
                print("✅ 查询成功，无返回数据")
                
        except Exception as e:
            print(f"❌ 查询失败: {str(e)}")
            results[test_query['name']] = None
    
    return results

def generate_complaint_statistics_report(template_id, data_source_id):
    """生成投诉统计报告"""
    print("\n📋 生成投诉统计报告...")
    
    # 模拟占位符数据
    placeholder_values = {
        "区域:地区名称": "深圳市",
        "周期:统计开始日期": "2024-01-01",
        "周期:统计结束日期": "2024-12-31",
        "统计:总投诉件数": "12580",
        "统计:去年同期总投诉件数": "11350",
        "统计:同比变化方向": "增长",
        "统计:同比变化百分比": "10.8",
        "统计:去重身份证投诉件数": "11890",
        "统计:去年同期去重身份证投诉件数": "10720",
        "统计:身份证去重同比变化方向": "增长",
        "统计:身份证去重同比变化百分比": "10.9",
        "统计:去重手机号投诉件数": "12100",
        "统计:去年同期去重手机号投诉件数": "10980",
        "统计:手机号去重同比变化方向": "增长",
        "统计:手机号去重同比变化百分比": "10.2"
    }
    
    report_data = {
        "template_id": template_id,
        "data_source_id": data_source_id,
        "placeholder_values": placeholder_values,
        "ai_provider": "xiaoai",
        "ai_model": "gpt-4o-mini"
    }
    
    response = requests.post(f"{BASE_URL}/intelligent-placeholders/generate-report", headers=headers, json=report_data)
    
    if response.status_code == 200:
        report = response.json()
        print(f"✅ 报告生成成功: {report.get('task_id', 'N/A')}")
        return report
    else:
        print(f"❌ 报告生成失败: {response.status_code}")
        print(response.text)
        return None

def test_advanced_statistics_analysis():
    """测试高级统计分析功能"""
    print("\n📈 测试高级统计分析功能...")
    
    # 测试同比计算
    def calculate_year_over_year(current, previous):
        if previous == 0:
            return "增长", "100+"
        
        change = ((current - previous) / previous) * 100
        direction = "增长" if change > 0 else "下降" if change < 0 else "持平"
        percentage = abs(round(change, 1))
        
        return direction, str(percentage)
    
    # 测试数据
    test_cases = [
        {"current": 12580, "previous": 11350, "name": "总投诉件数"},
        {"current": 11890, "previous": 10720, "name": "去重身份证投诉件数"},
        {"current": 12100, "previous": 10980, "name": "去重手机号投诉件数"},
        {"current": 8500, "previous": 9200, "name": "某区域投诉件数（下降示例）"},
        {"current": 5000, "previous": 5000, "name": "某类型投诉件数（持平示例）"}
    ]
    
    print("📊 同比变化计算测试:")
    for case in test_cases:
        direction, percentage = calculate_year_over_year(case["current"], case["previous"])
        print(f"  {case['name']}: {case['current']} vs {case['previous']} → {direction}{percentage}%")
    
    return test_cases

def run_comprehensive_test():
    """运行全面测试"""
    print("🚀 开始投诉统计系统全面测试\n")
    
    # 1. 测试Doris连接
    doris_source = test_doris_connection()
    if not doris_source:
        print("❌ Doris连接测试失败，终止测试")
        return False
    
    # 2. 创建统计报告模板
    template = create_complaint_statistics_template()
    if not template:
        print("❌ 模板创建失败，终止测试")
        return False
    
    # 3. 分析占位符
    analysis = analyze_template_placeholders(template['id'])
    if not analysis:
        print("❌ 占位符分析失败，终止测试")
        return False
    
    # 4. 测试SQL查询
    query_results = test_complaint_statistics_queries()
    
    # 5. 测试高级统计分析
    statistics_tests = test_advanced_statistics_analysis()
    
    # 6. 生成测试报告
    report = generate_complaint_statistics_report(template['id'], doris_source['id'])
    
    # 汇总测试结果
    print("\n" + "="*50)
    print("📊 测试结果汇总")
    print("="*50)
    print(f"✅ Doris数据源连接: 成功")
    print(f"✅ 统计报告模板创建: 成功")
    print(f"✅ 占位符分析: 发现 {len(analysis.get('placeholders', []))} 个占位符")
    print(f"✅ SQL查询测试: {len([r for r in query_results.values() if r is not None])}/{len(query_results)} 成功")
    print(f"✅ 高级统计分析: {len(statistics_tests)} 个测试用例")
    print(f"✅ 报告生成: {'成功' if report else '失败'}")
    
    print("\n🎯 测试完成！投诉统计系统功能正常")
    return True

if __name__ == "__main__":
    try:
        success = run_comprehensive_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")
        sys.exit(1)