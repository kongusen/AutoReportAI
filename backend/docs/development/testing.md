# 测试指南

在AutoReportAI项目中，我们高度重视代码质量和稳定性。测试是确保这两点的关键环节。本指南将介绍我们的测试理念、不同类型的测试以及如何编写和运行测试。

项目已完成全面的架构重构，测试结构也相应进行了优化。请参考[架构指南](./architecture-guide.md)了解新的架构设计。

## 测试理念

- **测试是第一公民**: 编写功能代码时，应同时考虑其可测试性。
- **高覆盖率**: 我们追求高测试覆盖率，但更注重测试的质量和有效性。
- **自动化**: 所有测试都应是自动化的，并集成到CI/CD流程中。

## 测试类型

我们主要采用以下几种测试类型：

1.  **单元测试 (Unit Tests)**:
    - **目的**: 测试最小的可测试单元（如单个函数、类或React组件）的功能是否正确。
    - **位置**:
        - 后端: `backend/tests/unit`
        - 前端: 组件目录下的 `__tests__` 文件夹，如 `frontend/src/components/ui/__tests__/button.test.tsx`
    - **特点**: 速度快，不依赖外部服务（如数据库、API），通常使用Mocking。

2.  **集成测试 (Integration Tests)**:
    - **目的**: 测试多个组件或模块协同工作时是否正确。
    - **位置**:
        - 后端: `backend/tests/integration` (例如，测试API端点与其依赖的服务和数据库的交互)
        - 前端: `frontend/src/__tests__/integration` (例如，测试一个包含多个组件的页面的完整流程)
    - **特点**: 速度慢于单元测试，可能需要真实或测试用的数据库/API。

3.  **端到端测试 (E2E Tests)**:
    - **目的**: 模拟真实用户操作，从用户界面到后端服务，测试整个应用的完整流程。
    - **位置**: `backend/tests/e2e` (使用 `pytest` 和 `requests` 或 `playwright`)
    - **特点**: 最慢，最接近真实用户场景，也最脆弱。

4.  **可视化回归测试 (Visual Regression Tests)**:
    - **目的**: 捕捉UI上的意外视觉变化。
    - **位置**: `frontend/src/__tests__/visual`
    - **特点**: 通过比较组件渲染后的截图来检测变更。

## 后端测试 (Python & Pytest)

### 运行测试
- **运行所有测试**:
  ```bash
  # 在 backend 目录下
  make test
  ```
- **运行并生成覆盖率报告**:
  ```bash
  make test-cov
  ```
  报告将生成在 `backend/htmlcov` 目录下。
- **运行特定测试**:
  ```bash
  pytest tests/unit/services/test_user_service.py
  ```

### 编写测试
- **文件命名**: 测试文件必须以 `test_` 开头。
- **函数命名**: 测试函数必须以 `test_` 开头。
- **Fixtures**: 使用 `pytest` 的 [Fixtures](https://docs.pytest.org/en/6.2.x/fixture.html) 来准备测试环境和数据。常见的Fixtures定义在 `tests/conftest.py` 中，如 `db` (数据库会话) 和 `client` (API测试客户端)。
- **Mocking**: 使用 `pytest-mock` (基于 `unittest.mock`) 来模拟外部依赖。

### 新架构下的测试模式

#### 服务层测试
```python
# tests/unit/services/test_intelligent_placeholder.py
import pytest
from unittest.mock import Mock, AsyncMock
from app.services.intelligent_placeholder import IntelligentPlaceholderProcessor
from app.services.ai_integration import LLMService

@pytest.fixture
def mock_llm_service():
    return Mock(spec=LLMService)

@pytest.fixture
def placeholder_processor(mock_llm_service):
    return IntelligentPlaceholderProcessor(llm_service=mock_llm_service)

@pytest.mark.asyncio
async def test_process_placeholder_success(placeholder_processor, mock_llm_service):
    """测试智能占位符处理成功场景"""
    # Arrange
    mock_llm_service.generate.return_value = "Generated content"
    placeholder_data = {"template": "Hello {name}", "context": {"name": "World"}}
    
    # Act
    result = await placeholder_processor.process(placeholder_data)
    
    # Assert
    assert result is not None
    assert "Generated content" in result
    mock_llm_service.generate.assert_called_once()
```

#### API端点测试
```python
# tests/integration/api/test_intelligent_placeholders.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

def test_process_placeholder_endpoint(client: TestClient):
    """测试智能占位符处理API端点"""
    with patch('app.services.intelligent_placeholder.IntelligentPlaceholderProcessor') as mock_processor:
        # Arrange
        mock_processor.return_value.process.return_value = {"result": "processed"}
        payload = {
            "template_id": "test-template",
            "placeholder_data": {"key": "value"}
        }
        
        # Act
        response = client.post("/api/v1/intelligent-placeholders/process", json=payload)
        
        # Assert
        assert response.status_code == 200
        assert response.json()["result"] == "processed"
```

#### 依赖注入测试
```python
# tests/unit/api/test_deps.py
import pytest
from app.api.deps import get_placeholder_processor
from app.services.intelligent_placeholder import IntelligentPlaceholderProcessor

def test_get_placeholder_processor():
    """测试依赖注入返回正确的服务实例"""
    processor = get_placeholder_processor()
    assert isinstance(processor, IntelligentPlaceholderProcessor)
```

### 示例: 单元测试
```python
# tests/unit/services/test_example.py
from app.services.some_service import add_numbers

def test_add_numbers():
    """测试 add_numbers 函数"""
    assert add_numbers(2, 3) == 5
    assert add_numbers(-1, 1) == 0
```

### 示例: 集成测试
```python
# tests/integration/api/test_users.py
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

def test_get_users_me(client: TestClient, db: Session, normal_user_token_headers: dict):
    """测试获取当前用户信息的API端点"""
    response = client.get("/api/v1/users/me", headers=normal_user_token_headers)
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["email"] == "test@example.com"
```

## 前端测试 (Jest & React Testing Library)

### 运行测试
- **运行所有测试**:
  ```bash
  # 在 frontend 目录下
  npm test
  ```
- **运行测试并进入观察模式**:
  ```bash
  npm test -- --watch
  ```
- **运行特定测试**:
  ```bash
  npm test -- src/components/ui/__tests__/button.test.tsx
  ```

### 编写测试
- **理念**: 我们遵循 [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/) 的理念：测试你的组件的方式应该和用户使用它的方式尽量相似。
- **文件命名**: 测试文件通常以 `.test.tsx` 或 `.spec.tsx` 结尾。
- **查询元素**: 优先使用用户可见的查询方式，如 `getByRole`, `getByLabelText`, `getByText`。
- **用户交互**: 使用 `@testing-library/user-event` 来模拟用户交互，如点击、输入等。
- **Mocking API**: 使用 `jest.mock` 来模拟 `fetch` 或 `axios` 等API请求。

### 示例: 组件单元测试
```tsx
// src/components/ui/__tests__/button.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button } from '@/components/ui/button';

test('renders button and handles click', async () => {
  const handleClick = jest.fn();
  render(<Button onClick={handleClick}>Click Me</Button>);

  const buttonElement = screen.getByRole('button', { name: /click me/i });
  expect(buttonElement).toBeInTheDocument();

  await userEvent.click(buttonElement);
  expect(handleClick).toHaveBeenCalledTimes(1);
});
```

## 贡献新测试

- **新功能**: 必须附带相应的单元测试和/或集成测试。
- **Bug修复**: 必须附带一个能复现该Bug的回归测试。

通过遵循这些指南，我们可以共同维护一个高质量、高可靠性的代码库。