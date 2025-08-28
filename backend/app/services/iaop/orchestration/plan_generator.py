from __future__ import annotations

import logging
from typing import Dict, List, Any
from datetime import datetime

from .models.execution_plan import ExecutionPlan
from .models.task_node import TaskNode
from ..context.execution_context import EnhancedExecutionContext

logger = logging.getLogger(__name__)


class PlanGenerator:
    """
    智能计划生成器 - 基于上下文和任务类型生成优化的执行计划
    """
    
    def __init__(self):
        self.predefined_plans = {
            'placeholder_analysis': self._create_placeholder_analysis_plan,
            'batch_placeholder_analysis': self._create_batch_analysis_plan,
            'quality_focused_analysis': self._create_quality_focused_plan,
            'performance_focused_analysis': self._create_performance_focused_plan
        }
        
    def generate_plan(
        self, 
        *, 
        placeholder_id: str = None, 
        context: EnhancedExecutionContext,
        plan_type: str = 'placeholder_analysis',
        custom_requirements: Dict[str, Any] = None
    ) -> ExecutionPlan:
        """
        生成执行计划
        
        根据任务类型和上下文生成最优化的执行计划
        """
        try:
            logger.info(f"开始生成执行计划: {plan_type}")
            
            # 选择计划生成策略
            plan_generator = self.predefined_plans.get(plan_type, self._create_default_plan)
            
            # 生成计划
            plan = plan_generator(
                placeholder_id=placeholder_id,
                context=context,
                custom_requirements=custom_requirements or {}
            )
            
            logger.info(f"执行计划生成完成: {len(plan.nodes)}个节点")
            
            return plan
            
        except Exception as e:
            logger.error(f"执行计划生成失败: {e}")
            # 返回默认计划
            return self._create_fallback_plan(placeholder_id, context)
    
    def _create_placeholder_analysis_plan(
        self,
        placeholder_id: str = None,
        context: EnhancedExecutionContext = None,
        custom_requirements: Dict[str, Any] = None
    ) -> ExecutionPlan:
        """创建标准的占位符分析计划"""
        
        nodes = [
            # 1. 语义分析节点
            TaskNode(
                task_id='semantic_analysis',
                agent_type='semantic_analyzer',
                dependencies=[],
                metadata={
                    'placeholder_id': placeholder_id,
                    'priority': 'high',
                    'timeout': 30,
                    'retry_count': 2
                },
                required_fields=['placeholder_text', 'data_source_context']
            ),
            
            # 2. SQL生成节点
            TaskNode(
                task_id='sql_generation',
                agent_type='sql_generator',
                dependencies=['semantic_analysis'],
                metadata={
                    'placeholder_id': placeholder_id,
                    'priority': 'high',
                    'timeout': 45,
                    'retry_count': 2
                },
                required_fields=['semantic_analysis', 'data_source_context']
            ),
            
            # 3. 质量评估节点(可选)
            TaskNode(
                task_id='quality_assessment',
                agent_type='quality_assessor',
                dependencies=['sql_generation'],
                metadata={
                    'placeholder_id': placeholder_id,
                    'priority': 'medium',
                    'timeout': 20,
                    'retry_count': 1,
                    'optional': True  # 即使失败也不阻断流程
                },
                required_fields=['sql_query']
            )
        ]
        
        return ExecutionPlan(
            nodes=nodes,
            plan_type='placeholder_analysis',
            fail_fast=custom_requirements.get('fail_fast', False) if custom_requirements else False,
            parallel_execution=custom_requirements.get('parallel_execution', False) if custom_requirements else False,
            metadata={
                'created_at': datetime.now().isoformat(),
                'placeholder_id': placeholder_id,
                'custom_requirements': custom_requirements
            }
        )
    
    def _create_batch_analysis_plan(
        self,
        placeholder_id: str = None,
        context: EnhancedExecutionContext = None,
        custom_requirements: Dict[str, Any] = None
    ) -> ExecutionPlan:
        """创建批量分析计划(简化版)"""
        
        nodes = [
            TaskNode(
                task_id='batch_analysis',
                agent_type='batch_analyzer',
                dependencies=[],
                metadata={
                    'batch_mode': True,
                    'priority': 'high',
                    'timeout': 120,
                    'retry_count': 1
                },
                required_fields=['placeholder_batch']
            )
        ]
        
        return ExecutionPlan(
            nodes=nodes,
            plan_type='batch_analysis',
            fail_fast=False,
            parallel_execution=True,
            metadata={'created_at': datetime.now().isoformat()}
        )
    
    def _create_quality_focused_plan(
        self,
        placeholder_id: str = None,
        context: EnhancedExecutionContext = None,
        custom_requirements: Dict[str, Any] = None
    ) -> ExecutionPlan:
        """创建质量优先计划(简化版)"""
        
        nodes = [
            TaskNode(
                task_id='enhanced_semantic_analysis',
                agent_type='enhanced_semantic_analyzer',
                dependencies=[],
                metadata={
                    'quality_mode': True,
                    'priority': 'high',
                    'timeout': 60,
                    'retry_count': 3
                },
                required_fields=['placeholder_text', 'data_source_context']
            ),
            
            TaskNode(
                task_id='comprehensive_sql_generation',
                agent_type='comprehensive_sql_generator',
                dependencies=['enhanced_semantic_analysis'],
                metadata={
                    'quality_mode': True,
                    'priority': 'high',
                    'timeout': 90,
                    'retry_count': 2
                },
                required_fields=['semantic_analysis']
            ),
            
            TaskNode(
                task_id='full_quality_assessment',
                agent_type='comprehensive_quality_assessor',
                dependencies=['comprehensive_sql_generation'],
                metadata={
                    'comprehensive_mode': True,
                    'priority': 'high',
                    'timeout': 45,
                    'retry_count': 2
                },
                required_fields=['sql_query']
            )
        ]
        
        return ExecutionPlan(
            nodes=nodes,
            plan_type='quality_focused',
            fail_fast=True,
            parallel_execution=False,
            metadata={'created_at': datetime.now().isoformat()}
        )
    
    def _create_performance_focused_plan(
        self,
        placeholder_id: str = None,
        context: EnhancedExecutionContext = None,
        custom_requirements: Dict[str, Any] = None
    ) -> ExecutionPlan:
        """创建性能优先计划(简化版)"""
        
        nodes = [
            TaskNode(
                task_id='fast_semantic_analysis',
                agent_type='fast_semantic_analyzer',
                dependencies=[],
                metadata={
                    'fast_mode': True,
                    'priority': 'high',
                    'timeout': 15,
                    'retry_count': 1
                },
                required_fields=['placeholder_text']
            ),
            
            TaskNode(
                task_id='cached_sql_generation',
                agent_type='cached_sql_generator',
                dependencies=['fast_semantic_analysis'],
                metadata={
                    'cache_first': True,
                    'priority': 'high',
                    'timeout': 20,
                    'retry_count': 1
                },
                required_fields=['semantic_analysis']
            )
        ]
        
        return ExecutionPlan(
            nodes=nodes,
            plan_type='performance_focused',
            fail_fast=False,
            parallel_execution=True,
            metadata={'created_at': datetime.now().isoformat()}
        )
    
    def _create_default_plan(
        self,
        placeholder_id: str = None,
        context: EnhancedExecutionContext = None,
        custom_requirements: Dict[str, Any] = None
    ) -> ExecutionPlan:
        """创建默认计划"""
        return self._create_placeholder_analysis_plan(placeholder_id, context, custom_requirements)
    
    def _create_fallback_plan(
        self, 
        placeholder_id: str, 
        context: EnhancedExecutionContext
    ) -> ExecutionPlan:
        """创建回退计划"""
        logger.warning("使用回退执行计划")
        
        fallback_node = TaskNode(
            task_id='fallback_analysis',
            agent_type='fallback_analyzer',
            dependencies=[],
            metadata={
                'placeholder_id': placeholder_id,
                'fallback_mode': True,
                'priority': 'high',
                'timeout': 10,
                'retry_count': 0
            },
            required_fields=[]
        )
        
        return ExecutionPlan(
            nodes=[fallback_node],
            plan_type='fallback',
            fail_fast=False,
            parallel_execution=False,
            metadata={
                'created_at': datetime.now().isoformat(),
                'plan_type': 'emergency_fallback',
                'placeholder_id': placeholder_id
            }
        )


