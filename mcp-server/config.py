"""
AutoReportAI MCP Server Configuration
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """MCP服务器配置管理"""
    
    # 后端API配置
    BACKEND_BASE_URL: str = os.getenv("BACKEND_BASE_URL", "http://localhost:8000/api/v1")
    BACKEND_TIMEOUT: int = int(os.getenv("BACKEND_TIMEOUT", "30"))
    
    # 默认管理员配置
    DEFAULT_ADMIN_USERNAME: str = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD: str = os.getenv("DEFAULT_ADMIN_PASSWORD", "password")
    
    # MCP服务器配置
    MCP_SERVER_HOST: str = os.getenv("MCP_SERVER_HOST", "localhost")
    MCP_SERVER_PORT: int = int(os.getenv("MCP_SERVER_PORT", "8001"))
    
    # 会话配置
    SESSION_TIMEOUT: int = int(os.getenv("SESSION_TIMEOUT", "3600"))  # 1小时
    MAX_SESSIONS: int = int(os.getenv("MAX_SESSIONS", "100"))
    
    # 文件上传配置
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "50")) * 1024 * 1024  # 50MB
    ALLOWED_FILE_EXTENSIONS: list = [
        ".csv", ".xlsx", ".xls", ".docx", ".doc", ".html", ".htm", ".pdf", ".txt"
    ]
    
    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "mcp-server.log")
    
    # 数据库连接池配置
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    
    @classmethod
    def get_backend_headers(cls, token: str = None) -> Dict[str, str]:
        """获取后端API请求头"""
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers
    
    @classmethod
    def validate_file_extension(cls, filename: str) -> bool:
        """验证文件扩展名"""
        if not filename:
            return False
        ext = os.path.splitext(filename.lower())[1]
        return ext in cls.ALLOWED_FILE_EXTENSIONS
    
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "backend_base_url": cls.BACKEND_BASE_URL,
            "backend_timeout": cls.BACKEND_TIMEOUT,
            "session_timeout": cls.SESSION_TIMEOUT,
            "max_sessions": cls.MAX_SESSIONS,
            "max_file_size": cls.MAX_FILE_SIZE,
            "allowed_extensions": cls.ALLOWED_FILE_EXTENSIONS,
            "log_level": cls.LOG_LEVEL
        }

# 全局配置实例
config = Config()