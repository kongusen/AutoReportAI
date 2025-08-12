#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试投诉件统计模板的智能占位符解析
"""

import requests
import json

# API配置
BASE_URL = "http://localhost:8000"
AUTH_URL = f"{BASE_URL}/api/v1/auth/login"
PLACEHOLDER_URL = f"{BASE_URL}/api/v1/intelligent-placeholders/generate-report"

def login():
    """登录获取token"""
    login_data = {
        "username": "admin",
        "password": "password"
    }
    
    response = requests.post(
        AUTH_URL,
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code == 200:
        token_data = response.json()
        # 处理新的响应格式
        if "data" in token_data and "access_token" in token_data["data"]:
            return token_data["data"]["access_token"]
        return token_data.get("access_token")
    else:
        print(f"登录失败: {response.status_code}")
        print(f"响应: {response.text}")
        return None

def test_complaint_template():
    """测试投诉件统计模板"""
    
    # 获取token
    token = login()
    if not token:
        print("无法获取认证token")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 使用现有的投诉统计模板
    template_id = "45cfcb95-01c7-45ed-a63c-5aae24ed7c87"  # 投诉统计演示报告模板
    data_source_id = "9d7e4bd1-7ae3-458a-b25f-6408074df186"  # DorisTestDataSource
    
    # 准备请求数据 - 使用GET参数方式
    params = {
        "template_id": template_id,
        "data_source_id": data_source_id
    }
    
    # 额外的请求体（如果需要）
    request_data = {
        "processing_config": {
            "region": "全市",
            "time_range": "2024年度"
        },
        "output_config": {
            "format": "text"
        }
    }
    
    print("🔍 开始测试投诉件统计模板...")
    print(f"📝 模板ID: {template_id}")
    print(f"📊 数据源ID: {data_source_id}\n")
    
    try:
        # 发送请求
        response = requests.post(
            PLACEHOLDER_URL,
            headers=headers,
            params=params,
            json=request_data,
            timeout=60
        )
        
        print(f"📊 响应状态: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 请求成功!")
            print(f"📋 解析结果:")
            
            # 显示解析的占位符
            if "placeholders" in result:
                print("\n🏷️  识别的占位符:")
                for placeholder in result["placeholders"]:
                    print(f"  - {placeholder.get('original', 'N/A')} -> {placeholder.get('resolved_value', 'N/A')}")
            
            # 显示生成的内容
            if "processed_content" in result:
                print(f"\n📄 生成的报告内容:\n{result['processed_content']}")
            
            # 显示使用的数据
            if "data_summary" in result:
                print(f"\n📈 数据摘要:\n{result['data_summary']}")
                
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏱️ 请求超时")
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求异常: {e}")
    except Exception as e:
        print(f"❌ 未知错误: {e}")

if __name__ == "__main__":
    test_complaint_template()