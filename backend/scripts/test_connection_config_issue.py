"""
测试 connection_config 参数传递问题
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_dict_constructor():
    """测试 dict() 构造函数的各种情况"""

    print("=" * 80)
    print("测试 dict() 构造函数")
    print("=" * 80)

    # 情况1: 正常的字典
    try:
        cfg = {"host": "localhost", "port": 3306}
        result = dict(cfg)
        print(f"✅ 情况1（正常字典）: {result}")
    except Exception as e:
        print(f"❌ 情况1失败: {e}")

    # 情况2: 列表
    try:
        cfg = ["host", "localhost"]
        result = dict(cfg)
        print(f"✅ 情况2（列表）: {result}")
    except Exception as e:
        print(f"❌ 情况2失败: {e}")

    # 情况3: 键值对列表
    try:
        cfg = [("host", "localhost"), ("port", 3306)]
        result = dict(cfg)
        print(f"✅ 情况3（键值对列表）: {result}")
    except Exception as e:
        print(f"❌ 情况3失败: {e}")

    # 情况4: 单字符串列表（模拟错误情况）
    try:
        cfg = ["a", "b"]
        result = dict(cfg)
        print(f"✅ 情况4（单字符串列表）: {result}")
    except Exception as e:
        print(f"❌ 情况4失败（预期）: {e}")

    # 情况5: None
    try:
        cfg = None
        if cfg:
            result = dict(cfg)
        else:
            result = {}
        print(f"✅ 情况5（None）: {result}")
    except Exception as e:
        print(f"❌ 情况5失败: {e}")


def test_connection_config_parse():
    """测试可能导致错误的 connection_config 格式"""

    print("\n" + "=" * 80)
    print("测试 connection_config 解析")
    print("=" * 80)

    # 模拟可能的错误输入
    error_inputs = [
        ("列表而不是字典", ["host", "port", "database"]),
        ("元组而不是字典", ("host", "port")),
        ("字符串而不是字典", "host=localhost,port=3306"),
    ]

    for name, cfg in error_inputs:
        print(f"\n测试: {name}")
        print(f"输入类型: {type(cfg)}")
        print(f"输入值: {cfg}")

        try:
            result = dict(cfg)
            print(f"✅ 转换成功: {result}")
        except Exception as e:
            print(f"❌ 转换失败: {e}")
            print(f"   错误类型: {type(e).__name__}")


if __name__ == "__main__":
    test_dict_constructor()
    test_connection_config_parse()
