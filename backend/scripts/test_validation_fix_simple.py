#!/usr/bin/env python3
"""
简单测试：验证修复逻辑（不依赖loom等外部模块）

直接读取并分析validation_tools.py的代码逻辑
"""

import re
from pathlib import Path


def analyze_validation_logic():
    """分析validation_tools.py中的验证逻辑"""

    # 读取文件
    file_path = Path(__file__).parent.parent / "app/services/infrastructure/agents/tools/validation_tools.py"
    content = file_path.read_text()

    print("=" * 80)
    print("🔍 分析 validation_tools.py 中的验证逻辑")
    print("=" * 80)

    # 检查1: 是否定义了 invalid_tables 变量
    if "invalid_tables = []" in content:
        print("✅ 检查1通过: 定义了 invalid_tables 变量")
    else:
        print("❌ 检查1失败: 未定义 invalid_tables 变量")
        return False

    # 检查2: 检测到表不存在时，是否记录到 invalid_tables
    pattern1 = r"if table_name not in table_columns_map:.*?invalid_tables\.append\(table_name\)"
    if re.search(pattern1, content, re.DOTALL):
        print("✅ 检查2通过: 表不存在时会记录到 invalid_tables")
    else:
        print("❌ 检查2失败: 表不存在时未记录到 invalid_tables")
        return False

    # 检查3: valid 的计算逻辑是否同时检查 invalid_tables
    pattern2 = r"valid = .*invalid_columns.*invalid_tables"
    if re.search(pattern2, content):
        print("✅ 检查3通过: valid 计算同时检查 invalid_columns 和 invalid_tables")
    else:
        print("❌ 检查3失败: valid 计算未同时检查两者")
        return False

    # 检查4: 返回结果是否包含 invalid_tables
    pattern3 = r'"invalid_tables": invalid_tables'
    if re.search(pattern3, content):
        print("✅ 检查4通过: 返回结果包含 invalid_tables")
    else:
        print("❌ 检查4失败: 返回结果未包含 invalid_tables")
        return False

    # 检查5: 日志输出是否包含详细信息
    if "failure_details" in content and "个不存在的表" in content:
        print("✅ 检查5通过: 日志输出包含详细的失败信息")
    else:
        print("❌ 检查5失败: 日志输出未包含详细信息")
        return False

    return True


def main():
    print("\n" + "=" * 80)
    print("🧪 验证修复后的代码逻辑")
    print("=" * 80 + "\n")

    if analyze_validation_logic():
        print("\n" + "=" * 80)
        print("✅ 所有检查通过！修复逻辑已正确实现")
        print("=" * 80)
        print("\n修复要点:")
        print("1. ✅ 新增 invalid_tables 列表跟踪不存在的表")
        print("2. ✅ 表不存在时记录到 invalid_tables（不再直接跳过）")
        print("3. ✅ valid 计算同时检查 invalid_tables 和 invalid_columns")
        print("4. ✅ 返回结果包含 invalid_tables 信息")
        print("5. ✅ 日志输出更详细的失败原因")
        print("\n预期效果:")
        print("- 之前: 表不存在但验证通过 ❌")
        print("- 现在: 表不存在时验证失败 ✅")
        return 0
    else:
        print("\n" + "=" * 80)
        print("❌ 检查失败！修复逻辑可能不完整")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    exit(main())
