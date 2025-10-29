#!/usr/bin/env python3
"""
简单验证脚本：检查 StageAwareContextRetriever 是否有 initialize 和 schema_cache
"""
import ast
import sys


def check_file(filepath):
    """检查文件中是否定义了 initialize 方法和 schema_cache 属性"""
    with open(filepath, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())

    stage_aware_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'StageAwareContextRetriever':
            stage_aware_class = node
            break

    if not stage_aware_class:
        print("❌ 未找到 StageAwareContextRetriever 类")
        return False

    # 检查方法和属性
    has_initialize = False
    has_schema_cache = False

    for item in stage_aware_class.body:
        # 检查 async def initialize
        if isinstance(item, ast.AsyncFunctionDef) and item.name == 'initialize':
            has_initialize = True
            print("✅ 找到 async def initialize() 方法")

        # 检查 @property 装饰器的方法
        if isinstance(item, ast.FunctionDef):
            for decorator in item.decorator_list:
                if isinstance(decorator, ast.Name) and decorator.id == 'property':
                    if item.name == 'schema_cache':
                        has_schema_cache = True
                        print("✅ 找到 @property schema_cache")

    if not has_initialize:
        print("❌ 未找到 initialize() 方法")
    if not has_schema_cache:
        print("❌ 未找到 schema_cache 属性")

    return has_initialize and has_schema_cache


if __name__ == "__main__":
    filepath = "app/services/infrastructure/agents/context_manager.py"
    print(f"🔍 检查文件: {filepath}")
    print("=" * 60)

    success = check_file(filepath)

    print("=" * 60)
    if success:
        print("🎉 验证通过！StageAwareContextRetriever 已正确修复")
        sys.exit(0)
    else:
        print("❌ 验证失败")
        sys.exit(1)
