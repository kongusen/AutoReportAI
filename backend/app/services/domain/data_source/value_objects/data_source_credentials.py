"""
Domain层数据源凭据值对象

封装数据源认证凭据的不可变值对象：

核心职责：
1. 封装各种类型的认证凭据
2. 提供凭据的安全处理
3. 支持凭据的验证和有效期检查
4. 处理凭据的加密和解密（接口）

Value Object特点：
- 不可变对象
- 值相等性比较
- 安全的凭据处理
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class CredentialType(Enum):
    """凭据类型"""
    USERNAME_PASSWORD = "username_password"
    API_KEY = "api_key"
    TOKEN = "token"
    OAUTH2 = "oauth2"
    CERTIFICATE = "certificate"
    KERBEROS = "kerberos"
    NONE = "none"


@dataclass(frozen=True)
class DataSourceCredentials:
    """
    Domain层数据源凭据值对象
    
    封装数据源认证的所有凭据信息：
    - 用户名密码认证
    - API密钥认证
    - Token认证
    - OAuth2认证
    - 证书认证
    """
    
    # 凭据类型
    credential_type: CredentialType
    
    # 基本认证
    username: Optional[str] = None
    password_hash: Optional[str] = None  # 存储密码哈希而非明文
    
    # API密钥认证
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    
    # Token认证
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None
    
    # OAuth2认证
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    scope: Optional[str] = None
    auth_url: Optional[str] = None
    token_url: Optional[str] = None
    
    # 证书认证
    cert_path: Optional[str] = None
    key_path: Optional[str] = None
    ca_path: Optional[str] = None
    
    # 凭据元数据
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    last_refreshed_at: Optional[datetime] = None
    
    # 额外参数
    extra_params: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """初始化后验证"""
        if self.created_at is None:
            object.__setattr__(self, 'created_at', datetime.utcnow())
        self._validate_credentials()
    
    def _validate_credentials(self):
        """验证凭据的完整性"""
        
        if self.credential_type == CredentialType.USERNAME_PASSWORD:
            if not self.username:
                raise ValueError("用户名密码认证需要提供用户名")
            # 注意：这里不验证password_hash，因为可能在创建时还未设置
        
        elif self.credential_type == CredentialType.API_KEY:
            if not self.api_key:
                raise ValueError("API密钥认证需要提供API密钥")
        
        elif self.credential_type == CredentialType.TOKEN:
            if not self.access_token:
                raise ValueError("Token认证需要提供访问令牌")
        
        elif self.credential_type == CredentialType.OAUTH2:
            if not all([self.client_id, self.client_secret, self.auth_url, self.token_url]):
                raise ValueError("OAuth2认证需要提供完整的OAuth2配置")
        
        elif self.credential_type == CredentialType.CERTIFICATE:
            if not self.cert_path:
                raise ValueError("证书认证需要提供证书路径")
    
    def is_expired(self) -> bool:
        """检查凭据是否已过期"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def expires_soon(self, minutes: int = 30) -> bool:
        """检查凭据是否即将过期"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() + timedelta(minutes=minutes) > self.expires_at
    
    def time_until_expiry(self) -> Optional[timedelta]:
        """获取距离过期的时间"""
        if self.expires_at is None:
            return None
        return self.expires_at - datetime.utcnow()
    
    def needs_refresh(self) -> bool:
        """检查是否需要刷新凭据"""
        # Token类型的凭据可能需要刷新
        if self.credential_type == CredentialType.TOKEN and self.refresh_token:
            return self.expires_soon(minutes=5)  # 5分钟内过期就需要刷新
        
        if self.credential_type == CredentialType.OAUTH2:
            return self.expires_soon(minutes=5)
        
        return False
    
    def can_refresh(self) -> bool:
        """检查是否可以刷新凭据"""
        if self.credential_type == CredentialType.TOKEN:
            return bool(self.refresh_token)
        
        if self.credential_type == CredentialType.OAUTH2:
            return bool(self.client_id and self.client_secret and self.token_url)
        
        return False
    
    def create_refreshed_credentials(self, 
                                   new_access_token: str,
                                   new_expires_at: Optional[datetime] = None,
                                   new_refresh_token: Optional[str] = None) -> 'DataSourceCredentials':
        """创建刷新后的凭据（返回新对象）"""
        
        if not self.can_refresh():
            raise ValueError("当前凭据类型不支持刷新")
        
        # 创建新的凭据对象
        new_credentials_dict = self.to_dict()
        new_credentials_dict.update({
            'access_token': new_access_token,
            'expires_at': new_expires_at,
            'last_refreshed_at': datetime.utcnow()
        })
        
        if new_refresh_token:
            new_credentials_dict['refresh_token'] = new_refresh_token
        
        return DataSourceCredentials.from_dict(new_credentials_dict)
    
    def get_auth_headers(self) -> Dict[str, str]:
        """获取认证头部信息"""
        headers = {}
        
        if self.credential_type == CredentialType.API_KEY:
            if self.api_key:
                headers['X-API-Key'] = self.api_key
                # 或者根据具体API的要求设置不同的头部
                # headers['Authorization'] = f'ApiKey {self.api_key}'
        
        elif self.credential_type == CredentialType.TOKEN:
            if self.access_token:
                token_type = self.token_type or 'Bearer'
                headers['Authorization'] = f'{token_type} {self.access_token}'
        
        elif self.credential_type == CredentialType.OAUTH2:
            if self.access_token:
                headers['Authorization'] = f'Bearer {self.access_token}'
        
        # 添加额外的头部信息
        if self.extra_params:
            for key, value in self.extra_params.items():
                if key.startswith('header_'):
                    header_name = key[7:]  # 去掉 'header_' 前缀
                    headers[header_name] = str(value)
        
        return headers
    
    def get_connection_params(self) -> Dict[str, Any]:
        """获取连接参数"""
        params = {}
        
        if self.credential_type == CredentialType.USERNAME_PASSWORD:
            if self.username:
                params['username'] = self.username
            # 注意：这里不返回密码，密码应该通过安全的方式传递
        
        elif self.credential_type == CredentialType.CERTIFICATE:
            if self.cert_path:
                params['cert'] = self.cert_path
            if self.key_path:
                params['key'] = self.key_path
            if self.ca_path:
                params['ca'] = self.ca_path
        
        # 添加额外参数
        if self.extra_params:
            for key, value in self.extra_params.items():
                if not key.startswith('header_'):  # 排除头部信息
                    params[key] = value
        
        return params
    
    def mask_sensitive_data(self) -> Dict[str, Any]:
        """获取掩码后的敏感数据（用于日志记录）"""
        data = self.to_dict()
        
        # 敏感字段列表
        sensitive_fields = [
            'password_hash', 'api_key', 'api_secret', 'access_token', 
            'refresh_token', 'client_secret'
        ]
        
        for field in sensitive_fields:
            if field in data and data[field]:
                data[field] = "***MASKED***"
        
        # 处理额外参数中的敏感信息
        if data.get('extra_params'):
            extra_params = data['extra_params'].copy()
            for key, value in extra_params.items():
                if any(sensitive_word in key.lower() for sensitive_word in ['password', 'secret', 'key', 'token']):
                    extra_params[key] = "***MASKED***"
            data['extra_params'] = extra_params
        
        return data
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            'credential_type': self.credential_type.value
        }
        
        # 基本认证
        if self.username is not None:
            result['username'] = self.username
        if self.password_hash is not None:
            result['password_hash'] = self.password_hash
        
        # API密钥认证
        if self.api_key is not None:
            result['api_key'] = self.api_key
        if self.api_secret is not None:
            result['api_secret'] = self.api_secret
        
        # Token认证
        if self.access_token is not None:
            result['access_token'] = self.access_token
        if self.refresh_token is not None:
            result['refresh_token'] = self.refresh_token
        if self.token_type is not None:
            result['token_type'] = self.token_type
        
        # OAuth2认证
        if self.client_id is not None:
            result['client_id'] = self.client_id
        if self.client_secret is not None:
            result['client_secret'] = self.client_secret
        if self.scope is not None:
            result['scope'] = self.scope
        if self.auth_url is not None:
            result['auth_url'] = self.auth_url
        if self.token_url is not None:
            result['token_url'] = self.token_url
        
        # 证书认证
        if self.cert_path is not None:
            result['cert_path'] = self.cert_path
        if self.key_path is not None:
            result['key_path'] = self.key_path
        if self.ca_path is not None:
            result['ca_path'] = self.ca_path
        
        # 时间戳
        if self.expires_at is not None:
            result['expires_at'] = self.expires_at.isoformat()
        if self.created_at is not None:
            result['created_at'] = self.created_at.isoformat()
        if self.last_refreshed_at is not None:
            result['last_refreshed_at'] = self.last_refreshed_at.isoformat()
        
        # 额外参数
        if self.extra_params is not None:
            result['extra_params'] = self.extra_params.copy()
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataSourceCredentials':
        """从字典创建凭据对象"""
        # 转换时间戳
        processed_data = data.copy()
        
        for time_field in ['expires_at', 'created_at', 'last_refreshed_at']:
            if time_field in processed_data and processed_data[time_field]:
                if isinstance(processed_data[time_field], str):
                    processed_data[time_field] = datetime.fromisoformat(processed_data[time_field])
        
        # 转换凭据类型
        if 'credential_type' in processed_data:
            if isinstance(processed_data['credential_type'], str):
                processed_data['credential_type'] = CredentialType(processed_data['credential_type'])
        
        return cls(**processed_data)
    
    @classmethod
    def create_username_password(cls, username: str, password_hash: str) -> 'DataSourceCredentials':
        """创建用户名密码凭据"""
        return cls(
            credential_type=CredentialType.USERNAME_PASSWORD,
            username=username,
            password_hash=password_hash
        )
    
    @classmethod
    def create_api_key(cls, api_key: str, api_secret: Optional[str] = None) -> 'DataSourceCredentials':
        """创建API密钥凭据"""
        return cls(
            credential_type=CredentialType.API_KEY,
            api_key=api_key,
            api_secret=api_secret
        )
    
    @classmethod
    def create_token(cls, 
                    access_token: str, 
                    token_type: str = "Bearer",
                    expires_at: Optional[datetime] = None,
                    refresh_token: Optional[str] = None) -> 'DataSourceCredentials':
        """创建Token凭据"""
        return cls(
            credential_type=CredentialType.TOKEN,
            access_token=access_token,
            token_type=token_type,
            expires_at=expires_at,
            refresh_token=refresh_token
        )
    
    @classmethod
    def create_oauth2(cls,
                     client_id: str,
                     client_secret: str,
                     auth_url: str,
                     token_url: str,
                     scope: Optional[str] = None,
                     access_token: Optional[str] = None,
                     expires_at: Optional[datetime] = None) -> 'DataSourceCredentials':
        """创建OAuth2凭据"""
        return cls(
            credential_type=CredentialType.OAUTH2,
            client_id=client_id,
            client_secret=client_secret,
            auth_url=auth_url,
            token_url=token_url,
            scope=scope,
            access_token=access_token,
            expires_at=expires_at
        )
    
    @classmethod
    def create_certificate(cls,
                          cert_path: str,
                          key_path: Optional[str] = None,
                          ca_path: Optional[str] = None) -> 'DataSourceCredentials':
        """创建证书凭据"""
        return cls(
            credential_type=CredentialType.CERTIFICATE,
            cert_path=cert_path,
            key_path=key_path,
            ca_path=ca_path
        )
    
    @classmethod
    def create_none(cls) -> 'DataSourceCredentials':
        """创建无需认证的凭据"""
        return cls(credential_type=CredentialType.NONE)
    
    def __str__(self) -> str:
        """字符串表示（安全版本）"""
        masked_data = self.mask_sensitive_data()
        return f"DataSourceCredentials({masked_data['credential_type']}, expires: {masked_data.get('expires_at', 'Never')})"