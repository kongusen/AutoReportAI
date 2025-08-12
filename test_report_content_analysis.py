#!/usr/bin/env python3
"""
分析生成的报告内容和数据结果
检查Agent从Doris查询的真实数据
"""

import requests
import json
import time
import sys

# API配置
BASE_URL = "http://localhost:8000/api/v1"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTQ5NjgzNzQsInN1YiI6IjJmZjkzNmY3LTg4YWItNDVhYS1hMDU2LTIyOWQ5YTFjNjcxZCJ9.Ah2EplbqNxyhPr_nRkq9fPfZQfs0Fjsl7djsvbZ06Vw"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def test_doris_direct_query():
    """直接测试Doris连接器查询真实数据"""
    print("🔍 直接测试Doris数据查询...")
    
    # 添加backend路径以便导入
    sys.path.insert(0, '/Users/shan/work/uploads/AutoReportAI/backend')
    
    try:
        from app.services.connectors.doris_connector import DorisConnector
        
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
        
        # 测试基础查询
        queries = [
            {
                "name": "查看数据库列表",
                "sql": "SHOW DATABASES"
            },
            {
                "name": "查看当前数据库表",
                "sql": "SHOW TABLES"
            }
        ]
        
        results = {}
        for query in queries:
            try:
                print(f"\n📊 执行查询: {query['name']}")
                result = connector.execute_query(query['sql'])
                results[query['name']] = result
                
                if result:
                    print(f"✅ 查询成功，返回 {len(result)} 条记录:")
                    for i, row in enumerate(result[:5]):  # 显示前5条
                        print(f"  {i+1}: {row}")
                    if len(result) > 5:
                        print(f"  ... 还有 {len(result) - 5} 条记录")
                else:
                    print("✅ 查询成功，但无返回数据")
                    
            except Exception as e:
                print(f"❌ 查询失败: {str(e)}")
                results[query['name']] = f"错误: {str(e)}"
        
        return results
        
    except Exception as e:
        print(f"❌ Doris连接器初始化失败: {str(e)}")
        return None

def find_complaint_tables():
    """查找投诉相关的数据表"""
    print("\n🔍 查找投诉相关数据表...")
    
    sys.path.insert(0, '/Users/shan/work/uploads/AutoReportAI/backend')
    
    try:
        from app.services.connectors.doris_connector import DorisConnector
        
        doris_config = {
            'fe_hosts': ['192.168.61.30'],
            'http_port': 8030,
            'query_port': 9030,
            'database': 'yjg',
            'username': 'root',
            'password': 'yjg@123456'
        }
        
        connector = DorisConnector(doris_config)
        
        # 查看所有表
        tables_result = connector.execute_query("SHOW TABLES")
        
        if tables_result:
            print(f"✅ 找到 {len(tables_result)} 个表:")
            complaint_related = []
            
            for table_info in tables_result:
                table_name = table_info[0] if isinstance(table_info, (list, tuple)) else str(table_info)
                print(f"  - {table_name}")
                
                # 检查是否是投诉相关表
                if any(keyword in table_name.lower() for keyword in ['complaint', 'report', '投诉', '举报', 'issue']):
                    complaint_related.append(table_name)
            
            if complaint_related:
                print(f"\n📋 投诉相关表: {complaint_related}")
                
                # 查看表结构
                for table in complaint_related[:2]:  # 查看前2个表的结构
                    try:
                        desc_result = connector.execute_query(f"DESC {table}")
                        print(f"\n📊 表 {table} 结构:")
                        for col_info in desc_result[:10]:  # 显示前10个字段
                            print(f"  {col_info}")
                    except Exception as e:
                        print(f"  ❌ 无法查看表结构: {str(e)}")
            else:
                print("📋 未找到明显的投诉相关表，显示所有表供参考")
                
                # 查看前几个表的结构作为示例
                for table_info in tables_result[:3]:
                    table_name = table_info[0] if isinstance(table_info, (list, tuple)) else str(table_info)
                    try:
                        desc_result = connector.execute_query(f"DESC {table_name}")
                        print(f"\n📊 表 {table_name} 结构:")
                        for col_info in desc_result[:5]:  # 显示前5个字段
                            print(f"  {col_info}")
                    except Exception as e:
                        print(f"  ❌ 无法查看表结构: {str(e)}")
            
            return tables_result
        else:
            print("❌ 未找到任何表")
            return None
            
    except Exception as e:
        print(f"❌ 查找表失败: {str(e)}")
        return None

def test_sample_data_queries():
    """测试示例数据查询"""
    print("\n📊 测试示例数据查询...")
    
    sys.path.insert(0, '/Users/shan/work/uploads/AutoReportAI/backend')
    
    try:
        from app.services.connectors.doris_connector import DorisConnector
        
        doris_config = {
            'fe_hosts': ['192.168.61.30'],
            'http_port': 8030,
            'query_port': 9030,
            'database': 'yjg',
            'username': 'root',
            'password': 'yjg@123456'
        }
        
        connector = DorisConnector(doris_config)
        
        # 获取表列表
        tables_result = connector.execute_query("SHOW TABLES")
        
        if tables_result and len(tables_result) > 0:
            # 选择第一个表进行示例查询
            first_table = tables_result[0][0] if isinstance(tables_result[0], (list, tuple)) else str(tables_result[0])
            
            sample_queries = [
                {
                    "name": f"查看表 {first_table} 前5条记录",
                    "sql": f"SELECT * FROM {first_table} LIMIT 5"
                },
                {
                    "name": f"统计表 {first_table} 总记录数",
                    "sql": f"SELECT COUNT(*) as total_count FROM {first_table}"
                }
            ]
            
            results = {}
            for query in sample_queries:
                try:
                    print(f"\n📋 执行查询: {query['name']}")
                    result = connector.execute_query(query['sql'])
                    results[query['name']] = result
                    
                    if result:
                        print(f"✅ 查询成功:")
                        for i, row in enumerate(result):
                            print(f"  {i+1}: {row}")
                    else:
                        print("✅ 查询成功，但无返回数据")
                        
                except Exception as e:
                    print(f"❌ 查询失败: {str(e)}")
                    results[query['name']] = f"错误: {str(e)}"
            
            return results
        else:
            print("❌ 无可用表进行示例查询")
            return None
            
    except Exception as e:
        print(f"❌ 示例查询失败: {str(e)}")
        return None

def generate_real_data_report():
    """使用真实数据生成报告"""
    print("\n📋 使用真实数据生成报告...")
    
    # 首先创建一个简化的模板
    template_content = """# 投诉数据统计报告

## 数据概览
- 数据库：{{数据库名称}}
- 统计时间：{{统计时间}}
- 表总数：{{表总数}}

## 数据详情
根据系统查询结果：
- 可用数据表：{{可用表列表}}
- 数据记录总数：{{总记录数}}

此报告基于Doris数据源的真实查询结果生成。
"""

    template_data = {
        "name": "真实数据统计报告",
        "description": "基于Doris真实数据的统计报告",
        "content": template_content,
        "is_active": True
    }
    
    # 创建模板
    response = requests.post(f"{BASE_URL}/templates/", headers=headers, json=template_data)
    if response.status_code in [200, 201]:
        template = response.json()
        template_id = template['id']
        print(f"✅ 创建真实数据模板成功: {template_id}")
        
        # 获取数据源
        ds_response = requests.get(f"{BASE_URL}/data-sources/", headers=headers)
        if ds_response.status_code == 200:
            ds_data = ds_response.json()
            sources = ds_data.get('data', {}).get('items', [])
            doris_sources = [s for s in sources if s.get('source_type') == 'doris']
            
            if doris_sources:
                data_source_id = doris_sources[0]['id']
                
                # 生成报告
                url = f"{BASE_URL}/intelligent-placeholders/generate-report?template_id={template_id}&data_source_id={data_source_id}"
                report_response = requests.post(url, headers=headers, json={})
                
                if report_response.status_code == 200:
                    report_result = report_response.json()
                    if report_result.get('success'):
                        task_id = report_result.get('data', {}).get('task_id')
                        print(f"✅ 真实数据报告生成任务启动: {task_id}")
                        return task_id
                    else:
                        print(f"❌ 报告生成失败: {report_result.get('message')}")
                        return None
                else:
                    print(f"❌ 报告生成请求失败: {report_response.status_code}")
                    return None
            else:
                print("❌ 未找到Doris数据源")
                return None
        else:
            print(f"❌ 获取数据源失败: {ds_response.status_code}")
            return None
    else:
        print(f"❌ 创建模板失败: {response.status_code}")
        print(response.text)
        return None

def check_report_files():
    """检查是否有生成的报告文件"""
    print("\n📁 检查报告文件...")
    
    import os
    
    # 检查可能的报告存储路径
    possible_paths = [
        "/Users/shan/work/uploads/AutoReportAI/reports",
        "/Users/shan/work/uploads/AutoReportAI/backend/reports",
        "/Users/shan/work/uploads/AutoReportAI/generated_reports",
        "/tmp/reports"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ 找到报告目录: {path}")
            files = os.listdir(path)
            if files:
                print(f"  📄 发现 {len(files)} 个文件:")
                for file in files[:5]:  # 显示前5个文件
                    print(f"    - {file}")
                if len(files) > 5:
                    print(f"    ... 还有 {len(files) - 5} 个文件")
            else:
                print(f"  📂 目录为空")
        else:
            print(f"❌ 路径不存在: {path}")

def run_report_analysis():
    """运行报告内容分析"""
    print("🚀 开始分析生成的报告内容和数据结果\n")
    
    # 1. 直接测试Doris查询
    doris_results = test_doris_direct_query()
    
    # 2. 查找投诉相关表
    table_discovery = find_complaint_tables()
    
    # 3. 测试示例数据查询
    sample_results = test_sample_data_queries()
    
    # 4. 检查报告文件
    check_report_files()
    
    # 5. 生成基于真实数据的报告
    real_report_task = generate_real_data_report()
    
    # 汇总分析结果
    print("\n" + "="*60)
    print("📊 报告内容和数据分析结果")
    print("="*60)
    
    analysis_results = [
        ("Doris连接测试", doris_results is not None),
        ("数据表发现", table_discovery is not None),
        ("示例数据查询", sample_results is not None),
        ("真实数据报告", real_report_task is not None)
    ]
    
    for test_name, success in analysis_results:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"{test_name:15} : {status}")
    
    print(f"\n🎯 关键发现:")
    if doris_results:
        print(f"  - Doris数据库连接正常")
    if table_discovery:
        print(f"  - 发现数据表，可进行统计查询")
    if sample_results:
        print(f"  - 示例数据查询成功，Agent可获取真实数据")
    if real_report_task:
        print(f"  - 真实数据报告生成任务已启动")
    
    print(f"\n📋 下一步:")
    print(f"  1. Agent会查询Doris中的真实投诉数据")
    print(f"  2. 根据占位符需求生成相应的SQL查询")
    print(f"  3. 使用查询结果替换模板中的占位符")
    print(f"  4. 生成包含真实统计数据的最终报告")

if __name__ == "__main__":
    try:
        run_report_analysis()
    except Exception as e:
        print(f"❌ 分析过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()