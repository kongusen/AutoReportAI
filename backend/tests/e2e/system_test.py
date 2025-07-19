#!/usr/bin/env python3
"""
AutoReportAI 系统功能测试脚本
"""
import json
import time
from datetime import datetime

import requests

# 测试配置
BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "admin"
PASSWORD = "password"


def print_test_header(test_name):
    """打印测试标题"""
    print(f"\n{'='*60}")
    print(f"🧪 {test_name}")
    print(f"{'='*60}")


def print_result(success, message):
    """打印测试结果"""
    icon = "✅" if success else "❌"
    print(f"{icon} {message}")


def get_auth_token():
    """获取认证令牌"""
    login_data = {"username": USERNAME, "password": PASSWORD}
    response = requests.post(f"{BASE_URL}/auth/access-token", data=login_data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"登录失败: {response.status_code} - {response.text}")


def test_system_health():
    """测试系统健康状态"""
    print_test_header("系统健康状态检查")

    # 测试根端点
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            print_result(True, "API服务正常运行")
        else:
            print_result(False, f"API服务异常: {response.status_code}")
    except Exception as e:
        print_result(False, f"API服务连接失败: {e}")

    # 测试认证
    try:
        token = get_auth_token()
        print_result(True, "用户认证系统正常")
    except Exception as e:
        print_result(False, f"用户认证失败: {e}")
        return None

    return token


def test_ai_providers(token):
    """测试AI Provider功能"""
    print_test_header("AI Provider功能测试")

    headers = {"Authorization": f"Bearer {token}"}

    # 获取AI Provider列表
    try:
        response = requests.get(f"{BASE_URL}/ai-providers/", headers=headers)
        if response.status_code == 200:
            providers = response.json()
            print_result(True, f"AI Provider列表获取成功，共{len(providers)}个提供商")

            if providers:
                provider_id = providers[0]["id"]
                provider_name = providers[0]["provider_name"]

                # 测试连接
                response = requests.post(
                    f"{BASE_URL}/ai-providers/{provider_id}/test", headers=headers
                )
                if response.status_code == 200:
                    print_result(True, f"AI Provider '{provider_name}' 连接测试成功")
                else:
                    print_result(False, f"AI Provider '{provider_name}' 连接测试失败")

                # 获取模型列表
                response = requests.get(
                    f"{BASE_URL}/ai-providers/{provider_id}/models", headers=headers
                )
                if response.status_code == 200:
                    models = response.json()
                    print_result(
                        True, f"AI Provider模型列表获取成功，共{len(models)}个模型"
                    )
                else:
                    print_result(False, "AI Provider模型列表获取失败")
            else:
                print_result(False, "没有找到AI Provider")
        else:
            print_result(False, f"AI Provider列表获取失败: {response.status_code}")
    except Exception as e:
        print_result(False, f"AI Provider测试异常: {e}")


def test_data_sources(token):
    """测试数据源功能"""
    print_test_header("数据源功能测试")

    headers = {"Authorization": f"Bearer {token}"}

    # 获取数据源列表
    try:
        response = requests.get(f"{BASE_URL}/data-sources/", headers=headers)
        if response.status_code == 200:
            sources = response.json()
            print_result(True, f"数据源列表获取成功，共{len(sources)}个数据源")

            if sources:
                source_id = sources[0]["id"]
                source_name = sources[0]["name"]

                # 测试连接
                response = requests.post(
                    f"{BASE_URL}/data-sources/{source_id}/test", headers=headers
                )
                if response.status_code == 200:
                    print_result(True, f"数据源 '{source_name}' 连接测试成功")
                else:
                    print_result(False, f"数据源 '{source_name}' 连接测试失败")

                # 数据预览
                response = requests.get(
                    f"{BASE_URL}/data-sources/{source_id}/preview", headers=headers
                )
                if response.status_code == 200:
                    preview = response.json()
                    print_result(True, f"数据预览成功，共{len(preview['data'])}行数据")
                else:
                    print_result(False, "数据预览失败")
            else:
                print_result(False, "没有找到数据源")
        else:
            print_result(False, f"数据源列表获取失败: {response.status_code}")
    except Exception as e:
        print_result(False, f"数据源测试异常: {e}")


def test_etl_jobs(token):
    """测试ETL作业功能"""
    print_test_header("ETL作业功能测试")

    headers = {"Authorization": f"Bearer {token}"}

    # 获取ETL作业列表
    try:
        response = requests.get(f"{BASE_URL}/etl-jobs/", headers=headers)
        if response.status_code == 200:
            jobs = response.json()
            print_result(True, f"ETL作业列表获取成功，共{len(jobs)}个作业")

            if jobs:
                job_id = jobs[0]["id"]
                job_name = jobs[0]["name"]

                # 验证配置
                response = requests.post(
                    f"{BASE_URL}/etl-jobs/{job_id}/validate", headers=headers
                )
                if response.status_code == 200:
                    validation = response.json()
                    if validation["valid"]:
                        print_result(True, f"ETL作业 '{job_name}' 配置验证成功")
                    else:
                        print_result(False, f"ETL作业 '{job_name}' 配置验证失败")
                else:
                    print_result(False, f"ETL作业 '{job_name}' 配置验证失败")

                # 干运行测试
                response = requests.post(
                    f"{BASE_URL}/etl-jobs/{job_id}/run?dry_run=true", headers=headers
                )
                if response.status_code == 200:
                    print_result(True, f"ETL作业 '{job_name}' 干运行测试成功")
                else:
                    print_result(False, f"ETL作业 '{job_name}' 干运行测试失败")
            else:
                print_result(False, "没有找到ETL作业")
        else:
            print_result(False, f"ETL作业列表获取失败: {response.status_code}")
    except Exception as e:
        print_result(False, f"ETL作业测试异常: {e}")


def test_report_generation(token):
    """测试报告生成功能"""
    print_test_header("报告生成功能测试")

    headers = {"Authorization": f"Bearer {token}"}

    # 测试报告生成管道
    try:
        response = requests.post(f"{BASE_URL}/reports/test", headers=headers)
        if response.status_code == 200:
            result = response.json()
            pipeline_status = result.get("pipeline_status", "unknown")
            print_result(True, f"报告生成管道状态: {pipeline_status}")

            components = result.get("components", {})
            for component, status in components.items():
                print_result(True, f"  - {component}: {status}")
        else:
            print_result(False, f"报告生成管道测试失败: {response.status_code}")
    except Exception as e:
        print_result(False, f"报告生成测试异常: {e}")


def test_tasks(token):
    """测试任务管理功能"""
    print_test_header("任务管理功能测试")

    headers = {"Authorization": f"Bearer {token}"}

    # 获取任务列表
    try:
        response = requests.get(f"{BASE_URL}/tasks/", headers=headers)
        if response.status_code == 200:
            tasks = response.json()
            print_result(True, f"任务列表获取成功，共{len(tasks)}个任务")
        else:
            print_result(False, f"任务列表获取失败: {response.status_code}")
    except Exception as e:
        print_result(False, f"任务管理测试异常: {e}")


def test_database_connectivity():
    """测试数据库连接"""
    print_test_header("数据库连接测试")

    try:
        import psycopg2

        from app.core.config import settings

        # 测试主数据库
        conn = psycopg2.connect(settings.DATABASE_URL)
        conn.close()
        print_result(True, "主数据库连接正常")

        # 测试测试数据库
        conn = psycopg2.connect(settings.test_db_url)
        conn.close()
        print_result(True, "测试数据库连接正常")

    except Exception as e:
        print_result(False, f"数据库连接测试失败: {e}")


def test_redis_connectivity():
    """测试Redis连接"""
    print_test_header("Redis连接测试")

    try:
        import redis

        from app.core.config import settings

        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        print_result(True, "Redis连接正常")

    except Exception as e:
        print_result(False, f"Redis连接测试失败: {e}")


def run_performance_test(token):
    """运行性能测试"""
    print_test_header("性能测试")

    headers = {"Authorization": f"Bearer {token}"}

    # API响应时间测试
    endpoints = [
        ("/ai-providers/", "AI Provider列表"),
        ("/data-sources/", "数据源列表"),
        ("/etl-jobs/", "ETL作业列表"),
        ("/tasks/", "任务列表"),
    ]

    for endpoint, name in endpoints:
        try:
            start_time = time.time()
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            end_time = time.time()

            response_time = (end_time - start_time) * 1000  # 转换为毫秒

            if response.status_code == 200:
                if response_time < 1000:  # 小于1秒
                    print_result(True, f"{name} 响应时间: {response_time:.2f}ms")
                else:
                    print_result(False, f"{name} 响应时间过长: {response_time:.2f}ms")
            else:
                print_result(False, f"{name} 响应失败: {response.status_code}")
        except Exception as e:
            print_result(False, f"{name} 测试异常: {e}")


def main():
    """主测试函数"""
    print("🚀 AutoReportAI 系统功能测试开始")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 系统健康检查
    token = test_system_health()
    if not token:
        print("\n❌ 系统健康检查失败，终止测试")
        return

    # 数据库和Redis连接测试
    test_database_connectivity()
    test_redis_connectivity()

    # 功能测试
    test_ai_providers(token)
    test_data_sources(token)
    test_etl_jobs(token)
    test_report_generation(token)
    test_tasks(token)

    # 性能测试
    run_performance_test(token)

    print("\n" + "=" * 60)
    print("🎉 AutoReportAI 系统功能测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
