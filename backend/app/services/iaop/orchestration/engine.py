from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict, List
from datetime import datetime

from .models.execution_plan import ExecutionPlan
from ..context.execution_context import EnhancedExecutionContext
from ..agents.specialized.semantic_analyzer_agent import PlaceholderSemanticAnalyzerAgent
from ..agents.specialized.sql_generation_agent import SQLGenerationAgent
from ..agents.specialized.sql_quality_assessor_agent import SQLQualityAssessorAgent


logger = logging.getLogger(__name__)


AsyncHook = Callable[[EnhancedExecutionContext], Awaitable[None]]


class OrchestrationEngine:
    """
增强的编排引擎 - 协调多个Agent的执行
支持智能编排、错误处理和结果聚合
"""
    
    def __init__(self):
        self._pre_hooks: List[AsyncHook] = []
        self._post_hooks: List[AsyncHook] = []
        
        # 初始化核心Agents
        self.semantic_agent = PlaceholderSemanticAnalyzerAgent()
        self.sql_agent = SQLGenerationAgent()
        self.quality_agent = SQLQualityAssessorAgent()
        
        logger.info("OrchestrationEngine initialized with core agents")

    def use_pre_hook(self, hook: AsyncHook) -> None:
        """注册前置钩子"""
        self._pre_hooks.append(hook)

    def use_post_hook(self, hook: AsyncHook) -> None:
        """注册后置钩子"""
        self._post_hooks.append(hook)

    async def execute_plan(self, plan: ExecutionPlan, context: EnhancedExecutionContext) -> Dict[str, Any]:
        """
        执行编排计划
        
        基于计划中的节点顺序执行，支持依赖管理和错误处理
        """
        start_time = datetime.now()
        
        try:
            # 执行前置钩子
            for hook in self._pre_hooks:
                await hook(context)
            
            execution_results = {}
            
            # 按计划顺序执行节点
            for node in plan.get_execution_order():
                try:
                    logger.info(f"开始执行节点: {node.task_id} ({node.agent_type})")
                    
                    # 验证前置条件
                    if not await self._validate_node_preconditions(node, context):
                        logger.warning(f"节点前置条件验证失败: {node.task_id}")
                        continue
                    
                    # 执行节点
                    node_result = await node.execute(context)
                    
                    # 存储结果
                    context.agent_results[node.task_id] = node_result
                    execution_results[node.task_id] = node_result
                    
                    # 检查节点执行是否成功
                    if not node_result.get('success', False):
                        logger.warning(f"节点执行失败: {node.task_id}, 错误: {node_result.get('error', 'unknown')}")
                        # 根据计划配置决定是否继续执行
                        if plan.fail_fast:
                            break
                    
                    logger.info(f"节点执行完成: {node.task_id}")
                    
                except Exception as e:
                    logger.error(f"节点执行异常: {node.task_id}, 错误: {e}")
                    execution_results[node.task_id] = {
                        'success': False,
                        'error': str(e),
                        'agent': node.agent_type,
                        'task_id': node.task_id
                    }
                    context.agent_results[node.task_id] = execution_results[node.task_id]
                    
                    if plan.fail_fast:
                        break
            
            # 生成最终结果
            final_result = self._aggregate_results(execution_results, context)
            
            # 执行后置钩子
            for hook in self._post_hooks:
                await hook(context)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"编排执行完成，耗时: {execution_time:.2f}s")
            
            return {
                'success': True,
                'result': final_result,
                'execution_results': execution_results,
                'execution_time': execution_time,
                'time_constraints': context.time_constraints,
                'metadata': {
                    'start_time': start_time.isoformat(),
                    'end_time': datetime.now().isoformat(),
                    'nodes_executed': len(execution_results),
                    'successful_nodes': len([r for r in execution_results.values() if r.get('success')])
                }
            }
            
        except Exception as e:
            logger.error(f"编排执行失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'execution_time': (datetime.now() - start_time).total_seconds(),
                'metadata': {
                    'start_time': start_time.isoformat(),
                    'error_time': datetime.now().isoformat()
                }
            }
    
    async def execute_placeholder_analysis_pipeline(
        self, 
        placeholder_text: str,
        data_source_context: Dict[str, Any],
        template_context: Dict[str, Any],
        context: EnhancedExecutionContext
    ) -> Dict[str, Any]:
        """
        执行占位符分析的完整流水线
        
        这是一个预定义的高效流水线，适用于大多数占位符分析场景
        """
        pipeline_start = datetime.now()
        
        try:
            # 准备共享的请求数据
            base_request = {
                'placeholder_text': placeholder_text,
                'data_source_context': data_source_context,
                'template_context': template_context
            }
            
            # 1. 语义分析阶段
            logger.info(f"开始语义分析: {placeholder_text}")
            context.request = base_request
            
            semantic_result = await self.semantic_agent.execute(context)
            
            if not semantic_result.get('success', False):
                logger.warning(f"语义分析失败: {semantic_result.get('error', 'unknown')}")
                return self._create_pipeline_error_result("semantic_analysis", semantic_result.get('error', 'unknown'))
            
            # 2. SQL生成阶段
            logger.info(f"开始SQL生成: {placeholder_text}")
            context.request = {
                **base_request,
                'semantic_analysis': semantic_result.get('data', {})
            }
            
            sql_result = await self.sql_agent.execute(context)
            
            if not sql_result.get('success', False):
                logger.warning(f"SQL生成失败: {sql_result.get('error', 'unknown')}")
                return self._create_pipeline_error_result("sql_generation", sql_result.get('error', 'unknown'))
            
            # 3. 质量评估阶段
            logger.info(f"开始质量评估: {placeholder_text}")
            sql_data = sql_result.get('data', {})
            context.request = {
                **base_request,
                'semantic_analysis': semantic_result.get('data', {}),
                'sql_query': sql_data.get('sql_query', '')
            }
            
            quality_result = await self.quality_agent.execute(context)
            
            # 质量评估失败不阻断流程，只记录警告
            if not quality_result.get('success', False):
                logger.warning(f"质量评估失败: {quality_result.get('error', 'unknown')}")
            
            # 4. 结果聚合
            pipeline_result = self._aggregate_pipeline_results(
                semantic_result,
                sql_result, 
                quality_result,
                placeholder_text
            )
            
            pipeline_time = (datetime.now() - pipeline_start).total_seconds()
            pipeline_result['pipeline_execution_time'] = pipeline_time
            
            logger.info(f"占位符分析流水线完成: {placeholder_text}, 耗时: {pipeline_time:.2f}s")
            
            return pipeline_result
            
        except Exception as e:
            logger.error(f"占位符分析流水线异常: {e}")
            return self._create_pipeline_error_result("pipeline_execution", str(e))
    
    async def _validate_node_preconditions(self, node, context: EnhancedExecutionContext) -> bool:
        """
        验证节点的前置条件
        
        检查依赖的数据是否已准备就绪
        """
        # 基础数据检查
        required_fields = getattr(node, 'required_fields', [])
        for field in required_fields:
            if field not in context.request:
                logger.warning(f"节点{node.task_id}缺少必要字段: {field}")
                return False
        
        # 依赖节点检查
        dependencies = getattr(node, 'dependencies', [])
        for dep_id in dependencies:
            if dep_id not in context.agent_results:
                logger.warning(f"节点{node.task_id}缺少依赖结果: {dep_id}")
                return False
            
            # 检查依赖节点是否成功执行
            dep_result = context.agent_results[dep_id]
            if not dep_result.get('success', False):
                logger.warning(f"节点{node.task_id}的依赖{dep_id}执行失败")
                return False
        
        return True
    
    def _aggregate_results(self, execution_results: Dict[str, Any], context: EnhancedExecutionContext) -> Dict[str, Any]:
        """
        聚合各节点的执行结果
        
        生成统一的结果格式
        """
        successful_results = {k: v for k, v in execution_results.items() if v.get('success', False)}
        failed_results = {k: v for k, v in execution_results.items() if not v.get('success', False)}
        
        # 如果有SQL生成结果，优先使用
        if 'sql_generation' in successful_results:
            sql_result = successful_results['sql_generation']
            base_result = sql_result.get('data', {})
        elif successful_results:
            # 使用第一个成功的结果
            first_success = list(successful_results.values())[0]
            base_result = first_success.get('data', {})
        else:
            # 所有节点都失败了
            base_result = {'error': '所有节点执行失败'}
        
        # 聚合元数据
        aggregated_result = {
            **base_result,
            'execution_summary': {
                'total_nodes': len(execution_results),
                'successful_nodes': len(successful_results),
                'failed_nodes': len(failed_results),
                'success_rate': len(successful_results) / len(execution_results) if execution_results else 0
            }
        }
        
        # 如果有质量评估结果，添加质量信息
        if 'quality_assessment' in successful_results:
            quality_data = successful_results['quality_assessment'].get('data', {})
            aggregated_result.update({
                'quality_score': quality_data.get('overall_score', 0),
                'quality_level': quality_data.get('overall_level', 'unknown'),
                'quality_issues': quality_data.get('issues', []),
                'quality_suggestions': quality_data.get('suggestions', [])
            })
        
        return aggregated_result
    
    def _aggregate_pipeline_results(
        self,
        semantic_result: Dict[str, Any],
        sql_result: Dict[str, Any],
        quality_result: Dict[str, Any],
        placeholder_text: str
    ) -> Dict[str, Any]:
        """
        聚合流水线结果
        
        整合语义分析、SQL生成和质量评估的结果
        """
        # 基础结果来自SQL生成
        sql_data = sql_result.get('data', {})
        result = {
            'placeholder_text': placeholder_text,
            'sql_query': sql_data.get('sql_query', ''),
            'target_table': sql_data.get('target_table', ''),
            'target_columns': sql_data.get('target_columns', []),
            'business_logic': sql_data.get('business_logic', ''),
            'confidence': sql_data.get('confidence', 0.5)
        }
        
        # 添加语义分析结果
        semantic_data = semantic_result.get('data', {})
        result.update({
            'semantic_analysis': {
                'primary_intent': semantic_data.get('primary_intent', ''),
                'data_type': semantic_data.get('data_type', ''),
                'business_concept': semantic_data.get('business_concept', ''),
                'keywords': semantic_data.get('keywords', []),
                'confidence': semantic_data.get('confidence', 0.5)
            }
        })
        
        # 添加质量评估结果
        quality_data = quality_result.get('data', {})
        if quality_result.get('success', False):
            result.update({
                'quality_assessment': {
                    'overall_score': quality_data.get('overall_score', 0.5),
                    'overall_level': quality_data.get('overall_level', 'unknown'),
                    'dimension_scores': quality_data.get('dimension_scores', {}),
                    'total_issues': quality_data.get('total_issues', 0),
                    'critical_issues': quality_data.get('critical_issues', 0),
                    'suggestions': quality_data.get('suggestions', [])
                }
            })
        else:
            result.update({
                'quality_assessment': {
                    'overall_score': 0.1,
                    'overall_level': 'critical',
                    'error': quality_result.get('error', 'unknown'),
                    'suggestions': ['质量评估失败，建议人工检查']
                }
            })
        
        # 添加流水线元数据
        result.update({
            'pipeline_metadata': {
                'semantic_success': semantic_result.get('success', False),
                'sql_success': sql_result.get('success', False), 
                'quality_success': quality_result.get('success', False),
                'overall_success': semantic_result.get('success', False) and sql_result.get('success', False),
                'execution_timestamp': datetime.now().isoformat()
            }
        })
        
        return result
    
    def _create_pipeline_error_result(self, stage: str, error_msg: str) -> Dict[str, Any]:
        """
        创建流水线错误结果
        """
        return {
            'success': False,
            'error': f'{stage}阶段失败: {error_msg}',
            'stage': stage,
            'pipeline_metadata': {
                'semantic_success': stage != 'semantic_analysis',
                'sql_success': False,
                'quality_success': False,
                'overall_success': False,
                'error_stage': stage,
                'execution_timestamp': datetime.now().isoformat()
            }
        }
    
    # 新增方法：支持基于Agent注册器的执行
    async def execute_agents_by_capability(self, capability: str, context: EnhancedExecutionContext,
                                          parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """根据能力执行相关的Agent"""
        suitable_agents = self.agent_registry.get_agents_by_capability(capability)
        
        if not suitable_agents:
            logger.warning(f"No agents found for capability: {capability}")
            return []
        
        results = []
        for agent in suitable_agents:
            try:
                if parameters:
                    for key, value in parameters.items():
                        context.set_context(f"param_{key}", value, ContextScope.REQUEST)
                
                if hasattr(agent, 'execute_with_tracking'):
                    result = await agent.execute_with_tracking(context)
                else:
                    result = await agent.execute(context)
                
                results.append({
                    'agent_name': agent.name,
                    'result': result,
                    'success': result.get('success', False)
                })
                
            except Exception as e:
                logger.error(f"Error executing agent {agent.name}: {e}")
                results.append({
                    'agent_name': agent.name,
                    'error': str(e),
                    'success': False
                })
        
        return results
    
    def get_engine_status(self) -> Dict[str, Any]:
        """获取编排引擎状态"""
        return {
            'engine_type': 'OrchestrationEngine',
            'core_agents': {
                'semantic_agent': type(self.semantic_agent).__name__,
                'sql_agent': type(self.sql_agent).__name__,
                'quality_agent': type(self.quality_agent).__name__
            },
            'hooks': {
                'pre_hooks_count': len(self._pre_hooks),
                'post_hooks_count': len(self._post_hooks)
            },
            'registry_status': self.agent_registry.get_registry_status(),
            'context_manager_available': self.context_manager is not None
        }


# 全局编排引擎实例
_global_orchestration_engine = None

def get_orchestration_engine() -> OrchestrationEngine:
    """获取全局编排引擎实例"""
    global _global_orchestration_engine
    if _global_orchestration_engine is None:
        _global_orchestration_engine = OrchestrationEngine()
    return _global_orchestration_engine


