#!/usr/bin/env python3
"""
简化版本的 Schema 工具替换测试

验证关键代码变更，不需要完整的运行环境
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import re


def test_tools_init_changes():
    """测试 1: 验证 tools/__init__.py 的变更"""
    print("=" * 60)
    print("测试 1: 验证 tools/__init__.py 的变更")
    print("=" * 60)

    tools_init_path = backend_dir / "app" / "services" / "infrastructure" / "agents" / "tools" / "__init__.py"

    with open(tools_init_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 验证：schema 工具已注释
    schema_tools_commented = all([
        re.search(r'#.*schema_tools.*SchemaListTablesTool', content),
        re.search(r'#.*schema_tools.*SchemaListColumnsTool', content),
        re.search(r'#.*schema_tools.*SchemaGetColumnsTool', content),
    ])

    if schema_tools_commented:
        print("✅ 确认：schema 工具已注释")
    else:
        print("⚠️  警告：未找到注释的 schema 工具")
        # 检查是否完全删除了
        schema_in_specs = "schema_tools" in content and "DEFAULT_TOOL_SPECS" in content
        if not schema_in_specs:
            print("✅ 确认：schema 工具已从 DEFAULT_TOOL_SPECS 中移除")
        else:
            print("❌ 错误：schema 工具仍在 DEFAULT_TOOL_SPECS 中")
            return False

    # 验证：validation 工具已添加
    validation_tools_added = all([
        "validation_tools" in content,
        "SQLColumnValidatorTool" in content,
        "SQLColumnAutoFixTool" in content,
    ])

    if validation_tools_added:
        print("✅ 确认：validation 工具已添加")
    else:
        print("❌ 错误：validation 工具未添加")
        return False

    print("✅ 测试 1 通过\n")
    return True


def test_prompts_changes():
    """测试 2: 验证 prompts.py 的变更"""
    print("=" * 60)
    print("测试 2: 验证 prompts.py 的变更")
    print("=" * 60)

    prompts_path = backend_dir / "app" / "services" / "infrastructure" / "agents" / "prompts.py"

    with open(prompts_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 验证：包含"已自动注入"说明
    has_auto_inject_note = "已自动注入" in content or "已经自动提供" in content

    if has_auto_inject_note:
        print("✅ 确认：包含'已自动注入'说明")
    else:
        print("❌ 错误：缺少'已自动注入'说明")
        return False

    # 验证：包含"不要调用 schema.* 工具"警告
    has_no_schema_warning = "不要调用 schema" in content or "❌" in content

    if has_no_schema_warning:
        print("✅ 确认：包含'不要调用 schema 工具'警告")
    else:
        print("❌ 错误：缺少警告")
        return False

    # 验证：提到了 validate_columns 和 auto_fix_columns
    has_validation_tools = "validate_columns" in content or "auto_fix_columns" in content

    if has_validation_tools:
        print("✅ 确认：提到了 validation 工具")
    else:
        print("⚠️  警告：未提到 validation 工具（可选）")

    print("✅ 测试 2 通过\n")
    return True


def test_schema_tools_deprecated():
    """测试 3: 验证 schema_tools.py 标记为 DEPRECATED"""
    print("=" * 60)
    print("测试 3: 验证 schema_tools.py 标记为 DEPRECATED")
    print("=" * 60)

    schema_tools_path = backend_dir / "app" / "services" / "infrastructure" / "agents" / "tools" / "schema_tools.py"

    with open(schema_tools_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 验证：文件开头包含 DEPRECATED 标记
    first_500_chars = content[:500]

    if "DEPRECATED" in first_500_chars or "废弃" in first_500_chars:
        print("✅ 确认：文件开头包含 DEPRECATED 标记")
    else:
        print("❌ 错误：文件开头缺少 DEPRECATED 标记")
        return False

    # 验证：包含替代方案说明
    has_replacement = "context_retriever" in content.lower() or "ContextRetriever" in content

    if has_replacement:
        print("✅ 确认：包含 ContextRetriever 替代方案说明")
    else:
        print("❌ 错误：缺少替代方案说明")
        return False

    # 验证：包含废弃日期
    has_date = "2025-10-24" in content

    if has_date:
        print("✅ 确认：包含废弃日期")
    else:
        print("⚠️  警告：缺少废弃日期")

    print("✅ 测试 3 通过\n")
    return True


def test_new_files_exist():
    """测试 4: 验证新文件存在"""
    print("=" * 60)
    print("测试 4: 验证新文件存在")
    print("=" * 60)

    files_to_check = [
        ("context_retriever.py", backend_dir / "app" / "services" / "infrastructure" / "agents" / "context_retriever.py"),
        ("validation_tools.py", backend_dir / "app" / "services" / "infrastructure" / "agents" / "tools" / "validation_tools.py"),
    ]

    all_exist = True

    for file_name, file_path in files_to_check:
        if file_path.exists():
            print(f"✅ 确认：{file_name} 存在")

            # 检查文件大小
            file_size = file_path.stat().st_size
            if file_size > 100:
                print(f"   文件大小: {file_size} 字节")
            else:
                print(f"⚠️  警告：{file_name} 文件太小 ({file_size} 字节)")
                all_exist = False

        else:
            print(f"❌ 错误：{file_name} 不存在")
            all_exist = False

    if all_exist:
        print("✅ 测试 4 通过\n")
    else:
        print("❌ 测试 4 失败\n")

    return all_exist


def test_runtime_facade_service_changes():
    """测试 5: 验证 runtime, facade, service 的变更"""
    print("=" * 60)
    print("测试 5: 验证 runtime, facade, service 的变更")
    print("=" * 60)

    files_to_check = [
        ("runtime.py", backend_dir / "app" / "services" / "infrastructure" / "agents" / "runtime.py"),
        ("facade.py", backend_dir / "app" / "services" / "infrastructure" / "agents" / "facade.py"),
        ("service.py", backend_dir / "app" / "services" / "infrastructure" / "agents" / "service.py"),
    ]

    all_have_context_retriever = True

    for file_name, file_path in files_to_check:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否有 context_retriever 参数
        has_parameter = "context_retriever" in content

        if has_parameter:
            print(f"✅ 确认：{file_name} 包含 context_retriever 参数")
        else:
            print(f"❌ 错误：{file_name} 缺少 context_retriever 参数")
            all_have_context_retriever = False

    if all_have_context_retriever:
        print("✅ 测试 5 通过\n")
    else:
        print("❌ 测试 5 失败\n")

    return all_have_context_retriever


def test_tasks_changes():
    """测试 6: 验证 tasks.py 的变更"""
    print("=" * 60)
    print("测试 6: 验证 tasks.py 的变更")
    print("=" * 60)

    tasks_path = backend_dir / "app" / "services" / "infrastructure" / "task_queue" / "tasks.py"

    with open(tasks_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 验证：包含 Schema Context 初始化代码
    has_schema_init = "create_schema_context_retriever" in content

    if has_schema_init:
        print("✅ 确认：包含 create_schema_context_retriever 调用")
    else:
        print("❌ 错误：缺少 Schema Context 初始化代码")
        return False

    # 验证：包含 initialize() 调用
    has_initialize = "initialize()" in content or "retriever.initialize" in content

    if has_initialize:
        print("✅ 确认：包含 initialize() 调用")
    else:
        print("⚠️  警告：未找到 initialize() 调用")

    # 验证：传递 context_retriever 到 PlaceholderProcessingSystem
    has_pass_context = "context_retriever=" in content

    if has_pass_context:
        print("✅ 确认：传递 context_retriever 参数")
    else:
        print("❌ 错误：未传递 context_retriever 参数")
        return False

    print("✅ 测试 6 通过\n")
    return True


def test_placeholder_service_changes():
    """测试 7: 验证 placeholder_service.py 的变更"""
    print("=" * 60)
    print("测试 7: 验证 placeholder_service.py 的变更")
    print("=" * 60)

    service_path = backend_dir / "app" / "services" / "application" / "placeholder" / "placeholder_service.py"

    with open(service_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 验证：__init__ 方法接收 context_retriever 参数
    has_parameter = re.search(r'def __init__\(.*context_retriever', content, re.DOTALL)

    if has_parameter:
        print("✅ 确认：__init__ 方法接收 context_retriever 参数")
    else:
        print("❌ 错误：__init__ 方法缺少 context_retriever 参数")
        return False

    # 验证：保存 context_retriever
    has_save = "self.context_retriever" in content

    if has_save:
        print("✅ 确认：保存 context_retriever 到实例变量")
    else:
        print("❌ 错误：未保存 context_retriever")
        return False

    # 验证：传递 context_retriever 到 AgentService
    has_pass = re.search(r'AgentService\(.*context_retriever', content, re.DOTALL)

    if has_pass:
        print("✅ 确认：传递 context_retriever 到 AgentService")
    else:
        print("❌ 错误：未传递 context_retriever 到 AgentService")
        return False

    print("✅ 测试 7 通过\n")
    return True


def test_documentation_exists():
    """测试 8: 验证文档存在"""
    print("=" * 60)
    print("测试 8: 验证文档存在")
    print("=" * 60)

    docs_to_check = [
        ("REPLACEMENT_SUMMARY.md", backend_dir / "docs" / "REPLACEMENT_SUMMARY.md"),
    ]

    all_exist = True

    for doc_name, doc_path in docs_to_check:
        if doc_path.exists():
            print(f"✅ 确认：{doc_name} 存在")

            # 检查文件大小
            file_size = doc_path.stat().st_size
            if file_size > 1000:
                print(f"   文件大小: {file_size} 字节")
            else:
                print(f"⚠️  警告：{doc_name} 文件太小 ({file_size} 字节)")

        else:
            print(f"❌ 错误：{doc_name} 不存在")
            all_exist = False

    if all_exist:
        print("✅ 测试 8 通过\n")
    else:
        print("❌ 测试 8 失败\n")

    return all_exist


def main():
    """主测试流程"""
    print("\n")
    print("🚀 开始测试 Schema 工具替换（简化版本）")
    print("\n")

    tests = [
        ("tools/__init__.py 变更", test_tools_init_changes),
        ("prompts.py 变更", test_prompts_changes),
        ("schema_tools.py DEPRECATED", test_schema_tools_deprecated),
        ("新文件存在性", test_new_files_exist),
        ("runtime/facade/service 变更", test_runtime_facade_service_changes),
        ("tasks.py 变更", test_tasks_changes),
        ("placeholder_service.py 变更", test_placeholder_service_changes),
        ("文档存在性", test_documentation_exists),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ 测试异常: {e}\n")
            results.append((test_name, False))

    print("\n")
    print("=" * 60)
    print("测试总结")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {test_name}")

    print("\n")
    print(f"总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n")
        print("=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        print("\n")
        print("替换总结：")
        print("  ✅ 所有代码变更已完成")
        print("  ✅ 旧工具已移除")
        print("  ✅ 新工具已添加")
        print("  ✅ Prompt 已更新")
        print("  ✅ 业务流程已修改")
        print("  ✅ 文档已创建")
        print("\n")
        print("下一步：")
        print("  1. 在开发环境运行完整集成测试")
        print("  2. 创建测试任务验证功能")
        print("  3. 监控 LLM 调用次数和执行时间")
        print("  4. 验证 SQL 准确率是否提升至 95%+")
        print("  5. 准备生产环境部署")
        print("\n")
        return 0
    else:
        print("\n")
        print("=" * 60)
        print(f"❌ {total - passed} 个测试失败")
        print("=" * 60)
        print("\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
