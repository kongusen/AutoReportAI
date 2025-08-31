"""
抽象LLM路由器
基于任务类型路由到抽象模型类型，具体模型配置从LLM服务获取
"""

import logging
import hashlib
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class AbstractModelType(Enum):
    """抽象模型类型枚举"""
    DEFAULT = "default"             # 默认处理 - 日常对话和基础任务
    BACKGROUND = "background"       # 后台任务 - 高质量分析，不限时间
    THINK = "think"                # 思考推理 - 复杂推理和深度分析  
    LONG_CONTEXT = "longContext"    # 长上下文 - 处理大量文本和长对话


class TaskComplexity(Enum):
    """任务复杂度枚举"""
    SIMPLE = "simple"
    MEDIUM = "medium" 
    HIGH = "high"
    VERY_HIGH = "very_high"


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high" 
    URGENT = "urgent"


@dataclass
class TaskContext:
    """任务上下文"""
    content: str                           # 任务内容
    agent_type: str = "general"           # Agent类型
    complexity: TaskComplexity = TaskComplexity.MEDIUM
    priority: TaskPriority = TaskPriority.NORMAL
    requires_reasoning: bool = False       # 是否需要深度推理
    requires_long_context: bool = False    # 是否需要长上下文
    is_background_task: bool = False       # 是否为后台任务
    user_id: str = "system"
    estimated_tokens: int = 1000
    time_constraint: Optional[float] = None
    
    def get_cache_key(self) -> str:
        """获取缓存键"""
        key_str = f"{self.agent_type}|{self.complexity.value}|{self.requires_reasoning}|{self.requires_long_context}"
        return hashlib.md5(key_str.encode()).hexdigest()


class AbstractLLMRouter:
    """
    抽象LLM路由器
    
    核心功能：
    1. 根据任务特征路由到抽象模型类型
    2. 具体模型配置从LLM服务获取
    3. 支持动态配置更新
    4. 性能统计和优化建议
    """
    
    def __init__(self):
        # 抽象模型类型路由规则
        self.routing_rules = self._build_routing_rules()
        
        # 性能统计
        self.usage_stats: Dict[str, Dict[str, Any]] = {}
        
        # 从LLM服务获取的模型配置缓存
        self.model_configs_cache: Optional[Dict[str, Any]] = None
        self.cache_timestamp: Optional[float] = None
        self.cache_ttl = 300  # 5分钟缓存
        
        logger.info("抽象LLM路由器初始化完成")
    
    def _build_routing_rules(self) -> Dict[str, List[AbstractModelType]]:
        """构建路由规则 - 任务类型到抽象模型类型的映射"""
        return {
            # Agent类型映射
            "general": [AbstractModelType.DEFAULT],
            "placeholder_expert": [AbstractModelType.THINK, AbstractModelType.DEFAULT], 
            "chart_specialist": [AbstractModelType.THINK, AbstractModelType.DEFAULT],
            "data_analyst": [AbstractModelType.THINK, AbstractModelType.DEFAULT],
            
            # 特殊任务类型
            "reasoning_task": [AbstractModelType.THINK],
            "background_analysis": [AbstractModelType.BACKGROUND],
            "long_document": [AbstractModelType.LONG_CONTEXT],
            
            # 复杂度路由
            "simple_task": [AbstractModelType.DEFAULT],
            "complex_reasoning": [AbstractModelType.THINK, AbstractModelType.BACKGROUND],
            "massive_context": [AbstractModelType.LONG_CONTEXT, AbstractModelType.BACKGROUND]
        }
    
    def route_to_abstract_model(self, task_context: TaskContext) -> AbstractModelType:
        """
        路由到抽象模型类型
        
        Args:
            task_context: 任务上下文
            
        Returns:
            选择的抽象模型类型
        """
        try:
            # 1. 基于特殊需求的优先路由
            if task_context.requires_long_context:
                logger.info(f"长上下文任务路由: {AbstractModelType.LONG_CONTEXT.value}")
                return AbstractModelType.LONG_CONTEXT
            
            if task_context.is_background_task:
                logger.info(f"后台任务路由: {AbstractModelType.BACKGROUND.value}")
                return AbstractModelType.BACKGROUND
            
            # 2. 基于推理需求和复杂度的路由
            if task_context.requires_reasoning or task_context.complexity in [TaskComplexity.HIGH, TaskComplexity.VERY_HIGH]:
                # 复杂推理任务
                if task_context.priority == TaskPriority.URGENT:
                    # 紧急任务可能需要在think和default之间权衡
                    abstract_type = AbstractModelType.THINK
                else:
                    # 非紧急的复杂任务用background获得最高质量
                    abstract_type = AbstractModelType.BACKGROUND if not task_context.time_constraint else AbstractModelType.THINK
                
                logger.info(f"推理任务路由: {abstract_type.value}")
                return abstract_type
            
            # 3. 基于Agent类型的默认路由
            agent_candidates = self.routing_rules.get(task_context.agent_type, [AbstractModelType.DEFAULT])
            
            if len(agent_candidates) == 1:
                selected = agent_candidates[0]
            else:
                # 多候选时根据任务特征选择
                selected = self._select_from_candidates(agent_candidates, task_context)
            
            logger.info(f"Agent {task_context.agent_type} 路由: {selected.value}")
            return selected
            
        except Exception as e:
            logger.error(f"路由失败: {e}，回退到默认模型")
            return AbstractModelType.DEFAULT
    
    def _select_from_candidates(
        self, 
        candidates: List[AbstractModelType], 
        task_context: TaskContext
    ) -> AbstractModelType:
        """从候选抽象模型中选择最佳的"""
        
        # 基于任务特征计算每个候选的得分
        scored_candidates = []
        
        for candidate in candidates:
            score = self._calculate_abstract_model_score(candidate, task_context)
            scored_candidates.append((candidate, score))
        
        # 按得分排序，选择最高分
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        return scored_candidates[0][0]
    
    def _calculate_abstract_model_score(
        self, 
        abstract_type: AbstractModelType, 
        task_context: TaskContext
    ) -> float:
        """计算抽象模型类型对任务的适合度得分"""
        score = 50.0  # 基础得分
        
        # 复杂度匹配得分
        if abstract_type == AbstractModelType.THINK:
            if task_context.complexity in [TaskComplexity.HIGH, TaskComplexity.VERY_HIGH]:
                score += 30
            elif task_context.complexity == TaskComplexity.MEDIUM:
                score += 20
            else:
                score += 10
                
        elif abstract_type == AbstractModelType.BACKGROUND:
            if task_context.complexity == TaskComplexity.VERY_HIGH:
                score += 40
            elif task_context.complexity == TaskComplexity.HIGH:
                score += 35
            else:
                score += 15
                
        elif abstract_type == AbstractModelType.DEFAULT:
            if task_context.complexity in [TaskComplexity.SIMPLE, TaskComplexity.MEDIUM]:
                score += 25
            else:
                score += 10
        
        # 优先级和时间约束得分
        if task_context.priority == TaskPriority.URGENT:
            if abstract_type == AbstractModelType.DEFAULT:
                score += 20  # 默认模型响应更快
            elif abstract_type == AbstractModelType.THINK:
                score += 15
            else:
                score -= 10  # 后台和长上下文模型可能较慢
        
        if task_context.time_constraint and task_context.time_constraint < 10:
            # 有严格时间约束
            if abstract_type == AbstractModelType.DEFAULT:
                score += 15
            elif abstract_type in [AbstractModelType.BACKGROUND, AbstractModelType.LONG_CONTEXT]:
                score -= 20
        
        # 基于历史性能调整得分
        performance_adjustment = self._get_performance_adjustment(abstract_type, task_context)
        score += performance_adjustment
        
        return score
    
    def _get_performance_adjustment(self, abstract_type: AbstractModelType, task_context: TaskContext) -> float:
        """基于历史性能调整得分"""
        stats_key = f"{abstract_type.value}_{task_context.agent_type}"
        
        if stats_key not in self.usage_stats:
            return 0.0
        
        stats = self.usage_stats[stats_key]
        
        # 基于成功率和响应时间调整
        success_rate = stats.get("success_rate", 0.8)
        avg_response_time = stats.get("avg_response_time", 3.0)
        
        adjustment = (success_rate - 0.8) * 20  # 成功率调整
        adjustment += max(0, (5 - avg_response_time) * 2)  # 响应时间调整
        
        return adjustment
    
    def get_model_config_for_abstract_type(self, abstract_type: AbstractModelType) -> Optional[Dict[str, Any]]:
        """
        从LLM服务获取抽象模型类型对应的具体模型配置
        
        这个方法应该从 backend/app/services/llm 获取配置
        """
        try:
            # 检查缓存
            import time
            current_time = time.time()
            if (self.model_configs_cache and self.cache_timestamp and 
                current_time - self.cache_timestamp < self.cache_ttl):
                config = self.model_configs_cache.get(abstract_type.value)
                if config:
                    return config
            
            # TODO: 这里应该从LLM服务的配置API获取路由配置
            # 目前使用默认映射作为示例
            default_mappings = {
                AbstractModelType.DEFAULT.value: {
                    "provider": "openai",
                    "model_name": "gpt-4o-mini",
                    "max_tokens": 4096,
                    "temperature": 0.3,
                    "description": "默认处理模型，快速响应"
                },
                AbstractModelType.BACKGROUND.value: {
                    "provider": "anthropic", 
                    "model_name": "claude-sonnet-4-20250514",
                    "max_tokens": 8192,
                    "temperature": 0.1,
                    "description": "后台高质量分析模型"
                },
                AbstractModelType.THINK.value: {
                    "provider": "openai",
                    "model_name": "gpt-4o",
                    "max_tokens": 8192,
                    "temperature": 0.2,
                    "description": "深度思考推理模型"
                },
                AbstractModelType.LONG_CONTEXT.value: {
                    "provider": "anthropic",
                    "model_name": "claude-sonnet-4-20250514", 
                    "max_tokens": 8192,
                    "temperature": 0.3,
                    "description": "长上下文处理模型"
                }
            }
            
            # 更新缓存
            self.model_configs_cache = default_mappings
            self.cache_timestamp = current_time
            
            return default_mappings.get(abstract_type.value)
            
        except Exception as e:
            logger.error(f"获取模型配置失败: {e}")
            return None
    
    def record_usage(
        self,
        abstract_type: AbstractModelType,
        task_context: TaskContext,
        success: bool,
        response_time: float
    ):
        """记录使用统计"""
        stats_key = f"{abstract_type.value}_{task_context.agent_type}"
        
        if stats_key not in self.usage_stats:
            self.usage_stats[stats_key] = {
                "total_requests": 0,
                "successful_requests": 0,
                "total_response_time": 0.0,
                "avg_response_time": 0.0,
                "success_rate": 0.0
            }
        
        stats = self.usage_stats[stats_key]
        stats["total_requests"] += 1
        stats["total_response_time"] += response_time
        
        if success:
            stats["successful_requests"] += 1
        
        # 更新统计指标
        stats["avg_response_time"] = stats["total_response_time"] / stats["total_requests"]
        stats["success_rate"] = stats["successful_requests"] / stats["total_requests"]
        
        logger.debug(f"记录使用统计: {stats_key} - 成功率: {stats['success_rate']:.2f}")
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """获取路由统计信息"""
        total_requests = sum(stats.get("total_requests", 0) for stats in self.usage_stats.values())
        
        abstract_model_stats = {}
        for abstract_type in AbstractModelType:
            type_requests = sum(
                stats.get("total_requests", 0) 
                for key, stats in self.usage_stats.items() 
                if key.startswith(abstract_type.value)
            )
            abstract_model_stats[abstract_type.value] = type_requests
        
        return {
            "total_requests": total_requests,
            "abstract_model_usage": abstract_model_stats,
            "detailed_stats": self.usage_stats,
            "routing_rules": {k: [t.value for t in v] for k, v in self.routing_rules.items()},
            "cache_status": {
                "cached": self.model_configs_cache is not None,
                "cache_timestamp": self.cache_timestamp,
                "cache_ttl": self.cache_ttl
            }
        }
    
    def update_routing_rules(self, new_rules: Dict[str, List[str]]):
        """动态更新路由规则"""
        try:
            converted_rules = {}
            for key, abstract_types in new_rules.items():
                converted_rules[key] = [AbstractModelType(t) for t in abstract_types]
            
            self.routing_rules.update(converted_rules)
            logger.info(f"更新路由规则: {list(new_rules.keys())}")
            
        except Exception as e:
            logger.error(f"更新路由规则失败: {e}")
    
    def clear_cache(self):
        """清除模型配置缓存"""
        self.model_configs_cache = None
        self.cache_timestamp = None
        logger.info("模型配置缓存已清除")


# 全局路由器实例
_global_abstract_router: Optional[AbstractLLMRouter] = None


def get_abstract_llm_router() -> AbstractLLMRouter:
    """获取全局抽象LLM路由器实例"""
    global _global_abstract_router
    if _global_abstract_router is None:
        _global_abstract_router = AbstractLLMRouter()
    return _global_abstract_router


# 便捷函数
def route_task_to_abstract_model(
    content: str,
    agent_type: str = "general",
    **kwargs
) -> tuple[AbstractModelType, Optional[Dict[str, Any]]]:
    """
    将任务路由到抽象模型类型并获取配置
    
    Returns:
        (抽象模型类型, 模型配置)
    """
    router = get_abstract_llm_router()
    
    # 创建任务上下文
    task_context = TaskContext(
        content=content,
        agent_type=agent_type,
        **kwargs
    )
    
    # 路由到抽象模型类型
    abstract_type = router.route_to_abstract_model(task_context)
    
    # 获取模型配置
    model_config = router.get_model_config_for_abstract_type(abstract_type)
    
    return abstract_type, model_config


def analyze_task_requirements(content: str) -> Dict[str, bool]:
    """分析任务需求特征"""
    content_lower = content.lower()
    
    return {
        "requires_reasoning": any(keyword in content_lower for keyword in [
            "分析", "推理", "解释", "原因", "为什么", "逻辑", "因果", "推导"
        ]),
        "requires_long_context": len(content) > 8000 or "长文" in content_lower or "大量" in content_lower,
        "is_background_task": any(keyword in content_lower for keyword in [
            "详细分析", "深入研究", "全面报告", "后台", "批量"
        ])
    }