"""
Domain层数据源领域服务

提供数据源相关的核心业务逻辑和规则：

核心职责：
1. 数据源的业务逻辑协调
2. 复杂的数据源规则处理
3. 数据源生命周期管理
4. 数据源权限和安全策略

Domain层服务特点：
- 包含核心业务逻辑
- 协调实体和值对象
- 不依赖外部基础设施
- 可被Application层调用
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import re

from ..entities.data_source_entity import (
    DataSourceEntity, 
    DataSourceType, 
    DataSourceStatus
)
from ..value_objects.connection_config import ConnectionConfig
from ..value_objects.data_source_credentials import (
    DataSourceCredentials, 
    CredentialType
)

logger = logging.getLogger(__name__)


class DataSourceValidationError(Exception):
    """数据源验证错误"""
    pass


class DataSourceBusinessRuleError(Exception):
    """数据源业务规则错误"""
    pass


class DataSourceDomainService:
    """
    Domain层数据源领域服务
    
    核心职责：
    1. 执行复杂的数据源业务逻辑
    2. 验证数据源业务规则
    3. 协调数据源实体和值对象
    4. 提供数据源专业领域能力
    
    Domain层定位：
    - 包含核心业务逻辑
    - 独立于技术实现
    - 可被Application层调用
    """
    
    def __init__(self):
        # 业务规则配置
        self.max_connections_per_type = {
            DataSourceType.MYSQL: 100,
            DataSourceType.POSTGRESQL: 100,
            DataSourceType.DORIS: 50,
            DataSourceType.CLICKHOUSE: 80,
            DataSourceType.MONGODB: 60,
            DataSourceType.API: 200
        }
        
        self.default_timeouts = {
            DataSourceType.MYSQL: 30,
            DataSourceType.POSTGRESQL: 30,
            DataSourceType.DORIS: 60,
            DataSourceType.CLICKHOUSE: 45,
            DataSourceType.MONGODB: 30,
            DataSourceType.API: 10
        }
        
        # 安全策略
        self.password_policy = {
            'min_length': 8,
            'require_uppercase': True,
            'require_lowercase': True,
            'require_numbers': True,
            'require_special_chars': False,
            'forbidden_patterns': ['123456', 'password', 'admin']
        }
        
        logger.info("数据源领域服务初始化完成")
    
    def create_data_source(self,
                          source_id: str,
                          name: str,
                          source_type: DataSourceType,
                          connection_config: Dict[str, Any],
                          credentials: Optional[DataSourceCredentials] = None,
                          description: str = "",
                          tags: List[str] = None,
                          owner_id: str = None) -> DataSourceEntity:
        """
        创建数据源（执行业务逻辑）
        
        Args:
            source_id: 数据源ID
            name: 数据源名称
            source_type: 数据源类型
            connection_config: 连接配置
            credentials: 认证凭据
            description: 描述
            tags: 标签
            owner_id: 所有者ID
            
        Returns:
            数据源实体
        """
        # 1. 业务规则验证
        self._validate_creation_rules(name, source_type, connection_config)
        
        # 2. 增强连接配置
        enhanced_config = self._enhance_connection_config(source_type, connection_config)
        
        # 3. 验证凭据
        if credentials:
            self._validate_credentials_for_source_type(source_type, credentials)
        
        # 4. 创建实体
        try:
            data_source = DataSourceEntity(
                source_id=source_id,
                name=name,
                source_type=source_type,
                connection_config=enhanced_config,
                description=description,
                tags=tags or [],
                owner_id=owner_id
            )
            
            # 5. 应用业务规则
            self._apply_creation_business_rules(data_source)
            
            logger.info(f"数据源创建成功: {name} ({source_type.value})")
            return data_source
            
        except Exception as e:
            logger.error(f"数据源创建失败: {name}, 错误: {e}")
            raise DataSourceBusinessRuleError(f"数据源创建失败: {e}")
    
    def validate_data_source_configuration(self,
                                         source_type: DataSourceType,
                                         connection_config: Dict[str, Any],
                                         credentials: Optional[DataSourceCredentials] = None) -> Tuple[bool, List[str]]:
        """
        验证数据源配置的完整性和正确性
        
        Args:
            source_type: 数据源类型
            connection_config: 连接配置
            credentials: 认证凭据
            
        Returns:
            (验证是否通过, 错误信息列表)
        """
        errors = []
        
        try:
            # 1. 基本配置验证
            config_obj = ConnectionConfig.from_dict(connection_config)
            
            # 2. 特定类型验证
            type_errors = self._validate_type_specific_config(source_type, config_obj)
            errors.extend(type_errors)
            
            # 3. 凭据验证
            if credentials:
                cred_errors = self._validate_credentials_for_source_type(source_type, credentials)
                errors.extend(cred_errors)
            
            # 4. 安全验证
            security_errors = self._validate_security_requirements(source_type, connection_config)
            errors.extend(security_errors)
            
            # 5. 性能配置验证
            performance_errors = self._validate_performance_config(source_type, config_obj)
            errors.extend(performance_errors)
            
            is_valid = len(errors) == 0
            
            if is_valid:
                logger.info(f"数据源配置验证通过: {source_type.value}")
            else:
                logger.warning(f"数据源配置验证失败: {source_type.value}, 错误: {errors}")
            
            return is_valid, errors
            
        except Exception as e:
            logger.error(f"配置验证异常: {e}")
            return False, [f"配置验证异常: {str(e)}"]
    
    def analyze_data_source_health(self, data_source: DataSourceEntity) -> Dict[str, Any]:
        """
        分析数据源健康状况
        
        Args:
            data_source: 数据源实体
            
        Returns:
            健康分析结果
        """
        health_analysis = {
            'overall_health': 'unknown',
            'health_score': 0.0,
            'issues': [],
            'recommendations': [],
            'risk_level': 'low',
            'analysis_time': datetime.utcnow().isoformat()
        }
        
        try:
            # 1. 基础健康检查
            basic_health = data_source.get_health_status()
            health_analysis.update(basic_health)
            
            # 2. 业务规则健康检查
            business_issues = self._check_business_health_rules(data_source)
            health_analysis['issues'].extend(business_issues)
            
            # 3. 性能健康检查
            performance_issues = self._check_performance_health(data_source)
            health_analysis['issues'].extend(performance_issues)
            
            # 4. 安全健康检查
            security_issues = self._check_security_health(data_source)
            health_analysis['issues'].extend(security_issues)
            
            # 5. 生成建议
            recommendations = self._generate_health_recommendations(data_source, health_analysis['issues'])
            health_analysis['recommendations'] = recommendations
            
            # 6. 计算风险等级
            risk_level = self._calculate_risk_level(health_analysis['health_score'], health_analysis['issues'])
            health_analysis['risk_level'] = risk_level
            
            # 7. 确定总体健康状况
            if health_analysis['health_score'] > 0.8:
                health_analysis['overall_health'] = 'excellent'
            elif health_analysis['health_score'] > 0.6:
                health_analysis['overall_health'] = 'good'
            elif health_analysis['health_score'] > 0.4:
                health_analysis['overall_health'] = 'fair'
            else:
                health_analysis['overall_health'] = 'poor'
            
            logger.info(f"数据源健康分析完成: {data_source.name}, 健康分数: {health_analysis['health_score']:.2f}")
            
            return health_analysis
            
        except Exception as e:
            logger.error(f"数据源健康分析失败: {data_source.name}, 错误: {e}")
            health_analysis.update({
                'overall_health': 'error',
                'health_score': 0.0,
                'issues': [f"健康分析失败: {str(e)}"],
                'risk_level': 'high'
            })
            return health_analysis
    
    def recommend_configuration_optimization(self, data_source: DataSourceEntity) -> Dict[str, Any]:
        """
        推荐配置优化方案
        
        Args:
            data_source: 数据源实体
            
        Returns:
            优化建议
        """
        optimization_recommendations = {
            'performance_optimizations': [],
            'security_enhancements': [],
            'reliability_improvements': [],
            'cost_optimizations': [],
            'priority_level': 'medium',
            'estimated_impact': 'moderate',
            'implementation_effort': 'medium'
        }
        
        try:
            # 1. 性能优化建议
            perf_recommendations = self._analyze_performance_optimization(data_source)
            optimization_recommendations['performance_optimizations'] = perf_recommendations
            
            # 2. 安全增强建议
            security_recommendations = self._analyze_security_enhancement(data_source)
            optimization_recommendations['security_enhancements'] = security_recommendations
            
            # 3. 可靠性改进建议
            reliability_recommendations = self._analyze_reliability_improvement(data_source)
            optimization_recommendations['reliability_improvements'] = reliability_recommendations
            
            # 4. 成本优化建议
            cost_recommendations = self._analyze_cost_optimization(data_source)
            optimization_recommendations['cost_optimizations'] = cost_recommendations
            
            # 5. 评估优先级和影响
            priority, impact, effort = self._evaluate_optimization_priority(optimization_recommendations)
            optimization_recommendations.update({
                'priority_level': priority,
                'estimated_impact': impact,
                'implementation_effort': effort
            })
            
            logger.info(f"配置优化分析完成: {data_source.name}")
            
            return optimization_recommendations
            
        except Exception as e:
            logger.error(f"配置优化分析失败: {data_source.name}, 错误: {e}")
            return {
                'error': str(e),
                'performance_optimizations': [],
                'security_enhancements': [],
                'reliability_improvements': [],
                'cost_optimizations': []
            }
    
    def validate_data_source_migration(self,
                                     source_data_source: DataSourceEntity,
                                     target_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证数据源迁移的可行性
        
        Args:
            source_data_source: 源数据源
            target_config: 目标配置
            
        Returns:
            迁移验证结果
        """
        migration_analysis = {
            'is_feasible': False,
            'compatibility_score': 0.0,
            'migration_risks': [],
            'required_changes': [],
            'estimated_downtime': 'unknown',
            'data_loss_risk': 'low',
            'rollback_plan': []
        }
        
        try:
            # 1. 配置兼容性检查
            compatibility_score = self._check_migration_compatibility(source_data_source, target_config)
            migration_analysis['compatibility_score'] = compatibility_score
            
            # 2. 识别迁移风险
            risks = self._identify_migration_risks(source_data_source, target_config)
            migration_analysis['migration_risks'] = risks
            
            # 3. 分析必需的变更
            required_changes = self._analyze_required_changes(source_data_source, target_config)
            migration_analysis['required_changes'] = required_changes
            
            # 4. 评估停机时间
            downtime = self._estimate_migration_downtime(source_data_source, target_config)
            migration_analysis['estimated_downtime'] = downtime
            
            # 5. 评估数据丢失风险
            data_loss_risk = self._assess_data_loss_risk(source_data_source, target_config)
            migration_analysis['data_loss_risk'] = data_loss_risk
            
            # 6. 生成回滚计划
            rollback_plan = self._generate_rollback_plan(source_data_source, target_config)
            migration_analysis['rollback_plan'] = rollback_plan
            
            # 7. 综合评估可行性
            migration_analysis['is_feasible'] = (
                compatibility_score > 0.7 and
                data_loss_risk != 'high' and
                len([r for r in risks if r.get('severity') == 'critical']) == 0
            )
            
            logger.info(f"迁移验证完成: {source_data_source.name}, 可行性: {migration_analysis['is_feasible']}")
            
            return migration_analysis
            
        except Exception as e:
            logger.error(f"迁移验证失败: {source_data_source.name}, 错误: {e}")
            migration_analysis.update({
                'is_feasible': False,
                'error': str(e)
            })
            return migration_analysis
    
    # 私有辅助方法
    
    def _validate_creation_rules(self, 
                               name: str, 
                               source_type: DataSourceType, 
                               connection_config: Dict[str, Any]):
        """验证创建规则"""
        
        # 名称唯一性检查（这里是业务逻辑，实际检查由Repository执行）
        if not name or len(name.strip()) == 0:
            raise DataSourceValidationError("数据源名称不能为空")
        
        # 名称长度和格式检查
        if len(name) > 100:
            raise DataSourceValidationError("数据源名称长度不能超过100字符")
        
        if not re.match(r'^[a-zA-Z0-9_\-\u4e00-\u9fa5\s]+$', name.strip()):
            raise DataSourceValidationError("数据源名称包含非法字符")
        
        # 类型支持检查
        if source_type == DataSourceType.UNKNOWN:
            raise DataSourceValidationError("不支持未知类型的数据源")
        
        # 配置基本验证
        if not connection_config:
            raise DataSourceValidationError("连接配置不能为空")
    
    def _enhance_connection_config(self, 
                                 source_type: DataSourceType, 
                                 config: Dict[str, Any]) -> Dict[str, Any]:
        """增强连接配置（应用默认值和优化）"""
        
        enhanced_config = config.copy()
        
        # 应用类型特定的默认值
        if source_type in self.default_timeouts:
            enhanced_config.setdefault('connection_timeout', self.default_timeouts[source_type])
            enhanced_config.setdefault('query_timeout', self.default_timeouts[source_type] * 10)
        
        if source_type in self.max_connections_per_type:
            enhanced_config.setdefault('max_connections', min(
                enhanced_config.get('max_connections', 10),
                self.max_connections_per_type[source_type]
            ))
        
        # 应用安全默认值
        enhanced_config.setdefault('use_ssl', True)
        enhanced_config.setdefault('pool_pre_ping', True)
        enhanced_config.setdefault('max_retries', 3)
        enhanced_config.setdefault('retry_delay', 1.0)
        
        return enhanced_config
    
    def _validate_credentials_for_source_type(self, 
                                            source_type: DataSourceType, 
                                            credentials: DataSourceCredentials) -> List[str]:
        """验证凭据与数据源类型的兼容性"""
        errors = []
        
        if source_type in [DataSourceType.MYSQL, DataSourceType.POSTGRESQL, DataSourceType.DORIS]:
            if credentials.credential_type != CredentialType.USERNAME_PASSWORD:
                errors.append(f"{source_type.value}数据源需要用户名密码认证")
        
        elif source_type == DataSourceType.API:
            if credentials.credential_type not in [CredentialType.API_KEY, CredentialType.TOKEN, CredentialType.OAUTH2]:
                errors.append("API数据源需要API密钥、Token或OAuth2认证")
        
        # 检查凭据是否过期
        if credentials.is_expired():
            errors.append("认证凭据已过期")
        
        return errors
    
    def _apply_creation_business_rules(self, data_source: DataSourceEntity):
        """应用创建时的业务规则"""
        
        # 设置初始状态
        data_source.status = DataSourceStatus.INACTIVE
        
        # 根据类型设置默认标签
        if not data_source.tags:
            type_tags = {
                DataSourceType.MYSQL: ['database', 'sql', 'mysql'],
                DataSourceType.POSTGRESQL: ['database', 'sql', 'postgresql'],
                DataSourceType.DORIS: ['database', 'olap', 'doris'],
                DataSourceType.API: ['api', 'rest', 'external']
            }
            data_source.tags = type_tags.get(data_source.source_type, ['database'])
    
    def _validate_type_specific_config(self, source_type: DataSourceType, config: ConnectionConfig) -> List[str]:
        """验证特定类型的配置"""
        errors = []
        
        if source_type == DataSourceType.DORIS:
            if not config.doris_fe_hosts or len(config.doris_fe_hosts) == 0:
                errors.append("Doris数据源必须配置FE主机列表")
        
        elif source_type == DataSourceType.API:
            if not config.base_url:
                errors.append("API数据源必须配置基础URL")
        
        return errors
    
    def _validate_security_requirements(self, source_type: DataSourceType, config: Dict[str, Any]) -> List[str]:
        """验证安全要求"""
        errors = []
        
        # 生产环境安全检查
        if not config.get('use_ssl', False) and source_type in [DataSourceType.MYSQL, DataSourceType.POSTGRESQL]:
            errors.append("建议在生产环境启用SSL连接")
        
        return errors
    
    def _validate_performance_config(self, source_type: DataSourceType, config: ConnectionConfig) -> List[str]:
        """验证性能配置"""
        errors = []
        
        # 连接数检查
        max_allowed = self.max_connections_per_type.get(source_type, 50)
        if config.max_connections > max_allowed:
            errors.append(f"{source_type.value}数据源最大连接数不应超过{max_allowed}")
        
        # 超时检查
        if config.connection_timeout > 300:  # 5分钟
            errors.append("连接超时时间过长，建议不超过300秒")
        
        return errors
    
    def _check_business_health_rules(self, data_source: DataSourceEntity) -> List[str]:
        """检查业务健康规则"""
        issues = []
        
        # 检查是否长时间未使用
        if data_source.last_accessed_at:
            unused_days = (datetime.utcnow() - data_source.last_accessed_at).days
            if unused_days > 30:
                issues.append(f"数据源已{unused_days}天未使用，建议检查是否还需要")
        
        # 检查标签完整性
        if not data_source.tags or len(data_source.tags) == 0:
            issues.append("数据源缺少标签，不利于分类管理")
        
        # 检查描述信息
        if not data_source.description or len(data_source.description.strip()) < 10:
            issues.append("数据源缺少详细描述信息")
        
        return issues
    
    def _check_performance_health(self, data_source: DataSourceEntity) -> List[str]:
        """检查性能健康状况"""
        issues = []
        
        if data_source.average_response_time > 10.0:  # 超过10秒
            issues.append(f"平均响应时间过长: {data_source.average_response_time:.2f}秒")
        
        if data_source.access_count > 0:
            error_rate = data_source.error_count / data_source.access_count
            if error_rate > 0.1:  # 错误率超过10%
                issues.append(f"错误率偏高: {error_rate:.2%}")
        
        return issues
    
    def _check_security_health(self, data_source: DataSourceEntity) -> List[str]:
        """检查安全健康状况"""
        issues = []
        
        # 检查SSL配置
        if not data_source.connection_config.get('use_ssl', False):
            issues.append("未启用SSL加密，存在安全风险")
        
        # 检查认证配置
        if not data_source.requires_authentication():
            issues.append("未配置认证，存在安全风险")
        
        return issues
    
    def _generate_health_recommendations(self, data_source: DataSourceEntity, issues: List[str]) -> List[str]:
        """生成健康建议"""
        recommendations = []
        
        for issue in issues:
            if "响应时间过长" in issue:
                recommendations.append("建议优化查询性能或增加连接池大小")
            elif "错误率偏高" in issue:
                recommendations.append("建议检查网络连接和服务器状态")
            elif "未使用" in issue:
                recommendations.append("建议评估是否需要保留此数据源")
            elif "SSL" in issue:
                recommendations.append("建议启用SSL加密保护数据传输")
        
        return list(set(recommendations))  # 去重
    
    def _calculate_risk_level(self, health_score: float, issues: List[str]) -> str:
        """计算风险等级"""
        
        if health_score < 0.3:
            return 'critical'
        elif health_score < 0.5:
            return 'high'
        elif health_score < 0.7:
            return 'medium'
        else:
            critical_issues = sum(1 for issue in issues if any(
                keyword in issue.lower() for keyword in ['ssl', 'security', 'authentication']
            ))
            if critical_issues > 0:
                return 'high'
            return 'low'
    
    def _analyze_performance_optimization(self, data_source: DataSourceEntity) -> List[Dict[str, Any]]:
        """分析性能优化机会"""
        optimizations = []
        
        if data_source.average_response_time > 5.0:
            optimizations.append({
                'type': 'connection_pool',
                'description': '增加连接池大小以提高并发性能',
                'current_value': data_source.connection_config.get('max_connections', 10),
                'recommended_value': min(50, data_source.connection_config.get('max_connections', 10) * 2),
                'expected_improvement': '30-50%响应时间改善'
            })
        
        if data_source.connection_config.get('pool_pre_ping', True) == False:
            optimizations.append({
                'type': 'pool_settings',
                'description': '启用连接池预检查以减少连接错误',
                'current_value': False,
                'recommended_value': True,
                'expected_improvement': '减少连接失败率'
            })
        
        return optimizations
    
    def _analyze_security_enhancement(self, data_source: DataSourceEntity) -> List[Dict[str, Any]]:
        """分析安全增强机会"""
        enhancements = []
        
        if not data_source.connection_config.get('use_ssl', False):
            enhancements.append({
                'type': 'ssl_encryption',
                'description': '启用SSL加密保护数据传输',
                'risk_level': 'high',
                'implementation_effort': 'low'
            })
        
        return enhancements
    
    def _analyze_reliability_improvement(self, data_source: DataSourceEntity) -> List[Dict[str, Any]]:
        """分析可靠性改进机会"""
        improvements = []
        
        if data_source.connection_config.get('max_retries', 0) < 3:
            improvements.append({
                'type': 'retry_policy',
                'description': '优化重试策略以提高连接可靠性',
                'current_value': data_source.connection_config.get('max_retries', 0),
                'recommended_value': 3
            })
        
        return improvements
    
    def _analyze_cost_optimization(self, data_source: DataSourceEntity) -> List[Dict[str, Any]]:
        """分析成本优化机会"""
        optimizations = []
        
        # 如果长时间未使用，建议考虑资源优化
        if data_source.last_accessed_at:
            unused_days = (datetime.utcnow() - data_source.last_accessed_at).days
            if unused_days > 7:
                optimizations.append({
                    'type': 'resource_optimization',
                    'description': f'数据源{unused_days}天未使用，建议评估是否需要保留',
                    'potential_savings': 'medium'
                })
        
        return optimizations
    
    def _evaluate_optimization_priority(self, recommendations: Dict[str, List]) -> Tuple[str, str, str]:
        """评估优化建议的优先级"""
        
        total_recommendations = sum(len(recs) for recs in recommendations.values())
        
        if total_recommendations == 0:
            return 'low', 'minimal', 'minimal'
        elif total_recommendations < 3:
            return 'medium', 'moderate', 'low'
        elif total_recommendations < 6:
            return 'high', 'significant', 'medium'
        else:
            return 'urgent', 'major', 'high'
    
    def _check_migration_compatibility(self, source: DataSourceEntity, target_config: Dict[str, Any]) -> float:
        """检查迁移兼容性"""
        # 简化的兼容性评分逻辑
        compatibility_score = 0.5  # 基础分数
        
        # 如果是相同类型，兼容性更高
        target_type = target_config.get('source_type')
        if target_type and target_type == source.source_type.value:
            compatibility_score += 0.3
        
        return min(1.0, compatibility_score)
    
    def _identify_migration_risks(self, source: DataSourceEntity, target_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """识别迁移风险"""
        risks = []
        
        # 类型变更风险
        target_type = target_config.get('source_type')
        if target_type and target_type != source.source_type.value:
            risks.append({
                'type': 'type_change',
                'description': f'数据源类型从{source.source_type.value}变更为{target_type}',
                'severity': 'high',
                'mitigation': '需要重新测试所有依赖的查询和应用'
            })
        
        return risks
    
    def _analyze_required_changes(self, source: DataSourceEntity, target_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """分析必需的变更"""
        changes = []
        
        # 配置变更分析
        for key, target_value in target_config.items():
            if key in source.connection_config:
                current_value = source.connection_config[key]
                if current_value != target_value:
                    changes.append({
                        'field': key,
                        'current_value': current_value,
                        'target_value': target_value,
                        'impact': 'medium'
                    })
        
        return changes
    
    def _estimate_migration_downtime(self, source: DataSourceEntity, target_config: Dict[str, Any]) -> str:
        """估算迁移停机时间"""
        # 简化的停机时间估算
        if target_config.get('source_type') != source.source_type.value:
            return '2-4小时'  # 类型变更需要更多时间
        else:
            return '30分钟-1小时'  # 配置变更
    
    def _assess_data_loss_risk(self, source: DataSourceEntity, target_config: Dict[str, Any]) -> str:
        """评估数据丢失风险"""
        # 如果只是配置变更，数据丢失风险较低
        if target_config.get('source_type') == source.source_type.value:
            return 'low'
        else:
            return 'medium'  # 类型变更可能需要数据转换
    
    def _generate_rollback_plan(self, source: DataSourceEntity, target_config: Dict[str, Any]) -> List[str]:
        """生成回滚计划"""
        rollback_steps = [
            '1. 停止使用新配置',
            '2. 恢复原始连接配置',
            '3. 验证连接正常',
            '4. 通知相关应用恢复正常使用'
        ]
        
        return rollback_steps
    
    def get_domain_service_info(self) -> Dict[str, Any]:
        """获取领域服务信息"""
        return {
            'service_name': 'DataSourceDomainService',
            'version': '1.0.0-ddd',
            'architecture': 'DDD Domain Layer',
            'supported_types': [t.value for t in DataSourceType if t != DataSourceType.UNKNOWN],
            'business_rules': {
                'max_connections_per_type': {k.value: v for k, v in self.max_connections_per_type.items()},
                'default_timeouts': {k.value: v for k, v in self.default_timeouts.items()},
                'password_policy': self.password_policy
            },
            'capabilities': [
                'data_source_creation_with_business_rules',
                'configuration_validation',
                'health_analysis',
                'optimization_recommendations',
                'migration_feasibility_analysis'
            ]
        }