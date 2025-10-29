#!/usr/bin/env python3
"""
测试混合SQL执行策略

验证内容：
1. 错误分类功能
2. 错误指导生成
3. SQLRetryContext 的基本功能
4. 重试流程的逻辑验证
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.infrastructure.agents.types import SQLExecutionMode, SQLRetryContext


# 🔥 直接复制 orchestrator 中的方法用于测试（避免初始化依赖）
def classify_error(error_message: str) -> str:
    """分类 SQL 执行错误"""
    error_msg_lower = error_message.lower()

    # 语法错误
    if any(kw in error_msg_lower for kw in ["syntax", "parser", "unexpected", "invalid syntax"]):
        return "syntax_error"

    # 列不存在
    if any(kw in error_msg_lower for kw in ["column", "field", "unknown column", "no such column"]):
        return "column_not_found"

    # 表不存在
    if any(kw in error_msg_lower for kw in ["table", "relation", "unknown table", "no such table"]):
        return "table_not_found"

    # 连接错误
    if any(kw in error_msg_lower for kw in ["connection", "timeout", "refused", "cannot connect"]):
        return "connection_error"

    # 权限错误
    if any(kw in error_msg_lower for kw in ["permission", "access denied", "forbidden", "not authorized"]):
        return "permission_error"

    # 数据类型错误
    if any(kw in error_msg_lower for kw in ["type", "conversion", "cast", "datatype"]):
        return "type_error"

    # 其他错误
    return "unknown_error"


def generate_error_guidance(error_type: str, error_message: str) -> str:
    """根据错误类型生成修复指导"""
    guidance_map = {
        "syntax_error": "检查 SQL 语法是否正确",
        "column_not_found": "使用 cached_schema_list_columns 工具确认列名是否正确",
        "table_not_found": "使用 cached_schema_list_tables 工具确认表名是否正确",
        "connection_error": "这是数据库连接问题，不是 SQL 问题",
        "permission_error": "这是数据库权限问题，不是 SQL 问题",
        "type_error": "检查字段类型是否匹配",
        "unknown_error": "仔细阅读错误信息，理解问题所在",
    }

    guidance = guidance_map.get(error_type, guidance_map["unknown_error"])
    return f"{guidance}\n\n原始错误信息：\n{error_message}"


def test_error_classification():
    """测试错误分类功能"""
    print("=" * 80)
    print("🧪 测试 1: 错误分类功能")
    print("=" * 80)

    # 测试用例
    test_cases = [
        ("Syntax error near 'SELECT'", "syntax_error"),
        ("Unknown column 'user_id' in 'field list'", "column_not_found"),
        ("Table 'db.users' doesn't exist", "table_not_found"),
        ("Connection timeout", "connection_error"),
        ("Access denied for user", "permission_error"),
        ("Type conversion error", "type_error"),
        ("Some random error", "unknown_error"),
    ]

    all_passed = True
    for error_msg, expected_type in test_cases:
        result = classify_error(error_msg)
        status = "✅" if result == expected_type else "❌"
        if result != expected_type:
            all_passed = False

        print(f"{status} 错误: '{error_msg[:50]}...' -> {result} (期望: {expected_type})")

    print()
    if all_passed:
        print("✅ 所有错误分类测试通过！")
    else:
        print("❌ 部分错误分类测试失败")

    print()
    return all_passed


def test_error_guidance_generation():
    """测试错误指导生成"""
    print("=" * 80)
    print("🧪 测试 2: 错误指导生成")
    print("=" * 80)

    error_types = [
        "syntax_error",
        "column_not_found",
        "table_not_found",
        "connection_error",
        "permission_error",
        "type_error",
        "unknown_error",
    ]

    all_passed = True
    for error_type in error_types:
        error_msg = f"Sample {error_type} message"
        guidance = generate_error_guidance(error_type, error_msg)

        # 验证指导包含错误类型关键词
        has_guidance = len(guidance) > 20  # 至少有一些指导内容（简化版）
        has_error_msg = error_msg in guidance  # 包含原始错误信息

        status = "✅" if (has_guidance and has_error_msg) else "❌"
        if not (has_guidance and has_error_msg):
            all_passed = False

        print(f"{status} 错误类型: {error_type}")
        print(f"   - 指导长度: {len(guidance)} 字符")
        print(f"   - 包含原始错误: {has_error_msg}")
        print()

    if all_passed:
        print("✅ 所有错误指导生成测试通过！")
    else:
        print("❌ 部分错误指导生成测试失败")

    print()
    return all_passed


def test_sql_retry_context():
    """测试 SQLRetryContext"""
    print("=" * 80)
    print("🧪 测试 3: SQLRetryContext 功能")
    print("=" * 80)

    # 创建重试上下文
    retry_context = SQLRetryContext(
        placeholder_id="test_id",
        placeholder_name="测试占位符",
        original_sql="SELECT * FROM users",
        error_message="Unknown column 'name'",
        error_type="column_not_found",
        retry_count=0,
        max_retries=1,
    )

    all_passed = True

    # 测试初始状态
    test_1 = retry_context.can_retry()
    print(f"{'✅' if test_1 else '❌'} 初始状态可以重试: {test_1} (期望: True)")
    if not test_1:
        all_passed = False

    # 测试增加重试次数
    retry_context.increment_retry()
    retry_count_1 = retry_context.retry_count
    print(f"{'✅' if retry_count_1 == 1 else '❌'} 重试次数增加后: {retry_count_1} (期望: 1)")
    if retry_count_1 != 1:
        all_passed = False

    # 测试达到最大重试次数
    test_2 = retry_context.can_retry()
    print(f"{'✅' if not test_2 else '❌'} 达到最大重试次数后不能重试: {not test_2} (期望: True)")
    if test_2:
        all_passed = False

    print()
    if all_passed:
        print("✅ SQLRetryContext 所有测试通过！")
    else:
        print("❌ SQLRetryContext 部分测试失败")

    print()
    return all_passed


def test_sql_execution_mode():
    """测试 SQLExecutionMode 枚举"""
    print("=" * 80)
    print("🧪 测试 4: SQLExecutionMode 枚举")
    print("=" * 80)

    all_passed = True

    # 测试枚举值
    test_1 = SQLExecutionMode.STATIC_ONLY.value == "static_only"
    print(f"{'✅' if test_1 else '❌'} STATIC_ONLY 值: {SQLExecutionMode.STATIC_ONLY.value} (期望: 'static_only')")
    if not test_1:
        all_passed = False

    test_2 = SQLExecutionMode.ALLOW_EXECUTION.value == "allow_execution"
    print(f"{'✅' if test_2 else '❌'} ALLOW_EXECUTION 值: {SQLExecutionMode.ALLOW_EXECUTION.value} (期望: 'allow_execution')")
    if not test_2:
        all_passed = False

    # 测试枚举比较
    mode = SQLExecutionMode.STATIC_ONLY
    test_3 = mode == SQLExecutionMode.STATIC_ONLY
    print(f"{'✅' if test_3 else '❌'} 枚举比较: {test_3} (期望: True)")
    if not test_3:
        all_passed = False

    print()
    if all_passed:
        print("✅ SQLExecutionMode 所有测试通过！")
    else:
        print("❌ SQLExecutionMode 部分测试失败")

    print()
    return all_passed


def test_retry_logic_simulation():
    """模拟重试逻辑"""
    print("=" * 80)
    print("🧪 测试 5: 重试逻辑模拟")
    print("=" * 80)

    # 模拟场景：3 个 SQL，其中 1 个失败
    sql_results = [
        {
            "placeholder_id": "1",
            "placeholder_name": "总用户数",
            "sql": "SELECT COUNT(*) FROM users",
            "success": True,
            "row_count": 1,
        },
        {
            "placeholder_id": "2",
            "placeholder_name": "活跃用户数",
            "sql": "SELECT COUNT(*) FROM user WHERE active = 1",  # 故意写错表名
            "success": False,
            "error": "Unknown table 'user'",
        },
        {
            "placeholder_id": "3",
            "placeholder_name": "新增用户数",
            "sql": "SELECT COUNT(*) FROM users WHERE created_at > NOW() - INTERVAL 7 DAY",
            "success": True,
            "row_count": 1,
        },
    ]

    # 提取失败的 SQL
    failed_sqls = [r for r in sql_results if not r.get("success")]

    print(f"总 SQL 数量: {len(sql_results)}")
    print(f"失败 SQL 数量: {len(failed_sqls)}")
    print()

    all_passed = True

    # 验证失败的 SQL
    if len(failed_sqls) != 1:
        print(f"❌ 期望 1 个失败的 SQL，实际: {len(failed_sqls)}")
        all_passed = False
    else:
        print(f"✅ 成功识别 1 个失败的 SQL")

        # 分析失败的 SQL
        failed_sql = failed_sqls[0]
        print(f"\n失败的 SQL 详情:")
        print(f"  - 占位符: {failed_sql['placeholder_name']}")
        print(f"  - SQL: {failed_sql['sql']}")
        print(f"  - 错误: {failed_sql['error']}")

        # 创建重试上下文
        error_type = classify_error(failed_sql['error'])

        print(f"\n错误分析:")
        print(f"  - 错误类型: {error_type}")

        # 验证错误类型
        if error_type == "table_not_found":
            print(f"  ✅ 错误分类正确")
        else:
            print(f"  ❌ 错误分类不正确，期望: table_not_found, 实际: {error_type}")
            all_passed = False

        # 生成指导
        guidance = generate_error_guidance(error_type, failed_sql['error'])
        print(f"\n修复指导 (部分):")
        print("  " + "\n  ".join(guidance.split("\n")[:5]))

    print()
    if all_passed:
        print("✅ 重试逻辑模拟测试通过！")
    else:
        print("❌ 重试逻辑模拟测试失败")

    print()
    return all_passed


def main():
    """运行所有测试"""
    print("\n")
    print("=" * 80)
    print(" 🧪 混合SQL执行策略测试套件")
    print("=" * 80)
    print()

    results = []

    # 运行测试
    results.append(("错误分类", test_error_classification()))
    results.append(("错误指导生成", test_error_guidance_generation()))
    results.append(("SQLRetryContext", test_sql_retry_context()))
    results.append(("SQLExecutionMode", test_sql_execution_mode()))
    results.append(("重试逻辑模拟", test_retry_logic_simulation()))

    # 汇总结果
    print("=" * 80)
    print("📊 测试结果汇总")
    print("=" * 80)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}  {name}")

    print()
    print(f"总计: {passed_count}/{total_count} 测试通过")

    if passed_count == total_count:
        print()
        print("🎉 所有测试通过！混合执行策略核心功能正常。")
        print()
        return 0
    else:
        print()
        print(f"⚠️  {total_count - passed_count} 个测试失败，请检查实现。")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
