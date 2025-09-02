#!/usr/bin/env python3
"""
AutoReportAI 系统验证脚本
验证依赖结构简化和CI兼容性
"""
import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd: str, description: str) -> bool:
    """运行命令并返回成功状态"""
    print(f"🔍 {description}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - 成功")
            return True
        else:
            print(f"❌ {description} - 失败")
            print(f"   错误: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} - 异常: {e}")
        return False

def check_files() -> bool:
    """检查关键文件存在性"""
    print("\n📋 检查关键文件...")
    
    required_files = [
        "backend/requirements.txt",
        "run_tests.py", 
        "Makefile",
        ".github/workflows/test.yml",
        "frontend/package.json"
    ]
    
    all_exist = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - 不存在")
            all_exist = False
    
    return all_exist

def check_single_requirements() -> bool:
    """验证只有一个requirements文件"""
    print("\n🎯 验证单一依赖文件结构...")
    
    # 查找项目根目录下的requirements文件
    req_files = list(Path(".").glob("**/requirements*.txt"))
    # 过滤掉虚拟环境和第三方包中的文件
    req_files = [f for f in req_files if "venv" not in str(f) and "site-packages" not in str(f)]
    
    if len(req_files) == 1 and str(req_files[0]) == "backend/requirements.txt":
        print("✅ 只存在一个requirements.txt文件")
        return True
    else:
        print(f"❌ 发现多个requirements文件: {req_files}")
        return False

def test_makefile_commands() -> bool:
    """测试Makefile命令"""
    print("\n🔨 测试Makefile命令...")
    
    commands = [
        ("make help", "显示帮助信息"),
        ("make install-test", "安装测试依赖"),
    ]
    
    all_passed = True
    for cmd, desc in commands:
        if not run_command(cmd, desc):
            all_passed = False
    
    return all_passed

def test_ci_compatibility() -> bool:
    """测试CI环境兼容性"""
    print("\n🚀 测试CI环境兼容性...")
    
    # 设置CI环境变量
    env = os.environ.copy()
    env['CI'] = 'true'
    env['GITHUB_ACTIONS'] = 'true'
    
    try:
        # 检测并使用正确的Python命令
        venv_python = Path("backend/venv/bin/python")
        if venv_python.exists():
            python_cmd = str(venv_python)
        elif env.get('CI') == 'true':
            python_cmd = "python"  # CI环境使用python
        else:
            python_cmd = "python3"  # 本地环境fallback
        
        # 测试运行器在CI环境下的行为
        result = subprocess.run(
            [python_cmd, "run_tests.py", "--help"],
            env=env,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and "测试运行器" in result.stdout:
            print("✅ CI环境兼容性测试通过")
            return True
        else:
            print("❌ CI环境兼容性测试失败")
            return False
            
    except Exception as e:
        print(f"❌ CI兼容性测试异常: {e}")
        return False

def main():
    """主验证流程"""
    print("🎉 AutoReportAI 系统验证开始")
    print("=" * 50)
    
    checks = [
        ("文件存在性", check_files),
        ("单一依赖结构", check_single_requirements), 
        ("Makefile命令", test_makefile_commands),
        ("CI兼容性", test_ci_compatibility),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name}检查异常: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 50)
    print("📊 验证结果汇总:")
    
    all_passed = True
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {name:<15} {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 所有验证通过！系统已准备就绪。")
        print("   ✅ 依赖结构已简化")
        print("   ✅ GitHub Actions兼容")
        print("   ✅ 本地开发环境正常")
        print("   ✅ 复杂结构已清理")
        return 0
    else:
        print("❌ 部分验证失败，请检查上述问题。")
        return 1

if __name__ == "__main__":
    sys.exit(main())