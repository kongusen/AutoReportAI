#!/usr/bin/env python3
"""
AI提供商配置脚本
基于用户提供的配置信息设置AI提供商
"""

import requests
import json
import sys
from typing import Dict, Any

class AIProviderConfigurator:
    def __init__(self):
        self.base_url = "http://localhost:8000/api/v1"
        self.auth_headers = {}
        
    def create_test_user(self) -> Dict[str, Any]:
        """创建测试用户"""
        import uuid
        unique_id = uuid.uuid4().hex[:8]
        register_data = {
            "username": f"admin_{unique_id}",
            "email": f"admin_{unique_id}@example.com",
            "password": "AdminPass123!",
            "full_name": "Admin User"
        }
        
        response = requests.post(f"{self.base_url}/auth/register", json=register_data)
        if response.status_code == 201:
            print("✅ 测试用户创建成功")
            return register_data
        else:
            print(f"❌ 用户创建失败: {response.status_code} - {response.text}")
            return None
    
    def login_user(self, user_data: Dict[str, Any]) -> bool:
        """用户登录"""
        login_data = {
            "username": user_data["username"],
            "password": user_data["password"]
        }
        
        response = requests.post(f"{self.base_url}/auth/login", data=login_data)
        if response.status_code == 200:
            login_response = response.json()
            self.auth_headers = {"Authorization": f"Bearer {login_response['access_token']}"}
            print("✅ 用户登录成功")
            return True
        else:
            print(f"❌ 用户登录失败: {response.status_code} - {response.text}")
            return False
    
    def configure_xiaoai_provider(self) -> bool:
        """配置小爱AI提供商"""
        import uuid
        unique_id = uuid.uuid4().hex[:8]
        
        ai_data = {
            "provider_name": f"xiaoai_{unique_id}",
            "provider_type": "openai",  # 使用openai类型，因为小爱使用OpenAI兼容的API
            "api_base_url": "https://xiaoai.com/api/v1/chat/completions",
            "api_key": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "default_model_name": "gpt-4o-mini",
            "is_active": True
        }
        
        print(f"🔧 配置小爱AI提供商...")
        print(f"   提供商名称: {ai_data['provider_name']}")
        print(f"   API地址: {ai_data['api_base_url']}")
        print(f"   模型: {ai_data['default_model_name']}")
        
        response = requests.post(f"{self.base_url}/ai-providers/", json=ai_data, headers=self.auth_headers)
        if response.status_code in [200, 201]:
            ai_response = response.json()
            print("✅ 小爱AI提供商配置成功")
            print(f"   ID: {ai_response['data']['id']}")
            return True
        else:
            print(f"❌ AI提供商配置失败: {response.status_code} - {response.text}")
            return False
    
    def test_ai_provider(self, provider_id: int) -> bool:
        """测试AI提供商连接"""
        print(f"🧪 测试AI提供商 {provider_id}...")
        
        response = requests.post(f"{self.base_url}/ai-providers/{provider_id}/test", headers=self.auth_headers)
        if response.status_code == 200:
            test_response = response.json()
            print("✅ AI提供商测试成功")
            print(f"   响应时间: {test_response.get('data', {}).get('response_time', 'N/A')}ms")
            return True
        else:
            print(f"❌ AI提供商测试失败: {response.status_code} - {response.text}")
            return False
    
    def list_ai_providers(self) -> bool:
        """列出所有AI提供商"""
        print("📋 列出AI提供商...")
        
        response = requests.get(f"{self.base_url}/ai-providers/", headers=self.auth_headers)
        if response.status_code == 200:
            data = response.json()
            providers = data.get('data', {}).get('items', [])
            print(f"✅ 找到 {len(providers)} 个AI提供商:")
            for provider in providers:
                print(f"   - {provider['provider_name']} ({provider['provider_type']}) - {'激活' if provider['is_active'] else '未激活'}")
            return True
        else:
            print(f"❌ 获取AI提供商列表失败: {response.status_code} - {response.text}")
            return False
    
    def run_configuration(self) -> bool:
        """运行完整的配置流程"""
        print("🚀 开始AI提供商配置...")
        print("=" * 50)
        
        # 1. 创建测试用户
        print("\n1. 创建测试用户...")
        user_data = self.create_test_user()
        if not user_data:
            return False
        
        # 2. 用户登录
        print("\n2. 用户登录...")
        if not self.login_user(user_data):
            return False
        
        # 3. 配置小爱AI提供商
        print("\n3. 配置小爱AI提供商...")
        if not self.configure_xiaoai_provider():
            return False
        
        # 4. 列出AI提供商
        print("\n4. 列出AI提供商...")
        if not self.list_ai_providers():
            return False
        
        print("\n" + "=" * 50)
        print("🎉 AI提供商配置完成！")
        print("\n📋 配置摘要:")
        print("   - 小爱AI提供商已配置")
        print("   - API地址: https://xiaoai.com/api/v1/chat/completions")
        print("   - 模型: gpt-4o-mini")
        print("   - 状态: 激活")
        
        return True

def main():
    """主函数"""
    configurator = AIProviderConfigurator()
    
    try:
        success = configurator.run_configuration()
        if success:
            print("\n✅ 配置成功完成！")
            sys.exit(0)
        else:
            print("\n❌ 配置失败！")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ 配置过程中发生错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 