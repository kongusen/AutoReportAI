"""
多上下文集成系统

基于AutoReportAI Agent设计的核心功能：
5. 多上下文集成流程: 数据源上下文 + 任务上下文 + 模板上下文 + 时间上下文的智能融合

特性：
- 上下文感知：智能识别和分析各种上下文信息
- 动态融合：根据任务需求动态组合上下文
- 语义理解：深度理解上下文间的关联关系
- 优先级管理：根据重要性和相关性排序上下文
- 增量更新：支持上下文的实时更新和融合
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib

from ..llm.step_based_model_selector import (
    StepBasedModelSelector, 
    StepContext, 
    ProcessingStep,
    create_step_based_model_selector
)
from ..llm import ask_agent_for_user

logger = logging.getLogger(__name__)


class ContextType(Enum):
    """上下文类型"""
    DATA_SOURCE = "data_source"      # 数据源上下文
    TASK = "task"                    # 任务上下文
    TEMPLATE = "template"            # 模板上下文
    TIME = "time"                    # 时间上下文
    USER = "user"                    # 用户上下文
    BUSINESS = "business"            # 业务上下文
    TECHNICAL = "technical"          # 技术上下文


class ContextPriority(Enum):
    """上下文优先级"""
    CRITICAL = "critical"            # 关键：必须使用
    HIGH = "high"                    # 高：强烈建议使用
    MEDIUM = "medium"                # 中：建议使用
    LOW = "low"                      # 低：可选使用


@dataclass
class ContextItem:
    """上下文项"""
    context_id: str
    context_type: ContextType
    priority: ContextPriority
    content: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    expiry_time: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)  # 依赖的其他上下文ID
    
    @property
    def is_expired(self) -> bool:
        """是否已过期"""
        if self.expiry_time:
            return datetime.now() > self.expiry_time
        return False
    
    @property
    def age_hours(self) -> float:
        """上下文年龄（小时）"""
        return (datetime.now() - self.timestamp).total_seconds() / 3600


@dataclass
class ContextRelationship:
    """上下文关系"""
    source_context_id: str
    target_context_id: str
    relationship_type: str          # 'depends_on', 'conflicts_with', 'enhances', 'requires'
    strength: float                 # 关系强度 0.0 - 1.0
    description: Optional[str] = None


@dataclass
class IntegrationResult:
    """集成结果"""
    integration_id: str
    integrated_context: Dict[str, Any]
    used_contexts: List[str]
    context_weights: Dict[str, float]
    integration_confidence: float
    processing_time_seconds: float
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MultiContextIntegrator:
    """多上下文集成器"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.model_selector = create_step_based_model_selector()
        
        # 上下文存储
        self.contexts: Dict[str, ContextItem] = {}
        self.relationships: List[ContextRelationship] = []
        
        # 集成历史
        self.integration_history: List[IntegrationResult] = []
        
        # 上下文权重配置
        self.default_weights = {
            ContextType.DATA_SOURCE: 0.25,
            ContextType.TASK: 0.25, 
            ContextType.TEMPLATE: 0.20,
            ContextType.TIME: 0.15,
            ContextType.USER: 0.10,
            ContextType.BUSINESS: 0.05
        }
    
    def add_context(
        self,
        context_id: str,
        context_type: ContextType,
        content: Dict[str, Any],
        priority: ContextPriority = ContextPriority.MEDIUM,
        expiry_hours: Optional[int] = None,
        dependencies: Optional[List[str]] = None
    ) -> ContextItem:
        """添加上下文"""
        
        expiry_time = None
        if expiry_hours:
            expiry_time = datetime.now() + timedelta(hours=expiry_hours)
        
        context_item = ContextItem(
            context_id=context_id,
            context_type=context_type,
            priority=priority,
            content=content,
            expiry_time=expiry_time,
            dependencies=dependencies or []
        )
        
        self.contexts[context_id] = context_item
        logger.info(f"添加上下文 {context_id} ({context_type.value})")
        
        return context_item
    
    def add_relationship(
        self,
        source_context_id: str,
        target_context_id: str,
        relationship_type: str,
        strength: float,
        description: Optional[str] = None
    ):
        """添加上下文关系"""
        
        relationship = ContextRelationship(
            source_context_id=source_context_id,
            target_context_id=target_context_id,
            relationship_type=relationship_type,
            strength=strength,
            description=description
        )
        
        self.relationships.append(relationship)
        logger.info(f"添加上下文关系: {source_context_id} -> {target_context_id} ({relationship_type})")
    
    async def integrate_contexts(
        self,
        target_task: str,
        required_context_types: Optional[List[ContextType]] = None,
        custom_weights: Optional[Dict[ContextType, float]] = None
    ) -> IntegrationResult:
        """
        集成多个上下文
        
        Args:
            target_task: 目标任务描述
            required_context_types: 必需的上下文类型
            custom_weights: 自定义权重
            
        Returns:
            IntegrationResult: 集成结果
        """
        integration_id = f"integration_{int(datetime.now().timestamp() * 1000)}"
        start_time = datetime.now()
        
        try:
            logger.info(f"开始多上下文集成 {integration_id}")
            
            # 1. 清理过期上下文
            self._cleanup_expired_contexts()
            
            # 2. 选择相关上下文
            relevant_contexts = await self._select_relevant_contexts(
                target_task, required_context_types
            )
            
            if not relevant_contexts:
                raise ValueError("没有找到相关的上下文")
            
            # 3. 计算上下文权重
            context_weights = self._calculate_context_weights(
                relevant_contexts, custom_weights
            )
            
            # 4. 检查上下文依赖和冲突
            dependency_warnings = self._check_dependencies_and_conflicts(relevant_contexts)
            
            # 5. 执行智能融合
            integrated_context = await self._perform_intelligent_fusion(
                target_task, relevant_contexts, context_weights
            )
            
            # 6. 计算集成信心度
            confidence = self._calculate_integration_confidence(
                relevant_contexts, context_weights, integrated_context
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = IntegrationResult(
                integration_id=integration_id,
                integrated_context=integrated_context,
                used_contexts=[ctx.context_id for ctx in relevant_contexts],
                context_weights=context_weights,
                integration_confidence=confidence,
                processing_time_seconds=processing_time,
                warnings=dependency_warnings
            )
            
            self.integration_history.append(result)
            logger.info(f"多上下文集成完成 {integration_id}, 信心度: {confidence:.2f}")
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"多上下文集成失败 {integration_id}: {e}")
            
            # 返回错误结果
            return IntegrationResult(
                integration_id=integration_id,
                integrated_context={},
                used_contexts=[],
                context_weights={},
                integration_confidence=0.0,
                processing_time_seconds=processing_time,
                warnings=[f"集成失败: {str(e)}"]
            )
    
    def _cleanup_expired_contexts(self):
        """清理过期上下文"""
        expired_contexts = []
        
        for context_id, context in self.contexts.items():
            if context.is_expired:
                expired_contexts.append(context_id)
        
        for context_id in expired_contexts:
            del self.contexts[context_id]
            logger.info(f"清理过期上下文: {context_id}")
        
        if expired_contexts:
            # 同时清理相关的关系
            self.relationships = [
                rel for rel in self.relationships
                if rel.source_context_id not in expired_contexts 
                and rel.target_context_id not in expired_contexts
            ]
    
    async def _select_relevant_contexts(
        self,
        target_task: str,
        required_context_types: Optional[List[ContextType]]
    ) -> List[ContextItem]:
        """选择相关上下文"""
        
        # 1. 必需的上下文类型
        relevant_contexts = []
        
        if required_context_types:
            for context_type in required_context_types:
                type_contexts = [
                    ctx for ctx in self.contexts.values()
                    if ctx.context_type == context_type and not ctx.is_expired
                ]
                
                if type_contexts:
                    # 选择优先级最高的
                    best_context = max(type_contexts, key=lambda x: (
                        self._get_priority_weight(x.priority),
                        -x.age_hours  # 越新越好
                    ))
                    relevant_contexts.append(best_context)
        
        # 2. 使用AI分析任务需求，选择额外的相关上下文
        additional_contexts = await self._ai_select_contexts(target_task)
        
        # 3. 合并并去重
        all_context_ids = set(ctx.context_id for ctx in relevant_contexts)
        for ctx in additional_contexts:
            if ctx.context_id not in all_context_ids:
                relevant_contexts.append(ctx)
                all_context_ids.add(ctx.context_id)
        
        # 4. 按优先级排序
        relevant_contexts.sort(key=lambda x: (
            self._get_priority_weight(x.priority),
            -x.age_hours
        ), reverse=True)
        
        logger.info(f"选择了 {len(relevant_contexts)} 个相关上下文")
        return relevant_contexts
    
    def _get_priority_weight(self, priority: ContextPriority) -> int:
        """获取优先级权重"""
        weights = {
            ContextPriority.CRITICAL: 4,
            ContextPriority.HIGH: 3,
            ContextPriority.MEDIUM: 2,
            ContextPriority.LOW: 1
        }
        return weights.get(priority, 1)
    
    async def _ai_select_contexts(self, target_task: str) -> List[ContextItem]:
        """使用AI选择上下文"""
        
        step_context = StepContext(
            step=ProcessingStep.CONTEXT_ANALYSIS,
            task_description="AI上下文选择",
            data_complexity="medium"
        )
        
        model_selection = self.model_selector.select_model_for_step(step_context)
        
        # 构建上下文信息
        available_contexts = {}
        for ctx_id, ctx in self.contexts.items():
            if not ctx.is_expired:
                available_contexts[ctx_id] = {
                    "type": ctx.context_type.value,
                    "priority": ctx.priority.value,
                    "age_hours": ctx.age_hours,
                    "summary": self._summarize_context_content(ctx.content)
                }
        
        prompt = f"""
        请为以下任务选择最相关的上下文：
        
        目标任务: {target_task}
        
        可用上下文:
        {json.dumps(available_contexts, ensure_ascii=False, indent=2)}
        
        请分析：
        1. 任务需要哪些类型的上下文信息
        2. 各个上下文与任务的相关性
        3. 上下文的重要性和优先级
        
        返回JSON格式的选择结果：
        {{
            "selected_contexts": ["context_id1", "context_id2", ...],
            "reasoning": "选择理由",
            "relevance_scores": {{
                "context_id1": 0.9,
                "context_id2": 0.7
            }}
        }}
        """
        
        try:
            response = await ask_agent_for_user(
                user_id=self.user_id,
                question=prompt,
                agent_type="general",
                task_type="context_selection",
                complexity=model_selection.complexity.value
            )
            
            selection_result = json.loads(response)
            selected_ids = selection_result.get("selected_contexts", [])
            
            # 返回选中的上下文对象
            selected_contexts = []
            for ctx_id in selected_ids:
                if ctx_id in self.contexts:
                    selected_contexts.append(self.contexts[ctx_id])
            
            logger.info(f"AI选择了 {len(selected_contexts)} 个上下文")
            return selected_contexts
            
        except Exception as e:
            logger.error(f"AI上下文选择失败: {e}")
            return []
    
    def _summarize_context_content(self, content: Dict[str, Any]) -> str:
        """概述上下文内容"""
        # 简化的内容概述
        summary_parts = []
        
        for key, value in content.items():
            if isinstance(value, (str, int, float)):
                summary_parts.append(f"{key}: {str(value)[:50]}")
            elif isinstance(value, (list, dict)):
                summary_parts.append(f"{key}: {type(value).__name__}({len(value)})")
        
        return "; ".join(summary_parts[:5])  # 最多显示5个字段
    
    def _calculate_context_weights(
        self,
        contexts: List[ContextItem],
        custom_weights: Optional[Dict[ContextType, float]]
    ) -> Dict[str, float]:
        """计算上下文权重"""
        
        weights = {}
        total_weight = 0.0
        
        # 基础权重计算
        for context in contexts:
            base_weight = (custom_weights or self.default_weights).get(
                context.context_type, 0.1
            )
            
            # 根据优先级调整权重
            priority_multiplier = {
                ContextPriority.CRITICAL: 1.5,
                ContextPriority.HIGH: 1.2,
                ContextPriority.MEDIUM: 1.0,
                ContextPriority.LOW: 0.8
            }.get(context.priority, 1.0)
            
            # 根据新鲜度调整权重（越新越好）
            age_multiplier = max(0.5, 1.0 - context.age_hours / 72)  # 72小时内线性衰减
            
            final_weight = base_weight * priority_multiplier * age_multiplier
            weights[context.context_id] = final_weight
            total_weight += final_weight
        
        # 归一化权重
        if total_weight > 0:
            for context_id in weights:
                weights[context_id] /= total_weight
        
        return weights
    
    def _check_dependencies_and_conflicts(self, contexts: List[ContextItem]) -> List[str]:
        """检查上下文依赖和冲突"""
        warnings = []
        context_ids = set(ctx.context_id for ctx in contexts)
        
        # 检查依赖
        for context in contexts:
            missing_deps = []
            for dep_id in context.dependencies:
                if dep_id not in context_ids:
                    missing_deps.append(dep_id)
            
            if missing_deps:
                warnings.append(f"上下文 {context.context_id} 缺少依赖: {', '.join(missing_deps)}")
        
        # 检查冲突关系
        for rel in self.relationships:
            if (rel.source_context_id in context_ids and 
                rel.target_context_id in context_ids and
                rel.relationship_type == "conflicts_with"):
                warnings.append(
                    f"上下文冲突: {rel.source_context_id} 与 {rel.target_context_id} 存在冲突"
                )
        
        return warnings
    
    async def _perform_intelligent_fusion(
        self,
        target_task: str,
        contexts: List[ContextItem],
        weights: Dict[str, float]
    ) -> Dict[str, Any]:
        """执行智能融合"""
        
        step_context = StepContext(
            step=ProcessingStep.CONTEXT_INTEGRATION,
            task_description="多上下文智能融合",
            data_complexity="high"
        )
        
        model_selection = self.model_selector.select_model_for_step(step_context)
        
        # 构建上下文信息和权重
        context_info = {}
        for context in contexts:
            context_info[context.context_id] = {
                "type": context.context_type.value,
                "priority": context.priority.value,
                "weight": weights.get(context.context_id, 0.0),
                "content": context.content,
                "metadata": context.metadata
            }
        
        prompt = f"""
        请将以下多个上下文智能融合为一个统一的上下文，服务于目标任务：
        
        目标任务: {target_task}
        
        上下文信息（包含权重）:
        {json.dumps(context_info, ensure_ascii=False, indent=2)}
        
        融合要求：
        1. 根据权重合理组合各上下文信息
        2. 解决上下文间的冲突和重复
        3. 保留对任务最重要的信息
        4. 创建逻辑一致的统一上下文
        5. 标识信息来源和可信度
        
        返回JSON格式的融合结果：
        {{
            "unified_context": {{
                "data_sources": "融合的数据源信息",
                "task_requirements": "任务需求信息",
                "time_constraints": "时间约束信息",
                "business_rules": "业务规则信息",
                "technical_constraints": "技术约束信息"
            }},
            "fusion_strategy": "融合策略说明",
            "confidence_factors": "影响信心度的因素",
            "information_sources": "信息来源映射"
        }}
        """
        
        try:
            response = await ask_agent_for_user(
                user_id=self.user_id,
                question=prompt,
                agent_type="general",
                task_type="context_fusion",
                complexity=model_selection.complexity.value
            )
            
            fusion_result = json.loads(response)
            
            # 添加元数据
            unified_context = fusion_result.get("unified_context", {})
            unified_context["_fusion_metadata"] = {
                "fusion_strategy": fusion_result.get("fusion_strategy"),
                "information_sources": fusion_result.get("information_sources"),
                "context_count": len(contexts),
                "total_weight": sum(weights.values()),
                "fusion_timestamp": datetime.now().isoformat()
            }
            
            logger.info("多上下文智能融合完成")
            return unified_context
            
        except Exception as e:
            logger.error(f"多上下文智能融合失败: {e}")
            # 降级策略：简单合并
            return self._simple_context_merge(contexts, weights)
    
    def _simple_context_merge(
        self,
        contexts: List[ContextItem],
        weights: Dict[str, float]
    ) -> Dict[str, Any]:
        """简单的上下文合并（降级策略）"""
        
        merged_context = {
            "data_sources": {},
            "task_requirements": {},
            "time_constraints": {},
            "business_rules": {},
            "technical_constraints": {},
            "_merge_metadata": {
                "merge_strategy": "simple_merge",
                "context_count": len(contexts),
                "merge_timestamp": datetime.now().isoformat()
            }
        }
        
        for context in contexts:
            weight = weights.get(context.context_id, 0.0)
            context_type = context.context_type.value
            
            # 按类型归类上下文内容
            if context_type == "data_source":
                merged_context["data_sources"].update(context.content)
            elif context_type == "task":
                merged_context["task_requirements"].update(context.content)
            elif context_type == "time":
                merged_context["time_constraints"].update(context.content)
            elif context_type in ["business", "user"]:
                merged_context["business_rules"].update(context.content)
            else:
                merged_context["technical_constraints"].update(context.content)
        
        return merged_context
    
    def _calculate_integration_confidence(
        self,
        contexts: List[ContextItem],
        weights: Dict[str, float],
        integrated_context: Dict[str, Any]
    ) -> float:
        """计算集成信心度"""
        
        confidence_factors = []
        
        # 1. 上下文完整性（有关键类型的上下文）
        required_types = [ContextType.DATA_SOURCE, ContextType.TASK]
        available_types = set(ctx.context_type for ctx in contexts)
        completeness = len(available_types.intersection(required_types)) / len(required_types)
        confidence_factors.append(completeness * 0.3)
        
        # 2. 权重分布均衡性
        weight_values = list(weights.values())
        if weight_values:
            weight_entropy = -sum(w * (w + 1e-10) for w in weight_values if w > 0)  # 避免log(0)
            balance_score = min(1.0, weight_entropy / len(weight_values))
            confidence_factors.append(balance_score * 0.2)
        
        # 3. 上下文新鲜度
        if contexts:
            avg_age = sum(ctx.age_hours for ctx in contexts) / len(contexts)
            freshness = max(0.0, 1.0 - avg_age / 48)  # 48小时内认为新鲜
            confidence_factors.append(freshness * 0.2)
        
        # 4. 优先级分布
        high_priority_count = sum(1 for ctx in contexts if ctx.priority in [ContextPriority.CRITICAL, ContextPriority.HIGH])
        priority_score = min(1.0, high_priority_count / len(contexts)) if contexts else 0
        confidence_factors.append(priority_score * 0.15)
        
        # 5. 集成内容丰富度
        content_richness = len(integrated_context) / 10  # 假设10个字段为满分
        confidence_factors.append(min(1.0, content_richness) * 0.15)
        
        final_confidence = sum(confidence_factors)
        return min(1.0, final_confidence)
    
    def get_context_summary(self) -> Dict[str, Any]:
        """获取上下文摘要"""
        active_contexts = [ctx for ctx in self.contexts.values() if not ctx.is_expired]
        
        # 按类型统计
        type_counts = {}
        for ctx in active_contexts:
            type_counts[ctx.context_type.value] = type_counts.get(ctx.context_type.value, 0) + 1
        
        # 按优先级统计
        priority_counts = {}
        for ctx in active_contexts:
            priority_counts[ctx.priority.value] = priority_counts.get(ctx.priority.value, 0) + 1
        
        return {
            "total_contexts": len(self.contexts),
            "active_contexts": len(active_contexts),
            "expired_contexts": len(self.contexts) - len(active_contexts),
            "type_distribution": type_counts,
            "priority_distribution": priority_counts,
            "relationships_count": len(self.relationships),
            "integration_history_count": len(self.integration_history),
            "average_integration_confidence": sum(r.integration_confidence for r in self.integration_history) / max(len(self.integration_history), 1)
        }


def create_multi_context_integrator(user_id: str) -> MultiContextIntegrator:
    """创建多上下文集成器实例"""
    if not user_id:
        raise ValueError("user_id is required for MultiContextIntegrator")
    return MultiContextIntegrator(user_id)