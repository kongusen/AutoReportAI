#!/usr/bin/env python3
"""
AutoReportAI 测试运行器
提供多种测试运行模式和配置选项
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import List, Optional

# 项目根目录
ROOT_DIR = Path(__file__).parent
BACKEND_DIR = ROOT_DIR / "backend"

class TestRunner:
    """测试运行器"""
    
    def __init__(self):
        self.root_dir = ROOT_DIR
        self.tests_dir = ROOT_DIR / "tests"
        self.python_cmd = self._get_python_command()
        
    def _get_python_command(self) -> str:
        """获取Python命令，智能检测环境"""
        # CI环境检测
        if os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS'):
            return "python"
        
        # 本地虚拟环境检测
        venv_python = ROOT_DIR / "backend" / "venv" / "bin" / "python"
        if venv_python.exists():
            return str(venv_python)
            
        # 当前激活的虚拟环境
        if os.environ.get('VIRTUAL_ENV'):
            venv_python = Path(os.environ['VIRTUAL_ENV']) / "bin" / "python"
            if venv_python.exists():
                return str(venv_python)
        
        # 回退到系统Python
        return "python3"
        
    def run_command(self, cmd: List[str], cwd: Optional[Path] = None) -> int:
        """运行命令并返回退出码"""
        try:
            result = subprocess.run(
                cmd, 
                cwd=cwd or self.root_dir,
                capture_output=False,
                text=True
            )
            return result.returncode
        except Exception as e:
            print(f"❌ 命令执行失败: {e}")
            return 1
    
    def check_dependencies(self) -> bool:
        """检查测试依赖"""
        print("🔍 检查测试依赖...")
        
        # 检查pytest
        if self.run_command([self.python_cmd, "-m", "pytest", "--version"]) != 0:
            print("❌ pytest未安装，请运行: pip install pytest")
            return False
            
        # 检查coverage
        if self.run_command([self.python_cmd, "-m", "coverage", "--version"]) != 0:
            print("⚠️  coverage未安装，将无法生成覆盖率报告")
            
        print("✅ 依赖检查完成")
        return True
    
    def run_unit_tests(self, verbose: bool = False) -> int:
        """运行单元测试"""
        print("\n🧪 运行单元测试...")
        cmd = [self.python_cmd, "-m", "pytest", "tests/unit/", "-m", "unit"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_integration_tests(self, verbose: bool = False) -> int:
        """运行集成测试"""
        print("\n🔗 运行集成测试...")
        cmd = [self.python_cmd, "-m", "pytest", "tests/integration/", "-m", "integration"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_api_tests(self, verbose: bool = False) -> int:
        """运行API测试"""
        print("\n🌐 运行API测试...")
        cmd = [self.python_cmd, "-m", "pytest", "tests/api/", "-m", "api"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_agent_tests(self, verbose: bool = False) -> int:
        """运行React Agent测试"""
        print("\n🤖 运行React Agent测试...")
        cmd = [self.python_cmd, "-m", "pytest", "tests/agent/", "-m", "agent"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_chart_tests(self, verbose: bool = False) -> int:
        """运行图表测试"""
        print("\n📊 运行图表生成测试...")
        cmd = [self.python_cmd, "-m", "pytest", "tests/charts/", "-m", "charts"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_docker_tests(self, verbose: bool = False) -> int:
        """运行Docker环境测试"""
        print("\n🐳 运行Docker环境测试...")
        cmd = [self.python_cmd, "-m", "pytest", "tests/docker/", "-m", "docker"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_minio_tests(self, verbose: bool = False) -> int:
        """运行Minio存储测试"""
        print("\n📦 运行Minio存储测试...")
        cmd = [self.python_cmd, "-m", "pytest", "tests/minio/", "-m", "minio"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_e2e_tests(self, verbose: bool = False) -> int:
        """运行端到端测试"""
        print("\n🏁 运行端到端测试...")
        cmd = [self.python_cmd, "-m", "pytest", "tests/e2e/", "-m", "e2e"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_performance_tests(self, verbose: bool = False) -> int:
        """运行性能测试"""
        print("\n⚡ 运行性能测试...")
        cmd = [self.python_cmd, "-m", "pytest", "tests/performance/", "-m", "performance"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_all_tests(self, verbose: bool = False, coverage: bool = True) -> int:
        """运行所有测试"""
        print("\n🚀 运行完整测试套件...")
        
        cmd = [self.python_cmd, "-m", "pytest", "tests/"]
        if verbose:
            cmd.append("-v")
        if coverage:
            cmd.extend(["--cov=backend/app", "--cov-report=html", "--cov-report=term"])
        
        return self.run_command(cmd)
    
    def run_specific_test(self, test_path: str, verbose: bool = False) -> int:
        """运行特定测试文件或目录"""
        print(f"\n🎯 运行特定测试: {test_path}")
        cmd = [self.python_cmd, "-m", "pytest", test_path]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def generate_coverage_report(self) -> int:
        """生成覆盖率报告"""
        print("\n📈 生成覆盖率报告...")
        
        # HTML报告
        html_result = self.run_command([
            self.python_cmd, "-m", "coverage", "html", 
            "--directory=htmlcov"
        ])
        
        # 终端报告
        term_result = self.run_command([
            self.python_cmd, "-m", "coverage", "report"
        ])
        
        if html_result == 0:
            print("✅ HTML覆盖率报告已生成: htmlcov/index.html")
        
        return max(html_result, term_result)
    
    def lint_code(self) -> int:
        """代码质量检查"""
        print("\n🔍 运行代码质量检查...")
        
        # 检查是否安装了linting工具
        tools = {
            "black": "代码格式化",
            "flake8": "代码风格检查", 
            "mypy": "类型检查"
        }
        
        results = []
        
        for tool, description in tools.items():
            print(f"运行 {tool} ({description})...")
            result = self.run_command([
                self.python_cmd, "-m", tool, "backend/app", "tests/"
            ])
            results.append(result)
            
            if result == 0:
                print(f"✅ {tool} 检查通过")
            else:
                print(f"❌ {tool} 检查失败")
        
        return max(results) if results else 0

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="AutoReportAI 测试运行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s --all                    # 运行所有测试
  %(prog)s --unit --integration     # 运行单元测试和集成测试
  %(prog)s --agent --charts         # 运行Agent和图表测试
  %(prog)s --test tests/api/         # 运行特定目录的测试
  %(prog)s --coverage               # 生成覆盖率报告
  %(prog)s --lint                   # 运行代码质量检查
        """
    )
    
    # 测试类型选项
    parser.add_argument("--all", action="store_true", help="运行所有测试")
    parser.add_argument("--unit", action="store_true", help="运行单元测试")
    parser.add_argument("--integration", action="store_true", help="运行集成测试")
    parser.add_argument("--api", action="store_true", help="运行API测试")
    parser.add_argument("--agent", action="store_true", help="运行React Agent测试")
    parser.add_argument("--charts", action="store_true", help="运行图表测试")
    parser.add_argument("--docker", action="store_true", help="运行Docker测试")
    parser.add_argument("--minio", action="store_true", help="运行Minio测试")
    parser.add_argument("--e2e", action="store_true", help="运行端到端测试")
    parser.add_argument("--performance", action="store_true", help="运行性能测试")
    
    # 其他选项
    parser.add_argument("--test", type=str, help="运行特定测试文件或目录")
    parser.add_argument("--coverage", action="store_true", help="生成覆盖率报告")
    parser.add_argument("--lint", action="store_true", help="运行代码质量检查")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    parser.add_argument("--no-coverage", action="store_true", help="跳过覆盖率收集")
    
    args = parser.parse_args()
    
    if len(sys.argv) == 1:
        parser.print_help()
        return 1
    
    runner = TestRunner()
    
    # 检查依赖
    if not runner.check_dependencies():
        return 1
    
    exit_codes = []
    
    # 代码质量检查
    if args.lint:
        exit_codes.append(runner.lint_code())
    
    # 覆盖率报告
    if args.coverage:
        exit_codes.append(runner.generate_coverage_report())
    
    # 特定测试
    if args.test:
        exit_codes.append(runner.run_specific_test(args.test, args.verbose))
    
    # 测试类型
    if args.all:
        exit_codes.append(runner.run_all_tests(args.verbose, not args.no_coverage))
    else:
        if args.unit:
            exit_codes.append(runner.run_unit_tests(args.verbose))
        if args.integration:
            exit_codes.append(runner.run_integration_tests(args.verbose))
        if args.api:
            exit_codes.append(runner.run_api_tests(args.verbose))
        if args.agent:
            exit_codes.append(runner.run_agent_tests(args.verbose))
        if args.charts:
            exit_codes.append(runner.run_chart_tests(args.verbose))
        if args.docker:
            exit_codes.append(runner.run_docker_tests(args.verbose))
        if args.minio:
            exit_codes.append(runner.run_minio_tests(args.verbose))
        if args.e2e:
            exit_codes.append(runner.run_e2e_tests(args.verbose))
        if args.performance:
            exit_codes.append(runner.run_performance_tests(args.verbose))
    
    # 总结
    if exit_codes:
        max_exit_code = max(exit_codes)
        if max_exit_code == 0:
            print("\n🎉 所有测试执行成功!")
        else:
            print(f"\n❌ 部分测试失败 (退出码: {max_exit_code})")
        return max_exit_code
    
    print("⚠️  没有执行任何测试")
    return 0

if __name__ == "__main__":
    sys.exit(main())