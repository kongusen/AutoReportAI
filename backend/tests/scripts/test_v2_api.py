#!/usr/bin/env python3
"""
API v2 测试脚本
用于验证新的v2 API端点是否正常工作
"""

import requests
import json
from typing import Dict, Any
import time

class APIv2Tester:
    def __init__(self, base_url: str = "http://localhost:8000/api/v2"):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
        
    def set_token(self, token: str):
        """设置认证令牌"""
        self.token = token
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        })
    
    def test_health(self) -> bool:
        """测试健康检查"""
        try:
            response = self.session.get(f"{self.base_url}/system/health")
            print(f"✅ 健康检查: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ 健康检查失败: {e}")
            return False
    
    def test_auth_register(self) -> Dict[str, Any]:
        """测试用户注册"""
        data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "testpass123",
            "full_name": "Test User"
        }
        try:
            response = requests.post(
                f"{self.base_url}/auth/register",
                json=data
            )
            print(f"✅ 用户注册: {response.status_code}")
            return response.json()
        except Exception as e:
            print(f"❌ 用户注册失败: {e}")
            return {}
    
    def test_auth_login(self) -> str:
        """测试用户登录"""
        data = {
            "username": "test@example.com",
            "password": "testpass123"
        }
        try:
            response = requests.post(
                f"{self.base_url}/auth/login",
                data=data
            )
            if response.status_code == 200:
                result = response.json()
                token = result.get("data", {}).get("access_token")
                print(f"✅ 用户登录: {response.status_code}, Token: {token[:20]}...")
                return token
            else:
                print(f"❌ 用户登录失败: {response.status_code}")
                return ""
        except Exception as e:
            print(f"❌ 用户登录失败: {e}")
            return ""
    
    def test_data_sources(self) -> bool:
        """测试数据源管理"""
        try:
            # 获取数据源列表
            response = self.session.get(f"{self.base_url}/data-sources")
            print(f"✅ 获取数据源列表: {response.status_code}")
            
            # 创建数据源
            data = {
                "name": "测试数据源",
                "source_type": "csv",
                "connection_string": "./test_data.csv",
                "is_active": True
            }
            response = self.session.post(f"{self.base_url}/data-sources", json=data)
            print(f"✅ 创建数据源: {response.status_code}")
            
            return response.status_code == 200
        except Exception as e:
            print(f"❌ 数据源测试失败: {e}")
            return False
    
    def test_templates(self) -> bool:
        """测试模板管理"""
        try:
            # 获取模板列表
            response = self.session.get(f"{self.base_url}/templates")
            print(f"✅ 获取模板列表: {response.status_code}")
            
            # 创建模板
            data = {
                "name": "测试模板",
                "template_type": "word",
                "content": "这是一个测试模板",
                "is_public": False,
                "is_active": True
            }
            response = self.session.post(f"{self.base_url}/templates", json=data)
            print(f"✅ 创建模板: {response.status_code}")
            
            return response.status_code == 200
        except Exception as e:
            print(f"❌ 模板测试失败: {e}")
            return False
    
    def test_dashboard(self) -> bool:
        """测试仪表板"""
        try:
            # 获取统计数据
            response = self.session.get(f"{self.base_url}/dashboard/stats")
            print(f"✅ 获取统计数据: {response.status_code}")
            
            # 获取图表数据
            response = self.session.get(f"{self.base_url}/dashboard/chart-data?days=7")
            print(f"✅ 获取图表数据: {response.status_code}")
            
            return response.status_code == 200
        except Exception as e:
            print(f"❌ 仪表板测试失败: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始测试 API v2...")
        print("=" * 50)
        
        # 测试健康检查
        if not self.test_health():
            return False
        
        # 测试认证
        register_result = self.test_auth_register()
        if not register_result.get("success"):
            print("⚠️  用户注册可能已存在，尝试登录...")
        
        # 测试登录
        token = self.test_auth_login()
        if not token:
            print("❌ 无法获取认证令牌，跳过需要认证的测试")
            return False
        
        self.set_token(token)
        
        # 测试需要认证的端点
        tests = [
            ("数据源管理", self.test_data_sources),
            ("模板管理", self.test_templates),
            ("仪表板", self.test_dashboard),
        ]
        
        all_passed = True
        for test_name, test_func in tests:
            print(f"\n📋 测试 {test_name}...")
            if not test_func():
                all_passed = False
        
        print("\n" + "=" * 50)
        if all_passed:
            print("🎉 所有测试通过！")
        else:
            print("⚠️  部分测试失败")
        
        return all_passed

def main():
    """主函数"""
    tester = APIv2Tester()
    
    # 检查服务是否可用
    try:
        response = requests.get("http://localhost:8000/api/v2/system/health")
        if response.status_code != 200:
            print("❌ API服务未启动，请先启动后端服务")
            return
    except:
        print("❌ 无法连接到API服务，请确保服务已启动")
        return
    
    # 运行测试
    tester.run_all_tests()

if __name__ == "__main__":
    main()
