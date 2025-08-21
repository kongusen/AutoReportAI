"""
Task Domain Service

任务领域服务，包含纯业务逻辑
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from ..entities.task_entity import (
    TaskEntity, TaskStatus, TaskPriority, ExecutionMode,
    ScheduleConfig, TaskExecution
)

logger = logging.getLogger(__name__)


class TaskDomainService:
    """任务领域服务"""
    
    def __init__(self):
        self.validation_rules = self._create_default_validation_rules()
    
    def create_task(self, task_id: str, name: str, task_type: str,
                   configuration: Dict[str, Any] = None,
                   owner_id: Optional[str] = None) -> TaskEntity:
        """创建新任务"""
        task = TaskEntity(task_id, name, task_type)
        
        if configuration:
            task.update_configuration(configuration)
        
        if owner_id:
            task.owner_id = owner_id
            task.created_by = owner_id
        
        # 根据任务类型设置默认配置
        self._apply_default_configuration(task)
        
        # 验证任务
        validation_errors = self.validate_task(task)
        if validation_errors:
            raise ValueError(f"Task validation failed: {validation_errors}")
        
        logger.info(f"Created task: {name} ({task_type})")
        return task
    
    def validate_task(self, task: TaskEntity) -> List[str]:
        """验证任务"""
        errors = task.validate()
        
        # 添加领域特定验证规则
        for rule in self.validation_rules:
            rule_errors = rule(task)
            errors.extend(rule_errors)
        
        return errors
    
    def configure_schedule(self, task: TaskEntity, cron_expression: str,
                         timezone: str = "UTC", 
                         max_retries: int = 3) -> ScheduleConfig:
        """配置任务调度"""
        schedule_config = ScheduleConfig(
            cron_expression=cron_expression,
            timezone=timezone,
            max_retries=max_retries
        )
        
        if not schedule_config.is_valid():
            raise ValueError("Invalid cron expression")
        
        task.set_schedule(schedule_config)
        return schedule_config
    
    def plan_execution(self, task: TaskEntity, execution_mode: ExecutionMode,
                      context: Dict[str, Any] = None) -> Dict[str, Any]:
        """规划任务执行"""
        execution_plan = {
            "task_id": task.id,
            "execution_mode": execution_mode.value,
            "planned_at": datetime.utcnow().isoformat(),
            "context": context or {},
            "prerequisites": [],
            "estimated_duration": None,
            "resource_requirements": {}
        }
        
        # 检查执行前置条件
        prerequisites = self._check_execution_prerequisites(task)
        execution_plan["prerequisites"] = prerequisites
        
        # 估算执行时间
        estimated_duration = self._estimate_execution_duration(task)
        execution_plan["estimated_duration"] = estimated_duration
        
        # 确定资源需求
        resource_requirements = self._determine_resource_requirements(task)
        execution_plan["resource_requirements"] = resource_requirements
        
        return execution_plan
    
    def analyze_task_performance(self, task: TaskEntity) -> Dict[str, Any]:
        """分析任务性能"""
        analysis = {
            "task_id": task.id,
            "total_executions": task.total_executions,
            "success_rate": task.get_success_rate(),
            "average_execution_time": task.get_average_execution_time(),
            "performance_trend": "stable",
            "issues": [],
            "recommendations": []
        }
        
        # 性能趋势分析
        if len(task.executions) >= 5:
            recent_executions = sorted(task.executions, key=lambda e: e.started_at or datetime.min)[-5:]
            performance_trend = self._analyze_performance_trend(recent_executions)
            analysis["performance_trend"] = performance_trend
        
        # 识别问题
        issues = self._identify_performance_issues(task)
        analysis["issues"] = issues
        
        # 生成建议
        recommendations = self._generate_performance_recommendations(task, issues)
        analysis["recommendations"] = recommendations
        
        return analysis
    
    def calculate_next_run_time(self, task: TaskEntity) -> Optional[datetime]:
        """计算下次运行时间"""
        if not task.can_be_scheduled():
            return None
        
        # 这里应该使用专门的cron表达式解析库
        # 简化实现，实际项目中应使用croniter等库
        from datetime import datetime, timedelta
        
        # 简化的逻辑，实际应根据cron表达式计算
        if task.schedule_config.cron_expression == "0 * * * *":  # 每小时
            return datetime.utcnow() + timedelta(hours=1)
        elif task.schedule_config.cron_expression == "0 0 * * *":  # 每天
            return datetime.utcnow() + timedelta(days=1)
        
        return None
    
    def should_retry_execution(self, execution: TaskExecution, 
                             max_retries: int = 3) -> bool:
        """判断是否应该重试执行"""
        if execution.status != TaskStatus.FAILED:
            return False
        
        # 检查重试次数（这里需要从上下文或数据库中获取）
        retry_count = execution.context.get("retry_count", 0)
        return retry_count < max_retries
    
    def _apply_default_configuration(self, task: TaskEntity):
        """应用默认配置"""
        if task.task_type == "report_generation":
            default_config = {
                "enable_caching": True,
                "timeout_seconds": 3600,
                "execution_mode": "smart",
                "retry_on_failure": True
            }
            task.update_configuration(default_config)
        
        elif task.task_type == "data_analysis":
            default_config = {
                "sample_size": 10000,
                "analysis_depth": "standard",
                "enable_profiling": True
            }
            task.update_configuration(default_config)
    
    def _create_default_validation_rules(self) -> List[callable]:
        """创建默认验证规则"""
        def check_name_uniqueness(task: TaskEntity) -> List[str]:
            # 实际实现中需要检查数据库
            return []
        
        def check_resource_availability(task: TaskEntity) -> List[str]:
            errors = []
            
            # 检查模板是否存在
            if task.template_id and task.task_type == "report_generation":
                # 实际实现中需要检查模板服务
                pass
            
            # 检查数据源是否存在
            if task.data_source_id:
                # 实际实现中需要检查数据源服务
                pass
            
            return errors
        
        def check_schedule_conflicts(task: TaskEntity) -> List[str]:
            # 检查调度冲突
            return []
        
        return [check_name_uniqueness, check_resource_availability, check_schedule_conflicts]
    
    def _check_execution_prerequisites(self, task: TaskEntity) -> List[str]:
        """检查执行前置条件"""
        prerequisites = []
        
        if not task.is_active:
            prerequisites.append("Task must be active")
        
        if task.is_running():
            prerequisites.append("Previous execution must be completed")
        
        if task.task_type == "report_generation":
            if not task.template_id:
                prerequisites.append("Template must be specified")
            if not task.data_source_id:
                prerequisites.append("Data source must be specified")
        
        return prerequisites
    
    def _estimate_execution_duration(self, task: TaskEntity) -> Optional[float]:
        """估算执行时间"""
        avg_time = task.get_average_execution_time()
        if avg_time is not None:
            return avg_time
        
        # 基于任务类型的默认估算
        if task.task_type == "report_generation":
            return 300.0  # 5分钟
        elif task.task_type == "data_analysis":
            return 180.0  # 3分钟
        
        return 120.0  # 默认2分钟
    
    def _determine_resource_requirements(self, task: TaskEntity) -> Dict[str, Any]:
        """确定资源需求"""
        requirements = {
            "cpu_cores": 1,
            "memory_mb": 512,
            "storage_mb": 100,
            "network_bandwidth": "standard"
        }
        
        # 根据任务类型和配置调整资源需求
        if task.task_type == "report_generation":
            requirements["memory_mb"] = 1024
            requirements["storage_mb"] = 500
        
        return requirements
    
    def _analyze_performance_trend(self, executions: List[TaskExecution]) -> str:
        """分析性能趋势"""
        if len(executions) < 3:
            return "insufficient_data"
        
        # 计算最近几次执行时间的趋势
        times = [e.execution_time_seconds for e in executions if e.execution_time_seconds]
        if len(times) < 3:
            return "insufficient_data"
        
        # 简单的趋势分析
        first_half_avg = sum(times[:len(times)//2]) / (len(times)//2)
        second_half_avg = sum(times[len(times)//2:]) / (len(times) - len(times)//2)
        
        if second_half_avg > first_half_avg * 1.2:
            return "degrading"
        elif second_half_avg < first_half_avg * 0.8:
            return "improving"
        else:
            return "stable"
    
    def _identify_performance_issues(self, task: TaskEntity) -> List[Dict[str, Any]]:
        """识别性能问题"""
        issues = []
        
        # 成功率过低
        if task.get_success_rate() < 0.8:
            issues.append({
                "type": "low_success_rate",
                "severity": "high",
                "message": f"Success rate is {task.get_success_rate():.1%}, below 80% threshold"
            })
        
        # 执行时间过长
        avg_time = task.get_average_execution_time()
        if avg_time and avg_time > 1800:  # 30分钟
            issues.append({
                "type": "long_execution_time",
                "severity": "medium",
                "message": f"Average execution time is {avg_time:.1f} seconds"
            })
        
        # 频繁失败
        if task.failed_executions >= 3 and len(task.executions) >= 5:
            failure_rate = task.failed_executions / len(task.executions)
            if failure_rate > 0.4:
                issues.append({
                    "type": "frequent_failures",
                    "severity": "high",
                    "message": f"Failure rate is {failure_rate:.1%}"
                })
        
        return issues
    
    def _generate_performance_recommendations(self, task: TaskEntity, 
                                           issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成性能建议"""
        recommendations = []
        
        for issue in issues:
            if issue["type"] == "low_success_rate":
                recommendations.append({
                    "type": "increase_monitoring",
                    "priority": "high",
                    "action": "Add more detailed logging and error handling",
                    "impact": "Improve debugging and success rate"
                })
            
            elif issue["type"] == "long_execution_time":
                recommendations.append({
                    "type": "optimize_performance",
                    "priority": "medium",
                    "action": "Enable caching and optimize data processing",
                    "impact": "Reduce execution time"
                })
            
            elif issue["type"] == "frequent_failures":
                recommendations.append({
                    "type": "improve_reliability",
                    "priority": "high",
                    "action": "Implement better error handling and retry mechanisms",
                    "impact": "Reduce failure rate"
                })
        
        # 通用建议
        if task.total_executions > 10 and not task.schedule_config:
            recommendations.append({
                "type": "enable_scheduling",
                "priority": "low",
                "action": "Consider enabling scheduled execution",
                "impact": "Automate task execution"
            })
        
        return recommendations