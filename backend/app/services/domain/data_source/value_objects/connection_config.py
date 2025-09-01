"""
Domain层连接配置值对象

封装数据源连接配置的不可变值对象：

核心职责：
1. 封装连接参数和配置
2. 提供配置验证逻辑
3. 支持配置的序列化和反序列化
4. 处理敏感信息的安全性

Value Object特点：
- 不可变对象
- 值相等性比较
- 包含业务验证逻辑
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import copy
import json

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConnectionConfig:
    """
    Domain层连接配置值对象
    
    封装数据源连接的所有配置信息：
    - 基本连接参数
    - 安全配置
    - 性能调优参数
    - 扩展配置项
    """
    
    # 基本连接配置
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    
    # Doris特定配置
    doris_fe_hosts: Optional[List[str]] = None
    doris_query_port: Optional[int] = None
    doris_database: Optional[str] = None
    doris_username: Optional[str] = None
    
    # API特定配置
    base_url: Optional[str] = None
    api_version: Optional[str] = None
    
    # 安全配置
    use_ssl: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    ssl_ca_path: Optional[str] = None
    
    # 连接池和性能配置
    max_connections: int = 10
    connection_timeout: int = 30
    query_timeout: int = 300
    pool_pre_ping: bool = True
    pool_recycle: int = 3600
    
    # 重试和错误处理配置
    max_retries: int = 3
    retry_delay: float = 1.0
    enable_failover: bool = False
    
    # 扩展配置
    extra_config: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """初始化后验证"""
        self._validate_configuration()
    
    def _validate_configuration(self):
        """验证配置的完整性和正确性"""
        
        # 端口号验证
        if self.port is not None and (not isinstance(self.port, int) or self.port <= 0 or self.port > 65535):
            raise ValueError("端口号必须是1-65535之间的整数")
        
        if self.doris_query_port is not None and (not isinstance(self.doris_query_port, int) or self.doris_query_port <= 0):
            raise ValueError("Doris查询端口必须是正整数")
        
        # URL格式验证
        if self.base_url is not None and not self.base_url.startswith(('http://', 'https://')):
            raise ValueError("base_url必须以http://或https://开头")
        
        # 连接池参数验证
        if self.max_connections <= 0:
            raise ValueError("最大连接数必须大于0")
        
        if self.connection_timeout <= 0:
            raise ValueError("连接超时时间必须大于0")
        
        if self.query_timeout <= 0:
            raise ValueError("查询超时时间必须大于0")
        
        # 重试参数验证
        if self.max_retries < 0:
            raise ValueError("最大重试次数不能小于0")
        
        if self.retry_delay < 0:
            raise ValueError("重试延迟不能小于0")
    
    def get_safe_config(self) -> Dict[str, Any]:
        """获取安全的配置（隐藏敏感信息）"""
        config = self.to_dict()
        
        # 隐藏敏感字段
        sensitive_fields = ['password', 'api_key', 'auth_token', 'ssl_key_path']
        for field in sensitive_fields:
            if field in config and config[field]:
                config[field] = "***HIDDEN***"
        
        # 处理extra_config中的敏感信息
        if config.get('extra_config'):
            extra_config = copy.deepcopy(config['extra_config'])
            for field in sensitive_fields:
                if field in extra_config:
                    extra_config[field] = "***HIDDEN***"
            config['extra_config'] = extra_config
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {}
        
        # 基本配置
        if self.host is not None:
            result['host'] = self.host
        if self.port is not None:
            result['port'] = self.port
        if self.database is not None:
            result['database'] = self.database
        if self.username is not None:
            result['username'] = self.username
        
        # Doris配置
        if self.doris_fe_hosts is not None:
            result['doris_fe_hosts'] = list(self.doris_fe_hosts)
        if self.doris_query_port is not None:
            result['doris_query_port'] = self.doris_query_port
        if self.doris_database is not None:
            result['doris_database'] = self.doris_database
        if self.doris_username is not None:
            result['doris_username'] = self.doris_username
        
        # API配置
        if self.base_url is not None:
            result['base_url'] = self.base_url
        if self.api_version is not None:
            result['api_version'] = self.api_version
        
        # 安全配置
        result['use_ssl'] = self.use_ssl
        if self.ssl_cert_path is not None:
            result['ssl_cert_path'] = self.ssl_cert_path
        if self.ssl_key_path is not None:
            result['ssl_key_path'] = self.ssl_key_path
        if self.ssl_ca_path is not None:
            result['ssl_ca_path'] = self.ssl_ca_path
        
        # 性能配置
        result.update({
            'max_connections': self.max_connections,
            'connection_timeout': self.connection_timeout,
            'query_timeout': self.query_timeout,
            'pool_pre_ping': self.pool_pre_ping,
            'pool_recycle': self.pool_recycle,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay,
            'enable_failover': self.enable_failover
        })
        
        # 扩展配置
        if self.extra_config is not None:
            result['extra_config'] = copy.deepcopy(self.extra_config)
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConnectionConfig':
        """从字典创建配置对象"""
        # 过滤掉None值和不存在的字段
        filtered_data = {}
        
        # 定义所有可能的字段
        valid_fields = {
            'host', 'port', 'database', 'username',
            'doris_fe_hosts', 'doris_query_port', 'doris_database', 'doris_username',
            'base_url', 'api_version',
            'use_ssl', 'ssl_cert_path', 'ssl_key_path', 'ssl_ca_path',
            'max_connections', 'connection_timeout', 'query_timeout',
            'pool_pre_ping', 'pool_recycle',
            'max_retries', 'retry_delay', 'enable_failover',
            'extra_config'
        }
        
        for key, value in data.items():
            if key in valid_fields and value is not None:
                filtered_data[key] = value
        
        return cls(**filtered_data)
    
    def merge_with(self, other_config: Dict[str, Any]) -> 'ConnectionConfig':
        """与其他配置合并，创建新的配置对象"""
        current_dict = self.to_dict()
        current_dict.update(other_config)
        return ConnectionConfig.from_dict(current_dict)
    
    def get_connection_string(self, source_type: str, include_password: bool = False) -> str:
        """生成连接字符串"""
        
        if source_type.lower() in ['mysql', 'postgresql']:
            # 标准数据库连接字符串
            if not all([self.host, self.port, self.database, self.username]):
                raise ValueError(f"{source_type}连接配置不完整")
            
            password_part = ""
            if include_password and self.extra_config and 'password' in self.extra_config:
                password_part = f":{self.extra_config['password']}"
            
            protocol = 'mysql' if source_type.lower() == 'mysql' else 'postgresql'
            return f"{protocol}://{self.username}{password_part}@{self.host}:{self.port}/{self.database}"
        
        elif source_type.lower() == 'doris':
            # Doris连接信息
            if not all([self.doris_fe_hosts, self.doris_database, self.doris_username]):
                raise ValueError("Doris连接配置不完整")
            
            fe_hosts_str = ','.join(self.doris_fe_hosts)
            port_part = f":{self.doris_query_port}" if self.doris_query_port else ""
            return f"doris://{self.doris_username}@{fe_hosts_str}{port_part}/{self.doris_database}"
        
        elif source_type.lower() == 'api':
            # API连接信息
            if not self.base_url:
                raise ValueError("API连接配置不完整")
            
            version_part = f"/v{self.api_version}" if self.api_version else ""
            return f"{self.base_url}{version_part}"
        
        else:
            return f"{source_type}://配置详见config对象"
    
    def is_ssl_enabled(self) -> bool:
        """检查是否启用SSL"""
        return self.use_ssl
    
    def has_ssl_certificates(self) -> bool:
        """检查是否配置了SSL证书"""
        return bool(self.ssl_cert_path and self.ssl_key_path)
    
    def get_timeout_config(self) -> Dict[str, int]:
        """获取超时配置"""
        return {
            'connection_timeout': self.connection_timeout,
            'query_timeout': self.query_timeout
        }
    
    def get_pool_config(self) -> Dict[str, Any]:
        """获取连接池配置"""
        return {
            'max_connections': self.max_connections,
            'pool_pre_ping': self.pool_pre_ping,
            'pool_recycle': self.pool_recycle
        }
    
    def get_retry_config(self) -> Dict[str, Any]:
        """获取重试配置"""
        return {
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay,
            'enable_failover': self.enable_failover
        }
    
    def __str__(self) -> str:
        """字符串表示（安全版本）"""
        safe_config = self.get_safe_config()
        return f"ConnectionConfig({json.dumps(safe_config, ensure_ascii=False, indent=2)})"