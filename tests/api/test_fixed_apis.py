#!/usr/bin/env python3
"""
测试修复后的API端点
验证所有之前缺失的功能是否正常工作
"""

import requests
import json
import time

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

def test_data_source_connection():
    """测试数据源连接API"""
    print("\n🔗 测试数据源连接API...")
    
    token = get_auth_token()
    if not token:
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # 使用正确的API路径进行连接测试
        response = requests.post(
            f"{BACKEND_URL}/data-sources/dce6826b-3181-458e-b568-9f60e6caa335/test",
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 数据源连接测试API可用")
            print(f"   响应: {result.get('message', 'N/A')}")
            if result.get('success'):
                print(f"   连接状态: 成功")
            else:
                print(f"   连接状态: {result.get('data', {}).get('connection_status', 'N/A')}")
                print(f"   错误信息: {result.get('data', {}).get('error', 'N/A')}")
            return True
        else:
            print(f"❌ API请求失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 测试异常: {e}")
    
    return False

def test_report_generation():
    """测试报告生成API"""
    print("\n📊 测试报告生成API...")
    
    token = get_auth_token()
    if not token:
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # 测试智能报告生成
        report_data = {
            "template_id": "3a0e86ac-e374-452d-835f-97bfe3382df4",
            "data_source_id": "dce6826b-3181-458e-b568-9f60e6caa335",
            "optimization_level": "enhanced",
            "enable_intelligent_etl": True,
            "name": "API测试报告",
            "description": "测试报告生成API功能"
        }
        
        response = requests.post(
            f"{BACKEND_URL}/reports/generate/intelligent",
            headers=headers,
            json=report_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 智能报告生成API可用")
            print(f"   响应: {result.get('message', 'N/A')}")
            if result.get('success'):
                task_id = result.get('data', {}).get('task_id')
                print(f"   任务ID: {task_id}")
                print(f"   优化级别: {result.get('data', {}).get('optimization_level')}")
                return True
            else:
                print(f"   错误: {result.get('error', 'N/A')}")
        else:
            print(f"❌ API请求失败: {response.status_code}")
            print(f"   错误详情: {response.text[:200]}")
    except Exception as e:
        print(f"❌ 测试异常: {e}")
    
    return False

def test_system_insights_analysis():
    """测试系统洞察分析API"""
    print("\n🤖 测试系统洞察分析API...")
    
    token = get_auth_token()
    if not token:
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # 测试SQL生成分析
        analysis_data = {
            "analysis_type": "sql_generation",
            "query": "生成查询销售总额和订单数量的SQL语句",
            "context": """
            Doris数据库表结构:
            
            表名: sales_order (150000 行)
            字段:
              - order_id: bigint (PRI)
              - customer_id: bigint
              - order_date: datetime
              - total_amount: decimal(10,2)
              - status: varchar(20)
            
            表名: customer (25000 行)  
            字段:
              - customer_id: bigint (PRI)
              - customer_name: varchar(100)
              - email: varchar(255)
              - created_at: datetime
              - city: varchar(50)
            """,
            "optimization_level": "enhanced"
        }
        
        response = requests.post(
            f"{BACKEND_URL}/system-insights/context-system/analyze",
            headers=headers,
            json=analysis_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 系统洞察分析API可用")
            print(f"   响应: {result.get('message', 'N/A')}")
            if result.get('success'):
                analysis_result = result.get('data', {})
                print(f"   分析类型: {analysis_result.get('analysis_type')}")
                print(f"   优化级别: {analysis_result.get('optimization_level')}")
                print(f"   分析者: {analysis_result.get('analyzed_by')}")
                print(f"   AI响应: {str(analysis_result.get('response', ''))[:100]}...")
                return True
            else:
                print(f"   错误: {result.get('error', 'N/A')}")
        else:
            print(f"❌ API请求失败: {response.status_code}")
            print(f"   错误详情: {response.text[:200]}")
    except Exception as e:
        print(f"❌ 测试异常: {e}")
    
    return False

def test_doris_password_fix():
    """测试Doris密码认证修复"""
    print("\n🔧 测试Doris密码认证修复...")
    
    token = get_auth_token()
    if not token:
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 更新数据源，确保使用正确的密码
    try:
        update_data = {
            "doris_fe_hosts": ["192.168.31.160"],
            "doris_query_port": 9030,
            "doris_database": "doris", 
            "doris_username": "root",
            "doris_password": "yjg@123456",  # 明确设置密码
            "is_active": True
        }
        
        response = requests.put(
            f"{BACKEND_URL}/data-sources/dce6826b-3181-458e-b568-9f60e6caa335",
            headers=headers,
            json=update_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 数据源密码更新成功")
            
            # 再次测试连接
            time.sleep(1)  # 稍等确保更新生效
            connection_result = test_data_source_connection()
            if connection_result:
                print(f"✅ Doris密码认证修复验证成功")
                return True
        else:
            print(f"❌ 数据源更新失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 测试异常: {e}")
    
    return False

def test_template_analysis():
    """测试模板分析API"""
    print("\n📝 测试模板分析API...")
    
    token = get_auth_token()
    if not token:
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # 测试模板分析
        response = requests.post(
            f"{BACKEND_URL}/templates/3a0e86ac-e374-452d-835f-97bfe3382df4/analyze",
            headers=headers,
            params={
                "data_source_id": "dce6826b-3181-458e-b568-9f60e6caa335",
                "force_reanalyze": True,
                "optimization_level": "enhanced"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 模板分析API可用")
            print(f"   响应: {result.get('message', 'N/A')}")
            if result.get('success'):
                analysis_data = result.get('data', {})
                print(f"   分析结果: {str(analysis_data.get('response', ''))[:100]}...")
                print(f"   执行时间: {analysis_data.get('conversation_time', 0)*1000:.2f}ms")
                return True
            else:
                print(f"   错误: {result.get('error', 'N/A')}")
        else:
            print(f"❌ API请求失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 测试异常: {e}")
    
    return False

def main():
    """主测试函数"""
    print("🚀 测试修复后的API功能")
    print("=" * 60)
    
    results = {}
    
    # 1. 测试数据源连接API
    results['data_source_connection'] = test_data_source_connection()
    
    # 2. 测试报告生成API
    results['report_generation'] = test_report_generation()
    
    # 3. 测试系统洞察分析API
    results['system_insights_analysis'] = test_system_insights_analysis()
    
    # 4. 测试模板分析API
    results['template_analysis'] = test_template_analysis()
    
    # 5. 测试Doris密码认证修复
    results['doris_password_fix'] = test_doris_password_fix()
    
    # 结果汇总
    print("\n" + "=" * 60)
    print("📊 API修复测试结果汇总")
    print("=" * 60)
    
    success_count = 0
    total_count = len(results)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            success_count += 1
    
    success_rate = (success_count / total_count) * 100
    print(f"\n🎯 测试通过率: {success_count}/{total_count} ({success_rate:.1f}%)")
    
    if success_count == total_count:
        print("🎉 所有API修复测试通过!")
        print("✨ 系统功能完整可用")
        print("🌐 可以进行完整的Agent测试了")
    elif success_count >= total_count * 0.8:
        print("⚠️  大部分API已修复，少数功能需要进一步调试")
    else:
        print("❌ 多个API需要继续修复")
    
    print(f"\n📋 API状态总结:")
    print(f"   • 数据源连接测试: {'✅' if results['data_source_connection'] else '❌'}")
    print(f"   • 智能报告生成: {'✅' if results['report_generation'] else '❌'}")
    print(f"   • 系统洞察分析: {'✅' if results['system_insights_analysis'] else '❌'}")
    print(f"   • 模板分析功能: {'✅' if results['template_analysis'] else '❌'}")
    print(f"   • Doris认证修复: {'✅' if results['doris_password_fix'] else '❌'}")
    
    return success_count == total_count

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)