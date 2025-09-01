"""
Domain层数据源实体

数据源的核心业务实体，包含数据源的业务逻辑和规则：

核心职责：
1. 封装数据源的核心业务属性
2. 实现数据源的业务规则和验证
3. 提供数据源操作的业务方法
4. 维护数据源状态的一致性

Domain层实体特点：
- 包含核心业务逻辑
- 独立于技术实现
- 封装业务规则
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import re

logger = logging.getLogger(__name__)


class DataSourceType(Enum):
    """数据源类型"""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql" 
    DORIS = "doris"
    CLICKHOUSE = "clickhouse"
    ORACLE = "oracle"
    SQLSERVER = "sqlserver"
    MONGODB = "mongodb"
    REDIS = "redis"
    ELASTICSEARCH = "elasticsearch"
    API = "api"
    FILE = "file"
    UNKNOWN = "unknown"


class DataSourceStatus(Enum):
    """数据源状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TESTING = "testing"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    DEPRECATED = "deprecated"


class DataSourceEntity:
    """
    Domain层数据源实体
    
    封装数据源的核心业务逻辑：
    1. 数据源基本信息和配置
    2. 连接状态和健康检查
    3. 业务规则和验证逻辑
    4. 权限和安全策略
    """
    
    def __init__(self, 
                 source_id: str,
                 name: str,
                 source_type: DataSourceType,
                 connection_config: Dict[str, Any],
                 description: str = "",
                 tags: List[str] = None,
                 owner_id: str = None,
                 created_by: str = None):
        
        # 业务验证
        self._validate_business_rules(name, source_type, connection_config)
        
        # 核心属性
        self.source_id = source_id
        self.name = name
        self.source_type = source_type
        self.connection_config = connection_config
        self.description = description
        self.tags = tags or []
        self.owner_id = owner_id
        self.created_by = created_by
        
        # 状态管理
        self.status = DataSourceStatus.INACTIVE
        self.is_active = True
        self.last_test_time = None
        self.last_test_result = None
        self.last_error = None
        
        # 时间戳
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.last_accessed_at = None
        
        # 使用统计
        self.access_count = 0
        self.success_count = 0
        self.error_count = 0
        
        # 性能指标
        self.average_response_time = 0.0
        self.max_response_time = 0.0
        self.min_response_time = float('inf')
        
        logger.info(f"创建数据源实体: {name} ({source_type.value})")
    
    def _validate_business_rules(self, 
                                name: str, 
                                source_type: DataSourceType, 
                                connection_config: Dict[str, Any]):
        """验证业务规则"""
        
        # 名称验证
        if not name or not name.strip():
            raise ValueError("数据源名称不能为空")
        
        if len(name) > 100:
            raise ValueError("数据源名称长度不能超过100字符")
        
        # 名称格式验证（只允许字母、数字、下划线、中划线）
        if not re.match(r'^[a-zA-Z0-9_\-\u4e00-\u9fa5]+$', name):
            raise ValueError("数据源名称只能包含字母、数字、下划线、中划线和中文字符")
        
        # 类型验证
        if source_type == DataSourceType.UNKNOWN:
            raise ValueError("数据源类型不能为未知")
        
        # 连接配置验证
        if not connection_config:
            raise ValueError("连接配置不能为空")
        
        # 根据类型验证必需的配置项
        self._validate_connection_config_by_type(source_type, connection_config)
    
    def _validate_connection_config_by_type(self, 
                                          source_type: DataSourceType, 
                                          config: Dict[str, Any]):
        """根据数据源类型验证连接配置"""
        
        if source_type in [DataSourceType.MYSQL, DataSourceType.POSTGRESQL]:
            required_fields = ['host', 'port', 'database', 'username']
            for field in required_fields:
                if field not in config or not config[field]:
                    raise ValueError(f"{source_type.value}数据源缺少必需的配置项: {field}")
            
            # 端口号验证
            port = config.get('port')
            if not isinstance(port, int) or port <= 0 or port > 65535:
                raise ValueError("端口号必须是1-65535之间的整数")
        
        elif source_type == DataSourceType.DORIS:
            required_fields = ['doris_fe_hosts', 'doris_username', 'doris_database']
            for field in required_fields:
                if field not in config or not config[field]:
                    raise ValueError(f"Doris数据源缺少必需的配置项: {field}")
            
            # FE hosts验证
            fe_hosts = config.get('doris_fe_hosts')
            if not isinstance(fe_hosts, list) or len(fe_hosts) == 0:
                raise ValueError("doris_fe_hosts必须是非空列表")
        
        elif source_type == DataSourceType.API:
            required_fields = ['base_url']
            for field in required_fields:
                if field not in config or not config[field]:
                    raise ValueError(f"API数据源缺少必需的配置项: {field}")
            
            # URL格式验证
            base_url = config.get('base_url')
            if not base_url.startswith(('http://', 'https://')):
                raise ValueError("API base_url必须以http://或https://开头")
    
    def update_configuration(self, new_config: Dict[str, Any]) -> bool:
        """更新连接配置"""
        try:
            # 验证新配置
            self._validate_connection_config_by_type(self.source_type, new_config)
            
            # 更新配置
            self.connection_config.update(new_config)
            self.updated_at = datetime.utcnow()
            
            logger.info(f"数据源配置已更新: {self.name}")
            return True
            
        except Exception as e:
            logger.error(f"更新数据源配置失败: {self.name}, 错误: {e}")
            return False
    
    def test_connection(self, response_time: float = None) -> bool:
        """测试连接（业务逻辑）"""
        self.last_test_time = datetime.utcnow()
        
        try:
            # 这里是业务逻辑，实际连接测试由Infrastructure层实现
            # Domain层只负责状态管理和业务规则
            
            if response_time is not None:
                self.update_performance_metrics(response_time, success=True)
            
            self.status = DataSourceStatus.ACTIVE
            self.last_test_result = "success"
            self.last_error = None
            self.success_count += 1
            
            logger.info(f"数据源连接测试成功: {self.name}")
            return True
            
        except Exception as e:
            self.status = DataSourceStatus.ERROR
            self.last_test_result = "failed"
            self.last_error = str(e)
            self.error_count += 1
            
            logger.error(f"数据源连接测试失败: {self.name}, 错误: {e}")
            return False
    
    def record_access(self, response_time: float = None, success: bool = True):
        """记录访问"""
        self.access_count += 1
        self.last_accessed_at = datetime.utcnow()
        
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
        
        if response_time is not None:
            self.update_performance_metrics(response_time, success)
        
        logger.debug(f"记录数据源访问: {self.name}, 成功: {success}")
    
    def update_performance_metrics(self, response_time: float, success: bool):
        """更新性能指标"""
        if success and response_time > 0:
            # 更新平均响应时间
            total_success = self.success_count
            if total_success > 0:
                self.average_response_time = (
                    (self.average_response_time * (total_success - 1) + response_time) / total_success
                )
            else:
                self.average_response_time = response_time
            
            # 更新最大和最小响应时间
            self.max_response_time = max(self.max_response_time, response_time)
            self.min_response_time = min(self.min_response_time, response_time)
    
    def set_maintenance_mode(self, maintenance: bool):
        """设置维护模式"""
        if maintenance:
            self.status = DataSourceStatus.MAINTENANCE
            logger.info(f"数据源进入维护模式: {self.name}")
        else:
            self.status = DataSourceStatus.ACTIVE
            logger.info(f"数据源退出维护模式: {self.name}")
        
        self.updated_at = datetime.utcnow()
    
    def mark_deprecated(self, reason: str = ""):
        """标记为已废弃"""
        self.status = DataSourceStatus.DEPRECATED
        self.is_active = False
        self.updated_at = datetime.utcnow()
        
        if reason:
            self.description = f"{self.description}\n[DEPRECATED] {reason}".strip()
        
        logger.info(f"数据源已标记为废弃: {self.name}, 原因: {reason}")
    
    def can_execute_query(self) -> bool:
        """检查是否可以执行查询"""
        if not self.is_active:
            return False
        
        if self.status in [DataSourceStatus.MAINTENANCE, DataSourceStatus.DEPRECATED, DataSourceStatus.ERROR]:
            return False
        
        # 业务规则：如果错误率过高，暂时禁用
        if self.access_count > 0:
            error_rate = self.error_count / self.access_count
            if error_rate > 0.5:  # 错误率超过50%
                logger.warning(f"数据源错误率过高，禁止查询: {self.name}, 错误率: {error_rate:.2%}")
                return False
        
        return True
    
    def requires_authentication(self) -> bool:
        """检查是否需要认证"""
        # 根据数据源类型和配置确定是否需要认证
        if self.source_type == DataSourceType.API:
            return 'api_key' in self.connection_config or 'auth_token' in self.connection_config
        
        if self.source_type in [DataSourceType.MYSQL, DataSourceType.POSTGRESQL, DataSourceType.DORIS]:
            return 'username' in self.connection_config
        
        return False
    
    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        # 计算健康分数
        health_score = 1.0
        issues = []
        
        # 检查连接状态
        if self.status != DataSourceStatus.ACTIVE:
            health_score -= 0.4
            issues.append(f"状态不正常: {self.status.value}")
        
        # 检查错误率
        if self.access_count > 0:
            error_rate = self.error_count / self.access_count
            if error_rate > 0.1:  # 错误率超过10%
                health_score -= 0.3
                issues.append(f"错误率较高: {error_rate:.2%}")
        
        # 检查最近是否有访问
        if self.last_accessed_at:
            time_since_last_access = (datetime.utcnow() - self.last_accessed_at).total_seconds()
            if time_since_last_access > 86400:  # 超过24小时未访问
                health_score -= 0.2
                issues.append("长时间未使用")
        
        # 检查响应时间
        if self.average_response_time > 5.0:  # 平均响应时间超过5秒
            health_score -= 0.1
            issues.append(f"响应时间较慢: {self.average_response_time:.2f}s")
        
        health_score = max(0, health_score)
        
        return {
            "health_score": health_score,
            "status": self.status.value,
            "is_healthy": health_score > 0.7,
            "issues": issues,
            "last_test_time": self.last_test_time.isoformat() if self.last_test_time else None,
            "last_test_result": self.last_test_result,
            "performance": {
                "access_count": self.access_count,
                "success_count": self.success_count,
                "error_count": self.error_count,
                "success_rate": self.success_count / max(self.access_count, 1),
                "average_response_time": self.average_response_time,
                "max_response_time": self.max_response_time,
                "min_response_time": self.min_response_time if self.min_response_time != float('inf') else 0
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        return {
            "source_id": self.source_id,
            "name": self.name,
            "source_type": self.source_type.value,
            "description": self.description,
            "tags": self.tags,
            "owner_id": self.owner_id,
            "created_by": self.created_by,
            "status": self.status.value,
            "is_active": self.is_active,
            "connection_config": self.connection_config,  # 注意：敏感信息应该在序列化时过滤
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "last_test_time": self.last_test_time.isoformat() if self.last_test_time else None,
            "last_test_result": self.last_test_result,
            "performance_metrics": {
                "access_count": self.access_count,
                "success_count": self.success_count,
                "error_count": self.error_count,
                "average_response_time": self.average_response_time
            }
        }
    
    def __str__(self) -> str:
        return f"DataSource({self.name}, {self.source_type.value}, {self.status.value})"
    
    def __repr__(self) -> str:
        return (f"DataSourceEntity(source_id='{self.source_id}', name='{self.name}', "
                f"type={self.source_type}, status={self.status})")