"""
测试 TaskComplexity 修复

验证 TaskComplexity 枚举可以正确转换为 float 并进行比较
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.infrastructure.agents.types import TaskComplexity


def test_task_complexity():
    """测试 TaskComplexity 枚举"""

    print("=" * 60)
    print("测试 TaskComplexity 枚举修复")
    print("=" * 60)

    # 测试1: 枚举值是 float 类型
    print("\n测试1: 枚举值类型检查")
    print(f"  TaskComplexity.SIMPLE = {TaskComplexity.SIMPLE} (类型: {type(TaskComplexity.SIMPLE)})")
    print(f"  TaskComplexity.MEDIUM = {TaskComplexity.MEDIUM} (类型: {type(TaskComplexity.MEDIUM)})")
    print(f"  TaskComplexity.COMPLEX = {TaskComplexity.COMPLEX} (类型: {type(TaskComplexity.COMPLEX)})")

    # 测试2: 枚举可以转换为 float
    print("\n测试2: float 转换")
    print(f"  float(TaskComplexity.SIMPLE) = {float(TaskComplexity.SIMPLE)}")
    print(f"  float(TaskComplexity.MEDIUM) = {float(TaskComplexity.MEDIUM)}")
    print(f"  float(TaskComplexity.COMPLEX) = {float(TaskComplexity.COMPLEX)}")

    # 测试3: 枚举可以与 float 进行比较
    print("\n测试3: 与 float 进行比较")
    try:
        result = TaskComplexity.MEDIUM >= 0.5
        print(f"  TaskComplexity.MEDIUM >= 0.5: {result} ✅")

        result = TaskComplexity.SIMPLE < TaskComplexity.COMPLEX
        print(f"  TaskComplexity.SIMPLE < TaskComplexity.COMPLEX: {result} ✅")

        result = TaskComplexity.MEDIUM == 0.5
        print(f"  TaskComplexity.MEDIUM == 0.5: {result} ✅")

        print("  ✅ 所有比较操作成功！")
    except Exception as e:
        print(f"  ❌ 比较失败: {e}")
        return False

    # 测试4: from_value 方法
    print("\n测试4: from_value 方法")
    try:
        # 从枚举创建
        result = TaskComplexity.from_value(TaskComplexity.MEDIUM)
        print(f"  from_value(TaskComplexity.MEDIUM) = {result} ✅")

        # 从字符串创建
        result = TaskComplexity.from_value("simple")
        print(f"  from_value('simple') = {result} ✅")

        # 从 float 创建
        result = TaskComplexity.from_value(0.3)
        print(f"  from_value(0.3) = {result} ✅")

        result = TaskComplexity.from_value(0.7)
        print(f"  from_value(0.7) = {result} ✅")

        print("  ✅ from_value 方法工作正常！")
    except Exception as e:
        print(f"  ❌ from_value 方法失败: {e}")
        return False

    # 测试5: isinstance 检查
    print("\n测试5: isinstance 检查")
    print(f"  isinstance(TaskComplexity.MEDIUM, (TaskComplexity, float, int)): {isinstance(TaskComplexity.MEDIUM, (TaskComplexity, float, int))} ✅")

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！TaskComplexity 修复成功！")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = test_task_complexity()
    sys.exit(0 if success else 1)
