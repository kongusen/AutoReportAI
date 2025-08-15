"""
上下文感知的Agent编排器

专门解决长篇报告生成中的上下文窗口限制问题，支持：
- 智能上下文压缩和摘要
- 分层结果汇总
- 增量内容处理
- 动态上下文窗口管理
"""

import asyncio
import json
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime
from enum import Enum
import logging

from ..core_types import BaseAgent, AgentConfig, AgentResult, AgentType
from ..orchestration.smart_orchestrator import SmartOrchestrator, WorkflowStep, Workflow
from ..enhanced.enhanced_content_generation_agent import EnhancedContentGenerationAgent

logger = logging.getLogger(__name__)


class ContextCompressionLevel(Enum):
    """上下文压缩级别"""
    NONE = "none"           # 不压缩
    LIGHT = "light"         # 轻度压缩，保留关键信息
    MEDIUM = "medium"       # 中度压缩，提取核心要点
    HEAVY = "heavy"         # 重度压缩，仅保留摘要


@dataclass
class ContextWindow:
    """上下文窗口管理"""
    max_tokens: int = 32000         # 最大token数量
    reserved_tokens: int = 4000     # 预留token（用于输出）
    current_tokens: int = 0         # 当前token数量
    compression_threshold: float = 0.8  # 压缩阈值（80%时开始压缩）
    
    @property
    def available_tokens(self) -> int:
        """可用token数量"""
        return self.max_tokens - self.reserved_tokens
    
    @property
    def should_compress(self) -> bool:
        """是否需要压缩"""
        return self.current_tokens > (self.available_tokens * self.compression_threshold)
    
    @property
    def compression_ratio(self) -> float:
        """建议压缩比例"""
        if not self.should_compress:
            return 1.0
        
        excess_ratio = self.current_tokens / self.available_tokens
        if excess_ratio > 1.5:
            return 0.3  # 重度压缩，保留30%
        elif excess_ratio > 1.2:
            return 0.5  # 中度压缩，保留50%
        else:
            return 0.7  # 轻度压缩，保留70%


@dataclass
class ContextChunk:
    """上下文分块"""
    chunk_id: str
    content_type: str  # "data", "analysis", "summary", "metadata"
    content: Any
    priority: int      # 优先级：1-10，10最高
    token_count: int
    created_at: datetime
    last_accessed: datetime
    compression_level: ContextCompressionLevel = ContextCompressionLevel.NONE
    
    def compress(self, target_ratio: float) -> 'ContextChunk':
        """压缩内容块"""
        if self.compression_level != ContextCompressionLevel.NONE:
            return self  # 已压缩
        
        if target_ratio >= 1.0:
            return self  # 无需压缩
        
        # 根据压缩比例确定压缩级别
        if target_ratio <= 0.3:
            compression_level = ContextCompressionLevel.HEAVY
        elif target_ratio <= 0.5:
            compression_level = ContextCompressionLevel.MEDIUM
        else:
            compression_level = ContextCompressionLevel.LIGHT
        
        compressed_content = self._apply_compression(self.content, compression_level)
        compressed_tokens = int(self.token_count * target_ratio)
        
        return ContextChunk(
            chunk_id=f"{self.chunk_id}_compressed",
            content_type=self.content_type,
            content=compressed_content,
            priority=self.priority,
            token_count=compressed_tokens,
            created_at=self.created_at,
            last_accessed=datetime.now(),
            compression_level=compression_level
        )
    
    def _apply_compression(self, content: Any, level: ContextCompressionLevel) -> Any:
        """应用具体的压缩算法"""
        if isinstance(content, dict):
            return self._compress_dict(content, level)
        elif isinstance(content, list):
            return self._compress_list(content, level)
        elif isinstance(content, str):
            return self._compress_text(content, level)
        else:
            return content
    
    def _compress_dict(self, data: Dict[str, Any], level: ContextCompressionLevel) -> Dict[str, Any]:
        """压缩字典数据"""
        if level == ContextCompressionLevel.LIGHT:
            # 保留核心字段
            key_fields = ["result", "data", "summary", "value", "total", "count", "insights"]
            return {k: v for k, v in data.items() if k in key_fields or k.endswith("_summary")}
        
        elif level == ContextCompressionLevel.MEDIUM:
            # 提取关键指标
            if "results" in data:
                results = data["results"]
                if isinstance(results, dict):
                    # 提取数值统计
                    numeric_data = {}
                    for k, v in results.items():
                        if isinstance(v, (int, float)):
                            numeric_data[k] = v
                        elif isinstance(v, dict) and "total" in v:
                            numeric_data[k] = v["total"]
                    return {"summary_metrics": numeric_data}
            
            return {"summary": "数据已压缩为摘要"}
        
        elif level == ContextCompressionLevel.HEAVY:
            # 仅保留元数据
            return {
                "type": data.get("type", "unknown"),
                "row_count": data.get("row_count", 0),
                "compressed": True
            }
        
        return data
    
    def _compress_list(self, data: List[Any], level: ContextCompressionLevel) -> List[Any]:
        """压缩列表数据"""
        if not data:
            return data
        
        if level == ContextCompressionLevel.LIGHT:
            # 保留前10项
            return data[:10] + [{"...": f"省略{len(data)-10}项"}] if len(data) > 10 else data
        
        elif level == ContextCompressionLevel.MEDIUM:
            # 保留前5项和统计摘要
            sample = data[:5]
            if isinstance(data[0], dict) and all(isinstance(item, dict) for item in data):
                # 计算数值字段的统计信息
                numeric_fields = {}
                for item in data:
                    for k, v in item.items():
                        if isinstance(v, (int, float)):
                            if k not in numeric_fields:
                                numeric_fields[k] = []
                            numeric_fields[k].append(v)
                
                summary = {f"{k}_avg": sum(values)/len(values) for k, values in numeric_fields.items()}
                return sample + [{"summary": summary, "total_items": len(data)}]
            
            return sample + [{"total_items": len(data)}]
        
        elif level == ContextCompressionLevel.HEAVY:
            # 仅保留统计信息
            return [{"total_items": len(data), "compressed": True}]
        
        return data
    
    def _compress_text(self, text: str, level: ContextCompressionLevel) -> str:
        """压缩文本内容"""
        if level == ContextCompressionLevel.LIGHT:
            # 截取前500字符
            return text[:500] + "..." if len(text) > 500 else text
        
        elif level == ContextCompressionLevel.MEDIUM:
            # 提取关键句子（简化实现）
            sentences = text.split('。')
            key_sentences = [s for s in sentences if any(keyword in s for keyword in ['总计', '平均', '最高', '最低', '增长', '下降', '重要', '关键'])]
            return '。'.join(key_sentences[:3]) + '。' if key_sentences else text[:200] + "..."
        
        elif level == ContextCompressionLevel.HEAVY:
            # 仅保留摘要
            return f"[文本摘要: {len(text)}字符的内容]"
        
        return text


class ContextManager:
    """上下文管理器"""
    
    def __init__(self, window: ContextWindow):
        self.window = window
        self.chunks: Dict[str, ContextChunk] = {}
        self.access_history: List[str] = []
        self.content_agent = EnhancedContentGenerationAgent()
    
    def add_chunk(self, chunk: ContextChunk) -> None:
        """添加内容块"""
        self.chunks[chunk.chunk_id] = chunk
        self.window.current_tokens += chunk.token_count
        self._update_access_history(chunk.chunk_id)
        
        # 检查是否需要压缩
        if self.window.should_compress:
            asyncio.create_task(self._compress_context())
    
    async def _compress_context(self) -> None:
        """压缩上下文"""
        logger.info(f"开始上下文压缩，当前tokens: {self.window.current_tokens}")
        
        target_ratio = self.window.compression_ratio
        
        # 按优先级和访问时间排序
        sorted_chunks = sorted(
            self.chunks.values(),
            key=lambda x: (x.priority, x.last_accessed),
            reverse=True
        )
        
        compressed_chunks = {}
        total_tokens = 0
        
        for chunk in sorted_chunks:
            if total_tokens < self.window.available_tokens:
                # 压缩当前块
                compressed_chunk = chunk.compress(target_ratio)
                compressed_chunks[compressed_chunk.chunk_id] = compressed_chunk
                total_tokens += compressed_chunk.token_count
            else:
                # 丢弃低优先级的块
                logger.debug(f"丢弃低优先级块: {chunk.chunk_id}")
        
        # 更新上下文
        self.chunks = compressed_chunks
        self.window.current_tokens = total_tokens
        
        logger.info(f"上下文压缩完成，tokens: {self.window.current_tokens}")
    
    def get_context_for_agent(self, agent_type: AgentType) -> Dict[str, Any]:
        """为特定Agent获取相关上下文"""
        relevant_chunks = self._filter_chunks_for_agent(agent_type)
        
        context = {}
        for chunk in relevant_chunks:
            context[chunk.chunk_id] = chunk.content
            self._update_access_history(chunk.chunk_id)
        
        return context
    
    def _filter_chunks_for_agent(self, agent_type: AgentType) -> List[ContextChunk]:
        """为Agent筛选相关的上下文块"""
        relevant_types = {
            AgentType.DATA_QUERY: ["metadata", "schema"],
            AgentType.ANALYSIS: ["data", "metadata"],
            AgentType.VISUALIZATION: ["data", "analysis"],
            AgentType.CONTENT_GENERATION: ["analysis", "summary", "data"]
        }
        
        target_types = relevant_types.get(agent_type, ["data", "analysis", "summary"])
        
        return [
            chunk for chunk in self.chunks.values()
            if chunk.content_type in target_types
        ]
    
    def _update_access_history(self, chunk_id: str) -> None:
        """更新访问历史"""
        if chunk_id in self.access_history:
            self.access_history.remove(chunk_id)
        self.access_history.append(chunk_id)
        
        # 更新访问时间
        if chunk_id in self.chunks:
            self.chunks[chunk_id].last_accessed = datetime.now()
    
    def _estimate_tokens(self, content: Any) -> int:
        """估算内容的token数量"""
        text = json.dumps(content, ensure_ascii=False) if not isinstance(content, str) else content
        # 简化估算：中文约1.5字符/token，英文约4字符/token
        return max(len(text) // 3, 10)


class HierarchicalResultAggregator:
    """分层结果聚合器"""
    
    def __init__(self, context_manager: ContextManager):
        self.context_manager = context_manager
        self.content_agent = EnhancedContentGenerationAgent()
        self.aggregation_tree = {}
    
    async def aggregate_results(self, execution_results: Dict[str, Any]) -> Dict[str, Any]:
        """分层聚合执行结果"""
        
        # 第一层：按类型分组
        grouped_results = self._group_results_by_type(execution_results)
        
        # 第二层：生成类型摘要
        type_summaries = {}
        for result_type, results in grouped_results.items():
            summary = await self._summarize_results_by_type(result_type, results)
            type_summaries[result_type] = summary
        
        # 第三层：生成整体摘要
        overall_summary = await self._create_overall_summary(type_summaries)
        
        # 构建分层结构
        hierarchical_result = {
            "overall_summary": overall_summary,
            "type_summaries": type_summaries,
            "detailed_results": self._compress_detailed_results(execution_results),
            "metadata": {
                "total_results": len(execution_results),
                "result_types": list(grouped_results.keys()),
                "compression_applied": True,
                "aggregation_timestamp": datetime.now().isoformat()
            }
        }
        
        return hierarchical_result
    
    def _group_results_by_type(self, results: Dict[str, Any]) -> Dict[str, List[Any]]:
        """按结果类型分组"""
        groups = {
            "data_query": [],
            "analysis": [],
            "visualization": [],
            "content": [],
            "other": []
        }
        
        for step_id, result in results.items():
            if "query" in step_id or "data" in step_id:
                groups["data_query"].append(result)
            elif "analysis" in step_id or "analyze" in step_id:
                groups["analysis"].append(result)
            elif "chart" in step_id or "visualization" in step_id:
                groups["visualization"].append(result)
            elif "content" in step_id or "generate" in step_id:
                groups["content"].append(result)
            else:
                groups["other"].append(result)
        
        # 移除空组
        return {k: v for k, v in groups.items() if v}
    
    async def _summarize_results_by_type(self, result_type: str, results: List[Any]) -> Dict[str, Any]:
        """按类型汇总结果"""
        if not results:
            return {}
        
        summary = {
            "count": len(results),
            "success_rate": sum(1 for r in results if r.get("success", True)) / len(results),
            "key_metrics": {},
            "insights": []
        }
        
        if result_type == "data_query":
            # 汇总数据查询结果
            total_rows = sum(r.get("row_count", 0) for r in results)
            summary["key_metrics"] = {
                "total_rows_retrieved": total_rows,
                "data_sources_accessed": len(set(r.get("data_source", "") for r in results))
            }
        
        elif result_type == "analysis":
            # 汇总分析结果
            summary["key_metrics"] = {
                "analyses_performed": len(results),
                "data_quality_average": sum(r.get("data_quality", {}).get("quality_score", 0) for r in results) / len(results)
            }
        
        elif result_type == "visualization":
            # 汇总可视化结果
            chart_types = [r.get("chart_type", "unknown") for r in results]
            summary["key_metrics"] = {
                "charts_created": len(results),
                "chart_types": list(set(chart_types))
            }
        
        return summary
    
    async def _create_overall_summary(self, type_summaries: Dict[str, Dict]) -> str:
        """创建整体摘要"""
        try:
            # 使用AI生成整体摘要
            summary_request = {
                "content_type": "executive_summary",
                "data": type_summaries,
                "format": "text",
                "max_length": 300,
                "language": "zh-CN"
            }
            
            result = await self.content_agent.execute(summary_request)
            if result.success:
                return result.data
            else:
                # 降级到模板化摘要
                return self._create_template_summary(type_summaries)
        
        except Exception as e:
            logger.warning(f"AI摘要生成失败，使用模板摘要: {e}")
            return self._create_template_summary(type_summaries)
    
    def _create_template_summary(self, type_summaries: Dict[str, Dict]) -> str:
        """创建模板化摘要"""
        parts = []
        
        for result_type, summary in type_summaries.items():
            count = summary.get("count", 0)
            success_rate = summary.get("success_rate", 0)
            
            if result_type == "data_query":
                total_rows = summary.get("key_metrics", {}).get("total_rows_retrieved", 0)
                parts.append(f"成功执行{count}个数据查询，获取{total_rows}行数据")
            
            elif result_type == "analysis":
                analyses = summary.get("key_metrics", {}).get("analyses_performed", 0)
                parts.append(f"完成{analyses}项数据分析")
            
            elif result_type == "visualization":
                charts = summary.get("key_metrics", {}).get("charts_created", 0)
                parts.append(f"生成{charts}个可视化图表")
        
        return "本次报告生成过程中，" + "，".join(parts) + "。"
    
    def _compress_detailed_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """压缩详细结果"""
        compressed = {}
        
        for step_id, result in results.items():
            # 保留关键信息，压缩详细数据
            compressed[step_id] = {
                "success": result.get("success", True),
                "execution_time": result.get("execution_time", 0),
                "data_summary": self._summarize_result_data(result.get("result", {})),
                "metadata": result.get("metadata", {})
            }
        
        return compressed
    
    def _summarize_result_data(self, data: Any) -> str:
        """汇总结果数据"""
        if isinstance(data, dict):
            if "data" in data:
                data_content = data["data"]
                if isinstance(data_content, list):
                    return f"数据集包含{len(data_content)}行记录"
                else:
                    return "结构化数据对象"
            elif "chart_data" in data:
                return f"图表数据：{data.get('chart_type', '未知类型')}"
            else:
                return f"包含{len(data)}个数据字段"
        elif isinstance(data, list):
            return f"列表数据，{len(data)}个项目"
        elif isinstance(data, str):
            return f"文本内容，{len(data)}字符"
        else:
            return "数据对象"


class ContextAwareOrchestrator(SmartOrchestrator):
    """上下文感知的Agent编排器"""
    
    def __init__(self, config: AgentConfig = None, max_tokens: int = 32000):
        super().__init__(config)
        self.context_window = ContextWindow(max_tokens=max_tokens)
        self.context_manager = ContextManager(self.context_window)
        self.result_aggregator = HierarchicalResultAggregator(self.context_manager)
    
    async def orchestrate(self, user_request: str, context: Dict[str, Any] = None) -> AgentResult:
        """上下文感知的编排执行"""
        try:
            logger.info(f"开始上下文感知编排: {user_request[:100]}...")
            
            # 添加初始上下文
            initial_chunk = ContextChunk(
                chunk_id="initial_request",
                content_type="metadata",
                content={"user_request": user_request, "context": context or {}},
                priority=10,
                token_count=self.context_manager._estimate_tokens(user_request),
                created_at=datetime.now(),
                last_accessed=datetime.now()
            )
            self.context_manager.add_chunk(initial_chunk)
            
            # 构建工作流
            workflow = await self.workflow_builder.build_workflow(user_request)
            
            # 执行工作流（带上下文管理）
            execution_results = await self._execute_workflow_with_context_management(workflow, context)
            
            # 分层汇总结果
            aggregated_result = await self.result_aggregator.aggregate_results(execution_results)
            
            # 生成最终结果
            final_result = AgentResult(
                success=any(result.success for result in execution_results.values()),
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                data=aggregated_result,
                metadata={
                    "workflow_id": workflow.workflow_id,
                    "context_tokens_used": self.context_window.current_tokens,
                    "compression_applied": self.context_window.should_compress,
                    "steps_executed": len(execution_results)
                }
            )
            
            logger.info(f"上下文感知编排完成，tokens使用: {self.context_window.current_tokens}")
            return final_result
            
        except Exception as e:
            error_msg = f"上下文感知编排失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            return AgentResult(
                success=False,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                error_message=error_msg
            )
    
    async def _execute_workflow_with_context_management(
        self, 
        workflow: Workflow, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """带上下文管理的工作流执行"""
        
        execution_results = {}
        
        for step in workflow.steps:
            try:
                # 获取Agent特定的上下文
                agent_context = self.context_manager.get_context_for_agent(step.agent_type)
                
                # 执行步骤
                result = await self._execute_step_with_context(step, agent_context)
                execution_results[step.step_id] = result
                
                # 将结果添加到上下文管理器
                if result.success:
                    result_chunk = ContextChunk(
                        chunk_id=f"result_{step.step_id}",
                        content_type=self._get_content_type_for_agent(step.agent_type),
                        content=result.result,
                        priority=self._get_priority_for_step(step),
                        token_count=self.context_manager._estimate_tokens(result.result),
                        created_at=datetime.now(),
                        last_accessed=datetime.now()
                    )
                    self.context_manager.add_chunk(result_chunk)
                
            except Exception as e:
                logger.error(f"步骤执行失败 {step.step_id}: {e}")
                execution_results[step.step_id] = type('ExecutionResult', (), {
                    'success': False,
                    'result': None,
                    'error_message': str(e),
                    'execution_time': 0.0,
                    'agent_used': step.agent_type.value
                })()
        
        return execution_results
    
    def _get_content_type_for_agent(self, agent_type: AgentType) -> str:
        """获取Agent结果的内容类型"""
        mapping = {
            AgentType.DATA_QUERY: "data",
            AgentType.ANALYSIS: "analysis", 
            AgentType.VISUALIZATION: "visualization",
            AgentType.CONTENT_GENERATION: "content"
        }
        return mapping.get(agent_type, "other")
    
    def _get_priority_for_step(self, step: WorkflowStep) -> int:
        """获取步骤的优先级"""
        # 数据查询优先级最高，内容生成其次
        priority_map = {
            AgentType.DATA_QUERY: 9,
            AgentType.ANALYSIS: 7,
            AgentType.VISUALIZATION: 5,
            AgentType.CONTENT_GENERATION: 6
        }
        return priority_map.get(step.agent_type, 5)
    
    async def _execute_step_with_context(
        self, 
        step: WorkflowStep, 
        agent_context: Dict[str, Any]
    ) -> Any:
        """带上下文的步骤执行"""
        # 这里应该调用具体的Agent执行逻辑
        # 为简化，返回模拟结果
        return type('StepResult', (), {
            'success': True,
            'result': f"模拟结果_{step.step_id}",
            'execution_time': 1.0,
            'agent_used': step.agent_type.value
        })()


# 便捷函数
async def create_context_aware_orchestrator(max_tokens: int = 32000) -> ContextAwareOrchestrator:
    """创建上下文感知编排器"""
    config = AgentConfig(
        agent_id="context_aware_orchestrator",
        agent_type=AgentType.ORCHESTRATOR,
        name="Context-Aware Agent Orchestrator",
        description="上下文感知的智能Agent编排器，支持长篇报告生成",
        timeout_seconds=600,
        enable_caching=False
    )
    
    return ContextAwareOrchestrator(config, max_tokens)


if __name__ == "__main__":
    async def test_context_aware_orchestrator():
        """测试上下文感知编排器"""
        orchestrator = await create_context_aware_orchestrator(max_tokens=16000)
        
        test_request = "生成一份包含销售数据分析、客户行为分析、产品性能报告和市场趋势预测的综合年度报告"
        
        result = await orchestrator.orchestrate(test_request)
        
        print(f"编排成功: {result.success}")
        print(f"Token使用: {result.metadata.get('context_tokens_used', 0)}")
        print(f"压缩应用: {result.metadata.get('compression_applied', False)}")
        
        if result.success:
            print("分层汇总结果:")
            data = result.data
            print(f"- 整体摘要: {data.get('overall_summary', '')[:100]}...")
            print(f"- 类型摘要数量: {len(data.get('type_summaries', {}))}")
            print(f"- 详细结果: {len(data.get('detailed_results', {}))}")
    
    asyncio.run(test_context_aware_orchestrator())