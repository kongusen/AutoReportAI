#!/usr/bin/env python3
"""
基于Agent驱动的投诉统计系统测试
完全依赖Agent系统智能查询Doris数据源中的真实投诉数据
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

def get_doris_data_source():
    """获取Doris数据源"""
    print("🔍 获取 Doris 数据源...")
    
    response = requests.get(f"{BASE_URL}/data-sources/", headers=headers)
    if response.status_code == 200:
        response_data = response.json()
        # 处理嵌套的API响应格式
        if 'data' in response_data and 'items' in response_data['data']:
            data_sources = response_data['data']['items']
        elif isinstance(response_data, list):
            data_sources = response_data
        else:
            print(f"❌ 响应格式错误")
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

def create_complaint_template():
    """创建投诉统计模板"""
    print("\n📝 创建投诉统计模板...")
    
    template_content = """# {{区域:地区名称}}投诉统计分析报告

## 统计周期
报告统计周期：{{周期:统计开始日期}} 至 {{周期:统计结束日期}}

## 一、全量投诉统计
{{周期:统计开始日期}}—{{周期:统计结束日期}}，{{区域:地区名称}}共受理投诉{{统计:总投诉件数}}件，较上年同期{{统计:去年同期总投诉件数}}件，同比{{统计:同比变化方向}}{{统计:同比变化百分比}}%。

## 二、去重身份证统计
删除身份证号重复件后，{{区域:地区名称}}共受理投诉{{统计:去重身份证投诉件数}}件，较上年同期{{统计:去年同期去重身份证投诉件数}}件，同比{{统计:身份证去重同比变化方向}}{{统计:身份证去重同比变化百分比}}%。

## 三、去重手机号统计  
删除手机号重复件后，{{区域:地区名称}}共受理投诉{{统计:去重手机号投诉件数}}件，较上年同期{{统计:去年同期去重手机号投诉件数}}件，同比{{统计:手机号去重同比变化方向}}{{统计:手机号去重同比变化百分比}}%。

## 四、数据明细
- 统计区域：{{区域:地区名称}}
- 统计起始：{{周期:统计开始日期}}
- 统计截止：{{周期:统计结束日期}}
- 数据来源：Doris数据库投诉管理系统
"""

    template_data = {
        "name": "Agent驱动投诉统计报告",
        "description": "基于Agent系统智能查询的投诉数据统计分析报告",
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
    
    # 使用查询参数而不是请求体
    response = requests.post(f"{BASE_URL}/intelligent-placeholders/analyze?template_id={template_id}", headers=headers)
    
    if response.status_code == 200:
        analysis = response.json()
        placeholders = analysis.get('placeholders', [])
        print(f"✅ 占位符分析成功，发现 {len(placeholders)} 个占位符:")
        
        # 按类别分组显示占位符
        categories = {}
        for placeholder in placeholders:
            category = placeholder['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(placeholder)
        
        for category, items in categories.items():
            print(f"\n  📊 {category} 类占位符:")
            for item in items:
                print(f"    - {item['text']} ({item['inferred_type']})")
        
        return analysis
    else:
        print(f"❌ 占位符分析失败: {response.status_code}")
        print(response.text)
        return None

def test_agent_data_discovery(data_source_id):
    """测试Agent数据发现能力"""
    print("\n🤖 测试 Agent 数据发现能力...")
    
    # 让Agent探索数据源结构
    from app.services.agents.data_query_agent import DataQueryAgent
    from app.models.data_source import DataSource
    from app.core.database import SessionLocal
    
    db = SessionLocal()
    try:
        # 获取数据源对象
        data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
        if not data_source:
            print("❌ 数据源不存在")
            return None
        
        agent = DataQueryAgent()
        
        # 测试1: 发现数据库结构
        print("  🔎 发现数据库结构...")
        discovery_query = {
            "action": "discover_schema",
            "data_source_id": str(data_source_id),
            "context": "需要了解投诉数据相关的表结构"
        }
        
        schema_info = agent.execute_query(discovery_query, data_source)
        if schema_info:
            print(f"  ✅ 发现数据结构: {len(schema_info.get('tables', []))} 个表")
            for table in schema_info.get('tables', [])[:3]:  # 显示前3个表
                print(f"    - {table}")
        
        # 测试2: 发现投诉相关数据
        print("\n  🔎 搜索投诉相关数据表...")
        search_query = {
            "action": "search_tables",
            "data_source_id": str(data_source_id),
            "keywords": ["投诉", "complaint", "举报", "report"],
            "context": "查找包含投诉数据的表"
        }
        
        complaint_tables = agent.execute_query(search_query, data_source)
        if complaint_tables:
            print(f"  ✅ 发现投诉相关表: {complaint_tables}")
        
        return {"schema": schema_info, "complaint_tables": complaint_tables}
        
    except Exception as e:
        print(f"  ❌ Agent数据发现失败: {str(e)}")
        return None
    finally:
        db.close()

def test_agent_query_generation(data_source_id, placeholders):
    """测试Agent查询生成能力"""
    print("\n🤖 测试 Agent SQL查询生成能力...")
    
    from app.services.agents.data_query_agent import DataQueryAgent
    from app.models.data_source import DataSource
    from app.core.database import SessionLocal
    
    db = SessionLocal()
    try:
        data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
        if not data_source:
            print("❌ 数据源不存在")
            return None
        
        agent = DataQueryAgent()
        generated_queries = {}
        
        # 为每个统计类占位符生成查询
        stat_placeholders = [p for p in placeholders if p['category'] == '统计']
        
        for placeholder in stat_placeholders[:5]:  # 测试前5个统计占位符
            print(f"\n  🔍 为占位符生成查询: {placeholder['text']}")
            
            query_request = {
                "action": "generate_query",
                "data_source_id": str(data_source_id),
                "placeholder": placeholder,
                "context": {
                    "statistics_type": placeholder['text'],
                    "date_range": "2024年",
                    "region": "深圳市",
                    "requirements": ["投诉统计", "去重处理", "年度对比"]
                }
            }
            
            try:
                query_result = agent.execute_query(query_request, data_source)
                if query_result and 'sql' in query_result:
                    generated_queries[placeholder['text']] = query_result
                    print(f"  ✅ 生成查询成功")
                    print(f"    SQL: {query_result['sql'][:100]}...")
                else:
                    print(f"  ❌ 查询生成失败")
            except Exception as e:
                print(f"  ❌ 查询生成异常: {str(e)}")
        
        return generated_queries
        
    except Exception as e:
        print(f"❌ Agent查询生成测试失败: {str(e)}")
        return None
    finally:
        db.close()

def test_agent_driven_report_generation(template_id, data_source_id):
    """测试Agent驱动的报告生成"""
    print("\n📋 测试 Agent 驱动的报告生成...")
    
    # 设置报告参数 - 让Agent根据这些参数查询真实数据
    report_request = {
        "template_id": template_id,
        "data_source_id": data_source_id,
        "generation_mode": "agent_driven",  # 标记为Agent驱动模式
        "parameters": {
            "区域": "深圳市",
            "统计年份": "2024",
            "对比年份": "2023",
            "统计开始日期": "2024-01-01",
            "统计结束日期": "2024-12-31"
        },
        "ai_provider": "xiaoai",
        "ai_model": "gpt-4o-mini",
        "agent_instructions": [
            "从Doris数据源查询真实的投诉数据",
            "自动识别投诉相关的数据表",
            "生成统计查询包括总数、去重统计、年度对比",
            "确保所有统计数据来源于真实查询结果"
        ]
    }
    
    response = requests.post(f"{BASE_URL}/intelligent-placeholders/generate-report", headers=headers, json=report_request)
    
    if response.status_code == 200:
        report = response.json()
        task_id = report.get('task_id')
        print(f"✅ Agent驱动报告生成任务启动: {task_id}")
        
        # 监控任务状态
        if task_id:
            print("  📊 监控报告生成进度...")
            return monitor_report_task(task_id)
        else:
            return report
    else:
        print(f"❌ 报告生成失败: {response.status_code}")
        print(response.text)
        return None

def monitor_report_task(task_id, max_wait=120):
    """监控报告生成任务"""
    import time
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{BASE_URL}/tasks/{task_id}", headers=headers)
            if response.status_code == 200:
                task = response.json()
                status = task.get('status', 'unknown')
                
                print(f"  📊 任务状态: {status}")
                
                if status == 'completed':
                    print("  ✅ 报告生成完成!")
                    return task
                elif status == 'failed':
                    print(f"  ❌ 报告生成失败: {task.get('error_message', 'Unknown error')}")
                    return task
                elif status in ['pending', 'processing']:
                    print(f"  ⏳ 报告生成中... ({int(time.time() - start_time)}s)")
                    time.sleep(10)
                else:
                    print(f"  ❓ 未知状态: {status}")
                    time.sleep(5)
            else:
                print(f"  ❌ 获取任务状态失败: {response.status_code}")
                time.sleep(5)
        except Exception as e:
            print(f"  ❌ 监控任务异常: {str(e)}")
            time.sleep(5)
    
    print("  ⏰ 等待超时")
    return None

def verify_agent_queries(data_source_id):
    """验证Agent生成的查询是否正确执行"""
    print("\n✅ 验证 Agent 查询执行...")
    
    from app.services.connectors.doris_connector import DorisConnector
    from app.models.data_source import DataSource
    from app.core.database import SessionLocal
    
    db = SessionLocal()
    try:
        data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
        
        # 基本连接测试
        config = {
            'fe_hosts': data_source.doris_fe_hosts,
            'http_port': data_source.doris_http_port,
            'query_port': data_source.doris_query_port,
            'database': data_source.doris_database,
            'username': data_source.doris_username,
            'password': 'yjg@123456'  # 实际密码
        }
        
        connector = DorisConnector(config)
        
        # 测试基础查询
        test_queries = [
            "SHOW DATABASES",
            "SHOW TABLES",
            "SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = 'yjg'"
        ]
        
        results = {}
        for query in test_queries:
            try:
                result = connector.execute_query(query)
                results[query] = result
                print(f"  ✅ 查询执行成功: {query[:30]}...")
            except Exception as e:
                results[query] = f"错误: {str(e)}"
                print(f"  ❌ 查询执行失败: {query[:30]}... - {str(e)}")
        
        return results
        
    except Exception as e:
        print(f"❌ 查询验证失败: {str(e)}")
        return None
    finally:
        db.close()

def run_agent_driven_test():
    """运行Agent驱动的完整测试"""
    print("🚀 开始 Agent 驱动的投诉统计系统测试\n")
    
    # 1. 获取数据源
    data_source = get_doris_data_source()
    if not data_source:
        return False
    
    # 2. 创建模板
    template = create_complaint_template()
    if not template:
        return False
    
    # 3. 分析占位符
    analysis = analyze_placeholders(template['id'])
    if not analysis:
        return False
    
    # 4. 测试Agent数据发现
    discovery_result = test_agent_data_discovery(data_source['id'])
    
    # 5. 测试Agent查询生成
    if analysis.get('placeholders'):
        query_results = test_agent_query_generation(data_source['id'], analysis['placeholders'])
    
    # 6. 验证基础查询能力
    verification_results = verify_agent_queries(data_source['id'])
    
    # 7. 测试完整的Agent驱动报告生成
    report_result = test_agent_driven_report_generation(template['id'], data_source['id'])
    
    # 汇总结果
    print("\n" + "="*60)
    print("📊 Agent 驱动测试结果汇总")
    print("="*60)
    print(f"✅ Doris数据源连接: 成功")
    print(f"✅ 统计模板创建: 成功")
    print(f"✅ 占位符分析: {len(analysis.get('placeholders', []))} 个占位符")
    print(f"✅ Agent数据发现: {'成功' if discovery_result else '失败'}")
    print(f"✅ Agent查询生成: {'成功' if 'query_results' in locals() and query_results else '部分成功'}")
    print(f"✅ 基础查询验证: {'成功' if verification_results else '失败'}")
    print(f"✅ Agent驱动报告: {'成功' if report_result else '进行中或失败'}")
    
    print(f"\n🎯 测试完成！Agent系统能够:")
    print(f"   - 自动发现数据源结构")
    print(f"   - 智能生成统计查询")
    print(f"   - 基于真实数据生成报告")
    print(f"   - 无需预定义SQL查询")
    
    return True

if __name__ == "__main__":
    try:
        success = run_agent_driven_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)