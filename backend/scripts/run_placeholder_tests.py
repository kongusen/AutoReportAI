#!/usr/bin/env python3
"""
智能占位符系统测试运行脚本

用于运行完整的占位符系统测试套件，包括：
- 单元测试
- 集成测试  
- 性能测试
- 功能测试
- 验收测试

使用方法:
    python scripts/run_placeholder_tests.py [选项]
    
选项:
    --all           运行所有测试 (默认)
    --unit          只运行单元测试
    --integration   只运行集成测试
    --performance   只运行性能测试
    --functional    只运行功能测试
    --acceptance    只运行验收测试
    --coverage      生成测试覆盖率报告
    --verbose       详细输出模式
    --parallel      并行运行测试
    --html          生成HTML测试报告
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime


class PlaceholderTestRunner:
    """占位符测试运行器"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_dir = project_root / "tests" / "services" / "domain" / "placeholder"
        self.reports_dir = project_root / "test_reports"
        self.reports_dir.mkdir(exist_ok=True)
        
    def run_tests(self, test_type: str = "all", options: dict = None):
        """运行指定类型的测试"""
        options = options or {}
        
        # 构建pytest命令
        cmd = ["python3.11", "-m", "pytest"]
        
        # 添加测试路径
        if test_type == "all":
            cmd.append(str(self.test_dir))
        elif test_type == "unit":
            cmd.extend([
                str(self.test_dir / "test_parsers.py"),
                str(self.test_dir / "test_context_analysis.py")
            ])
        elif test_type == "integration":
            cmd.append(str(self.test_dir / "test_integration.py"))
        elif test_type == "performance":
            cmd.append(str(self.test_dir / "test_performance.py"))
        elif test_type == "functional":
            cmd.append(str(self.test_dir / "test_functional.py"))
        elif test_type == "acceptance":
            cmd.append(str(self.test_dir / "test_acceptance.py"))
        else:
            raise ValueError(f"未知的测试类型: {test_type}")
        
        # 添加选项
        if options.get("verbose"):
            cmd.extend(["-v", "-s"])
        
        if options.get("parallel"):
            cmd.extend(["-n", "auto"])
        
        # 测试覆盖率
        if options.get("coverage"):
            cmd.extend([
                "--cov=app.services.domain.placeholder",
                "--cov-report=term-missing",
                f"--cov-report=html:{self.reports_dir}/coverage_html",
                f"--cov-report=xml:{self.reports_dir}/coverage.xml"
            ])
        
        # HTML报告
        if options.get("html"):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_report = self.reports_dir / f"test_report_{test_type}_{timestamp}.html"
            cmd.extend([f"--html={html_report}", "--self-contained-html"])
        
        # JUnit XML报告
        junit_report = self.reports_dir / f"junit_{test_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
        cmd.extend([f"--junit-xml={junit_report}"])
        
        # 执行测试
        print(f"🚀 开始运行 {test_type} 测试...")
        print(f"命令: {' '.join(cmd)}")
        print("-" * 80)
        
        try:
            result = subprocess.run(cmd, cwd=self.project_root, check=False)
            return result.returncode == 0
        except Exception as e:
            print(f"❌ 测试执行失败: {e}")
            return False
    
    def run_test_suite(self, options: dict = None):
        """运行完整的测试套件"""
        options = options or {}
        
        print("🧪 智能占位符系统测试套件")
        print("=" * 80)
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"项目根目录: {self.project_root}")
        print(f"测试目录: {self.test_dir}")
        print(f"报告目录: {self.reports_dir}")
        print("=" * 80)
        
        test_results = {}
        test_sequence = [
            ("unit", "单元测试"),
            ("integration", "集成测试"),
            ("performance", "性能测试"),
            ("functional", "功能测试"),
            ("acceptance", "验收测试")
        ]
        
        for test_type, test_name in test_sequence:
            print(f"\n📋 正在执行 {test_name}...")
            success = self.run_tests(test_type, options)
            test_results[test_type] = success
            
            status = "✅ 通过" if success else "❌ 失败"
            print(f"{test_name}: {status}")
            
            if not success and not options.get("continue_on_failure", True):
                print("⚠️  测试失败，停止执行后续测试")
                break
        
        # 测试结果总结
        self.print_summary(test_results)
        
        # 返回整体测试结果
        return all(test_results.values())
    
    def print_summary(self, test_results: dict):
        """打印测试结果总结"""
        print("\n" + "=" * 80)
        print("📊 测试结果总结")
        print("=" * 80)
        
        total_tests = len(test_results)
        passed_tests = sum(1 for result in test_results.values() if result)
        failed_tests = total_tests - passed_tests
        
        print(f"总测试套件数: {total_tests}")
        print(f"通过测试数: {passed_tests}")
        print(f"失败测试数: {failed_tests}")
        print(f"成功率: {passed_tests/total_tests*100:.1f}%")
        
        print("\n详细结果:")
        for test_type, success in test_results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            test_name = {
                "unit": "单元测试",
                "integration": "集成测试", 
                "performance": "性能测试",
                "functional": "功能测试",
                "acceptance": "验收测试"
            }.get(test_type, test_type)
            print(f"  {test_name}: {status}")
        
        if all(test_results.values()):
            print("\n🎉 所有测试通过！智能占位符系统已准备就绪。")
        else:
            print(f"\n⚠️  有 {failed_tests} 个测试套件失败，请检查并修复问题。")
        
        print(f"\n📁 测试报告保存在: {self.reports_dir}")
        print("=" * 80)
    
    def check_environment(self):
        """检查测试环境"""
        print("🔍 检查测试环境...")
        
        # 检查Python版本
        python_version = sys.version_info
        if python_version < (3, 8):
            print("❌ Python版本过低，需要Python 3.8+")
            return False
        print(f"✅ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        # 检查测试目录
        if not self.test_dir.exists():
            print(f"❌ 测试目录不存在: {self.test_dir}")
            return False
        print(f"✅ 测试目录: {self.test_dir}")
        
        # 检查必要的测试文件
        required_files = [
            "test_parsers.py",
            "test_context_analysis.py",
            "test_integration.py", 
            "test_performance.py",
            "test_functional.py",
            "test_acceptance.py"
        ]
        
        missing_files = []
        for file_name in required_files:
            file_path = self.test_dir / file_name
            if not file_path.exists():
                missing_files.append(file_name)
        
        if missing_files:
            print(f"❌ 缺少测试文件: {', '.join(missing_files)}")
            return False
        print(f"✅ 所有测试文件存在")
        
        # 检查依赖包
        try:
            import pytest
            import asyncio
            print(f"✅ pytest版本: {pytest.__version__}")
        except ImportError as e:
            print(f"❌ 缺少依赖包: {e}")
            return False
        
        return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="智能占位符系统测试运行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # 测试类型参数
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument("--all", action="store_true", default=True,
                          help="运行所有测试 (默认)")
    test_group.add_argument("--unit", action="store_true",
                          help="只运行单元测试")
    test_group.add_argument("--integration", action="store_true", 
                          help="只运行集成测试")
    test_group.add_argument("--performance", action="store_true",
                          help="只运行性能测试")
    test_group.add_argument("--functional", action="store_true",
                          help="只运行功能测试")
    test_group.add_argument("--acceptance", action="store_true",
                          help="只运行验收测试")
    
    # 输出选项
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="详细输出模式")
    parser.add_argument("--coverage", action="store_true",
                       help="生成测试覆盖率报告")
    parser.add_argument("--html", action="store_true",
                       help="生成HTML测试报告")
    parser.add_argument("--parallel", action="store_true",
                       help="并行运行测试")
    parser.add_argument("--continue-on-failure", action="store_true",
                       help="测试失败时继续执行后续测试")
    
    # 其他选项
    parser.add_argument("--project-root", type=Path,
                       default=Path(__file__).parent.parent,
                       help="项目根目录路径")
    
    args = parser.parse_args()
    
    # 确定项目根目录
    project_root = args.project_root.resolve()
    
    # 创建测试运行器
    runner = PlaceholderTestRunner(project_root)
    
    # 检查环境
    if not runner.check_environment():
        print("❌ 环境检查失败")
        return 1
    
    # 确定测试类型
    if args.unit:
        test_type = "unit"
    elif args.integration:
        test_type = "integration"
    elif args.performance:
        test_type = "performance"
    elif args.functional:
        test_type = "functional"
    elif args.acceptance:
        test_type = "acceptance"
    else:
        test_type = "all"
    
    # 准备选项
    options = {
        "verbose": args.verbose,
        "coverage": args.coverage,
        "html": args.html,
        "parallel": args.parallel,
        "continue_on_failure": args.continue_on_failure
    }
    
    # 运行测试
    try:
        if test_type == "all":
            success = runner.run_test_suite(options)
        else:
            success = runner.run_tests(test_type, options)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        return 130
    except Exception as e:
        print(f"❌ 测试运行出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())