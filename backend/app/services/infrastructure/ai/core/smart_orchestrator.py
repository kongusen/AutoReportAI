"""
智能提示词感知编排器 v3.0
====================================

基于提示词感知的智能编排，替代传统ReAct模式：
- 一次性智能分析和工具选择
- 深度上下文集成
- 自适应执行策略
- 企业级提示词优化
- 高性能执行路径

设计理念：
1. 智能 > 机械循环
2. 上下文丰富 > 简单推理
3. 一次到位 > 多轮迭代
4. 结果导向 > 过程导向
"""

import logging
import json
import uuid
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

from .tools import ToolChain, ToolContext, ToolResult, ToolResultType
from .prompts import PromptComplexity, get_prompt_manager
from .prompt_monitor import get_prompt_monitor
from ..llm import ask_agent_for_user

logger = logging.getLogger(__name__)


class ExecutionStrategy(Enum):
    """执行策略"""
    DIRECT = "direct"               # 直接执行单个工具
    SEQUENTIAL = "sequential"       # 顺序执行多个工具
    PARALLEL = "parallel"          # 并行执行多个工具
    ADAPTIVE = "adaptive"          # 自适应执行（基于中间结果调整）
    FALLBACK = "fallback"          # 回退策略（主策略失败时）


class ContextAnalysisLevel(Enum):
    """上下文分析级别"""
    BASIC = "basic"           # 基础分析：占位符 + 数据源
    STANDARD = "standard"     # 标准分析：+ 模板上下文
    COMPREHENSIVE = "comprehensive"  # 全面分析：+ 历史 + 学习
    EXPERT = "expert"         # 专家级：+ 性能优化 + 预测


@dataclass
class ContextEnrichment:
    """上下文丰富化信息"""
    # 基础信息
    placeholder_analysis: Dict[str, Any] = field(default_factory=dict)
    data_source_analysis: Dict[str, Any] = field(default_factory=dict)
    template_analysis: Dict[str, Any] = field(default_factory=dict)
    
    # 历史信息
    similar_tasks_history: List[Dict[str, Any]] = field(default_factory=list)
    success_patterns: List[str] = field(default_factory=list)
    failure_patterns: List[str] = field(default_factory=list)
    
    # 性能信息
    estimated_complexity: str = "medium"
    estimated_execution_time: Optional[float] = None
    performance_hints: List[str] = field(default_factory=list)
    
    # 业务信息
    business_context: str = ""
    domain_knowledge: List[str] = field(default_factory=list)


@dataclass
class IntelligentExecutionPlan:
    """智能执行计划"""
    strategy: ExecutionStrategy
    tools_sequence: List[str]
    tool_parameters: Dict[str, Dict[str, Any]]
    
    # 执行配置
    estimated_steps: int
    estimated_time: float
    confidence_threshold: float
    
    # 回退计划
    fallback_strategy: Optional[ExecutionStrategy] = None
    fallback_tools: List[str] = field(default_factory=list)
    
    # 优化设置
    enable_caching: bool = True
    enable_parallel: bool = False
    max_retries: int = 2


class SmartPrompAwareOrchestrator:
    """智能提示词感知编排器"""
    
    def __init__(self, tool_chain: ToolChain):
        self.tool_chain = tool_chain
        self.prompt_manager = get_prompt_manager()
        self.monitor = get_prompt_monitor()
        self.logger = logging.getLogger(f"{__name__}.SmartOrchestrator")
        
        # 智能缓存
        self.execution_cache = {}
        self.pattern_cache = {}
        
        # 性能统计
        self.total_executions = 0
        self.successful_executions = 0
        self.average_execution_time = 0.0
    
    async def smart_orchestrate(
        self,
        goal: str,
        context: ToolContext,
        analysis_level: ContextAnalysisLevel = ContextAnalysisLevel.STANDARD,
        available_tools: Optional[List[str]] = None,
        force_strategy: Optional[ExecutionStrategy] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        智能编排主入口
        
        核心思想：一次性深度分析 + 智能执行计划 + 高效执行
        """
        
        execution_id = f"smart_{uuid.uuid4().hex[:8]}"
        start_time = datetime.utcnow()
        self.total_executions += 1
        
        self.logger.info(f"🧠 启动智能提示词感知编排 {execution_id}")
        self.logger.info(f"🎯 目标: {goal[:100]}...")
        self.logger.info(f"📊 分析级别: {analysis_level.value}")
        
        try:
            # 阶段1: 深度上下文分析和丰富化
            if progress_callback:
                progress_callback(10, "深度上下文分析", "context_analysis")
            
            enriched_context = await self._deep_context_analysis(
                goal, context, analysis_level
            )
            
            # 阶段2: 智能执行计划生成
            if progress_callback:
                progress_callback(30, "生成智能执行计划", "plan_generation")
            
            execution_plan = await self._generate_intelligent_plan(
                goal, context, enriched_context, available_tools, force_strategy
            )
            
            self.logger.info(f"📋 执行计划: {execution_plan.strategy.value}")
            self.logger.info(f"🔧 工具序列: {execution_plan.tools_sequence}")
            self.logger.info(f"⏱️ 预估时间: {execution_plan.estimated_time:.1f}秒")
            
            # 阶段3: 高效执行
            if progress_callback:
                progress_callback(50, "执行智能计划", "execution")
            
            execution_result = await self._execute_intelligent_plan(
                execution_plan, context, enriched_context, progress_callback
            )
            
            # 阶段4: 结果处理和学习
            if progress_callback:
                progress_callback(90, "处理结果和学习", "learning")
            
            final_result = await self._process_results_and_learn(
                execution_result, execution_plan, enriched_context, context
            )
            
            # 更新性能统计
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_performance_stats(execution_time, final_result.get("status") == "success")
            
            if progress_callback:
                progress_callback(100, "编排完成", "completed")
            
            # 丰富返回结果
            final_result.update({
                "execution_id": execution_id,
                "execution_time": execution_time,
                "plan_used": execution_plan,
                "context_enrichment": enriched_context,
                "performance_stats": {
                    "total_executions": self.total_executions,
                    "success_rate": self.successful_executions / self.total_executions,
                    "average_time": self.average_execution_time
                }
            })
            
            self.logger.info(f"✅ 智能编排完成 {execution_id}: {final_result.get('status')}")
            return final_result
            
        except Exception as e:
            self.logger.error(f"❌ 智能编排失败 {execution_id}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "execution_id": execution_id,
                "execution_time": (datetime.utcnow() - start_time).total_seconds()
            }
    
    async def _deep_context_analysis(
        self,
        goal: str,
        context: ToolContext,
        analysis_level: ContextAnalysisLevel
    ) -> ContextEnrichment:
        """深度上下文分析和丰富化"""
        
        self.logger.info(f"🔍 开始深度上下文分析: {analysis_level.value}")
        
        enrichment = ContextEnrichment()
        
        # 基础分析：占位符和数据源
        if analysis_level.value in ["basic", "standard", "comprehensive", "expert"]:
            enrichment.placeholder_analysis = await self._analyze_placeholder_context(goal, context)
            enrichment.data_source_analysis = await self._analyze_data_source_context(context)
        
        # 标准分析：添加模板分析
        if analysis_level.value in ["standard", "comprehensive", "expert"]:
            enrichment.template_analysis = await self._analyze_template_context(context)
            enrichment.business_context = self._extract_business_context(goal, context)
        
        # 全面分析：添加历史和学习
        if analysis_level.value in ["comprehensive", "expert"]:
            enrichment.similar_tasks_history = await self._find_similar_tasks(goal, context)
            enrichment.success_patterns = self._extract_success_patterns(enrichment.similar_tasks_history)
            enrichment.failure_patterns = self._extract_failure_patterns(enrichment.similar_tasks_history)
        
        # 专家级分析：添加性能优化
        if analysis_level.value == "expert":
            enrichment.estimated_complexity = self._estimate_task_complexity(goal, enrichment)
            enrichment.estimated_execution_time = self._estimate_execution_time(enrichment)
            enrichment.performance_hints = self._generate_performance_hints(enrichment)
            enrichment.domain_knowledge = await self._extract_domain_knowledge(goal, context)
        
        self.logger.info(f"✅ 上下文分析完成:")
        self.logger.info(f"   - 占位符分析: {len(enrichment.placeholder_analysis)} 项")
        self.logger.info(f"   - 数据源分析: {len(enrichment.data_source_analysis)} 项")
        self.logger.info(f"   - 历史任务: {len(enrichment.similar_tasks_history)} 个")
        self.logger.info(f"   - 成功模式: {len(enrichment.success_patterns)} 个")
        
        return enrichment
    
    async def _generate_intelligent_plan(
        self,
        goal: str,
        context: ToolContext,
        enrichment: ContextEnrichment,
        available_tools: Optional[List[str]],
        force_strategy: Optional[ExecutionStrategy]
    ) -> IntelligentExecutionPlan:
        """生成智能执行计划"""
        
        self.logger.info("🧠 生成智能执行计划...")
        
        # 构建超级丰富的提示词上下文
        planning_context = {
            "goal": goal,
            "available_tools": available_tools or self.tool_chain.list_tools(),
            "placeholder_analysis": enrichment.placeholder_analysis,
            "data_source_analysis": enrichment.data_source_analysis,
            "template_analysis": enrichment.template_analysis,
            "business_context": enrichment.business_context,
            "similar_tasks": enrichment.similar_tasks_history[-3:],  # 最近3个相似任务
            "success_patterns": enrichment.success_patterns,
            "failure_patterns": enrichment.failure_patterns,
            "estimated_complexity": enrichment.estimated_complexity,
            "performance_hints": enrichment.performance_hints,
            "domain_knowledge": enrichment.domain_knowledge,
            "force_strategy": force_strategy.value if force_strategy else None
        }
        
        # 评估提示词复杂度
        prompt_complexity = self._assess_planning_complexity(enrichment)
        
        # 使用企业级提示词系统生成执行计划
        planning_prompt = self._build_planning_prompt(planning_context, prompt_complexity)
        
        try:
            # 调用LLM生成执行计划
            response = await ask_agent_for_user(
                user_id=context.user_id,
                question=planning_prompt,
                agent_type="smart_planner",
                task_type="execution_planning",
                complexity=prompt_complexity.value
            )
            
            # 解析执行计划
            plan = self._parse_execution_plan(response, available_tools or self.tool_chain.list_tools())
            
            # 验证和优化计划
            validated_plan = self._validate_and_optimize_plan(plan, enrichment)
            
            self.logger.info(f"✅ 执行计划生成完成: {validated_plan.strategy.value}")
            return validated_plan
            
        except Exception as e:
            self.logger.error(f"❌ 执行计划生成失败: {e}")
            # 回退到基础计划
            return self._generate_fallback_plan(goal, available_tools or self.tool_chain.list_tools())
    
    def _build_planning_prompt(
        self,
        planning_context: Dict[str, Any],
        complexity: PromptComplexity
    ) -> str:
        """构建执行计划生成提示词"""
        
        # 使用企业级提示词系统
        try:
            return self.prompt_manager.get_prompt(
                category="orchestration",
                prompt_type="intelligent_planning",
                context=planning_context,
                complexity=complexity
            )
        except Exception as e:
            self.logger.warning(f"获取企业级规划提示词失败: {e}")
            return self._build_basic_planning_prompt(planning_context)
    
    def _build_basic_planning_prompt(self, planning_context: Dict[str, Any]) -> str:
        """构建基础规划提示词（回退方案）"""
        
        goal = planning_context["goal"]
        available_tools = planning_context["available_tools"]
        business_context = planning_context.get("business_context", "")
        success_patterns = planning_context.get("success_patterns", [])
        
        return f"""
你是一个智能任务规划器，需要为以下任务制定最优执行计划。

【任务目标】: {goal}

【业务上下文】: {business_context}

【可用工具】: {', '.join(available_tools)}

【成功模式】:
{chr(10).join([f'- {pattern}' for pattern in success_patterns[:3]])}

【规划要求】:
1. 分析任务需求，选择最合适的工具组合
2. 确定执行策略（direct/sequential/parallel/adaptive）
3. 预估执行时间和复杂度
4. 提供回退方案

请返回JSON格式的执行计划:
{{
    "strategy": "执行策略",
    "tools_sequence": ["工具1", "工具2"],
    "tool_parameters": {{
        "工具1": {{"参数1": "值1"}},
        "工具2": {{"参数2": "值2"}}
    }},
    "estimated_steps": 数字,
    "estimated_time": 数字,
    "confidence_threshold": 0.8,
    "reasoning": "选择理由"
}}
"""
    
    async def _execute_intelligent_plan(
        self,
        plan: IntelligentExecutionPlan,
        context: ToolContext,
        enrichment: ContextEnrichment,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """执行智能计划"""
        
        self.logger.info(f"⚡ 开始执行智能计划: {plan.strategy.value}")
        
        if plan.strategy == ExecutionStrategy.DIRECT:
            return await self._execute_direct_strategy(plan, context, progress_callback)
        elif plan.strategy == ExecutionStrategy.SEQUENTIAL:
            return await self._execute_sequential_strategy(plan, context, progress_callback)
        elif plan.strategy == ExecutionStrategy.PARALLEL:
            return await self._execute_parallel_strategy(plan, context, progress_callback)
        elif plan.strategy == ExecutionStrategy.ADAPTIVE:
            return await self._execute_adaptive_strategy(plan, context, enrichment, progress_callback)
        else:
            return await self._execute_fallback_strategy(plan, context, progress_callback)
    
    async def _execute_direct_strategy(
        self,
        plan: IntelligentExecutionPlan,
        context: ToolContext,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """执行直接策略：单工具直接执行"""
        
        if not plan.tools_sequence:
            return {"status": "error", "error": "没有指定执行工具"}
        
        tool_name = plan.tools_sequence[0]
        tool_params = plan.tool_parameters.get(tool_name, {})
        
        self.logger.info(f"🔧 直接执行工具: {tool_name}")
        
        try:
            results = []
            async for result in self.tool_chain.execute_tool(tool_name, tool_params, context):
                results.append(result)
                
                if progress_callback and result.type == ToolResultType.PROGRESS:
                    progress_callback(70, f"执行 {tool_name}: {result.data}", "tool_execution")
            
            # 获取最终结果
            final_result = None
            for result in reversed(results):
                if result.type == ToolResultType.RESULT:
                    final_result = result
                    break
            
            if final_result:
                return {
                    "status": "success",
                    "strategy": "direct",
                    "tool_used": tool_name,
                    "result": final_result.data,
                    "confidence": getattr(final_result, 'confidence', 0.8),
                    "execution_details": {
                        "total_results": len(results),
                        "tool_parameters": tool_params
                    }
                }
            else:
                return {
                    "status": "error",
                    "error": f"工具 {tool_name} 未返回有效结果",
                    "tool_used": tool_name,
                    "total_results": len(results)
                }
                
        except Exception as e:
            self.logger.error(f"❌ 直接执行失败: {e}")
            return {
                "status": "error",
                "error": str(e),
                "tool_used": tool_name
            }
    
    # 辅助方法
    def _assess_planning_complexity(self, enrichment: ContextEnrichment) -> PromptComplexity:
        """评估规划提示词复杂度"""
        
        complexity_score = 0
        
        # 基于上下文丰富度评估
        if len(enrichment.placeholder_analysis) > 5:
            complexity_score += 1
        if len(enrichment.data_source_analysis) > 10:
            complexity_score += 1
        if len(enrichment.similar_tasks_history) > 3:
            complexity_score += 1
        if enrichment.estimated_complexity == "high":
            complexity_score += 2
        
        if complexity_score >= 4:
            return PromptComplexity.CRITICAL
        elif complexity_score >= 2:
            return PromptComplexity.HIGH
        else:
            return PromptComplexity.MEDIUM
    
    def _update_performance_stats(self, execution_time: float, success: bool):
        """更新性能统计"""
        if success:
            self.successful_executions += 1
        
        # 更新平均执行时间
        self.average_execution_time = (
            (self.average_execution_time * (self.total_executions - 1) + execution_time) /
            self.total_executions
        )
    
    # 更多辅助方法...
    async def _analyze_placeholder_context(self, goal: str, context: ToolContext) -> Dict[str, Any]:
        """分析占位符上下文"""
        # 简化实现
        return {
            "goal_keywords": goal.split()[:10],
            "placeholder_count": len(getattr(context, 'placeholders', [])),
            "complexity": "medium"
        }
    
    async def _analyze_data_source_context(self, context: ToolContext) -> Dict[str, Any]:
        """分析数据源上下文"""
        data_source_info = getattr(context, 'data_source_info', {})
        return {
            "table_count": len(data_source_info.get('tables', [])),
            "total_columns": sum(t.get('columns_count', 0) for t in data_source_info.get('table_details', [])),
            "data_volume": "large" if len(data_source_info.get('tables', [])) > 10 else "medium"
        }


# 全局实例
_smart_orchestrator: Optional[SmartPrompAwareOrchestrator] = None


def get_smart_orchestrator() -> SmartPrompAwareOrchestrator:
    """获取智能编排器实例"""
    global _smart_orchestrator
    if _smart_orchestrator is None:
        from .tools import ToolChain
        tool_chain = ToolChain()
        _smart_orchestrator = SmartPrompAwareOrchestrator(tool_chain)
    return _smart_orchestrator


async def smart_tt(
    goal: str,
    context: ToolContext,
    analysis_level: ContextAnalysisLevel = ContextAnalysisLevel.STANDARD,
    available_tools: Optional[List[str]] = None,
    force_strategy: Optional[ExecutionStrategy] = None,
    progress_callback: Optional[callable] = None
) -> Dict[str, Any]:
    """
    智能提示词感知编排函数 - 新一代tt函数
    
    相比ReAct的优势：
    1. 一次性深度分析，避免多轮低效推理
    2. 丰富上下文集成，提高决策质量
    3. 智能执行策略，优化性能表现
    4. 企业级提示词，保证输出质量
    """
    orchestrator = get_smart_orchestrator()
    return await orchestrator.smart_orchestrate(
        goal=goal,
        context=context,
        analysis_level=analysis_level,
        available_tools=available_tools,
        force_strategy=force_strategy,
        progress_callback=progress_callback
    )


# 便捷导入
__all__ = [
    "SmartPrompAwareOrchestrator",
    "ExecutionStrategy",
    "ContextAnalysisLevel", 
    "ContextEnrichment",
    "IntelligentExecutionPlan",
    "get_smart_orchestrator",
    "smart_tt"
]