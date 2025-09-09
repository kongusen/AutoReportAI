#!/usr/bin/env python3
"""
详细分析Python项目中第三方依赖的实际使用情况
"""
import ast
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Set, List, Dict, Any

# 已知的第三方库映射（包名到import名的映射）
KNOWN_THIRD_PARTY_PACKAGES = {
    # Web框架
    'fastapi': ['fastapi'],
    'fastapi-limiter': ['fastapi_limiter'],
    'uvicorn': ['uvicorn'],
    'starlette': ['starlette'],
    'pydantic': ['pydantic'],
    'pydantic-settings': ['pydantic_settings'],
    
    # 数据库
    'SQLAlchemy': ['sqlalchemy'],
    'alembic': ['alembic'],
    'psycopg2-binary': ['psycopg2'],
    'PyMySQL': ['pymysql', 'PyMySQL'],
    
    # Redis和缓存
    'redis': ['redis'],
    'cachetools': ['cachetools'],
    
    # 认证安全
    'PyJWT': ['jwt'],
    'python-jose': ['jose'],
    'passlib': ['passlib'],
    'cryptography': ['cryptography'],
    'bcrypt': ['bcrypt'],
    
    # 文件处理
    'python-multipart': ['multipart'],
    'python-docx': ['docx'],
    'openpyxl': ['openpyxl'],
    
    # 任务队列
    'celery': ['celery'],
    'apscheduler': ['apscheduler'],
    'cron-validator': ['cron_validator'],
    
    # 数据处理
    'pandas': ['pandas'],
    'numpy': ['numpy', 'np'],
    
    # AI和LLM
    'llama-index': ['llama_index'],
    'llama-index-llms-anthropic': ['llama_index'],
    'llama-index-llms-openai': ['llama_index'],
    'openai': ['openai'],
    'anthropic': ['anthropic'],
    
    # HTTP客户端
    'aiohttp': ['aiohttp'],
    'requests': ['requests'],
    'httpx': ['httpx'],
    
    # 日志监控
    'structlog': ['structlog'],
    'psutil': ['psutil'],
    
    # 可视化
    'matplotlib': ['matplotlib'],
    'seaborn': ['seaborn'],
    'plotly': ['plotly'],
    'kaleido': ['kaleido'],
    
    # 工具库
    'python-dotenv': ['dotenv'],
    'tenacity': ['tenacity'],
    'email-validator': ['email_validator'],
    'unidecode': ['unidecode'],
    
    # 存储
    'minio': ['minio'],
    
    # 其他常见库
    'Pillow': ['PIL', 'Image'],
    'pytz': ['pytz'],
    'dateutil': ['dateutil'],
    'aiofiles': ['aiofiles'],
    'croniter': ['croniter'],
}

# Python标准库模块
STDLIB_MODULES = {
    'abc', 'argparse', 'array', 'ast', 'asyncio', 'atexit', 'base64', 'bisect', 'builtins',
    'calendar', 'collections', 'concurrent', 'contextlib', 'contextvars', 'copy', 'csv',
    'datetime', 'decimal', 'difflib', 'email', 'enum', 'functools', 'gc', 'glob', 'gzip',
    'hashlib', 'heapq', 'hmac', 'html', 'http', 'importlib', 'inspect', 'io', 'itertools',
    'json', 'logging', 'math', 'multiprocessing', 'operator', 'os', 'pathlib', 'pickle',
    'platform', 'queue', 're', 'secrets', 'shutil', 'smtplib', 'socket', 'sqlite3',
    'statistics', 'string', 'struct', 'subprocess', 'sys', 'tempfile', 'threading',
    'time', 'traceback', 'types', 'typing', 'urllib', 'uuid', 'warnings', 'weakref',
    'xml', 'zipfile'
}

class DetailedImportAnalyzer(ast.NodeVisitor):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.imports = []
        self.from_imports = []
        self.string_references = []

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append({
                'type': 'import',
                'module': alias.name,
                'alias': alias.asname,
                'line': node.lineno
            })

    def visit_ImportFrom(self, node):
        if node.module:
            for alias in node.names:
                if alias.name != '*':
                    self.from_imports.append({
                        'type': 'from_import',
                        'module': node.module,
                        'name': alias.name,
                        'alias': alias.asname,
                        'line': node.lineno
                    })

    def visit_Str(self, node):
        # 检查字符串中可能的包名引用
        if isinstance(node.s, str) and any(pkg in node.s.lower() for pkg in ['openai', 'anthropic', 'llama']):
            self.string_references.append({
                'string': node.s,
                'line': node.lineno
            })

def analyze_file(file_path: Path) -> Dict[str, Any]:
    """分析单个Python文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content, filename=str(file_path))
        analyzer = DetailedImportAnalyzer(str(file_path))
        analyzer.visit(tree)
        
        return {
            'imports': analyzer.imports,
            'from_imports': analyzer.from_imports,
            'string_references': analyzer.string_references,
            'file_path': str(file_path)
        }
    except Exception as e:
        return {
            'imports': [], 'from_imports': [], 'string_references': [],
            'file_path': str(file_path), 'error': str(e)
        }

def get_package_name_from_import(import_name: str) -> str:
    """从import名获取包名"""
    return import_name.split('.')[0]

def classify_import(import_name: str) -> str:
    """分类导入"""
    top_level = get_package_name_from_import(import_name)
    
    # 本地模块
    if import_name.startswith('app') or import_name.startswith('.'):
        return 'local'
    
    # 标准库
    if top_level in STDLIB_MODULES:
        return 'stdlib'
    
    # 第三方库
    return 'third_party'

def find_package_for_import(import_name: str) -> str:
    """找到import对应的包名"""
    top_level = get_package_name_from_import(import_name)
    
    # 直接匹配
    for pkg, imports in KNOWN_THIRD_PARTY_PACKAGES.items():
        if top_level in imports or import_name in imports:
            return pkg
    
    # 返回顶级模块名作为包名
    return top_level

def main():
    backend_dir = Path('.')
    
    # 获取所有Python文件
    python_files = []
    for root, dirs, files in os.walk(backend_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
    
    print(f"分析 {len(python_files)} 个Python文件...")
    
    # 分析所有导入
    third_party_usage = defaultdict(list)
    all_third_party_modules = set()
    files_with_errors = []
    
    for file_path in python_files:
        result = analyze_file(file_path)
        
        if 'error' in result:
            files_with_errors.append((str(file_path), result['error']))
            continue
        
        # 处理import语句
        for imp in result['imports']:
            if classify_import(imp['module']) == 'third_party':
                pkg_name = find_package_for_import(imp['module'])
                third_party_usage[pkg_name].append({
                    'file': str(file_path),
                    'line': imp['line'],
                    'type': 'import',
                    'module': imp['module']
                })
                all_third_party_modules.add(get_package_name_from_import(imp['module']))
        
        # 处理from import语句
        for imp in result['from_imports']:
            if classify_import(imp['module']) == 'third_party':
                pkg_name = find_package_for_import(imp['module'])
                third_party_usage[pkg_name].append({
                    'file': str(file_path),
                    'line': imp['line'],
                    'type': 'from_import',
                    'module': imp['module'],
                    'name': imp['name']
                })
                all_third_party_modules.add(get_package_name_from_import(imp['module']))
    
    # 读取requirements.txt
    req_packages = set()
    try:
        with open('requirements.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # 提取包名（去掉版本号等）
                    pkg_name = re.split(r'[>=<!=]', line)[0].strip()
                    req_packages.add(pkg_name)
    except FileNotFoundError:
        print("未找到requirements.txt文件")
    
    print(f"\n{'='*80}")
    print("第三方依赖分析报告")
    print(f"{'='*80}")
    
    print(f"\n1. 实际使用的第三方依赖包 ({len(third_party_usage)} 个):")
    print("-" * 50)
    for pkg, usages in sorted(third_party_usage.items()):
        print(f"✓ {pkg} (使用 {len(usages)} 次)")
        # 显示前3个使用位置
        for usage in usages[:3]:
            if usage['type'] == 'import':
                print(f"  → {usage['file']}:{usage['line']} - import {usage['module']}")
            else:
                print(f"  → {usage['file']}:{usage['line']} - from {usage['module']} import {usage['name']}")
        if len(usages) > 3:
            print(f"  ... 还有 {len(usages) - 3} 处使用")
    
    print(f"\n2. requirements.txt中的包 ({len(req_packages)} 个):")
    print("-" * 50)
    used_in_requirements = set()
    unused_in_requirements = set()
    
    for req_pkg in sorted(req_packages):
        if req_pkg in third_party_usage or any(req_pkg.lower() == pkg.lower() for pkg in third_party_usage.keys()):
            used_in_requirements.add(req_pkg)
            print(f"✓ {req_pkg} (已使用)")
        else:
            unused_in_requirements.add(req_pkg)
            print(f"✗ {req_pkg} (未使用)")
    
    print(f"\n3. 可能缺失的依赖 (代码中使用但requirements.txt中没有):")
    print("-" * 50)
    missing_deps = set()
    for pkg in third_party_usage.keys():
        if not any(pkg.lower() == req_pkg.lower() for req_pkg in req_packages):
            missing_deps.add(pkg)
            print(f"! {pkg} (代码中使用但requirements.txt中缺失)")
    
    if not missing_deps:
        print("✓ 未发现缺失的依赖")
    
    print(f"\n4. 统计摘要:")
    print("-" * 50)
    print(f"• 实际使用的第三方包: {len(third_party_usage)}")
    print(f"• requirements.txt中的包: {len(req_packages)}")
    print(f"• 已使用的requirements包: {len(used_in_requirements)}")
    print(f"• 未使用的requirements包: {len(unused_in_requirements)}")
    print(f"• 可能缺失的依赖: {len(missing_deps)}")
    
    if files_with_errors:
        print(f"\n5. 分析错误的文件 ({len(files_with_errors)} 个):")
        print("-" * 50)
        for file_path, error in files_with_errors:
            print(f"✗ {file_path}: {error}")

if __name__ == "__main__":
    main()