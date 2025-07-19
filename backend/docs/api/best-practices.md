# API最佳实践指南

## 概述

本指南提供了使用AutoReportAI API的最佳实践，帮助开发者构建稳定、高效的集成。

## 认证与安全

### 1. Token管理

**正确做法：**
```python
import requests
from datetime import datetime, timedelta

class APIClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.token = None
        self.token_expires = None
    
    def get_token(self):
        """获取或刷新访问令牌"""
        if self.token and self.token_expires > datetime.now():
            return self.token
        
        response = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            data={"username": self.username, "password": self.password}
        )
        
        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            self.token_expires = datetime.now() + timedelta(seconds=data["expires_in"])
            return self.token
        else:
            raise Exception(f"登录失败: {response.text}")
    
    def make_request(self, method: str, endpoint: str, **kwargs):
        """发送认证请求"""
        token = self.get_token()
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        kwargs["headers"] = headers
        
        return requests.request(method, f"{self.base_url}{endpoint}", **kwargs)
```

**错误做法：**
```python
# ❌ 不要在每次请求时都重新登录
response = requests.post("/api/v1/auth/login", data={"username": "...", "password": "..."})
token = response.json()["access_token"]
requests.get("/api/v1/data-sources", headers={"Authorization": f"Bearer {token}"})
```

### 2. 密钥安全

**正确做法：**
```python
import os
from dataclasses import dataclass

@dataclass
class Config:
    api_base_url: str = os.getenv("AUTOREPORT_API_URL", "http://localhost:8000")
    username: str = os.getenv("AUTOREPORT_USERNAME")
    password: str = os.getenv("AUTOREPORT_PASSWORD")
    
    def __post_init__(self):
        if not self.username or not self.password:
            raise ValueError("请设置AUTOREPORT_USERNAME和AUTOREPORT_PASSWORD环境变量")
```

**错误做法：**
```python
# ❌ 不要将凭据硬编码在代码中
username = "admin"
password = "password123"
```

## 错误处理

### 1. 分层错误处理

```python
import requests
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class APIError(Exception):
    """API错误基类"""
    def __init__(self, message: str, status_code: int, details: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class APIClient:
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """统一处理API响应"""
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_detail = "未知错误"
            try:
                error_data = response.json()
                error_detail = error_data.get("detail", str(e))
            except:
                error_detail = response.text or str(e)
            
            logger.error(f"API错误 {response.status_code}: {error_detail}")
            raise APIError(error_detail, response.status_code)
        except requests.exceptions.RequestException as e:
            logger.error(f"请求错误: {e}")
            raise APIError(f"请求失败: {e}", 0)
    
    def get_data_sources(self) -> List[Dict[str, Any]]:
        """获取数据源列表"""
        try:
            response = self.make_request("GET", "/api/v1/data-sources")
            return self._handle_response(response)
        except APIError as e:
            if e.status_code == 401:
                # 尝试重新认证
                self.token = None
                response = self.make_request("GET", "/api/v1/data-sources")
                return self._handle_response(response)
            raise
```

### 2. 重试机制

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
                except APIError as e:
                    if e.status_code in [500, 502, 503, 504] and attempt < max_retries - 1:
                        # 指数退避
                        wait_time = backoff_factor * (2 ** attempt) + random.uniform(0, 1)
                        logger.warning(f"请求失败，{wait_time:.2f}秒后重试 (第{attempt + 1}次)")
                        time.sleep(wait_time)
                        continue
                    raise
            return None
        return wrapper
    return decorator

class APIClient:
    @retry_on_failure(max_retries=3, backoff_factor=1.0)
    def create_data_source(self, data_source_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建数据源"""
        response = self.make_request("POST", "/api/v1/data-sources", json=data_source_data)
        return self._handle_response(response)
```

## 数据处理

### 1. 分页处理

```python
def get_all_data_sources(self) -> List[Dict[str, Any]]:
    """获取所有数据源（处理分页）"""
    all_sources = []
    skip = 0
    limit = 100
    
    while True:
        response = self.make_request(
            "GET", 
            f"/api/v1/data-sources?skip={skip}&limit={limit}"
        )
        data = self._handle_response(response)
        
        if not data:
            break
        
        all_sources.extend(data)
        
        if len(data) < limit:
            break
        
        skip += limit
    
    return all_sources
```

### 2. 批量操作

```python
async def batch_create_data_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """批量创建数据源"""
    import asyncio
    import aiohttp
    
    async def create_single_source(session, source_data):
        async with session.post(
            f"{self.base_url}/api/v1/data-sources",
            json=source_data,
            headers={"Authorization": f"Bearer {self.get_token()}"}
        ) as response:
            return await response.json()
    
    async with aiohttp.ClientSession() as session:
        tasks = [create_single_source(session, source) for source in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return [result for result in results if not isinstance(result, Exception)]
```

## 性能优化

### 1. 连接池

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class APIClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url
        self.username = username
        self.password = password
        
        # 配置会话和连接池
        self.session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        # 配置适配器
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def make_request(self, method: str, endpoint: str, **kwargs):
        """使用会话发送请求"""
        token = self.get_token()
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        kwargs["headers"] = headers
        
        return self.session.request(method, f"{self.base_url}{endpoint}", **kwargs)
```

### 2. 缓存策略

```python
import functools
import time
from typing import Dict, Any, Optional

class CacheManager:
    def __init__(self, default_ttl: int = 300):
        self.cache = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key in self.cache:
            data, expires = self.cache[key]
            if expires > time.time():
                return data
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        ttl = ttl or self.default_ttl
        expires = time.time() + ttl
        self.cache[key] = (value, expires)

class APIClient:
    def __init__(self, base_url: str, username: str, password: str):
        # ... 其他初始化代码 ...
        self.cache = CacheManager()
    
    def get_data_source(self, data_source_id: str) -> Dict[str, Any]:
        """获取数据源（带缓存）"""
        cache_key = f"data_source_{data_source_id}"
        cached_data = self.cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        response = self.make_request("GET", f"/api/v1/data-sources/{data_source_id}")
        data = self._handle_response(response)
        
        # 缓存5分钟
        self.cache.set(cache_key, data, ttl=300)
        return data
```

## 监控与日志

### 1. 请求日志

```python
import logging
import time
from typing import Dict, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class APIClient:
    def make_request(self, method: str, endpoint: str, **kwargs):
        """发送请求并记录日志"""
        start_time = time.time()
        
        # 记录请求开始
        logger.info(f"API请求开始: {method} {endpoint}")
        
        try:
            token = self.get_token()
            headers = kwargs.get("headers", {})
            headers["Authorization"] = f"Bearer {token}"
            kwargs["headers"] = headers
            
            response = self.session.request(method, f"{self.base_url}{endpoint}", **kwargs)
            
            # 记录响应时间
            elapsed = time.time() - start_time
            logger.info(f"API请求完成: {method} {endpoint} - {response.status_code} - {elapsed:.2f}s")
            
            return response
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"API请求失败: {method} {endpoint} - {elapsed:.2f}s - {e}")
            raise
```

### 2. 指标收集

```python
from dataclasses import dataclass
from collections import defaultdict
import time

@dataclass
class RequestMetrics:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    
    @property
    def success_rate(self) -> float:
        return self.successful_requests / self.total_requests if self.total_requests > 0 else 0.0
    
    @property
    def average_response_time(self) -> float:
        return self.total_response_time / self.total_requests if self.total_requests > 0 else 0.0

class APIClient:
    def __init__(self, base_url: str, username: str, password: str):
        # ... 其他初始化代码 ...
        self.metrics = defaultdict(RequestMetrics)
    
    def make_request(self, method: str, endpoint: str, **kwargs):
        """发送请求并收集指标"""
        metric_key = f"{method}_{endpoint}"
        start_time = time.time()
        
        try:
            response = self.session.request(method, f"{self.base_url}{endpoint}", **kwargs)
            
            # 更新指标
            elapsed = time.time() - start_time
            metrics = self.metrics[metric_key]
            metrics.total_requests += 1
            metrics.total_response_time += elapsed
            
            if response.status_code < 400:
                metrics.successful_requests += 1
            else:
                metrics.failed_requests += 1
            
            return response
            
        except Exception as e:
            elapsed = time.time() - start_time
            metrics = self.metrics[metric_key]
            metrics.total_requests += 1
            metrics.failed_requests += 1
            metrics.total_response_time += elapsed
            raise
    
    def get_metrics_summary(self) -> Dict[str, Dict[str, Any]]:
        """获取指标摘要"""
        summary = {}
        for endpoint, metrics in self.metrics.items():
            summary[endpoint] = {
                "total_requests": metrics.total_requests,
                "success_rate": f"{metrics.success_rate:.2%}",
                "average_response_time": f"{metrics.average_response_time:.2f}s"
            }
        return summary
```

## 示例：完整的客户端实现

```python
# client.py
import os
import requests
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Config:
    api_base_url: str = os.getenv("AUTOREPORT_API_URL", "http://localhost:8000")
    username: str = os.getenv("AUTOREPORT_USERNAME")
    password: str = os.getenv("AUTOREPORT_PASSWORD")
    
    def __post_init__(self):
        if not self.username or not self.password:
            raise ValueError("请设置AUTOREPORT_USERNAME和AUTOREPORT_PASSWORD环境变量")

class AutoReportClient:
    """AutoReportAI API客户端"""
    
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.token = None
        self.token_expires = None
    
    def authenticate(self) -> str:
        """获取访问令牌"""
        if self.token and self.token_expires > datetime.now():
            return self.token
        
        response = self.session.post(
            f"{self.config.api_base_url}/api/v1/auth/login",
            data={
                "username": self.config.username,
                "password": self.config.password
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            self.token_expires = datetime.now() + timedelta(seconds=data["expires_in"])
            logger.info("认证成功")
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
        
        url = f"{self.config.api_base_url}{endpoint}"
        response = self.session.request(method, url, **kwargs)
        
        logger.info(f"{method} {endpoint} - {response.status_code}")
        return response
    
    # 数据源相关方法
    def get_data_sources(self) -> List[Dict[str, Any]]:
        """获取数据源列表"""
        response = self.make_request("GET", "/api/v1/data-sources")
        response.raise_for_status()
        return response.json()
    
    def create_data_source(self, data_source_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建数据源"""
        response = self.make_request("POST", "/api/v1/data-sources", json=data_source_data)
        response.raise_for_status()
        return response.json()
    
    def test_data_source(self, data_source_id: str) -> Dict[str, Any]:
        """测试数据源连接"""
        response = self.make_request("POST", f"/api/v1/data-sources/{data_source_id}/test")
        response.raise_for_status()
        return response.json()
    
    # AI服务相关方法
    def get_ai_providers(self) -> List[Dict[str, Any]]:
        """获取AI提供商列表"""
        response = self.make_request("GET", "/api/v1/ai-providers")
        response.raise_for_status()
        return response.json()
    
    def create_ai_provider(self, provider_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建AI提供商"""
        response = self.make_request("POST", "/api/v1/ai-providers", json=provider_data)
        response.raise_for_status()
        return response.json()
    
    # 报告相关方法
    def generate_report(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成报告"""
        response = self.make_request("POST", "/api/v1/reports/generate", json=report_data)
        response.raise_for_status()
        return response.json()
    
    def get_report_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取报告历史"""
        response = self.make_request("GET", f"/api/v1/reports/history?limit={limit}")
        response.raise_for_status()
        return response.json()

# 使用示例
if __name__ == "__main__":
    config = Config()
    client = AutoReportClient(config)
    
    try:
        # 获取数据源列表
        data_sources = client.get_data_sources()
        print(f"找到 {len(data_sources)} 个数据源")
        
        # 获取AI提供商列表
        ai_providers = client.get_ai_providers()
        print(f"找到 {len(ai_providers)} 个AI提供商")
        
        # 获取报告历史
        reports = client.get_report_history()
        print(f"找到 {len(reports)} 个历史报告")
        
    except Exception as e:
        logger.error(f"操作失败: {e}")
```

## 总结

遵循这些最佳实践可以帮助您构建稳定、高效的API集成：

1. **安全性**: 正确管理认证令牌，保护敏感信息
2. **错误处理**: 实现分层错误处理和重试机制
3. **性能**: 使用连接池、缓存和批量操作
4. **监控**: 记录日志和收集指标
5. **可维护性**: 结构化代码，使用配置管理

这些实践将帮助您在生产环境中稳定地使用AutoReportAI API。