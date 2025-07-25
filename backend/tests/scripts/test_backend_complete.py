#!/usr/bin/env python3
"""
完整的后端端到端测试脚本
测试从用户注册到报告生成的完整流程
"""

import requests
import json
import uuid
import time
import sys

# 测试配置
BASE_URL = "http://localhost:8000/api/v2"
HEADERS = {"Content-Type": "application/json"}

class BackendTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.headers = HEADERS
        self.auth_headers = {}
        self.test_data = {}
        
    def run_test(self, test_name, test_func):
        """运行单个测试并处理异常"""
        try:
            print(f"\n🧪 {test_name}...")
            result = test_func()
            if result:
                print(f"✅ {test_name} 通过")
                return True
            else:
                print(f"❌ {test_name} 失败")
                return False
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}")
            return False
    
    def test_health_check(self):
        """测试健康检查端点"""
        response = requests.get(f"{self.base_url}/system/health")
        return response.status_code == 200
    
    def test_user_registration(self):
        """测试用户注册"""
        unique_id = uuid.uuid4().hex[:8]
        register_data = {
            "username": f"testuser_{unique_id}",
            "email": f"test_{unique_id}@example.com",
            "password": "TestPass123!",
            "full_name": "Test User"
        }
        
        response = requests.post(f"{self.base_url}/auth/register", json=register_data)
        if response.status_code == 201:
            self.test_data['user'] = register_data
            self.test_data['unique_id'] = unique_id
            return True
        return False
    
    def test_user_login(self):
        """测试用户登录"""
        user_data = self.test_data['user']
        login_data = {
            "username": user_data["username"],
            "password": user_data["password"]
        }
        
        response = requests.post(f"{self.base_url}/auth/login", data=login_data)
        if response.status_code == 200:
            login_response = response.json()
            self.auth_headers = {"Authorization": f"Bearer {login_response['access_token']}"}
            return True
        return False
    
    def test_data_source_creation(self):
        """测试数据源创建"""
        unique_id = self.test_data['unique_id']
        ds_data = {
            "name": f"Test Data Source {unique_id}",
            "source_type": "database",
            "connection_string": "sqlite:///test.db",
            "description": "Test data source for E2E testing",
            "is_active": True
        }
        
        response = requests.post(f"{self.base_url}/data-sources", json=ds_data, headers=self.auth_headers)
        if response.status_code == 201:
            self.test_data['data_source_id'] = response.json()["id"]
            return True
        return False
    
    def test_template_creation(self):
        """测试模板创建"""
        unique_id = self.test_data['unique_id']
        template_data = {
            "name": f"Test Template {unique_id}",
            "description": "Test template for E2E testing",
            "content": """
            本月数据报告：
            总记录数：{{统计:总记录数}}
            平均数值：{{统计:平均值}}
            最高记录：{{统计:最大值}}
            生成时间：{{时间:当前时间}}
            """,
            "is_active": True
        }
        
        response = requests.post(f"{self.base_url}/templates", json=template_data, headers=self.auth_headers)
        if response.status_code == 201:
            self.test_data['template_id'] = response.json()["id"]
            return True
        return False
    
    def test_task_creation(self):
        """测试任务创建"""
        task_data = {
            "name": f"Test Task {self.test_data['unique_id']}",
            "description": "Test task for E2E testing",
            "data_source_id": self.test_data['data_source_id'],
            "template_id": self.test_data['template_id'],
            "is_active": True
        }
        
        response = requests.post(f"{self.base_url}/tasks", json=task_data, headers=self.auth_headers)
        if response.status_code == 201:
            self.test_data['task_id'] = response.json()["id"]
            return True
        return False
    
    def test_etl_job_creation(self):
        """测试ETL作业创建"""
        etl_data = {
            "name": f"Test ETL Job {self.test_data['unique_id']}",
            "description": "Test ETL job for E2E testing",
            "data_source_id": self.test_data['data_source_id'],
            "destination_table_name": f"etl_table_{self.test_data['unique_id']}",
            "source_query": "SELECT * FROM test_table",
            "schedule": "0 0 * * *",
            "enabled": True
        }
        
        response = requests.post(f"{self.base_url}/etl-jobs", json=etl_data, headers=self.auth_headers)
        if response.status_code == 201:
            self.test_data['etl_job_id'] = response.json()["id"]
            return True
        return False
    
    def test_dashboard_data(self):
        """测试仪表板数据"""
        response = requests.get(f"{self.base_url}/dashboard/summary", headers=self.auth_headers)
        if response.status_code == 200:
            dashboard_data = response.json()
            print(f"   📊 数据源: {dashboard_data.get('total_data_sources', 0)}")
            print(f"   📋 模板: {dashboard_data.get('total_templates', 0)}")
            print(f"   ⚙️  任务: {dashboard_data.get('total_tasks', 0)}")
            return True
        return False
    
    def test_data_validation(self):
        """测试数据验证"""
        validation_data = {
            "source_type": "database",
            "connection_string": "sqlite:///test.db"
        }
        
        response = requests.post(f"{self.base_url}/data-sources/validate", json=validation_data, headers=self.auth_headers)
        return response.status_code == 200
    
    def test_report_generation(self):
        """测试报告生成"""
        report_data = {
            "task_id": self.test_data['task_id'],
            "template_id": self.test_data['template_id'],
            "data_source_id": self.test_data['data_source_id'],
            "parameters": {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            }
        }
        
        response = requests.post(f"{self.base_url}/reports/generate", json=report_data, headers=self.auth_headers)
        return response.status_code in [200, 202]
    
    def test_list_endpoints(self):
        """测试列表端点"""
        endpoints = [
            ("data-sources", "数据源"),
            ("templates", "模板"),
            ("tasks", "任务"),
            ("etl-jobs", "ETL作业")
        ]
        
        for endpoint, name in endpoints:
            response = requests.get(f"{self.base_url}/{endpoint}", headers=self.auth_headers)
            if response.status_code != 200:
                print(f"   ❌ 获取{name}列表失败")
                return False
            else:
                data = response.json()
                print(f"   ✅ 获取{name}列表成功 ({len(data)} 条记录)")
        
        return True
    
    def run_all_tests(self):
        """运行所有测试"""
        tests = [
            ("健康检查", self.test_health_check),
            ("用户注册", self.test_user_registration),
            ("用户登录", self.test_user_login),
            ("数据源创建", self.test_data_source_creation),
            ("模板创建", self.test_template_creation),
            ("任务创建", self.test_task_creation),
            ("ETL作业创建", self.test_etl_job_creation),
            ("仪表板数据", self.test_dashboard_data),
            ("数据验证", self.test_data_validation),
            ("报告生成", self.test_report_generation),
            ("列表端点", self.test_list_endpoints)
        ]
