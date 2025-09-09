#!/usr/bin/env python3
"""
分析Python项目中的第三方依赖使用情况
"""
import ast
import os
import sys
from collections import defaultdict, Counter
from pathlib import Path
from typing import Set, List, Dict, Any

# Python标准库模块列表 (部分主要的)
STDLIB_MODULES = {
    'abc', 'argparse', 'array', 'ast', 'asyncio', 'atexit', 'base64', 'bisect', 'builtins',
    'calendar', 'collections', 'concurrent', 'contextlib', 'copy', 'datetime', 'decimal',
    'difflib', 'enum', 'functools', 'gc', 'glob', 'hashlib', 'heapq', 'hmac', 'html',
    'http', 'importlib', 'inspect', 'io', 'itertools', 'json', 'logging', 'math', 'multiprocessing',
    'operator', 'os', 'pathlib', 're', 'secrets', 'shutil', 'socket', 'sqlite3', 'statistics',
    'string', 'struct', 'subprocess', 'sys', 'tempfile', 'threading', 'time', 'traceback',
    'types', 'typing', 'uuid', 'warnings', 'weakref', 'xml', 'urllib', 'zipfile'
}

class ImportAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.imports = []
        self.from_imports = []

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)

    def visit_ImportFrom(self, node):
        if node.module:
            for alias in node.names:
                if alias.name != '*':
                    full_name = f"{node.module}.{alias.name}"
                    self.from_imports.append((node.module, alias.name, full_name))

def analyze_file(file_path: Path) -> Dict[str, Any]:
    """分析单个Python文件的导入"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content, filename=str(file_path))
        analyzer = ImportAnalyzer()
        analyzer.visit(tree)
        
        return {
            'imports': analyzer.imports,
            'from_imports': analyzer.from_imports,
            'file_path': str(file_path)
        }
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return {'imports': [], 'from_imports': [], 'file_path': str(file_path)}

def classify_import(import_name: str, project_root: str = "app") -> str:
    """分类导入: stdlib, third_party, local"""
    
    # 获取顶级模块名
    top_level = import_name.split('.')[0]
    
    # 检查是否为本地模块
    if import_name.startswith(project_root) or import_name.startswith('.'):
        return 'local'
    
    # 检查是否为标准库
    if top_level in STDLIB_MODULES:
        return 'stdlib'
    
    # 其他认为是第三方库
    return 'third_party'

def main():
    backend_dir = Path('.')
    
    # 找到所有Python文件
    python_files = []
    for root, dirs, files in os.walk(backend_dir):
        # 跳过一些目录
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
    
    print(f"Found {len(python_files)} Python files")
    
    # 分析所有文件
    all_imports = []
    all_from_imports = []
    
    for file_path in python_files:
        result = analyze_file(file_path)
        all_imports.extend(result['imports'])
        all_from_imports.extend(result['from_imports'])
    
    # 分类导入
    third_party_imports = set()
    third_party_modules = set()
    
    # 处理 import xxx
    for imp in all_imports:
        classification = classify_import(imp)
        if classification == 'third_party':
            third_party_imports.add(imp)
            third_party_modules.add(imp.split('.')[0])
    
    # 处理 from xxx import yyy
    for module, name, full_name in all_from_imports:
        classification = classify_import(module)
        if classification == 'third_party':
            third_party_imports.add(module)
            third_party_modules.add(module.split('.')[0])
    
    print("\n=== 第三方依赖包 (根据导入分析) ===")
    for module in sorted(third_party_modules):
        print(f"- {module}")
    
    print(f"\n总共发现 {len(third_party_modules)} 个第三方依赖包")

if __name__ == "__main__":
    main()