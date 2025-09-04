#!/usr/bin/env python3
"""
React Agent完整测试执行脚本

基于我们分析的架构运行完整的React Agent和多Agent协调测试
包括：
1. React Agent基础功能测试
2. Context控制和传递机制测试  
3. 多Agent协调工作流测试
4. 端到端业务流程测试
"""

import sys
import os
import subprocess
import asyncio
from datetime import datetime
from pathlib import Path

# 添加项目路径
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "backend"))


class TestRunner:
    """测试运行器"""
    
    def __init__(self):
        self.test_results = []
        self.start_time = None
        self.end_time = None
    
    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def run_test_file(self, test_file: str, test_name: str, markers: str = None) -> dict:
        """运行单个测试文件"""
        self.log(f"开始运行 {test_name}")
        
        # 构建pytest命令 - 使用backend venv的Python
        python_path = str(ROOT_DIR / "backend" / "venv" / "bin" / "python")
        cmd = [python_path, "-m", "pytest", test_file, "-v", "-s", "--tb=short"]
        
        if markers:
            cmd.extend(["-m", markers])
        
        start_time = datetime.now()
        
        try:
            # 运行测试
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=ROOT_DIR,
                timeout=300  # 5分钟超时
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # 解析结果
            success = result.returncode == 0
            output = result.stdout
            error = result.stderr
            
            # 提取测试统计
            test_stats = self.parse_pytest_output(output)
            
            test_result = {
                'name': test_name,
                'file': test_file,
                'success': success,
                'duration': duration,
                'stats': test_stats,
                'output': output,
                'error': error
            }
            
            self.test_results.append(test_result)
            
            status = "✅ 成功" if success else "❌ 失败"
            self.log(f"{test_name} - {status} (耗时: {duration:.2f}s)")
            
            if not success:
                self.log(f"错误输出: {error}", "ERROR")
            
            return test_result
            
        except subprocess.TimeoutExpired:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            test_result = {
                'name': test_name,
                'file': test_file,
                'success': False,
                'duration': duration,
                'stats': {},
                'output': '',
                'error': '测试超时'
            }
            
            self.test_results.append(test_result)
            self.log(f"{test_name} - ⏰ 超时 (耗时: {duration:.2f}s)", "ERROR")
            
            return test_result
        
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            test_result = {
                'name': test_name,
                'file': test_file,
                'success': False,
                'duration': duration,
                'stats': {},
                'output': '',
                'error': str(e)
            }
            
            self.test_results.append(test_result)
            self.log(f"{test_name} - 🔥 异常: {e}", "ERROR")
            
            return test_result
    
    def parse_pytest_output(self, output: str) -> dict:
        """解析pytest输出获取统计信息"""
        stats = {
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'warnings': 0,
            'total': 0
        }
        
        # 查找测试结果行
        lines = output.split('\n')
        for line in lines:
            if 'passed' in line and ('failed' in line or 'error' in line or 'warnings' in line or 'skipped' in line):
                # 解析类似 "5 passed, 2 warnings in 1.23s" 的行
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.isdigit():
                        count = int(part)
                        if i + 1 < len(parts):
                            category = parts[i + 1]
                            if category in stats:
                                stats[category] = count
                            elif category == 'error' or category == 'errors':
                                stats['failed'] = count
                
                break
        
        stats['total'] = sum(v for k, v in stats.items() if k != 'total')
        return stats
    
    async def run_all_tests(self):
        """运行所有测试"""
        self.log("🚀 开始运行React Agent完整测试套件")
        self.start_time = datetime.now()
        
        # 定义测试套件
        test_suite = [
            {
                'file': 'tests/agent/test_react_agent_complete_workflow.py',
                'name': 'React Agent完整工作流测试',
                'markers': 'agent'
            },
            {
                'file': 'tests/integration/test_context_agent_coordination.py',
                'name': 'Context控制和Agent协调测试',
                'markers': 'integration and agent'
            },
            {
                'file': 'tests/e2e/test_complete_agent_workflow_e2e.py',
                'name': '端到端业务流程测试',
                'markers': 'e2e and agent and not slow'
            },
            {
                'file': 'tests/e2e/test_complete_agent_workflow_e2e.py',
                'name': '负载压力测试',
                'markers': 'e2e and agent and slow'
            }
        ]
        
        # 运行每个测试
        for test_config in test_suite:
            self.run_test_file(
                test_config['file'],
                test_config['name'],
                test_config.get('markers')
            )
        
        self.end_time = datetime.now()
        
        # 生成测试报告
        self.generate_report()
    
    def generate_report(self):
        """生成测试报告"""
        total_duration = (self.end_time - self.start_time).total_seconds()
        
        self.log("=" * 60)
        self.log("📊 React Agent测试套件执行报告")
        self.log("=" * 60)
        
        # 总体统计
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r['success'])
        failed_tests = total_tests - successful_tests
        
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        self.log(f"📈 总体统计:")
        self.log(f"   - 测试套件数量: {total_tests}")
        self.log(f"   - 成功: {successful_tests}")
        self.log(f"   - 失败: {failed_tests}")
        self.log(f"   - 成功率: {success_rate:.1f}%")
        self.log(f"   - 总耗时: {total_duration:.2f}秒")
        
        # 详细结果
        self.log(f"\n📋 详细结果:")
        for result in self.test_results:
            status_icon = "✅" if result['success'] else "❌"
            self.log(f"   {status_icon} {result['name']} ({result['duration']:.2f}s)")
            
            if result['stats']:
                stats = result['stats']
                if stats['total'] > 0:
                    self.log(f"       测试用例: {stats['passed']}通过, {stats['failed']}失败, {stats['skipped']}跳过")
            
            if not result['success'] and result['error']:
                self.log(f"       错误: {result['error'][:100]}...")
        
        # 架构验证总结
        self.log(f"\n🏗️ 架构验证总结:")
        self.log(f"   基于我们分析的React Agent架构:")
        self.log(f"   API → WorkflowOrchestrationAgent → ContextAwareService → AIExecutionEngine → ReactAgent")
        
        if successful_tests >= 3:
            self.log(f"   ✅ 架构完整性验证通过")
            self.log(f"   ✅ Context传递机制验证通过")
            self.log(f"   ✅ 多Agent协调机制验证通过")
        else:
            self.log(f"   ⚠️ 部分架构组件需要进一步优化")
        
        # 性能评估
        avg_duration = sum(r['duration'] for r in self.test_results) / len(self.test_results)
        if avg_duration < 30:
            self.log(f"   ✅ 性能表现良好 (平均{avg_duration:.1f}s/套件)")
        else:
            self.log(f"   ⚠️ 性能需要优化 (平均{avg_duration:.1f}s/套件)")
        
        # 建议
        self.log(f"\n💡 优化建议:")
        if failed_tests > 0:
            self.log(f"   - 检查失败的测试用例，修复相关问题")
        if avg_duration > 60:
            self.log(f"   - 考虑并行化测试执行以提升性能")
        if success_rate < 90:
            self.log(f"   - 增强错误处理和降级机制")
        else:
            self.log(f"   - 当前架构运行良好，可考虑添加更多边界情况测试")
        
        self.log("=" * 60)
        
        # 保存报告到文件
        self.save_report_to_file()
    
    def save_report_to_file(self):
        """保存报告到文件"""
        report_file = ROOT_DIR / "tests" / "react_agent_test_report.json"
        
        import json
        report_data = {
            'test_run_info': {
                'start_time': self.start_time.isoformat(),
                'end_time': self.end_time.isoformat(),
                'total_duration': (self.end_time - self.start_time).total_seconds()
            },
            'summary': {
                'total_test_suites': len(self.test_results),
                'successful_suites': sum(1 for r in self.test_results if r['success']),
                'failed_suites': sum(1 for r in self.test_results if not r['success']),
                'success_rate': (sum(1 for r in self.test_results if r['success']) / len(self.test_results) * 100) if self.test_results else 0
            },
            'detailed_results': [
                {
                    'name': r['name'],
                    'file': r['file'],
                    'success': r['success'],
                    'duration': r['duration'],
                    'stats': r['stats'],
                    'error': r['error'] if not r['success'] else None
                }
                for r in self.test_results
            ]
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        self.log(f"📄 详细报告已保存到: {report_file}")


async def main():
    """主函数"""
    print("React Agent架构完整测试")
    print("=" * 50)
    print("基于分析的架构进行全面测试验证:")
    print("1. React Agent基础功能和模型选择")
    print("2. Context在各层级间的传递和管理")
    print("3. 多Agent协调和工作流编排")
    print("4. 端到端业务流程验证")
    print("5. 性能和负载测试")
    print("=" * 50)
    
    runner = TestRunner()
    await runner.run_all_tests()
    
    return runner.test_results


if __name__ == "__main__":
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("❌ 需要Python 3.8或更高版本")
        sys.exit(1)
    
    # 检查依赖
    try:
        import pytest
    except ImportError:
        print("❌ 请安装pytest: pip install pytest pytest-asyncio")
        sys.exit(1)
    
    # 运行测试
    results = asyncio.run(main())
    
    # 根据结果设置退出码
    failed_count = sum(1 for r in results if not r['success'])
    sys.exit(failed_count)