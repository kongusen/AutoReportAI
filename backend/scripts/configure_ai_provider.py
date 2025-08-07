#!/usr/bin/env python3
"""
脚本用于配置AI Provider
"""
import json
import sys
from pathlib import Path

import requests

# Add parent directory to path to import app modules if needed
sys.path.insert(0, str(Path(__file__).parent.parent))

# API配置
BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "admin"
PASSWORD = "password"


def login():
    """登录获取token"""
    login_data = {"username": USERNAME, "password": PASSWORD}

    response = requests.post(f"{BASE_URL}/auth/access-token", data=login_data)

    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"登录失败: {response.status_code} - {response.text}")
        return None


def create_ai_provider(token):
    """创建AI Provider"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    ai_provider_data = {
        "provider_name": "GPT-4o-mini",
        "provider_type": "openai",
        "api_key": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "api_base_url": "https://xiaoai.plus/v1",
        "default_model_name": "gpt-4o-mini",
        "is_active": 1,
    }

    response = requests.post(
        f"{BASE_URL}/ai-providers/", headers=headers, json=ai_provider_data
    )

    print("AI Provider API返回:", response.json())  # 调试用

    if response.status_code == 200:
        resp = response.json()
        provider = resp.get("data", resp)
        print(
            f"✅ AI Provider创建成功: {provider['provider_name']} (ID: {provider['id']})"
        )
        return provider
    else:
        print(f"❌ AI Provider创建失败: {response.status_code} - {response.text}")
        return None


def test_ai_provider(token, provider_id):
    """测试AI Provider连接"""
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.post(
        f"{BASE_URL}/ai-providers/{provider_id}/test", headers=headers
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ AI Provider连接测试成功: {result['msg']}")
        return True
    else:
        print(f"❌ AI Provider连接测试失败: {response.status_code} - {response.text}")
        return False


def create_data_source(token):
    """创建测试数据源"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    data_source_data = {
        "name": "Test_CSV_DataSource",
        "source_type": "csv",
        "file_path": "tests/test_data/csv_data/sample_data.csv",
    }

    response = requests.post(
        f"{BASE_URL}/data-sources/", headers=headers, json=data_source_data
    )

    if response.status_code == 200:
        data_source = response.json()
        print(f"✅ 数据源创建成功: {data_source['name']} (ID: {data_source['id']})")
        return data_source
    else:
        print(f"❌ 数据源创建失败: {response.status_code} - {response.text}")
        return None


def test_data_source(token, data_source_id):
    """测试数据源连接"""
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.post(
        f"{BASE_URL}/data-sources/{data_source_id}/test", headers=headers
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ 数据源连接测试成功: {result['msg']}")
        return True
    else:
        print(f"❌ 数据源连接测试失败: {response.status_code} - {response.text}")
        return False


def test_report_pipeline(token):
    """测试报告生成管道"""
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.post(f"{BASE_URL}/reports/test", headers=headers)

    if response.status_code == 200:
        result = response.json()
        print(f"✅ 报告生成管道测试成功:")
        print(f"   - 管道状态: {result.get('pipeline_status')}")
        print(f"   - AI服务: {result.get('components', {}).get('ai_service')}")
        print(f"   - 模板解析器: {result.get('components', {}).get('template_parser')}")
        print(f"   - Word生成器: {result.get('components', {}).get('word_generator')}")
        return True
    else:
        print(f"❌ 报告生成管道测试失败: {response.status_code} - {response.text}")
        return False


def main():
    print("🚀 开始配置AutoReportAI核心组件...")
    print()

    # 1. 登录
    print("1️⃣ 登录系统...")
    token = login()
    if not token:
        print("❌ 无法获取访问令牌，请检查用户名和密码")
        return
    print("✅ 登录成功!")
    print()

    # 2. 创建AI Provider
    print("2️⃣ 配置AI Provider...")
    provider = create_ai_provider(token)
    if provider:
        # 测试AI Provider连接
        test_ai_provider(token, provider["id"])
    print()

    # 3. 创建数据源
    print("3️⃣ 配置数据源...")
    data_source = create_data_source(token)
    if data_source:
        # 测试数据源连接
        test_data_source(token, data_source["id"])
    print()

    # 4. 测试报告生成管道
    print("4️⃣ 测试报告生成管道...")
    test_report_pipeline(token)
    print()

    print("🎉 核心组件配置完成!")
    print()
    print("📊 现在您可以:")
    print("   - 访问 http://localhost:8000/docs 查看API文档")
    print("   - 使用AI Provider进行智能分析")
    print("   - 测试数据源连接和数据预览")
    print("   - 体验完整的报告生成流程")


if __name__ == "__main__":
    main()
