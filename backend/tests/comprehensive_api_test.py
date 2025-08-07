#!/usr/bin/env python3
"""
全面的API测试脚本
测试AutoReportAI后端的所有主要功能
"""

import requests
import json
import uuid
import time
from typing import Dict, Any, List

class ComprehensiveAPITester:
    def __init__(self):
        self.base_url = "http://localhost:8000/api/v1"
        self.auth_headers = {}
        self.test_data = {}
        self.results = []
        
    def log_result(self, test_name: str, success: bool, details: str = ""):
        """记录测试结果"""
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} {test_name}")
        if details:
            print(f"   详情: {details}")
        self.results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
        
    def test_health_check(self) -> bool:
        """测试健康检查"""
        try:
            response = requests.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                self.log_result("健康检查", True, f"状态: {data.get('status')}")
                return True
            else:
                self.log_result("健康检查", False, f"状态码: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("健康检查", False, f"异常: {str(e)}")
            return False
    
    def test_user_registration(self) -> bool:
        """测试用户注册"""
        try:
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
                self.log_result("用户注册", True)
                return True
            else:
                self.log_result("用户注册", False, f"状态码: {response.status_code}, 响应: {response.text}")
                return False
        except Exception as e:
            self.log_result("用户注册", False, f"异常: {str(e)}")
            return False
    
    def test_user_login(self) -> bool:
        """测试用户登录"""
        try:
            user_data = self.test_data['user']
            login_data = {
                "username": user_data["username"],
                "password": user_data["password"]
            }
            
            response = requests.post(f"{self.base_url}/auth/login", data=login_data)
            if response.status_code == 200:
                login_response = response.json()
                self.auth_headers = {"Authorization": f"Bearer {login_response['access_token']}"}
                self.log_result("用户登录", True)
                return True
            else:
                self.log_result("用户登录", False, f"状态码: {response.status_code}, 响应: {response.text}")
                return False
        except Exception as e:
            self.log_result("用户登录", False, f"异常: {str(e)}")
            return False
    
    def test_data_source_creation(self) -> bool:
        """测试数据源创建"""
        try:
            unique_id = self.test_data['unique_id']
            ds_data = {
                "name": f"Test Data Source {unique_id}",
                "source_type": "sql",
                "connection_string": "sqlite:///test.db",
                "description": "Test data source for API testing",
                "is_active": True
            }
            
            response = requests.post(f"{self.base_url}/data-sources/", json=ds_data, headers=self.auth_headers)
            if response.status_code == 201:
                ds_response = response.json()
                self.test_data['data_source_id'] = ds_response["id"]
                self.log_result("数据源创建", True)
                return True
            else:
                self.log_result("数据源创建", False, f"状态码: {response.status_code}, 响应: {response.text}")
                return False
        except Exception as e:
            self.log_result("数据源创建", False, f"异常: {str(e)}")
            return False
    
    def test_template_creation(self) -> bool:
        """测试模板创建"""
        try:
            unique_id = self.test_data['unique_id']
            template_data = {
                "name": f"Test Template {unique_id}",
                "description": "Test template for API testing",
                "content": "本月数据报告：总记录数：{{统计:总记录数}}，平均数值：{{统计:平均值}}",
                "is_active": True
            }
            
            response = requests.post(f"{self.base_url}/templates/", json=template_data, headers=self.auth_headers)
            if response.status_code == 201:
                template_response = response.json()
                self.test_data['template_id'] = template_response["id"]
                self.log_result("模板创建", True)
                return True
            else:
                self.log_result("模板创建", False, f"状态码: {response.status_code}, 响应: {response.text}")
                return False
        except Exception as e:
            self.log_result("模板创建", False, f"异常: {str(e)}")
            return False
    
    def test_ai_provider_creation(self) -> bool:
        """测试AI提供商创建"""
        try:
            unique_id = self.test_data['unique_id']
            ai_data = {
                "provider_name": f"openai_{unique_id}",
                "provider_type": "openai",
                "api_key": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "api_base_url": "https://api.openai.com/v1",
                "default_model_name": "gpt-3.5-turbo",
                "is_active": True
            }
            
            response = requests.post(f"{self.base_url}/ai-providers/", json=ai_data, headers=self.auth_headers)
            if response.status_code in [200, 201]:
                ai_response = response.json()
                self.test_data['ai_provider_id'] = ai_response["data"]["id"]
                self.log_result("AI提供商创建", True)
                return True
            else:
                self.log_result("AI提供商创建", False, f"状态码: {response.status_code}, 响应: {response.text}")
                return False
        except Exception as e:
            self.log_result("AI提供商创建", False, f"异常: {str(e)}")
            return False
    
    def test_etl_job_creation(self) -> bool:
        """测试ETL作业创建"""
        try:
            unique_id = self.test_data['unique_id']
            etl_data = {
                "name": f"Test ETL Job {unique_id}",
                "description": "Test ETL job for API testing",
                "data_source_id": self.test_data['data_source_id'],
                "job_type": "extract",
                "schedule": "0 0 * * *",  # 使用有效的cron表达式
                "source_query": "SELECT * FROM test_table",  # 添加必需的source_query字段
                "destination_table_name": f"test_table_{unique_id}",  # 添加必需的destination_table_name字段
                "is_active": True
            }
            
            response = requests.post(f"{self.base_url}/etl-jobs/", json=etl_data, headers=self.auth_headers)
            if response.status_code == 201:
                etl_response = response.json()
                self.test_data['etl_job_id'] = etl_response["id"]
                self.log_result("ETL作业创建", True)
                return True
            else:
                self.log_result("ETL作业创建", False, f"状态码: {response.status_code}, 响应: {response.text}")
                return False
        except Exception as e:
            self.log_result("ETL作业创建", False, f"异常: {str(e)}")
            return False
    
    def test_list_endpoints(self) -> bool:
        """测试列表端点"""
        endpoints = [
            ("数据源列表", "/data-sources/"),
            ("模板列表", "/templates/"),
            ("AI提供商列表", "/ai-providers/"),
            ("ETL作业列表", "/etl-jobs/"),
        ]
        
        success_count = 0
        for name, endpoint in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", headers=self.auth_headers)
                if response.status_code == 200:
                    data = response.json()
                    # 处理不同的响应格式
                    if isinstance(data, dict) and "items" in data:
                        count = len(data.get("items", []))
                    elif isinstance(data, list):
                        count = len(data)
                    else:
                        count = 0
                    self.log_result(f"{name}", True, f"获取到 {count} 条记录")
                    success_count += 1
                else:
                    self.log_result(f"{name}", False, f"状态码: {response.status_code}")
            except Exception as e:
                self.log_result(f"{name}", False, f"异常: {str(e)}")
        
        return success_count == len(endpoints)
    
    def test_dashboard_data(self) -> bool:
        """测试仪表板数据"""
        try:
            response = requests.get(f"{self.base_url}/dashboard/", headers=self.auth_headers)
            if response.status_code == 200:
                data = response.json()
                self.log_result("仪表板数据", True, f"数据源: {data.get('data_sources_count', 0)}, 模板: {data.get('templates_count', 0)}")
                return True
            else:
                self.log_result("仪表板数据", False, f"状态码: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("仪表板数据", False, f"异常: {str(e)}")
            return False
    
    def test_system_endpoints(self) -> bool:
        """测试系统端点"""
        endpoints = [
            ("系统信息", "/system/info"),
            ("API版本", "/system/version"),
        ]
        
        success_count = 0
        for name, endpoint in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}")
                if response.status_code == 200:
                    self.log_result(f"{name}", True)
                    success_count += 1
                else:
                    self.log_result(f"{name}", False, f"状态码: {response.status_code}")
            except Exception as e:
                self.log_result(f"{name}", False, f"异常: {str(e)}")
        
        return success_count == len(endpoints)
    
    def test_intelligent_placeholders(self) -> bool:
        """测试智能占位符功能"""
        try:
            placeholder_data = {
                "template_content": "本月数据报告：总记录数：{{统计:总记录数}}，平均数值：{{统计:平均值}}",
                "template_id": self.test_data.get('template_id'),  # 添加必需的template_id字段
                "data_source_id": self.test_data.get('data_source_id')
            }
            
            response = requests.post(f"{self.base_url}/intelligent-placeholders/analyze", 
                                  json=placeholder_data, headers=self.auth_headers)
            if response.status_code == 200:
                self.log_result("智能占位符分析", True)
                return True
            else:
                self.log_result("智能占位符分析", False, f"状态码: {response.status_code}, 响应: {response.text}")
                return False
        except Exception as e:
            self.log_result("智能占位符分析", False, f"异常: {str(e)}")
            return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("🚀 AutoReportAI 后端全面API测试")
        print("=" * 50)
        
        tests = [
            ("健康检查", self.test_health_check),
            ("用户注册", self.test_user_registration),
            ("用户登录", self.test_user_login),
            ("数据源创建", self.test_data_source_creation),
            ("模板创建", self.test_template_creation),
            ("AI提供商创建", self.test_ai_provider_creation),
            ("ETL作业创建", self.test_etl_job_creation),
            ("列表端点", self.test_list_endpoints),
            ("仪表板数据", self.test_dashboard_data),
            ("系统端点", self.test_system_endpoints),
            ("智能占位符", self.test_intelligent_placeholders),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n🧪 {test_name}...")
            if test_func():
                passed += 1
        
        print("\n" + "=" * 50)
        print(f"📊 测试结果: {passed}/{total} 通过")
        
        if passed == total:
            print("🎉 所有测试通过！后端功能正常")
        else:
            print("⚠️ 部分测试失败，请检查相关功能")
        
        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "results": self.results
        }

def main():
    """主函数"""
    tester = ComprehensiveAPITester()
    result = tester.run_all_tests()
    
    # 输出详细结果
    print("\n📋 详细测试结果:")
    for result_item in result["results"]:
        status = "✅" if result_item["success"] else "❌"
        print(f"{status} {result_item['test']}")
        if result_item["details"]:
            print(f"   详情: {result_item['details']}")

if __name__ == "__main__":
    main() 