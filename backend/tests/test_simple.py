"""
简单测试验证测试框架是否正常工作
"""
import pytest
import json


def test_basic_math():
    """基础数学测试"""
    assert 1 + 1 == 2
    assert 5 * 3 == 15


def test_string_operations():
    """字符串操作测试"""
    test_str = "Hello, World!"
    assert len(test_str) == 13
    assert "Hello" in test_str
    assert test_str.upper() == "HELLO, WORLD!"


def test_list_operations():
    """列表操作测试"""
    test_list = [1, 2, 3, 4, 5]
    assert len(test_list) == 5
    assert sum(test_list) == 15
    assert max(test_list) == 5


def test_json_operations():
    """JSON操作测试"""
    test_dict = {"name": "测试", "value": 123}
    json_str = json.dumps(test_dict, ensure_ascii=False)
    parsed_dict = json.loads(json_str)
    
    assert parsed_dict["name"] == "测试"
    assert parsed_dict["value"] == 123


@pytest.mark.parametrize("input,expected", [
    (2, 4),
    (3, 9),
    (4, 16),
    (5, 25)
])
def test_square_numbers(input, expected):
    """参数化测试：平方数"""
    assert input ** 2 == expected


class TestCalculator:
    """计算器测试类"""
    
    def test_addition(self):
        assert self._add(2, 3) == 5
        assert self._add(-1, 1) == 0
    
    def test_subtraction(self):
        assert self._subtract(5, 3) == 2
        assert self._subtract(1, 1) == 0
    
    def test_multiplication(self):
        assert self._multiply(3, 4) == 12
        assert self._multiply(0, 5) == 0
    
    def test_division(self):
        assert self._divide(10, 2) == 5
        assert self._divide(7, 2) == 3.5
    
    def test_division_by_zero(self):
        with pytest.raises(ZeroDivisionError):
            self._divide(5, 0)
    
    # Helper methods
    def _add(self, a, b):
        return a + b
    
    def _subtract(self, a, b):
        return a - b
    
    def _multiply(self, a, b):
        return a * b
    
    def _divide(self, a, b):
        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        return a / b


@pytest.fixture
def sample_data():
    """提供测试数据"""
    return {
        "users": ["alice", "bob", "charlie"],
        "scores": [95, 87, 92],
        "settings": {"debug": True, "timeout": 30}
    }


def test_fixture_usage(sample_data):
    """测试fixture使用"""
    assert len(sample_data["users"]) == 3
    assert sample_data["users"][0] == "alice"
    assert sum(sample_data["scores"]) == 274
    assert sample_data["settings"]["debug"] is True


@pytest.mark.asyncio
async def test_async_operation():
    """异步测试"""
    import asyncio
    
    async def async_add(a, b):
        await asyncio.sleep(0.01)  # 模拟异步操作
        return a + b
    
    result = await async_add(3, 4)
    assert result == 7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])