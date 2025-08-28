"""
IAOP服务层 - 业务逻辑处理

提供高级别的业务服务接口，封装底层Agent调用
"""

import logging
import asyncio
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

from .schemas import *
from ..context.execution_context import EnhancedExecutionContext, ContextScope
from ..context.context_manager import IAOPContextManager, get_iaop_context_manager
from ..registry.agent_registry import IAOPAgentRegistry, get_iaop_agent_registry
from ..orchestration.engine import OrchestrationEngine, get_orchestration_engine
from ..agents.specialized import register_all_specialized_agents

logger = logging.getLogger(__name__)


class IAOPService:
    """IAOP核心服务类"""
    
    def __init__(self):
        self.context_manager = get_iaop_context_manager()
        self.agent_registry = get_iaop_agent_registry()
        self.orchestration_engine = get_orchestration_engine()
        
        # 系统状态
        self.start_time = datetime.utcnow()
        self.total_executions = 0
        self.successful_executions = 0
        self.total_execution_time = 0.0
        
        # 确保专业Agent已注册
        self._ensure_agents_registered()
        
        logger.info("IAOP服务初始化完成")

    def _ensure_agents_registered(self):
        """确保所有Agent已注册"""
        try:
            register_all_specialized_agents()
            logger.info("专业Agent注册检查完成")
        except Exception as e:
            logger.warning(f"Agent注册检查失败: {e}")

    async def generate_report(self, request: ReportGenerationRequest) -> ReportResponse:
        """生成单个报告"""
        session_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        try:
            # 创建执行上下文
            context = self.context_manager.create_context(
                session_id=session_id,
                user_id=request.template_context.get("user_id", "system"),
                request={
                    "placeholder_text": request.placeholder_text,
                    "data_source_context": request.data_source_context,
                    "template_context": request.template_context
                },
                task_id=str(uuid.uuid4())
            )
            
            # 设置上下文参数
            context.set_context("placeholder_text", request.placeholder_text, ContextScope.REQUEST)
            context.set_context("data_source_context", request.data_source_context, ContextScope.REQUEST)
            context.set_context("template_context", request.template_context, ContextScope.REQUEST)
            
            # 执行报告生成流水线
            result = await self.orchestration_engine.execute_placeholder_analysis_pipeline(
                placeholder_text=request.placeholder_text,
                data_source_context=request.data_source_context,
                template_context=request.template_context,
                context=context
            )
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # 更新统计信息
            self.total_executions += 1
            self.total_execution_time += execution_time
            
            if result.get('success', False):
                self.successful_executions += 1
                
                # 构建响应
                return await self._build_report_response(result, context, execution_time)
            else:
                return ReportResponse(
                    success=False,
                    task_type="unknown",
                    metric="unknown",
                    execution_time=execution_time,
                    agent_execution_path=[],
                    error=result.get('error', '报告生成失败')
                )
                
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self.total_executions += 1
            self.total_execution_time += execution_time
            
            logger.error(f"报告生成失败: {e}")
            return ReportResponse(
                success=False,
                task_type="unknown", 
                metric="unknown",
                execution_time=execution_time,
                agent_execution_path=[],
                error=str(e)
            )
        finally:
            # 清理上下文
            if session_id in self.context_manager.contexts:
                del self.context_manager.contexts[session_id]

    async def process_placeholders(self, request: PlaceholderRequest) -> BatchProcessingResponse:
        """处理模板中的占位符"""
        session_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        try:
            # 创建执行上下文
            context = self.context_manager.create_context(
                session_id=session_id,
                user_id=request.context_params.get("user_id", "system"),
                request={
                    "template_content": request.template_content,
                    "data_source_id": request.data_source_id,
                    "context_params": request.context_params
                }
            )
            
            # 设置上下文参数
            context.set_context("template_content", request.template_content, ContextScope.REQUEST)
            context.set_context("data_source_id", request.data_source_id, ContextScope.REQUEST)
            
            # 获取数据源信息（这里需要实际的数据源服务）
            data_source_context = await self._get_data_source_context(request.data_source_id)
            context.set_context("data_source_context", data_source_context, ContextScope.SESSION)
            
            # 执行占位符解析
            placeholder_parser = self.agent_registry.get_agent("placeholder_parser")
            if not placeholder_parser:
                raise ValueError("占位符解析Agent未找到")
            
            parse_result = await placeholder_parser.execute_with_tracking(context)
            
            if not parse_result.get('success', False):
                raise ValueError(f"占位符解析失败: {parse_result.get('error', 'unknown')}")
            
            # 处理每个占位符
            placeholders = parse_result.get('data', {}).get('placeholders', [])
            results = []
            
            for i, placeholder in enumerate(placeholders):
                if not placeholder.get('success', False):
                    results.append(ReportResponse(
                        success=False,
                        task_type="unknown",
                        metric="unknown",
                        execution_time=0,
                        agent_execution_path=[],
                        error=placeholder.get('error', '占位符处理失败')
                    ))
                    continue
                
                try:
                    # 为每个占位符创建报告生成请求
                    sub_request = ReportGenerationRequest(
                        placeholder_text=placeholder['original_text'],
                        task_type=placeholder.get('task_type'),
                        data_source_context=data_source_context,
                        template_context=request.context_params
                    )
                    
                    report = await self.generate_report(sub_request)
                    results.append(report)
                    
                except Exception as e:
                    logger.error(f"处理占位符{i}失败: {e}")
                    results.append(ReportResponse(
                        success=False,
                        task_type=placeholder.get('task_type', 'unknown'),
                        metric=placeholder.get('metric', 'unknown'),
                        execution_time=0,
                        agent_execution_path=[],
                        error=str(e)
                    ))
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            successful_count = sum(1 for r in results if r.success)
            
            return BatchProcessingResponse(
                success=True,
                total_requests=len(results),
                successful_requests=successful_count,
                failed_requests=len(results) - successful_count,
                results=results,
                execution_time=execution_time,
                summary={
                    "success_rate": successful_count / len(results) if results else 0,
                    "total_placeholders": len(placeholders),
                    "processed_placeholders": len(results)
                }
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"批量处理失败: {e}")
            
            return BatchProcessingResponse(
                success=False,
                total_requests=0,
                successful_requests=0,
                failed_requests=1,
                results=[],
                execution_time=execution_time,
                summary={"error": str(e)}
            )
        finally:
            # 清理上下文
            if session_id in self.context_manager.contexts:
                del self.context_manager.contexts[session_id]

    async def execute_agent(self, request: AgentExecutionRequest) -> Dict[str, Any]:
        """执行单个Agent"""
        session_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        try:
            # 获取Agent
            agent = self.agent_registry.get_agent(request.agent_name)
            if not agent:
                raise ValueError(f"Agent不存在: {request.agent_name}")
            
            # 创建执行上下文
            context = self.context_manager.create_context(
                session_id=session_id,
                user_id="system",
                request=request.context_data
            )
            
            # 设置参数
            for key, value in request.parameters.items():
                context.set_context(key, value, ContextScope.REQUEST)
            
            # 执行Agent（带超时）
            if request.timeout:
                result = await asyncio.wait_for(
                    agent.execute_with_tracking(context),
                    timeout=request.timeout
                )
            else:
                result = await agent.execute_with_tracking(context)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                "success": True,
                "agent_name": request.agent_name,
                "result": result,
                "execution_time": execution_time,
                "context_summary": {
                    "session_id": session_id,
                    "execution_history": len(context.execution_history),
                    "error_count": len(context.error_stack)
                }
            }
            
        except asyncio.TimeoutError:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            return {
                "success": False,
                "agent_name": request.agent_name,
                "error": f"Agent执行超时（{request.timeout}秒）",
                "execution_time": execution_time
            }
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Agent执行失败: {request.agent_name}, 错误: {e}")
            return {
                "success": False,
                "agent_name": request.agent_name,
                "error": str(e),
                "execution_time": execution_time
            }
        finally:
            # 清理上下文
            if session_id in self.context_manager.contexts:
                del self.context_manager.contexts[session_id]

    async def get_system_status(self) -> SystemStatusResponse:
        """获取系统状态"""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        registry_status = self.agent_registry.get_registry_status()
        
        return SystemStatusResponse(
            status="running",
            version="1.0.0",
            uptime=uptime,
            total_agents=registry_status['total_agents'],
            active_agents=registry_status['total_agents'],  # 简化处理
            agent_chains=registry_status['chains'],
            total_executions=self.total_executions,
            successful_executions=self.successful_executions,
            average_execution_time=self.total_execution_time / self.total_executions if self.total_executions > 0 else 0,
            active_contexts=len(self.context_manager.contexts)
        )

    async def get_agent_status(self, agent_name: str) -> Optional[AgentStatusResponse]:
        """获取Agent状态"""
        agent_info = self.agent_registry.get_agent_info(agent_name)
        if not agent_info:
            return None
        
        return AgentStatusResponse(
            name=agent_name,
            status="active",  # 简化处理
            capabilities=agent_info['capabilities'],
            requirements=agent_info['requirements'], 
            priority=agent_info['priority'],
            execution_count=0,  # TODO: 从监控系统获取
            success_rate=1.0,   # TODO: 从监控系统获取
            average_execution_time=0.0  # TODO: 从监控系统获取
        )

    async def list_agents(self) -> List[AgentStatusResponse]:
        """列出所有Agent"""
        agent_names = self.agent_registry.get_registered_agents()
        agents = []
        
        for name in agent_names:
            status = await self.get_agent_status(name)
            if status:
                agents.append(status)
        
        return agents

    async def _build_report_response(self, result: Dict[str, Any], 
                                   context: EnhancedExecutionContext,
                                   execution_time: float) -> ReportResponse:
        """构建报告响应"""
        pipeline_result = result.get('result', {})
        
        # 提取基本信息
        task_type = pipeline_result.get('task_type', 'unknown')
        metric = pipeline_result.get('placeholder_text', 'unknown')
        
        # 构建图表配置响应
        chart_config = None
        if 'chart_type' in pipeline_result:
            chart_config = ChartConfigResponse(
                chart_type=pipeline_result.get('chart_type', ''),
                echarts_config=pipeline_result.get('chart_config', {}),
                chart_data=pipeline_result.get('chart_data', []),
                metadata=pipeline_result.get('metadata', {}),
                chart_options=pipeline_result.get('chart_options', {})
            )
        
        # 构建叙述响应
        narrative = None
        if 'narrative_text' in pipeline_result:
            insights = [
                InsightResponse(**insight) for insight in pipeline_result.get('key_insights', [])
            ]
            recommendations = [
                RecommendationResponse(**rec) for rec in pipeline_result.get('recommendations', [])
            ]
            
            narrative = NarrativeResponse(
                narrative_text=pipeline_result.get('narrative_text', ''),
                key_insights=insights,
                recommendations=recommendations,
                structured_narrative=pipeline_result.get('structured_narrative', {}),
                narrative_metadata=pipeline_result.get('narrative_metadata', {})
            )
        
        # 提取执行路径
        execution_path = []
        for record in context.execution_history:
            execution_path.append(record.get('agent_name', 'unknown'))
        
        return ReportResponse(
            success=True,
            task_type=task_type,
            metric=metric,
            chart_config=chart_config,
            narrative=narrative,
            statistics=pipeline_result.get('statistics', {}),
            execution_time=execution_time,
            agent_execution_path=execution_path,
            context_summary={
                "session_id": context.session_id,
                "task_id": context.task_id,
                "execution_count": len(context.execution_history),
                "error_count": len(context.error_stack)
            }
        )

    async def _get_data_source_context(self, data_source_id: Optional[str]) -> Dict[str, Any]:
        """获取数据源上下文（模拟实现）"""
        if not data_source_id:
            return {
                "tables": [],
                "columns": [],
                "type": "unknown"
            }
        
        # TODO: 实际实现应该从数据源服务获取
        return {
            "name": data_source_id,
            "type": "mysql",
            "tables": [
                {
                    "name": "sales_orders",
                    "columns": [
                        {"name": "id", "type": "int", "comment": "订单ID"},
                        {"name": "order_date", "type": "datetime", "comment": "订单日期"},
                        {"name": "amount", "type": "decimal", "comment": "订单金额"},
                        {"name": "customer_id", "type": "int", "comment": "客户ID"},
                        {"name": "department", "type": "varchar", "comment": "部门"}
                    ]
                },
                {
                    "name": "users",
                    "columns": [
                        {"name": "id", "type": "int", "comment": "用户ID"},
                        {"name": "username", "type": "varchar", "comment": "用户名"},
                        {"name": "created_at", "type": "datetime", "comment": "创建时间"},
                        {"name": "status", "type": "varchar", "comment": "状态"}
                    ]
                }
            ]
        }


# 全局服务实例
_global_iaop_service = None

def get_iaop_service() -> IAOPService:
    """获取全局IAOP服务实例"""
    global _global_iaop_service
    if _global_iaop_service is None:
        _global_iaop_service = IAOPService()
    return _global_iaop_service