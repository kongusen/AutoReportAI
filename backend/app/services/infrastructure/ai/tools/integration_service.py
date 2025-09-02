"""
AI工具集成服务

负责React Agent工具的智能选择、组合和优化使用

核心职责：
- 基于任务类型智能选择最佳工具组合
- 管理工具间的协作和数据流
- 监控工具使用效果和性能
- 提供工具使用建议和优化
"""

import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

from app.core.exceptions import (
    ValidationError,
    LLMServiceError,
    ContentGenerationError
)
from .registry import AIToolsRegistry, ToolCategory, ToolComplexity
from .factory import AIToolsFactory

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """任务类型"""
    DATA_ANALYSIS = "data_analysis"
    TEMPLATE_PROCESSING = "template_processing"
    REPORT_GENERATION = "report_generation"
    SCHEMA_ANALYSIS = "schema_analysis"
    QUERY_OPTIMIZATION = "query_optimization"
    ETL_PROCESSING = "etl_processing"
    PERFORMANCE_TUNING = "performance_tuning"
    QUALITY_CHECKING = "quality_checking"


@dataclass
class ToolRecommendation:
    """工具推荐"""
    tool_name: str
    confidence: float
    reason: str
    category: ToolCategory
    estimated_performance: float


class AIToolsIntegrationService:
    """
    AI工具集成服务
    
    为React Agent提供智能工具选择和组合服务
    """
    
    def __init__(self, user_id: str):
        if not user_id:
            raise ValueError("user_id is required for AI Tools Integration Service")
        
        self.user_id = user_id
        self.registry = AIToolsRegistry()
        self.factory = AIToolsFactory(self.registry)
        
        # 任务-工具映射配置
        self.task_tool_mapping = self._initialize_task_tool_mapping()
        
        # 用户偏好跟踪
        self.user_tool_preferences = {}
        self.tool_performance_history = {}
        
        logger.info(f"AI工具集成服务初始化完成 - 用户: {user_id}")
    
    def _initialize_task_tool_mapping(self) -> Dict[TaskType, List[str]]:
        """初始化任务-工具映射"""
        return {
            TaskType.DATA_ANALYSIS: [
                "data_executor", "calculator", "result_validator", 
                "data_source_analyzer", "performance_optimizer"
            ],
            TaskType.TEMPLATE_PROCESSING: [
                "placeholder_parser", "template_processor", "context_analyzer", "formatter"
            ],
            TaskType.REPORT_GENERATION: [
                "template_processor", "report_quality_checker", "formatter", 
                "chart_generator", "business_processor"
            ],
            TaskType.SCHEMA_ANALYSIS: [
                "schema_inspector", "data_source_analyzer", "context_analyzer", "result_validator"
            ],
            TaskType.QUERY_OPTIMIZATION: [
                "sql_generator", "performance_optimizer", "data_executor", "result_validator"
            ],
            TaskType.ETL_PROCESSING: [
                "data_executor", "business_processor", "result_validator", "performance_optimizer"
            ],
            TaskType.PERFORMANCE_TUNING: [
                "performance_optimizer", "data_source_analyzer", "schema_inspector"
            ],
            TaskType.QUALITY_CHECKING: [
                "result_validator", "report_quality_checker", "schema_inspector"
            ]
        }
    
    async def recommend_tools_for_task(
        self, 
        task_type: TaskType, 
        task_context: Dict[str, Any] = None,
        max_tools: int = 5
    ) -> List[ToolRecommendation]:
        """
        为特定任务推荐最佳工具组合
        
        Args:
            task_type: 任务类型
            task_context: 任务上下文
            max_tools: 最大推荐工具数量
            
        Returns:
            工具推荐列表
        """
        try:
            # 获取基础工具列表
            base_tools = self.task_tool_mapping.get(task_type, [])
            
            recommendations = []
            
            for tool_name in base_tools[:max_tools]:
                # 获取工具元数据
                metadata = self.registry.get_tool_metadata(tool_name)
                if not metadata:
                    continue
                
                # 计算推荐置信度
                confidence = self._calculate_tool_confidence(
                    tool_name, task_type, task_context
                )
                
                # 估算性能
                estimated_performance = self._estimate_tool_performance(
                    tool_name, task_context
                )
                
                # 生成推荐理由
                reason = self._generate_recommendation_reason(
                    tool_name, task_type, metadata
                )
                
                recommendations.append(ToolRecommendation(
                    tool_name=tool_name,
                    confidence=confidence,
                    reason=reason,
                    category=metadata.category,
                    estimated_performance=estimated_performance
                ))
            
            # 按置信度排序
            recommendations.sort(key=lambda x: x.confidence, reverse=True)
            
            logger.info(f"为任务 {task_type.value} 推荐了 {len(recommendations)} 个工具")
            return recommendations
            
        except Exception as e:
            logger.error(f"工具推荐失败: {e}")
            return []
    
    async def create_optimized_tool_set(
        self, 
        task_type: TaskType,
        task_context: Dict[str, Any] = None
    ) -> List[Any]:
        """
        创建优化的工具集合
        
        Args:
            task_type: 任务类型
            task_context: 任务上下文
            
        Returns:
            优化的工具实例列表
        """
        try:
            # 获取工具推荐
            recommendations = await self.recommend_tools_for_task(
                task_type, task_context
            )
            
            # 创建工具实例
            tools = []
            for rec in recommendations:
                try:
                    tool = self.factory.create_tool_by_name(rec.tool_name)
                    tools.append(tool)
                except Exception as e:
                    logger.warning(f"创建工具 {rec.tool_name} 失败: {e}")
                    continue
            
            logger.info(f"为任务 {task_type.value} 创建了 {len(tools)} 个工具")
            return tools
            
        except Exception as e:
            logger.error(f"创建优化工具集合失败: {e}")
            return []
    
    def _calculate_tool_confidence(
        self, 
        tool_name: str, 
        task_type: TaskType, 
        context: Dict[str, Any] = None
    ) -> float:
        """计算工具推荐置信度"""
        base_confidence = 0.7
        
        # 基于历史使用情况调整
        if tool_name in self.tool_performance_history:
            historical_performance = self.tool_performance_history[tool_name].get("average_score", 0.7)
            base_confidence = (base_confidence + historical_performance) / 2
        
        # 基于用户偏好调整
        if tool_name in self.user_tool_preferences:
            preference_score = self.user_tool_preferences[tool_name]
            base_confidence = (base_confidence + preference_score) / 2
        
        # 基于上下文调整
        if context:
            complexity = context.get("complexity", "medium")
            if complexity == "high":
                metadata = self.registry.get_tool_metadata(tool_name)
                if metadata and metadata.complexity in [ToolComplexity.HIGH, ToolComplexity.VERY_HIGH]:
                    base_confidence += 0.1
        
        return min(1.0, max(0.1, base_confidence))
    
    def _estimate_tool_performance(
        self, 
        tool_name: str, 
        context: Dict[str, Any] = None
    ) -> float:
        """估算工具性能"""
        # 基础性能评分
        base_performance = 0.8
        
        # 基于工具复杂度调整
        metadata = self.registry.get_tool_metadata(tool_name)
        if metadata:
            if metadata.complexity == ToolComplexity.LOW:
                base_performance += 0.1
            elif metadata.complexity == ToolComplexity.VERY_HIGH:
                base_performance -= 0.1
        
        # 基于历史性能调整
        if tool_name in self.tool_performance_history:
            historical_performance = self.tool_performance_history[tool_name].get("average_performance", 0.8)
            base_performance = (base_performance + historical_performance) / 2
        
        return min(1.0, max(0.1, base_performance))
    
    def _generate_recommendation_reason(
        self, 
        tool_name: str, 
        task_type: TaskType, 
        metadata
    ) -> str:
        """生成推荐理由"""
        reasons = []
        
        # 基于类别匹配
        if task_type == TaskType.DATA_ANALYSIS and metadata.category == ToolCategory.DATA_PROCESSING:
            reasons.append("专为数据分析任务设计")
        elif task_type == TaskType.TEMPLATE_PROCESSING and "template" in tool_name:
            reasons.append("专门的模板处理工具")
        elif task_type == TaskType.SCHEMA_ANALYSIS and "schema" in tool_name:
            reasons.append("专业的Schema分析工具")
        
        # 基于复杂度匹配
        if metadata.complexity == ToolComplexity.HIGH:
            reasons.append("高级功能适合复杂任务")
        elif metadata.complexity == ToolComplexity.LOW:
            reasons.append("轻量级工具，执行效率高")
        
        # 基于历史表现
        if tool_name in self.tool_performance_history:
            avg_score = self.tool_performance_history[tool_name].get("average_score", 0.7)
            if avg_score > 0.8:
                reasons.append("历史表现优秀")
        
        return "; ".join(reasons) if reasons else "通用推荐工具"
    
    def record_tool_usage(
        self, 
        tool_name: str, 
        task_type: TaskType,
        performance_score: float,
        execution_time: float
    ):
        """记录工具使用情况"""
        try:
            if tool_name not in self.tool_performance_history:
                self.tool_performance_history[tool_name] = {
                    "usage_count": 0,
                    "total_score": 0.0,
                    "total_time": 0.0,
                    "average_score": 0.0,
                    "average_time": 0.0,
                    "last_used": None
                }
            
            history = self.tool_performance_history[tool_name]
            history["usage_count"] += 1
            history["total_score"] += performance_score
            history["total_time"] += execution_time
            history["average_score"] = history["total_score"] / history["usage_count"]
            history["average_time"] = history["total_time"] / history["usage_count"]
            history["last_used"] = datetime.utcnow().isoformat()
            
            # 更新用户偏好
            if performance_score > 0.8:
                current_preference = self.user_tool_preferences.get(tool_name, 0.5)
                self.user_tool_preferences[tool_name] = min(1.0, current_preference + 0.1)
            elif performance_score < 0.5:
                current_preference = self.user_tool_preferences.get(tool_name, 0.5)
                self.user_tool_preferences[tool_name] = max(0.1, current_preference - 0.1)
            
            logger.debug(f"记录工具使用: {tool_name}, 性能: {performance_score:.2f}")
            
        except Exception as e:
            logger.error(f"记录工具使用失败: {e}")
    
    def get_user_tool_analytics(self) -> Dict[str, Any]:
        """获取用户工具使用分析"""
        total_usage = sum(
            history["usage_count"] 
            for history in self.tool_performance_history.values()
        )
        
        # 最常用工具
        most_used_tools = sorted(
            self.tool_performance_history.items(),
            key=lambda x: x[1]["usage_count"],
            reverse=True
        )[:5]
        
        # 最高性能工具
        best_performance_tools = sorted(
            self.tool_performance_history.items(),
            key=lambda x: x[1]["average_score"],
            reverse=True
        )[:5]
        
        return {
            "user_id": self.user_id,
            "total_tool_usage": total_usage,
            "unique_tools_used": len(self.tool_performance_history),
            "most_used_tools": [
                {"tool": name, "usage_count": data["usage_count"], "avg_score": data["average_score"]}
                for name, data in most_used_tools
            ],
            "best_performance_tools": [
                {"tool": name, "avg_score": data["average_score"], "usage_count": data["usage_count"]}
                for name, data in best_performance_tools
            ],
            "user_preferences": self.user_tool_preferences,
            "analytics_generated_at": datetime.utcnow().isoformat()
        }
    
    async def optimize_tool_selection_for_user(
        self, 
        task_type: TaskType,
        performance_requirements: Dict[str, Any] = None
    ) -> List[str]:
        """
        为用户优化工具选择
        
        Args:
            task_type: 任务类型
            performance_requirements: 性能要求
            
        Returns:
            优化的工具名称列表
        """
        try:
            # 获取推荐工具
            recommendations = await self.recommend_tools_for_task(task_type)
            
            # 应用性能要求过滤
            if performance_requirements:
                min_performance = performance_requirements.get("min_performance", 0.6)
                recommendations = [
                    rec for rec in recommendations 
                    if rec.estimated_performance >= min_performance
                ]
            
            # 考虑用户偏好
            for rec in recommendations:
                if rec.tool_name in self.user_tool_preferences:
                    preference = self.user_tool_preferences[rec.tool_name]
                    rec.confidence = (rec.confidence + preference) / 2
            
            # 重新排序
            recommendations.sort(key=lambda x: x.confidence, reverse=True)
            
            optimized_tools = [rec.tool_name for rec in recommendations]
            
            logger.info(f"为用户 {self.user_id} 优化工具选择: {optimized_tools}")
            return optimized_tools
            
        except Exception as e:
            logger.error(f"优化工具选择失败: {e}")
            return []
    
    def get_integration_status(self) -> Dict[str, Any]:
        """获取集成状态"""
        registry_stats = self.registry.get_statistics()
        factory_info = self.factory.get_factory_info()
        
        return {
            "service_name": "AI Tools Integration Service",
            "user_id": self.user_id,
            "version": "1.0.0",
            "status": "active",
            "registry_status": {
                "total_tools": registry_stats["total_tools"],
                "active_tools": registry_stats["active_tools"],
                "total_usage": registry_stats["total_usage"]
            },
            "factory_status": {
                "llamaindex_available": factory_info["llamaindex_available"],
                "total_builders": factory_info["total_builders"],
                "cached_tools": factory_info["cached_tools"]
            },
            "user_analytics": {
                "tools_used": len(self.tool_performance_history),
                "preferences_count": len(self.user_tool_preferences),
                "total_usage": sum(
                    h["usage_count"] for h in self.tool_performance_history.values()
                )
            },
            "supported_task_types": [t.value for t in TaskType],
            "status_checked_at": datetime.utcnow().isoformat()
        }


# Factory function for AI Tools Integration Service
def create_ai_tools_integration_service(user_id: str) -> AIToolsIntegrationService:
    """创建AI工具集成服务"""
    return AIToolsIntegrationService(user_id)