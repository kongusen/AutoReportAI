#!/usr/bin/env python3
"""
后端测试运行器
支持多种测试模式：单元测试、集成测试、端到端测试
"""

import subprocess
import sys
import os
import argparse
from pathlib import Path

def run_command(cmd, cwd=None):
    """运行shell命令"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_backend_running():
    """检查后端是否运行"""
    try:
        import requests
        response = requests.get("http://localhost:8000/api/v2/system/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def run_unit_tests():
    """运行单元测试"""
    print("🔬 运行单元测试...")
    cmd = "python -m pytest tests/unit -v --tb=short"
    success, stdout, stderr = run_command(cmd)
    if success:
        print("✅ 单元测试通过")
    else:
        print("❌ 单元测试失败")
        print(stderr)
    return success

def run_integration_tests():
    """运行集成测试"""
    print("🔗 运行集成测试...")
    cmd = "python -m pytest tests/integration -v --tb=short"
    success, stdout, stderr = run_command(cmd)
    if success:
        print("✅ 集成测试通过")
    else:
        print("❌ 集成测试失败")
        print(stderr)
    return success

def run_e2e_tests():
    """运行端到端测试"""
    print("🎯 运行端到端测试...")
    
    if not check_backend_running():
        print("⚠️  后端服务未运行，请先启动后端:")
        print("   make run-backend")
        return False
    
    cmd = "python test_backend_final.py"
    success, stdout, stderr = run_command(cmd)
    if success:
        print("✅ 端到端测试通过")
    else:
        print("❌ 端到端测试失败")
        print(stderr)
    return success

def run_all_tests():
    """运行所有测试"""
    print("🚀 运行所有测试...")
    
    results = []
    
    # 运行单元测试
    results.append(run_unit_tests())
    
    # 运行集成测试
    results.append(run_integration_tests())
    
    # 运行端到端测试
    results.append(run_e2e_tests())
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 测试总结: {passed}/{total} 测试套件通过")
    
    return passed == total

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AutoReportAI 后端测试运行器")
    parser.add_argument("--mode", choices=["unit", "integration", "e2e", "all"], 
                       default="all", help="测试模式")
    parser.add_argument("--backend-only", action="store_true", 
                       help="仅测试后端，不启动服务")
    
    args = parser.parse_args()
    
    print("🔍 AutoReportAI 后端测试运行器")
    print("=" * 50)
    
    # 切换到backend目录
    os.chdir(Path(__file__).parent)
    
    success = False
    
    if args.mode == "unit":
        success = run_unit_tests()
    elif args.mode == "integration":
        success = run_integration_tests()
    elif args.mode == "e2e":
        success = run_e2e_tests()
    else:
        success = run_all_tests()
    
    if success:
        print("\n🎉 所有测试完成！")
    else:
        print("\n❌ 部分测试失败")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
