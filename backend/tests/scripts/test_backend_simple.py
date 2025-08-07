#!/usr/bin/env python3
"""
简单的后端功能测试脚本
测试核心API端点的可用性
"""

import requests
import json
import uuid
import time

# 测试配置
BASE_URL = "http://localhost:8000/api/v1"
HEADERS = {"Content-Type": "application/json"}

def test_backend_endpoints():
    """测试后端核心端点"""
    print("🚀 开始测试后端功能...")
    
    # 1. 测试健康检查
    print("\n1. 测试健康检查...")
    try:
        response = requests.get(f"{BASE_URL}/system/health")
        if response.status_code == 200:
            print("✅ 健康检查通过")
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 健康检查异常: {e}")
        return False
    
    # 2. 测试用户注册
    print("\n2. 测试用户注册...")
    unique_id = uuid.uuid4().hex[:8]
    register_data = {
        "username": f"testuser_{unique_id}",
        "email": f"test_{unique_id}@example.com",
        "password": "TestPass123!",
        "full_name": "Test User"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
        if response.status_code == 201:
            user_data = response.json()
            print("✅ 用户注册成功")
            user_id = user_data["id"]
        else:
            print(f"❌ 用户注册失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ 用户注册异常: {e}")
        return False
    
    # 3. 测试用户登录
    print("\n3. 测试用户登录...")
    login_data = {
        "username": register_data["username"],
        "password": register_data["password"]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
        if response.status_code == 200:
            login_response = response.json()
            access_token = login_response["access_token"]
            print("✅ 用户登录成功")
            auth_headers = {"Authorization": f"Bearer {access_token}"}
        else:
            print(f"❌ 用户登录失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ 用户登录异常: {e}")
        return False
    
    # 4. 测试数据源创建
    print("\n4. 测试数据源创建...")
    ds_data = {
        "name": f"Test Data Source {unique_id}",
        "source_type": "database",
        "connection_string": "sqlite:///test.db",
        "description": "Test data source",
        "is_active": True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/data-sources", json=ds_data, headers=auth_headers)
        if response.status_code == 201:
            ds_response = response.json()
            data_source_id = ds_response["id"]
            print("✅ 数据源创建成功")
        else:
            print(f"❌ 数据源创建失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ 数据源创建异常: {e}")
        return False
    
    # 5. 测试模板创建
    print("\n5. 测试模板创建...")
    template_data = {
        "name": f"Test Template {unique_id}",
        "description": "Test template",
        "content": "本月数据报告：总记录数：{{统计:总记录数}}",
        "is_active": True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/templates", json=template_data, headers=auth_headers)
        if response.status_code == 201:
            template_response = response.json()
            template_id = template_response["id"]
            print("✅ 模板创建成功")
        else:
            print(f"❌ 模板创建失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ 模板创建异常: {e}")
        return False
    
    # 6. 测试任务创建
    print("\n6. 测试任务创建...")
    task_data = {
        "name": f"Test Task {unique_id}",
        "description": "Test task",
        "data_source_id": data_source_id,
        "template_id": template_id,
        "is_active": True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/tasks", json=task_data, headers=auth_headers)
        if response.status_code == 201:
            task_response = response.json()
            task_id = task_response["id"]
            print("✅ 任务创建成功")
        else:
            print(f"❌ 任务创建失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ 任务创建异常: {e}")
        return False
    
    # 7. 测试ETL作业创建
    print("\n7. 测试ETL作业创建...")
    etl_data = {
        "name": f"Test ETL Job {unique_id}",
        "description": "Test ETL job",
        "data_source_id": data_source_id,
        "destination_table_name": f"etl_table_{unique_id}",
        "source_query": "SELECT * FROM test_table",
        "schedule": "0 0 * * *",
        "enabled": True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/etl-jobs", json=etl_data, headers=auth_headers)
        if response.status_code == 201:
            etl_response = response.json()
            etl_job_id = etl_response["id"]
            print("✅ ETL作业创建成功")
        else:
            print(f"❌ ETL作业创建失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ ETL作业创建异常: {e}")
        return False
    
    # 8. 测试仪表板数据
    print("\n8. 测试仪表板数据...")
    try:
        response = requests.get(f"{BASE_URL}/dashboard/summary", headers=auth_headers)
        if response.status_code == 200:
            dashboard_data = response.json()
            print("✅ 仪表板数据获取成功")
            print(f"   数据源总数: {dashboard_data.get('total_data_sources', 0)}")
            print(f"   模板总数: {dashboard_data.get('total_templates', 0)}")
            print(f"   任务总数: {dashboard_data.get('total_tasks', 0)}")
        else:
            print(f"❌ 仪表板数据获取失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ 仪表板数据获取异常: {e}")
        return False
    
    # 9. 测试数据验证
    print("\n9. 测试数据验证...")
    validation_data = {
        "source_type": "database",
        "connection_string": "sqlite:///test.db"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/data-sources/validate", json=validation_data, headers=auth_headers)
        if response.status_code == 200:
            validation_result = response.json()
            print("✅ 数据源验证成功")
        else:
            print(f"❌ 数据源验证失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ 数据源验证异常: {e}")
        return False
