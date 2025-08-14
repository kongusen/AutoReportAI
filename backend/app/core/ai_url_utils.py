"""
AI提供商URL智能处理工具
自动处理和标准化AI API的URL格式
"""

from typing import Optional
from urllib.parse import urljoin, urlparse


class AIUrlHandler:
    """AI提供商URL智能处理器"""
    
    # 标准的AI提供商端点路径
    STANDARD_ENDPOINTS = {
        'openai': '/v1/chat/completions',
        'azure_openai': '/openai/deployments/{deployment}/chat/completions',
        'anthropic': '/v1/messages',
        'google': '/v1beta/models/{model}:generateContent'
    }
    
    # 已知的AI提供商域名模式
    KNOWN_PROVIDERS = {
        'api.openai.com': 'openai',
        'xiaoai.com': 'openai',  # xiaoai使用OpenAI兼容接口
        'api.anthropic.com': 'anthropic',
        'generativelanguage.googleapis.com': 'google',
        'openai.azure.com': 'azure_openai'
    }
    
    @classmethod
    def normalize_url(cls, base_url: str, provider_type: str = None) -> str:
        """
        智能标准化AI提供商URL
        
        规则：
        1. 如果URL已包含完整路径（如/v1/chat/completions），直接返回
        2. 如果URL只是域名或基础路径，自动添加标准端点
        3. 支持自动检测提供商类型
        
        Args:
            base_url: 原始URL
            provider_type: 提供商类型（可选，用于自动检测）
            
        Returns:
            标准化后的完整URL
        """
        if not base_url:
            return base_url
            
        # 解析URL
        parsed = urlparse(base_url)
        
        # 如果没有协议，默认添加https
        if not parsed.scheme:
            base_url = f"https://{base_url}"
            parsed = urlparse(base_url)
        
        # 自动检测提供商类型
        if not provider_type:
            provider_type = cls._detect_provider_type(parsed.netloc)
        
        # 检查是否已经包含完整的API路径
        if cls._has_complete_api_path(parsed.path):
            return base_url
        
        # 获取标准端点路径
        endpoint_path = cls._get_standard_endpoint(provider_type)
        if not endpoint_path:
            # 如果不是已知提供商，假设是OpenAI兼容的
            endpoint_path = cls.STANDARD_ENDPOINTS['openai']
        
        # 构建完整URL
        base_without_path = f"{parsed.scheme}://{parsed.netloc}"
        if parsed.port:
            base_without_path = f"{parsed.scheme}://{parsed.netloc}:{parsed.port}"
            
        # 处理基础路径
        base_path = parsed.path.rstrip('/')
        if base_path and not base_path.startswith('/v1'):
            # 如果有基础路径但不是/v1开头，保留它
            full_url = urljoin(base_without_path + base_path, endpoint_path.lstrip('/'))
        else:
            full_url = base_without_path + endpoint_path
            
        return full_url
    
    @classmethod
    def _detect_provider_type(cls, netloc: str) -> Optional[str]:
        """根据域名检测提供商类型"""
        netloc_lower = netloc.lower()
        
        for domain, provider in cls.KNOWN_PROVIDERS.items():
            if domain in netloc_lower:
                return provider
                
        # 检查Azure OpenAI的模式
        if 'openai.azure.com' in netloc_lower:
            return 'azure_openai'
            
        return None
    
    @classmethod
    def _has_complete_api_path(cls, path: str) -> bool:
        """检查路径是否已包含完整的API端点"""
        path_lower = path.lower()
        
        # 检查常见的完整API路径
        complete_paths = [
            '/v1/chat/completions',
            '/v1/messages',
            '/v1/completions',
            'chat/completions',
            'generatecontent',
            'openai/deployments'
        ]
        
        return any(complete_path in path_lower for complete_path in complete_paths)
    
    @classmethod
    def _get_standard_endpoint(cls, provider_type: str) -> Optional[str]:
        """获取标准端点路径"""
        return cls.STANDARD_ENDPOINTS.get(provider_type)
    
    @classmethod
    def validate_url(cls, url: str) -> dict:
        """
        验证URL的有效性
        
        Returns:
            验证结果字典，包含：
            - is_valid: 是否有效
            - provider_type: 检测到的提供商类型
            - normalized_url: 标准化后的URL
            - issues: 发现的问题列表
        """
        issues = []
        
        if not url:
            return {
                'is_valid': False,
                'provider_type': None,
                'normalized_url': None,
                'issues': ['URL不能为空']
            }
        
        try:
            parsed = urlparse(url)
            
            # 检查基本格式
            if not parsed.netloc:
                issues.append('URL格式无效，缺少域名')
            
            # 检测提供商类型
            provider_type = cls._detect_provider_type(parsed.netloc)
            if not provider_type:
                issues.append('未识别的AI提供商域名')
            
            # 标准化URL
            normalized_url = cls.normalize_url(url, provider_type)
            
            return {
                'is_valid': len(issues) == 0,
                'provider_type': provider_type,
                'normalized_url': normalized_url,
                'issues': issues
            }
            
        except Exception as e:
            return {
                'is_valid': False,
                'provider_type': None,
                'normalized_url': None,
                'issues': [f'URL解析错误: {str(e)}']
            }


def normalize_ai_provider_url(base_url: str, provider_type: str = None) -> str:
    """
    便捷函数：标准化AI提供商URL
    
    示例:
    - "xiaoai.com" -> "https://xiaoai.com/v1/chat/completions"
    - "https://xiaoai.com" -> "https://xiaoai.com/v1/chat/completions"
    - "https://xiaoai.com/v1/chat/completions" -> "https://xiaoai.com/v1/chat/completions"
    - "https://api.openai.com" -> "https://api.openai.com/v1/chat/completions"
    """
    return AIUrlHandler.normalize_url(base_url, provider_type)


def validate_ai_provider_url(url: str) -> dict:
    """
    便捷函数：验证AI提供商URL
    """
    return AIUrlHandler.validate_url(url)