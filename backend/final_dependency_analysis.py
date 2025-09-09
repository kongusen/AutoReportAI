#!/usr/bin/env python3
"""
AutoReportAI Backend 依赖分析报告生成器
"""
import ast
import os
import re
from pathlib import Path
from collections import defaultdict

def extract_requirements():
    """提取requirements.txt中的包列表"""
    req_packages = {}
    try:
        with open('requirements.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # 提取包名和版本
                    match = re.match(r'^([a-zA-Z0-9\-_\.]+)', line)
                    if match:
                        pkg_name = match.group(1)
                        req_packages[pkg_name.lower()] = line
    except FileNotFoundError:
        print("未找到requirements.txt文件")
    return req_packages

def analyze_third_party_imports():
    """分析代码中实际使用的第三方包"""
    
    # 已知第三方包到import名的映射
    known_mappings = {
        'fastapi': ['fastapi'],
        'fastapi-limiter': ['fastapi_limiter'],
        'uvicorn': ['uvicorn'],
        'starlette': ['starlette'], 
        'pydantic': ['pydantic'],
        'pydantic-settings': ['pydantic_settings'],
        'SQLAlchemy': ['sqlalchemy'],
        'alembic': ['alembic'],
        'psycopg2-binary': ['psycopg2'],
        'PyMySQL': ['pymysql'],
        'redis': ['redis'],
        'cachetools': ['cachetools'],
        'PyJWT': ['jwt'],
        'python-jose': ['jose'],
        'passlib': ['passlib'],
        'cryptography': ['cryptography'],
        'bcrypt': ['bcrypt'],
        'python-multipart': ['multipart'],
        'python-docx': ['docx'],
        'openpyxl': ['openpyxl'],
        'celery': ['celery'],
        'apscheduler': ['apscheduler'],
        'cron-validator': ['cron_validator'],
        'pandas': ['pandas'],
        'numpy': ['numpy'],
        'llama-index': ['llama_index'],
        'llama-index-llms-anthropic': ['llama_index'],
        'llama-index-llms-openai': ['llama_index'],
        'openai': ['openai'],
        'anthropic': ['anthropic'],
        'aiohttp': ['aiohttp'],
        'requests': ['requests'],
        'httpx': ['httpx'],
        'structlog': ['structlog'],
        'psutil': ['psutil'],
        'matplotlib': ['matplotlib'],
        'seaborn': ['seaborn'],
        'plotly': ['plotly'],
        'kaleido': ['kaleido'],
        'python-dotenv': ['dotenv'],
        'tenacity': ['tenacity'],
        'email-validator': ['email_validator'],
        'unidecode': ['unidecode'],
        'minio': ['minio'],
        'Pillow': ['PIL'],
        'pytz': ['pytz'],
        'aiofiles': ['aiofiles'],
        'croniter': ['croniter'],
    }
    
    # Python标准库
    stdlib_modules = {
        'abc', 'argparse', 'array', 'ast', 'asyncio', 'atexit', 'base64', 'bisect', 
        'builtins', 'calendar', 'collections', 'concurrent', 'contextlib', 'contextvars',
        'copy', 'csv', 'datetime', 'decimal', 'difflib', 'email', 'enum', 'functools',
        'gc', 'glob', 'gzip', 'hashlib', 'heapq', 'hmac', 'html', 'http', 'importlib',
        'inspect', 'io', 'itertools', 'json', 'logging', 'math', 'multiprocessing',
        'operator', 'os', 'pathlib', 'pickle', 'platform', 'queue', 're', 'secrets',
        'shutil', 'smtplib', 'socket', 'sqlite3', 'statistics', 'string', 'struct',
        'subprocess', 'sys', 'tempfile', 'threading', 'time', 'traceback', 'types',
        'typing', 'urllib', 'uuid', 'warnings', 'weakref', 'xml', 'zipfile'
    }
    
    # 收集所有导入
    imports_found = set()
    
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                imports_found.add(alias.name.split('.')[0])
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                imports_found.add(node.module.split('.')[0])
                                
                except Exception:
                    continue
    
    # 分类导入
    used_third_party = {}
    for imp in imports_found:
        # 跳过本地模块
        if imp == 'app' or imp.startswith('.'):
            continue
        # 跳过标准库
        if imp in stdlib_modules:
            continue
            
        # 查找对应的包
        found_pkg = None
        for pkg, import_names in known_mappings.items():
            if imp in import_names:
                found_pkg = pkg
                break
        
        if found_pkg:
            used_third_party[found_pkg] = imp
        else:
            # 未知的第三方包
            used_third_party[imp] = imp
    
    return used_third_party

def main():
    print("="*80)
    print("AutoReportAI Backend 第三方依赖分析报告")
    print("="*80)
    
    # 获取requirements.txt中的包
    req_packages = extract_requirements()
    print(f"\n1. requirements.txt 中声明的依赖包 ({len(req_packages)} 个):")
    print("-"*50)
    for pkg, line in sorted(req_packages.items()):
        print(f"  {line}")
    
    # 分析实际使用的第三方包
    used_packages = analyze_third_party_imports()
    print(f"\n2. 代码中实际使用的第三方依赖 ({len(used_packages)} 个):")
    print("-"*50)
    for pkg, imp in sorted(used_packages.items()):
        print(f"  ✓ {pkg} (import {imp})")
    
    # 对比分析
    req_pkg_names = set(req_packages.keys())
    used_pkg_names = set(pkg.lower() for pkg in used_packages.keys())
    
    # 在requirements中但未使用的
    unused = req_pkg_names - used_pkg_names
    print(f"\n3. 在requirements.txt中但可能未使用的依赖 ({len(unused)} 个):")
    print("-"*50)
    if unused:
        for pkg in sorted(unused):
            print(f"  ⚠️  {pkg}")
    else:
        print("  ✓ 所有依赖都有被使用")
    
    # 使用了但不在requirements中的
    missing = used_pkg_names - req_pkg_names
    # 过滤掉一些已知的映射关系
    real_missing = set()
    for pkg in missing:
        # 检查是否有对应的包在requirements中
        found = False
        for req_pkg in req_pkg_names:
            if pkg.replace('-', '_') == req_pkg.replace('-', '_') or \
               pkg.replace('_', '-') == req_pkg.replace('_', '-'):
                found = True
                break
        if not found:
            real_missing.add(pkg)
    
    print(f"\n4. 代码中使用但requirements.txt中可能缺失的依赖 ({len(real_missing)} 个):")
    print("-"*50)
    if real_missing:
        for pkg in sorted(real_missing):
            print(f"  ❗ {pkg}")
    else:
        print("  ✓ 未发现缺失的依赖")
    
    # 重点关注的AI相关包
    ai_packages = {
        'llama-index': 'llama_index' in [imp for imp in used_packages.values()],
        'openai': 'openai' in [imp for imp in used_packages.values()],
        'anthropic': 'anthropic' in [imp for imp in used_packages.values()],
    }
    
    print(f"\n5. AI相关核心依赖使用情况:")
    print("-"*50)
    for pkg, used in ai_packages.items():
        status = "✓ 已使用" if used else "⚠️ 未使用"
        print(f"  {pkg}: {status}")
    
    # 数据处理相关包
    data_packages = {
        'pandas': 'pandas' in [imp for imp in used_packages.values()],
        'numpy': 'numpy' in [imp for imp in used_packages.values()],
        'matplotlib': 'matplotlib' in [imp for imp in used_packages.values()],
        'plotly': 'plotly' in [imp for imp in used_packages.values()],
    }
    
    print(f"\n6. 数据处理相关依赖使用情况:")
    print("-"*50)
    for pkg, used in data_packages.items():
        status = "✓ 已使用" if used else "⚠️ 未使用"
        print(f"  {pkg}: {status}")
    
    print(f"\n7. 总结:")
    print("-"*50)
    print(f"  • requirements.txt中的包: {len(req_packages)}")
    print(f"  • 实际使用的第三方包: {len(used_packages)}")
    print(f"  • 可能未使用的包: {len(unused)}")
    print(f"  • 可能缺失的包: {len(real_missing)}")
    
    if not unused and not real_missing:
        print("\n  🎉 依赖管理状况良好!")
    elif unused or real_missing:
        print("\n  🔧 建议优化依赖配置")

if __name__ == "__main__":
    main()