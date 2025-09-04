#!/usr/bin/env python3
"""
AutoReportAI 测试运行器
支持多种测试类型和参数
"""

import argparse
import sys
import subprocess
import os
from pathlib import Path


def run_command(cmd, description=""):
    """运行命令并处理结果"""
    if description:
        print(f"🔧 {description}")
    
    print(f"执行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ 命令执行失败 (退出码: {result.returncode})")
        if result.stderr:
            print(f"错误输出: {result.stderr}")
        return False
    else:
        print(f"✅ {description or '命令执行成功'}")
        if result.stdout:
            print(result.stdout)
        return True


def run_pytest(test_paths, options=None):
    """运行 pytest 测试"""
    cmd = ["python", "-m", "pytest"]
    
    if options:
        cmd.extend(options)
    
    cmd.extend(test_paths)
    
    return run_command(cmd, "运行 pytest 测试")


def run_linting():
    """运行代码质量检查"""
    print("🔍 运行代码质量检查...")
    
    # Black 格式化检查
    if not run_command(["python", "-m", "black", "--check", "backend/app", "tests/"], "Black 格式化检查"):
        return False
    
    # Flake8 检查
    if not run_command(["python", "-m", "flake8", "backend/app", "tests/"], "Flake8 代码检查"):
        return False
    
    # MyPy 类型检查
    if not run_command(["python", "-m", "mypy", "backend/app"], "MyPy 类型检查"):
        return False
    
    # Bandit 安全检查
    if not run_command(["python", "-m", "bandit", "-r", "backend/app"], "Bandit 安全检查"):
        return False
    
    return True


def run_unit_tests():
    """运行单元测试"""
    return run_pytest(["unit/"], ["-v", "--tb=short"])


def run_integration_tests():
    """运行集成测试"""
    return run_pytest(["integration/"], ["-v", "--tb=short"])


def run_api_tests():
    """运行API测试"""
    return run_pytest(["api/"], ["-v", "--tb=short"])


def run_agent_tests():
    """运行Agent测试"""
    return run_pytest(["agent/"], ["-v", "--tb=short"])


def run_chart_tests():
    """运行图表测试"""
    return run_pytest(["charts/"], ["-v", "--tb=short"])


def run_docker_tests():
    """运行Docker测试"""
    return run_pytest(["docker/"], ["-v", "--tb=short"])


def run_minio_tests():
    """运行Minio测试"""
    return run_pytest(["minio/"], ["-v", "--tb=short"])


def run_e2e_tests():
    """运行端到端测试"""
    return run_pytest(["e2e/"], ["-v", "--tb=short"])


def run_performance_tests():
    """运行性能测试"""
    return run_pytest(["performance/"], ["-v", "--tb=short"])


def run_coverage():
    """生成覆盖率报告"""
    cmd = [
        "python", "-m", "pytest",
        "--cov=backend/app",
        "--cov-report=html",
        "--cov-report=xml",
        "--cov-report=term-missing",
        "tests/"
    ]
    return run_command(cmd, "生成覆盖率报告")


def main():
    parser = argparse.ArgumentParser(description="AutoReportAI 测试运行器")
    parser.add_argument("--unit", action="store_true", help="运行单元测试")
    parser.add_argument("--integration", action="store_true", help="运行集成测试")
    parser.add_argument("--api", action="store_true", help="运行API测试")
    parser.add_argument("--agent", action="store_true", help="运行Agent测试")
    parser.add_argument("--charts", action="store_true", help="运行图表测试")
    parser.add_argument("--docker", action="store_true", help="运行Docker测试")
    parser.add_argument("--minio", action="store_true", help="运行Minio测试")
    parser.add_argument("--e2e", action="store_true", help="运行端到端测试")
    parser.add_argument("--performance", action="store_true", help="运行性能测试")
    parser.add_argument("--lint", action="store_true", help="运行代码质量检查")
    parser.add_argument("--coverage", action="store_true", help="生成覆盖率报告")
    parser.add_argument("--all", action="store_true", help="运行所有测试")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    # 如果没有指定任何参数，运行快速测试套件
    if not any(vars(args).values()):
        print("🚀 运行快速测试套件...")
        success = True
        success &= run_unit_tests()
        success &= run_api_tests()
        return 0 if success else 1
    
    success = True
    
    # 运行指定的测试
    if args.lint:
        success &= run_linting()
    
    if args.unit or args.all:
        success &= run_unit_tests()
    
    if args.integration or args.all:
        success &= run_integration_tests()
    
    if args.api or args.all:
        success &= run_api_tests()
    
    if args.agent or args.all:
        success &= run_agent_tests()
    
    if args.charts or args.all:
        success &= run_chart_tests()
    
    if args.docker or args.all:
        success &= run_docker_tests()
    
    if args.minio or args.all:
        success &= run_minio_tests()
    
    if args.e2e or args.all:
        success &= run_e2e_tests()
    
    if args.performance or args.all:
        success &= run_performance_tests()
    
    if args.coverage:
        success &= run_coverage()
    
    if success:
        print("🎉 所有测试通过!")
        return 0
    else:
        print("❌ 部分测试失败!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
