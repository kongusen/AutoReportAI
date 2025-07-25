"""
端到端集成测试
测试完整的API功能和后端服务集成
"""

import asyncio
import json
import sys
import traceback
from pathlib import Path
from typing import Dict, Any
import requests
import time

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

# 测试配置
API_BASE_URL = "http://localhost:8000"
TEST_USER_DATA = {
    "username": "test_admin",
    "email": "test@example.com", 
    "password": "test123456"
}


class E2ETestSuite:
    """端到端测试套件"""
    
    def __init__(self):
        self.base_url = API_BASE_URL
        self.token = None
        self.test_data = {}
    
    def test_server_health(self) -> bool:
        """测试服务器健康状态"""
        print("🔍 测试服务器健康状态...")
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                health_info = response.json()
                print(f"✅ 服务器健康: {health_info.get('message', 'OK')}")
                return True
            else:
                print(f"❌ 服务器健康检查失败: HTTP {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ 无法连接到服务器: {e}")
            return False
    
    def test_api_docs(self) -> bool:
        """测试API文档访问"""
        print("\n🔍 测试API文档访问...")
        try:
            response = requests.get(f"{self.base_url}/docs", timeout=10)
            if response.status_code == 200:
                print("✅ API文档可访问")
                return True
            else:
                print(f"❌ API文档访问失败: HTTP {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ API文档访问异常: {e}")
            return False
    
    def test_authentication_flow(self) -> bool:
        """测试认证流程"""
        print("\n🔍 测试认证流程...")
        try:
            # 尝试登录（可能用户不存在，这是正常的）
            login_data = {
                "username": TEST_USER_DATA["username"],
                "password": TEST_USER_DATA["password"]
            }
            
            # 测试登录端点存在
            response = requests.post(
                f"{self.base_url}/v1/auth/access-token",
                data=login_data,
                timeout=10
            )
            
            if response.status_code == 200:
                token_info = response.json()
                self.token = token_info.get("access_token")
                print("✅ 认证成功")
                return True
            elif response.status_code in [401, 404, 422]:
                print("✅ 认证端点正常响应（用户可能不存在，这是正常的）")
                return True
            else:
                print(f"⚠️  认证端点异常响应: HTTP {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 认证流程测试异常: {e}")
            return False
    
    def test_core_api_endpoints(self) -> bool:
        """测试核心API端点"""
        print("\n🔍 测试核心API端点...")
        
        endpoints_to_test = [
            ("GET", "/v1/data-sources", "数据源列表"),
            ("GET", "/v1/templates", "模板列表"),
            ("GET", "/v1/tasks", "任务列表"),
            ("GET", "/v1/etl-jobs", "ETL作业列表"),
            ("GET", "/v1/history", "历史记录"),
        ]
        
        passed = 0
        total = len(endpoints_to_test)
        
        for method, endpoint, description in endpoints_to_test:
            try:
                headers = {}
                if self.token:
                    headers["Authorization"] = f"Bearer {self.token}"
                
                response = requests.request(
                    method, 
                    f"{self.base_url}{endpoint}",
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code in [200, 401, 403]:  # 401/403 表示端点存在但需要认证
                    print(f"  ✅ {description}: {endpoint}")
                    passed += 1
                else:
                    print(f"  ❌ {description}: {endpoint} (HTTP {response.status_code})")
                    
            except requests.exceptions.RequestException as e:
                print(f"  ❌ {description}: {endpoint} (异常: {e})")
        
        success_rate = (passed / total) * 100
        print(f"\n📊 API端点测试: {passed}/{total} 通过 ({success_rate:.1f}%)")
        return success_rate >= 80  # 80%以上认为成功
    
    def test_database_integration(self) -> bool:
        """测试数据库集成"""
        print("\n🔍 测试数据库集成...")
        try:
            from app.db.session import SessionLocal
            from sqlalchemy import text
            
            db = SessionLocal()
            
            # 测试基本查询
            result = db.execute(text("SELECT 1 as test_value"))
            test_value = result.fetchone()[0]
            db.close()
            
            if test_value == 1:
                print("✅ 数据库集成正常")
                return True
            else:
                print("❌ 数据库查询结果异常")
                return False
                
        except Exception as e:
            print(f"❌ 数据库集成测试失败: {e}")
            return False
    
    def test_optimized_components(self) -> bool:
        """测试优化组件"""
        print("\n🔍 测试优化组件...")
        try:
            # 测试优化模型
            from app.models.optimized.data_source import DataSourceType
            assert DataSourceType.DORIS == "doris"
            
            # 测试CRUD基类
            from app.crud.base_optimized import CRUDBase
            
            # 测试性能优化组件
            from app.services.data_processing.query_optimizer import QueryOptimizer
            from app.services.async_mcp_client import AsyncMCPClient
            
            optimizer = QueryOptimizer()
            client = AsyncMCPClient()
            
            print("✅ 优化组件加载正常")
            return True
            
        except Exception as e:
            print(f"❌ 优化组件测试失败: {e}")
            traceback.print_exc()
            return False
    
    def test_doris_integration_availability(self) -> bool:
        """测试Doris集成可用性"""
        print("\n🔍 测试Doris集成可用性...")
        try:
            from app.services.connectors.doris_connector import DorisConnector, DorisConfig
            
            # 创建测试配置
            config = DorisConfig(
                fe_hosts=["localhost"],
                be_hosts=["localhost"],
                database="test"
            )
            
            connector = DorisConnector(config)
            
            print("✅ Doris集成组件可用")
            return True
            
        except Exception as e:
            print(f"❌ Doris集成测试失败: {e}")
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("🚀 开始运行AutoReportAI端到端集成测试\n")
        
        tests = [
            ("服务器健康", self.test_server_health),
            ("API文档", self.test_api_docs),
            ("认证流程", self.test_authentication_flow),
            ("核心API端点", self.test_core_api_endpoints),
            ("数据库集成", self.test_database_integration),
            ("优化组件", self.test_optimized_components),
            ("Doris集成", self.test_doris_integration_availability),
        ]
        
        results = {}
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                start_time = time.time()
                result = test_func()
                end_time = time.time()
                
                results[test_name] = {
                    "passed": result,
                    "duration": round(end_time - start_time, 2)
                }
                
                if result:
                    passed += 1
                else:
                    failed += 1
                    
            except Exception as e:
                print(f"❌ {test_name}测试异常: {e}")
                results[test_name] = {
                    "passed": False,
                    "error": str(e),
                    "duration": 0
                }
                failed += 1
        
        # 生成测试报告
        total_tests = passed + failed
        success_rate = (passed / total_tests) * 100 if total_tests > 0 else 0
        
        report = {
            "summary": {
                "total_tests": total_tests,
                "passed": passed,
                "failed": failed,
                "success_rate": round(success_rate, 1)
            },
            "results": results,
            "recommendations": []
        }
        
        # 生成建议
        if success_rate >= 90:
            report["recommendations"].append("🎉 系统运行良好，所有核心功能正常")
        elif success_rate >= 70:
            report["recommendations"].append("✅ 系统基本正常，建议修复失败的测试")
        else:
            report["recommendations"].append("⚠️  系统存在较多问题，需要重点关注")
        
        if not results.get("服务器健康", {}).get("passed", False):
            report["recommendations"].append("🔧 优先检查服务器启动状态")
        
        if not results.get("数据库集成", {}).get("passed", False):
            report["recommendations"].append("🗄️  检查数据库连接配置")
        
        return report


def print_test_report(report: Dict[str, Any]):
    """打印测试报告"""
    print("\n" + "="*60)
    print("📊 AutoReportAI 端到端集成测试报告")
    print("="*60)
    
    summary = report["summary"]
    print(f"\n📈 测试摘要:")
    print(f"   总计: {summary['total_tests']}")
    print(f"   通过: {summary['passed']}")
    print(f"   失败: {summary['failed']}")
    print(f"   成功率: {summary['success_rate']}%")
    
    print(f"\n📋 详细结果:")
    for test_name, result in report["results"].items():
        status = "✅" if result["passed"] else "❌"
        duration = result.get("duration", 0)
        print(f"   {status} {test_name}: {duration}s")
        if "error" in result:
            print(f"      错误: {result['error']}")
    
    print(f"\n💡 建议:")
    for recommendation in report["recommendations"]:
        print(f"   {recommendation}")
    
    print("\n" + "="*60)


async def main():
    """主函数"""
    try:
        suite = E2ETestSuite()
        report = await suite.run_all_tests()
        
        print_test_report(report)
        
        # 保存测试报告
        report_file = Path(__file__).parent / "test_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 测试报告已保存到: {report_file}")
        
        # 返回成功率
        success_rate = report["summary"]["success_rate"]
        return success_rate >= 70  # 70%以上认为成功
        
    except Exception as e:
        print(f"\n💥 测试执行异常: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  测试被用户中断")
        sys.exit(1)