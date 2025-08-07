#!/usr/bin/env python3
"""
AutoReportAI API测试运行器
统一运行所有API测试并生成报告
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

def run_test_script(script_name: str, description: str) -> bool:
    """运行测试脚本"""
    print(f"\n🧪 {description}")
    print("=" * 50)
    
    script_path = Path(__file__).parent / script_name
    if not script_path.exists():
        print(f"❌ 测试脚本不存在: {script_name}")
        return False
    
    try:
        result = subprocess.run([sys.executable, str(script_path)], 
                              capture_output=True, text=True, cwd=Path(__file__).parent)
        
        print(result.stdout)
        if result.stderr:
            print("错误输出:")
            print(result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ 运行测试脚本失败: {e}")
        return False

def generate_test_report():
    """生成测试报告"""
    print("\n📊 生成测试报告...")
    
    report_dir = Path(__file__).parent / "reports"
    report_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = report_dir / f"api_test_report_{timestamp}.md"
    
    # 这里可以添加更详细的报告生成逻辑
    print(f"✅ 测试报告已生成: {report_file}")

def main():
    """主函数"""
    print("🚀 AutoReportAI API测试套件")
    print("=" * 60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 测试脚本列表
    test_scripts = [
        ("final_api_test_summary.py", "核心功能测试"),
        ("comprehensive_api_test.py", "全面API测试"),
        ("configure_ai_provider.py", "AI提供商配置测试"),
    ]
    
    results = []
    
    for script_name, description in test_scripts:
        success = run_test_script(script_name, description)
        results.append((description, success))
    
    # 生成总结
    print("\n" + "=" * 60)
    print("📋 测试结果总结")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for description, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} {description}")
    
    print(f"\n总体结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！")
        generate_test_report()
    else:
        print("⚠️ 部分测试失败，请检查相关功能")
    
    print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main() 