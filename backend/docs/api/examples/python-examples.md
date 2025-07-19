# Python API使用示例

## 概述

本文档提供了使用Python调用AutoReportAI API的完整示例，包括认证、数据管理、报告生成等核心功能。

## 环境准备

### 安装依赖

```bash
pip install requests pydantic python-dotenv
```

### 环境配置

创建 `.env` 文件：

```bash
# .env
AUTOREPORT_API_URL=http://localhost:8000
AUTOREPORT_USERNAME=your_username
AUTOREPORT_PASSWORD=your_password
```

## 基础客户端类

```python
import os
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class AutoReportAPIClient:
    """AutoReportAI API客户端"""
    
    def __init__(self):
        self.base_url = os.getenv("AUTOREPORT_API_URL", "http://localhost:8000")
        self.username = os.getenv("AUTOREPORT_USERNAME")
        self.password = os.getenv("AUTOREPORT_PASSWORD")
        self.token = None
        self.token_expires = None
        self.session = requests.Session()
        
    def authenticate(self) -> str:
        """获取访问令牌"""
        if self.token and self.token_expires > datetime.now():
            return self.token
            
        response = self.session.post(
            f"{self.base_url}/api/v1/auth/login",
            json={
                "username": self.username,
                "password": self.password
            }
        )
        
        if response.status_code == 200:
            data = response.json()["data"]
            self.token = data["access_token"]
            self.token_expires = datetime.now() + timedelta(seconds=data["expires_in"])
            return self.token
        else:
            raise Exception(f"认证失败: {response.text}")
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """发送认证请求"""
        token = self.authenticate()
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        headers["Content-Type"] = "application/json"
        kwargs["headers"] = headers
        
        url = f"{self.base_url}{endpoint}"
        response = self.session.request(method, url, **kwargs)
        
        if response.status_code == 401:
            # 令牌可能过期，重新认证
            self.token = None
            token = self.authenticate()
            headers["Authorization"] = f"Bearer {token}"
            response = self.session.request(method, url, **kwargs)
        
        return response
```

## 1. 用户认证示例

```python
def authentication_example():
    """用户认证示例"""
    client = AutoReportAPIClient()
    
    try:
        # 获取当前用户信息
        response = client.make_request("GET", "/api/v1/users/me")
        
        if response.status_code == 200:
            user_info = response.json()["data"]
            print(f"登录成功！用户: {user_info['username']}")
            print(f"邮箱: {user_info['email']}")
            return user_info
        else:
            print(f"获取用户信息失败: {response.text}")
            
    except Exception as e:
        print(f"认证失败: {e}")

# 运行示例
if __name__ == "__main__":
    user = authentication_example()
```

## 2. 模板管理示例

```python
class TemplateManager:
    """模板管理器"""
    
    def __init__(self, client: AutoReportAPIClient):
        self.client = client
    
    def list_templates(self, skip: int = 0, limit: int = 10) -> List[Dict[str, Any]]:
        """获取模板列表"""
        response = self.client.make_request(
            "GET", 
            f"/api/v1/templates?skip={skip}&limit={limit}"
        )
        
        if response.status_code == 200:
            return response.json()["data"]
        else:
            raise Exception(f"获取模板列表失败: {response.text}")
    
    def create_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建模板"""
        response = self.client.make_request(
            "POST", 
            "/api/v1/templates",
            json=template_data
        )
        
        if response.status_code == 200:
            return response.json()["data"]
        else:
            raise Exception(f"创建模板失败: {response.text}")
    
    def upload_template_file(self, file_path: str, name: str, description: str = "") -> Dict[str, Any]:
        """上传模板文件"""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {
                'name': name,
                'description': description,
                'is_public': 'false'
            }
            
            # 上传文件时不使用JSON Content-Type
            token = self.client.authenticate()
            headers = {"Authorization": f"Bearer {token}"}
            
            response = requests.post(
                f"{self.client.base_url}/api/v1/templates/upload",
                files=files,
                data=data,
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()["data"]
            else:
                raise Exception(f"上传模板失败: {response.text}")

def template_management_example():
    """模板管理示例"""
    client = AutoReportAPIClient()
    template_manager = TemplateManager(client)
    
    # 1. 获取模板列表
    print("=== 获取模板列表 ===")
    templates = template_manager.list_templates()
    print(f"找到 {len(templates)} 个模板")
    for template in templates:
        print(f"- {template['name']}: {template['description']}")
    
    # 2. 创建新模板
    print("\n=== 创建新模板 ===")
    new_template_data = {
        "name": "Python示例模板",
        "description": "通过Python API创建的示例模板",
        "content": "本月共收到{{统计:投诉总数}}件投诉，主要来自{{区域:主要投诉地区}}。",
        "template_type": "txt",
        "is_public": False
    }
    
    try:
        new_template = template_manager.create_template(new_template_data)
        print(f"模板创建成功: {new_template['id']}")
        print(f"识别到 {new_template.get('placeholder_count', 0)} 个占位符")
        return new_template
    except Exception as e:
        print(f"创建模板失败: {e}")

# 运行示例
if __name__ == "__main__":
    template = template_management_example()
```

## 3. 智能占位符处理示例

```python
class PlaceholderProcessor:
    """智能占位符处理器"""
    
    def __init__(self, client: AutoReportAPIClient):
        self.client = client
    
    def analyze_placeholders(self, template_content: str, template_id: str = None) -> Dict[str, Any]:
        """分析占位符"""
        request_data = {
            "template_content": template_content,
            "analysis_options": {
                "include_context": True,
                "confidence_threshold": 0.7
            }
        }
        
        if template_id:
            request_data["template_id"] = template_id
        
        response = self.client.make_request(
            "POST",
            "/api/v1/intelligent-placeholders/analyze",
            json=request_data
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"占位符分析失败: {response.text}")
    
    def field_matching(self, placeholder_text: str, placeholder_type: str, 
                      description: str, data_source_id: int) -> Dict[str, Any]:
        """字段匹配验证"""
        request_data = {
            "placeholder_text": placeholder_text,
            "placeholder_type": placeholder_type,
            "description": description,
            "data_source_id": data_source_id,
            "matching_options": {
                "confidence_threshold": 0.8,
                "max_suggestions": 5
            }
        }
        
        response = self.client.make_request(
            "POST",
            "/api/v1/intelligent-placeholders/field-matching",
            json=request_data
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"字段匹配失败: {response.text}")
    
    def generate_intelligent_report(self, template_id: str, data_source_id: int, 
                                  email_recipients: List[str] = None) -> Dict[str, Any]:
        """生成智能报告"""
        request_data = {
            "template_id": template_id,
            "data_source_id": data_source_id,
            "processing_config": {
                "llm_provider": "openai",
                "llm_model": "gpt-4",
                "enable_caching": True,
                "quality_check": True
            },
            "output_config": {
                "format": "docx",
                "include_charts": True,
                "quality_report": True
            }
        }
        
        if email_recipients:
            request_data["email_config"] = {
                "recipients": email_recipients,
                "subject": "智能生成报告",
                "include_summary": True
            }
        
        response = self.client.make_request(
            "POST",
            "/api/v1/intelligent-placeholders/generate-report",
            json=request_data
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"报告生成失败: {response.text}")
    
    def check_task_status(self, task_id: str) -> Dict[str, Any]:
        """检查任务状态"""
        response = self.client.make_request(
            "GET",
            f"/api/v1/intelligent-placeholders/task/{task_id}/status"
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"获取任务状态失败: {response.text}")

def placeholder_processing_example():
    """智能占位符处理示例"""
    client = AutoReportAPIClient()
    processor = PlaceholderProcessor(client)
    
    # 1. 分析占位符
    print("=== 分析占位符 ===")
    template_content = """
    # 月度投诉分析报告
    
    ## 数据概览
    本月共收到{{统计:投诉总数}}件投诉，比上月{{统计:环比变化}}。
    
    ## 地区分布
    投诉主要集中在{{区域:主要投诉地区}}，占总投诉量的{{统计:主要地区占比}}。
    
    ## 时间趋势
    {{周期:本月}}的投诉趋势如下：
    {{图表:投诉趋势图}}
    """
    
    try:
        analysis_result = processor.analyze_placeholders(template_content)
        print(f"识别到 {analysis_result['total_count']} 个占位符")
        
        for placeholder in analysis_result['placeholders']:
            print(f"- {placeholder['placeholder_text']}")
            print(f"  类型: {placeholder['placeholder_type']}")
            print(f"  描述: {placeholder['description']}")
            print(f"  置信度: {placeholder['confidence']:.2f}")
            print()
        
        return analysis_result
        
    except Exception as e:
        print(f"占位符分析失败: {e}")

# 运行示例
if __name__ == "__main__":
    result = placeholder_processing_example()
```

## 4. 数据源管理示例

```python
class DataSourceManager:
    """数据源管理器"""
    
    def __init__(self, client: AutoReportAPIClient):
        self.client = client
    
    def list_data_sources(self) -> List[Dict[str, Any]]:
        """获取数据源列表"""
        response = self.client.make_request("GET", "/api/v1/data-sources")
        
        if response.status_code == 200:
            return response.json()["data"]
        else:
            raise Exception(f"获取数据源列表失败: {response.text}")
    
    def create_data_source(self, data_source_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建数据源"""
        response = self.client.make_request(
            "POST",
            "/api/v1/data-sources",
            json=data_source_data
        )
        
        if response.status_code == 200:
            return response.json()["data"]
        else:
            raise Exception(f"创建数据源失败: {response.text}")
    
    def test_data_source(self, data_source_id: int) -> Dict[str, Any]:
        """测试数据源连接"""
        response = self.client.make_request(
            "POST",
            f"/api/v1/data-sources/{data_source_id}/test"
        )
        
        if response.status_code == 200:
            return response.json()["data"]
        else:
            raise Exception(f"测试数据源失败: {response.text}")

def data_source_management_example():
    """数据源管理示例"""
    client = AutoReportAPIClient()
    ds_manager = DataSourceManager(client)
    
    # 1. 获取数据源列表
    print("=== 获取数据源列表 ===")
    data_sources = ds_manager.list_data_sources()
    print(f"找到 {len(data_sources)} 个数据源")
    
    for ds in data_sources:
        print(f"- {ds['name']}: {ds['connection_type']}")
        print(f"  状态: {'活跃' if ds['is_active'] else '非活跃'}")
    
    # 2. 创建新数据源
    print("\n=== 创建新数据源 ===")
    new_data_source = {
        "name": "测试PostgreSQL数据库",
        "description": "用于测试的PostgreSQL数据库连接",
        "connection_type": "postgresql",
        "connection_config": {
            "host": "localhost",
            "port": 5432,
            "database": "test_db",
            "username": "test_user",
            "password": "test_password"
        },
        "test_connection": True
    }
    
    try:
        created_ds = ds_manager.create_data_source(new_data_source)
        print(f"数据源创建成功: {created_ds['id']}")
        
        # 测试连接
        if created_ds.get('connection_test', {}).get('status') == 'success':
            print("✅ 数据源连接测试成功")
        else:
            print("❌ 数据源连接测试失败")
            
        return created_ds
        
    except Exception as e:
        print(f"创建数据源失败: {e}")

# 运行示例
if __name__ == "__main__":
    ds = data_source_management_example()
```

## 5. 完整工作流示例

```python
import time
from typing import Dict, Any

def complete_workflow_example():
    """完整工作流示例：从模板创建到报告生成"""
    client = AutoReportAPIClient()
    template_manager = TemplateManager(client)
    processor = PlaceholderProcessor(client)
    ds_manager = DataSourceManager(client)
    
    print("🚀 开始完整工作流演示")
    
    # 步骤1: 创建模板
    print("\n📝 步骤1: 创建报告模板")
    template_data = {
        "name": "完整工作流示例模板",
        "description": "演示完整工作流的报告模板",
        "content": """
        # 业务数据分析报告
        
        ## 核心指标
        - 总记录数: {{统计:总记录数}}
        - 活跃用户数: {{统计:活跃用户数}}
        - 主要业务区域: {{区域:主要业务区域}}
        
        ## 趋势分析
        {{周期:本季度}}的业务趋势：
        {{图表:业务趋势图}}
        
        ## 总结
        基于以上数据分析，我们可以看出...
        """,
        "template_type": "txt",
        "is_public": False
    }
    
    try:
        template = template_manager.create_template(template_data)
        print(f"✅ 模板创建成功: {template['name']}")
        template_id = template['id']
    except Exception as e:
        print(f"❌ 模板创建失败: {e}")
        return
    
    # 步骤2: 分析占位符
    print("\n🧠 步骤2: 分析模板占位符")
    try:
        analysis = processor.analyze_placeholders(template_data['content'], template_id)
        print(f"✅ 识别到 {analysis['total_count']} 个占位符")
        
        for placeholder in analysis['placeholders']:
            print(f"  - {placeholder['placeholder_text']} (置信度: {placeholder['confidence']:.2f})")
    except Exception as e:
        print(f"❌ 占位符分析失败: {e}")
        return
    
    # 步骤3: 检查数据源
    print("\n🗄️ 步骤3: 检查可用数据源")
    try:
        data_sources = ds_manager.list_data_sources()
        if not data_sources:
            print("⚠️ 没有可用的数据源，请先创建数据源")
            return
        
        data_source = data_sources[0]  # 使用第一个数据源
        print(f"✅ 使用数据源: {data_source['name']}")
        data_source_id = data_source['id']
    except Exception as e:
        print(f"❌ 获取数据源失败: {e}")
        return
    
    # 步骤4: 生成智能报告
    print("\n📊 步骤4: 生成智能报告")
    try:
        report_task = processor.generate_intelligent_report(
            template_id=template_id,
            data_source_id=data_source_id,
            email_recipients=["demo@example.com"]
        )
        
        task_id = report_task['task_id']
        print(f"✅ 报告生成任务已启动: {task_id}")
        
        # 监控任务状态
        print("⏳ 监控任务进度...")
        max_attempts = 30  # 最多等待5分钟
        attempt = 0
        
        while attempt < max_attempts:
            try:
                status = processor.check_task_status(task_id)
                print(f"  状态: {status['status']} - {status.get('message', '')}")
                
                if status['status'] == 'completed':
                    print("✅ 报告生成完成！")
                    if status.get('result'):
                        print(f"  报告文件: {status['result'].get('file_path')}")
                        print(f"  质量评分: {status['result'].get('quality_score', 'N/A')}")
                    break
                elif status['status'] == 'failed':
                    print(f"❌ 报告生成失败: {status.get('error')}")
                    break
                
                time.sleep(10)  # 等待10秒后再次检查
                attempt += 1
                
            except Exception as e:
                print(f"❌ 检查任务状态失败: {e}")
                break
        
        if attempt >= max_attempts:
            print("⏰ 任务执行超时")
            
    except Exception as e:
        print(f"❌ 报告生成失败: {e}")
    
    print("\n🎉 工作流演示完成！")

# 运行完整示例
if __name__ == "__main__":
    complete_workflow_example()
```

## 6. 错误处理和重试机制

```python
import time
import random
from functools import wraps

def retry_on_failure(max_retries: int = 3, backoff_factor: float = 1.0):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor * (2 ** attempt) + random.uniform(0, 1)
                        print(f"请求失败，{wait_time:.2f}秒后重试 (第{attempt + 1}次): {e}")
                        time.sleep(wait_time)
                        continue
                    raise
            return None
        return wrapper
    return decorator

class RobustAPIClient(AutoReportAPIClient):
    """增强的API客户端，包含错误处理和重试机制"""
    
    @retry_on_failure(max_retries=3, backoff_factor=1.0)
    def make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """带重试机制的请求方法"""
        return super().make_request(method, endpoint, **kwargs)
    
    def safe_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """安全的请求方法，返回None而不是抛出异常"""
        try:
            response = self.make_request(method, endpoint, **kwargs)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"请求失败 {response.status_code}: {response.text}")
                return None
        except Exception as e:
            print(f"请求异常: {e}")
            return None

def robust_api_example():
    """健壮的API调用示例"""
    client = RobustAPIClient()
    
    # 安全的API调用
    user_info = client.safe_request("GET", "/api/v1/users/me")
    if user_info:
        print(f"用户信息获取成功: {user_info['data']['username']}")
    else:
        print("用户信息获取失败")
    
    # 带重试的API调用
    try:
        templates = client.make_request("GET", "/api/v1/templates")
        print(f"模板列表获取成功: {len(templates.json()['data'])} 个模板")
    except Exception as e:
        print(f"模板列表获取失败: {e}")

# 运行示例
if __name__ == "__main__":
    robust_api_example()
```

## 总结

本文档提供了使用Python调用AutoReportAI API的完整示例，包括：

1. **基础认证和客户端设置**
2. **模板管理操作**
3. **智能占位符处理**
4. **数据源管理**
5. **完整的端到端工作流**
6. **错误处理和重试机制**

这些示例可以作为集成AutoReportAI API到您的Python应用程序的起点。根据具体需求，您可以扩展和定制这些示例代码。

## 相关资源

- [API参考文档](http://localhost:8000/api/v1/docs)
- [JavaScript示例](./javascript-examples.md)
- [最佳实践指南](../best-practices.md)
- [常见问题解答](../faq.md)