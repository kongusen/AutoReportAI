"""
统一工具生态系统
===================

统一的工具管理、发现、选择和执行引擎。
实现智能工具路由和协作执行，支持TT控制循环的工具集成。
"""

import asyncio
import logging
import importlib
import inspect
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union, Type, Callable
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """工具分类枚举"""
    LLM = "llm"
    DATA_PROCESSING = "data_processing"
    SYSTEM_OPERATIONS = "system_operations"
    ANALYSIS = "analysis"
    GENERATION = "generation"
    VALIDATION = "validation"
    VISUALIZATION = "visualization"


class ToolPriority(Enum):
    """工具优先级枚举"""
    CRITICAL = "critical"
    HIGH = "high" 
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ToolDefinition:
    """工具定义数据类"""
    name: str
    category: ToolCategory
    description: str
    tool_class: Optional[Type] = None
    capabilities: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    priority: ToolPriority = ToolPriority.MEDIUM
    performance_score: float = 0.8
    reliability_score: float = 0.9
    cost_score: float = 0.5  # 0=expensive, 1=cheap
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class SelectedTool:
    """选中的工具数据类"""
    definition: ToolDefinition
    parameters: Dict[str, Any] = field(default_factory=dict)
    execution_order: int = 0
    fallback_tools: List[str] = field(default_factory=list)
    confidence_score: float = 0.8
    selection_reason: str = ""


@dataclass
class ToolExecutionResult:
    """工具执行结果数据类"""
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class IntelligentToolSelector:
    """智能工具选择器"""
    
    def __init__(self):
        self.selection_strategies = {
            "performance_first": self._performance_first_selection,
            "reliability_first": self._reliability_first_selection,
            "cost_optimized": self._cost_optimized_selection,
            "balanced": self._balanced_selection
        }
        
    async def select_optimal_tools(
        self,
        available_tools: List[ToolDefinition],
        execution_strategy: 'ExecutionStrategy',
        context: 'SmartContext'
    ) -> List[SelectedTool]:
        """智能选择最优工具组合"""
        
        try:
            # 从执行策略获取工具偏好
            preferred_tools = execution_strategy.tool_selection
            strategy_type = execution_strategy.context_adaptations.get("selection_strategy", "balanced")
            
            # 1. 基于偏好的初步筛选
            candidate_tools = self._filter_by_preferences(available_tools, preferred_tools)
            
            # 2. 基于能力的匹配
            capability_matched = self._match_by_capabilities(candidate_tools, context)
            
            # 3. 智能选择策略
            selection_func = self.selection_strategies.get(strategy_type, self._balanced_selection)
            selected_tools = await selection_func(capability_matched, execution_strategy, context)
            
            # 4. 优化选择结果
            optimized_tools = self._optimize_tool_selection(selected_tools, execution_strategy)
            
            logger.info(f"Selected {len(optimized_tools)} tools using {strategy_type} strategy")
            return optimized_tools
            
        except Exception as e:
            logger.error(f"Tool selection failed: {e}")
            # 返回基础工具集
            return self._get_fallback_tools(available_tools)
    
    def _filter_by_preferences(
        self, 
        available_tools: List[ToolDefinition],
        preferred_tools: List[str]
    ) -> List[ToolDefinition]:
        """基于偏好筛选工具"""
        
        if not preferred_tools:
            return available_tools
        
        # 优先返回偏好工具
        preferred = []
        others = []
        
        for tool in available_tools:
            if tool.name in preferred_tools:
                preferred.append(tool)
            else:
                others.append(tool)
        
        # 按偏好顺序排序
        ordered_preferred = []
        for pref_name in preferred_tools:
            for tool in preferred:
                if tool.name == pref_name:
                    ordered_preferred.append(tool)
                    break
        
        return ordered_preferred + others
    
    def _match_by_capabilities(
        self,
        candidate_tools: List[ToolDefinition],
        context: 'SmartContext'
    ) -> List[ToolDefinition]:
        """基于能力匹配工具"""
        
        # 从上下文推断需要的能力
        required_capabilities = self._infer_required_capabilities(context)
        
        matched_tools = []
        for tool in candidate_tools:
            # 计算能力匹配度
            match_score = self._calculate_capability_match(tool.capabilities, required_capabilities)
            if match_score > 0.3:  # 阈值可配置
                tool.metadata["capability_match_score"] = match_score
                matched_tools.append(tool)
        
        # 按匹配度排序
        matched_tools.sort(key=lambda t: t.metadata.get("capability_match_score", 0), reverse=True)
        return matched_tools
    
    def _infer_required_capabilities(self, context: 'SmartContext') -> List[str]:
        """从上下文推断需要的能力"""
        capabilities = []
        
        # 基于场景推断
        scenario_capabilities = {
            "placeholder_analysis": ["text_processing", "context_analysis", "pattern_recognition"],
            "data_analysis": ["statistical_analysis", "data_processing", "pattern_detection"],
            "sql_generation": ["query_generation", "database_interaction", "syntax_validation"],
            "report_generation": ["document_generation", "data_visualization", "formatting"],
            "system_maintenance": ["system_monitoring", "file_operations", "process_management"]
        }
        
        capabilities.extend(scenario_capabilities.get(context.scenario, []))
        
        # 基于复杂度推断
        if context.complexity_level.value in ["high", "expert"]:
            capabilities.extend(["advanced_reasoning", "optimization", "error_handling"])
        
        # 基于数据敏感性推断
        if context.data_sensitivity in ["high", "confidential"]:
            capabilities.extend(["security_validation", "data_protection"])
        
        return list(set(capabilities))  # 去重
    
    def _calculate_capability_match(self, tool_capabilities: List[str], required: List[str]) -> float:
        """计算能力匹配度"""
        if not required:
            return 0.5  # 基础分数
        
        matches = len(set(tool_capabilities) & set(required))
        return matches / len(required)
    
    async def _performance_first_selection(
        self,
        tools: List[ToolDefinition],
        strategy: 'ExecutionStrategy',
        context: 'SmartContext'
    ) -> List[SelectedTool]:
        """性能优先选择策略"""
        
        # 按性能分数排序
        sorted_tools = sorted(tools, key=lambda t: t.performance_score, reverse=True)
        
        selected = []
        max_tools = strategy.performance_config.get("max_parallel_tools", 3)
        
        for i, tool in enumerate(sorted_tools[:max_tools]):
            selected.append(SelectedTool(
                definition=tool,
                execution_order=i,
                confidence_score=tool.performance_score,
                selection_reason=f"高性能工具 (score: {tool.performance_score})"
            ))
        
        return selected
    
    async def _reliability_first_selection(
        self,
        tools: List[ToolDefinition], 
        strategy: 'ExecutionStrategy',
        context: 'SmartContext'
    ) -> List[SelectedTool]:
        """可靠性优先选择策略"""
        
        sorted_tools = sorted(tools, key=lambda t: t.reliability_score, reverse=True)
        
        selected = []
        max_tools = strategy.performance_config.get("max_parallel_tools", 3)
        
        for i, tool in enumerate(sorted_tools[:max_tools]):
            selected.append(SelectedTool(
                definition=tool,
                execution_order=i,
                confidence_score=tool.reliability_score,
                selection_reason=f"高可靠性工具 (score: {tool.reliability_score})"
            ))
        
        return selected
    
    async def _cost_optimized_selection(
        self,
        tools: List[ToolDefinition],
        strategy: 'ExecutionStrategy', 
        context: 'SmartContext'
    ) -> List[SelectedTool]:
        """成本优化选择策略"""
        
        # 综合考虑成本和性能
        def cost_performance_score(tool):
            return (tool.cost_score * 0.6 + tool.performance_score * 0.4)
        
        sorted_tools = sorted(tools, key=cost_performance_score, reverse=True)
        
        selected = []
        max_tools = strategy.performance_config.get("max_parallel_tools", 3)
        
        for i, tool in enumerate(sorted_tools[:max_tools]):
            score = cost_performance_score(tool)
            selected.append(SelectedTool(
                definition=tool,
                execution_order=i,
                confidence_score=score,
                selection_reason=f"成本优化选择 (cost-perf score: {score:.2f})"
            ))
        
        return selected
    
    async def _balanced_selection(
        self,
        tools: List[ToolDefinition],
        strategy: 'ExecutionStrategy',
        context: 'SmartContext'
    ) -> List[SelectedTool]:
        """平衡选择策略"""
        
        # 综合评分：性能40% + 可靠性30% + 成本20% + 能力匹配10%
        def balanced_score(tool):
            capability_match = tool.metadata.get("capability_match_score", 0.5)
            return (
                tool.performance_score * 0.4 +
                tool.reliability_score * 0.3 + 
                tool.cost_score * 0.2 +
                capability_match * 0.1
            )
        
        sorted_tools = sorted(tools, key=balanced_score, reverse=True)
        
        selected = []
        max_tools = strategy.performance_config.get("max_parallel_tools", 3)
        
        for i, tool in enumerate(sorted_tools[:max_tools]):
            score = balanced_score(tool)
            selected.append(SelectedTool(
                definition=tool,
                execution_order=i,
                confidence_score=score,
                selection_reason=f"平衡选择 (balanced score: {score:.2f})"
            ))
        
        return selected
    
    def _optimize_tool_selection(
        self,
        selected_tools: List[SelectedTool],
        strategy: 'ExecutionStrategy'
    ) -> List[SelectedTool]:
        """优化工具选择结果"""
        
        # 1. 设置备用工具
        for selected in selected_tools:
            selected.fallback_tools = [
                tool.definition.name for tool in selected_tools 
                if tool.definition.name != selected.definition.name
            ][:2]  # 最多2个备用
        
        # 2. 优化执行顺序
        if strategy.stage_configuration.get("implementation", {}).get("execution_mode") == "parallel":
            # 并行执行：按优先级排序
            selected_tools.sort(key=lambda t: t.definition.priority.value, reverse=True)
        else:
            # 串行执行：按依赖关系排序
            selected_tools = self._sort_by_dependencies(selected_tools)
        
        # 重新设置执行顺序
        for i, tool in enumerate(selected_tools):
            tool.execution_order = i
        
        return selected_tools
    
    def _sort_by_dependencies(self, tools: List[SelectedTool]) -> List[SelectedTool]:
        """按依赖关系排序工具"""
        # 简单的拓扑排序实现
        sorted_tools = []
        remaining_tools = tools.copy()
        
        while remaining_tools:
            # 找到没有依赖或依赖已满足的工具
            ready_tools = []
            for tool in remaining_tools:
                dependencies = tool.definition.dependencies
                if not dependencies or all(
                    dep in [t.definition.name for t in sorted_tools] 
                    for dep in dependencies
                ):
                    ready_tools.append(tool)
            
            if not ready_tools:
                # 循环依赖或无法解决，直接添加剩余工具
                sorted_tools.extend(remaining_tools)
                break
            
            # 添加准备好的工具
            for tool in ready_tools:
                sorted_tools.append(tool)
                remaining_tools.remove(tool)
        
        return sorted_tools
    
    def _get_fallback_tools(self, available_tools: List[ToolDefinition]) -> List[SelectedTool]:
        """获取兜底工具"""
        logger.warning("Using fallback tool selection")
        
        # 返回最基础的工具
        fallback_names = ["reasoning_tool", "data_analyzer", "file_tool"]
        fallback_tools = []
        
        for name in fallback_names:
            for tool in available_tools:
                if tool.name == name:
                    fallback_tools.append(SelectedTool(
                        definition=tool,
                        confidence_score=0.6,
                        selection_reason="Fallback selection"
                    ))
                    break
        
        return fallback_tools or [SelectedTool(
            definition=available_tools[0] if available_tools else ToolDefinition("default", ToolCategory.LLM, "Default tool"),
            confidence_score=0.5,
            selection_reason="Last resort fallback"
        )]


class ToolExecutionEngine:
    """工具执行引擎"""
    
    def __init__(self):
        self.execution_cache = {}
        self.performance_stats = {}
    
    async def execute_with_coordination(
        self,
        selected_tools: List[SelectedTool],
        execution_context: 'TTContext'
    ) -> List[ToolExecutionResult]:
        """协调执行工具"""
        
        results = []
        
        try:
            # 根据执行模式选择策略
            execution_mode = execution_context.context_data.get("execution_mode", "sequential")
            
            if execution_mode == "parallel":
                results = await self._execute_parallel(selected_tools, execution_context)
            else:
                results = await self._execute_sequential(selected_tools, execution_context)
            
            # 更新性能统计
            self._update_performance_stats(results)
            
            return results
            
        except Exception as e:
            logger.error(f"Tool execution coordination failed: {e}")
            return [ToolExecutionResult(
                tool_name="coordination_error",
                success=False,
                error=str(e)
            )]
    
    async def _execute_parallel(
        self,
        selected_tools: List[SelectedTool], 
        context: 'TTContext'
    ) -> List[ToolExecutionResult]:
        """并行执行工具"""
        
        tasks = []
        for selected_tool in selected_tools:
            task = self._execute_single_tool(selected_tool, context)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ToolExecutionResult(
                    tool_name=selected_tools[i].definition.name,
                    success=False,
                    error=str(result)
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _execute_sequential(
        self,
        selected_tools: List[SelectedTool],
        context: 'TTContext'
    ) -> List[ToolExecutionResult]:
        """串行执行工具"""
        
        results = []
        
        for selected_tool in selected_tools:
            try:
                result = await self._execute_single_tool(selected_tool, context)
                results.append(result)
                
                # 如果工具执行失败且有备用工具，尝试备用
                if not result.success and selected_tool.fallback_tools:
                    logger.info(f"Tool {selected_tool.definition.name} failed, trying fallbacks")
                    for fallback_name in selected_tool.fallback_tools:
                        # TODO: 实现备用工具执行逻辑
                        pass
                
            except Exception as e:
                results.append(ToolExecutionResult(
                    tool_name=selected_tool.definition.name,
                    success=False,
                    error=str(e)
                ))
        
        return results
    
    async def _execute_single_tool(
        self,
        selected_tool: SelectedTool,
        context: 'TTContext'
    ) -> ToolExecutionResult:
        """执行单个工具"""
        
        start_time = datetime.utcnow()
        
        try:
            # 创建工具实例
            tool_instance = await self._create_tool_instance(selected_tool.definition)
            
            if not tool_instance:
                return ToolExecutionResult(
                    tool_name=selected_tool.definition.name,
                    success=False,
                    error="Failed to create tool instance"
                )
            
            # 准备执行参数
            execution_params = self._prepare_execution_params(selected_tool, context)
            
            # 执行工具
            if hasattr(tool_instance, 'execute'):
                if asyncio.iscoroutinefunction(tool_instance.execute):
                    result = await tool_instance.execute(execution_params, context)
                else:
                    result = tool_instance.execute(execution_params, context)
            else:
                raise Exception(f"Tool {selected_tool.definition.name} does not have execute method")
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return ToolExecutionResult(
                tool_name=selected_tool.definition.name,
                success=True,
                result=result,
                execution_time=execution_time,
                metadata={
                    "parameters": execution_params,
                    "confidence": selected_tool.confidence_score
                }
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Tool execution failed for {selected_tool.definition.name}: {e}")
            
            return ToolExecutionResult(
                tool_name=selected_tool.definition.name,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    async def _create_tool_instance(self, tool_def: ToolDefinition):
        """创建工具实例"""
        try:
            if tool_def.tool_class:
                return tool_def.tool_class()
            
            # 尝试从工具注册表动态加载
            # TODO: 实现工具动态加载逻辑
            return None
            
        except Exception as e:
            logger.error(f"Failed to create tool instance for {tool_def.name}: {e}")
            return None
    
    def _prepare_execution_params(
        self,
        selected_tool: SelectedTool,
        context: 'TTContext'
    ) -> Dict[str, Any]:
        """准备执行参数"""
        
        base_params = {
            "task_description": context.task_description,
            "context": context.context_data,
            "user_id": context.user_id
        }
        
        # 合并工具特定参数
        base_params.update(selected_tool.parameters)
        
        return base_params
    
    def _update_performance_stats(self, results: List[ToolExecutionResult]):
        """更新性能统计"""
        for result in results:
            tool_name = result.tool_name
            if tool_name not in self.performance_stats:
                self.performance_stats[tool_name] = {
                    "total_executions": 0,
                    "successful_executions": 0,
                    "total_time": 0.0,
                    "average_time": 0.0
                }
            
            stats = self.performance_stats[tool_name]
            stats["total_executions"] += 1
            if result.success:
                stats["successful_executions"] += 1
            stats["total_time"] += result.execution_time
            stats["average_time"] = stats["total_time"] / stats["total_executions"]


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self.registered_tools: Dict[str, ToolDefinition] = {}
        self.category_index: Dict[ToolCategory, List[str]] = {cat: [] for cat in ToolCategory}
        self.capability_index: Dict[str, List[str]] = {}
        
        # 自动发现系统工具
        self._discover_system_tools()
    
    def register_tool(self, tool_def: ToolDefinition) -> bool:
        """注册工具"""
        try:
            self.registered_tools[tool_def.name] = tool_def
            
            # 更新分类索引
            if tool_def.name not in self.category_index[tool_def.category]:
                self.category_index[tool_def.category].append(tool_def.name)
            
            # 更新能力索引
            for capability in tool_def.capabilities:
                if capability not in self.capability_index:
                    self.capability_index[capability] = []
                if tool_def.name not in self.capability_index[capability]:
                    self.capability_index[capability].append(tool_def.name)
            
            logger.info(f"Registered tool: {tool_def.name} ({tool_def.category.value})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register tool {tool_def.name}: {e}")
            return False
    
    def discover_tools_for_context(self, context: 'SmartContext') -> List[ToolDefinition]:
        """为上下文发现相关工具"""
        
        relevant_tools = []
        
        # 1. 基于场景的工具发现
        scenario_tools = self._get_tools_by_scenario(context.scenario)
        relevant_tools.extend(scenario_tools)
        
        # 2. 基于能力的工具发现
        required_capabilities = self._infer_capabilities_from_context(context)
        for capability in required_capabilities:
            if capability in self.capability_index:
                for tool_name in self.capability_index[capability]:
                    if tool_name in self.registered_tools:
                        tool_def = self.registered_tools[tool_name]
                        if tool_def not in relevant_tools:
                            relevant_tools.append(tool_def)
        
        # 3. 基于分类的工具发现
        relevant_categories = self._get_relevant_categories(context)
        for category in relevant_categories:
            for tool_name in self.category_index[category]:
                tool_def = self.registered_tools[tool_name]
                if tool_def not in relevant_tools:
                    relevant_tools.append(tool_def)
        
        # 4. 去重和排序
        unique_tools = list({tool.name: tool for tool in relevant_tools}.values())
        
        logger.info(f"Discovered {len(unique_tools)} relevant tools for scenario: {context.scenario}")
        return unique_tools
    
    def _discover_system_tools(self):
        """自动发现系统工具"""
        try:
            # 发现LLM工具
            self._register_llm_tools()
            
            # 发现数据处理工具
            self._register_data_tools()
            
            # 发现系统操作工具
            self._register_system_tools()
            
            logger.info(f"Auto-discovered {len(self.registered_tools)} system tools")
            
        except Exception as e:
            logger.error(f"Tool discovery failed: {e}")
    
    def _register_llm_tools(self):
        """注册LLM工具"""
        # TODO: 动态发现LLM工具
        llm_tools = [
            ToolDefinition(
                name="reasoning_tool",
                category=ToolCategory.LLM,
                description="LLM reasoning and analysis tool",
                capabilities=["reasoning", "analysis", "text_processing"],
                priority=ToolPriority.HIGH,
                performance_score=0.9,
                reliability_score=0.85
            ),
            ToolDefinition(
                name="llm_execution_tool", 
                category=ToolCategory.LLM,
                description="General LLM execution tool",
                capabilities=["text_generation", "question_answering", "summarization"],
                priority=ToolPriority.MEDIUM,
                performance_score=0.8,
                reliability_score=0.9
            )
        ]
        
        for tool in llm_tools:
            self.register_tool(tool)
    
    def _register_data_tools(self):
        """注册数据处理工具"""
        data_tools = [
            ToolDefinition(
                name="sql_generator",
                category=ToolCategory.DATA_PROCESSING,
                description="SQL query generation tool",
                capabilities=["sql_generation", "query_optimization", "database_interaction"],
                priority=ToolPriority.HIGH,
                performance_score=0.85,
                reliability_score=0.9
            ),
            ToolDefinition(
                name="data_analyzer",
                category=ToolCategory.ANALYSIS,
                description="Data analysis and statistics tool", 
                capabilities=["statistical_analysis", "data_processing", "pattern_detection"],
                priority=ToolPriority.MEDIUM,
                performance_score=0.8,
                reliability_score=0.85
            ),
            ToolDefinition(
                name="placeholder_analyzer",
                category=ToolCategory.ANALYSIS,
                description="Placeholder analysis and context extraction",
                capabilities=["text_processing", "context_analysis", "placeholder_resolution"],
                priority=ToolPriority.MEDIUM,
                performance_score=0.75,
                reliability_score=0.8
            )
        ]
        
        for tool in data_tools:
            self.register_tool(tool)
    
    def _register_system_tools(self):
        """注册系统操作工具"""
        system_tools = [
            ToolDefinition(
                name="file_tool",
                category=ToolCategory.SYSTEM_OPERATIONS,
                description="File system operations",
                capabilities=["file_operations", "data_persistence", "file_management"],
                priority=ToolPriority.LOW,
                performance_score=0.9,
                reliability_score=0.95
            ),
            ToolDefinition(
                name="bash_tool",
                category=ToolCategory.SYSTEM_OPERATIONS,
                description="System command execution",
                capabilities=["command_execution", "system_monitoring", "process_management"],
                priority=ToolPriority.LOW,
                performance_score=0.8,
                reliability_score=0.9
            )
        ]
        
        for tool in system_tools:
            self.register_tool(tool)
    
    def _get_tools_by_scenario(self, scenario: str) -> List[ToolDefinition]:
        """根据场景获取工具"""
        scenario_mappings = {
            "placeholder_analysis": ["placeholder_analyzer", "reasoning_tool"],
            "data_analysis": ["data_analyzer", "reasoning_tool", "sql_generator"],
            "sql_generation": ["sql_generator", "reasoning_tool"],
            "report_generation": ["data_analyzer", "reasoning_tool"],
            "system_maintenance": ["bash_tool", "file_tool"]
        }
        
        tool_names = scenario_mappings.get(scenario, ["reasoning_tool"])
        return [self.registered_tools[name] for name in tool_names if name in self.registered_tools]
    
    def _infer_capabilities_from_context(self, context: 'SmartContext') -> List[str]:
        """从上下文推断需要的能力"""
        # 复用IntelligentToolSelector的逻辑
        selector = IntelligentToolSelector()
        return selector._infer_required_capabilities(context)
    
    def _get_relevant_categories(self, context: 'SmartContext') -> List[ToolCategory]:
        """获取相关的工具分类"""
        categories = [ToolCategory.LLM]  # 默认包含LLM工具
        
        if context.scenario in ["data_analysis", "sql_generation", "placeholder_analysis"]:
            categories.extend([ToolCategory.DATA_PROCESSING, ToolCategory.ANALYSIS])
        
        if context.scenario == "system_maintenance":
            categories.append(ToolCategory.SYSTEM_OPERATIONS)
        
        if context.complexity_level.value in ["high", "expert"]:
            categories.extend([ToolCategory.ANALYSIS, ToolCategory.VALIDATION])
        
        return categories


class UnifiedToolEcosystem:
    """
    统一工具生态系统
    
    核心功能：
    1. 统一工具管理和注册
    2. 智能工具发现和选择  
    3. 协调工具执行
    4. 性能监控和优化
    """
    
    def __init__(self):
        self.tool_registry = ToolRegistry()
        self.tool_selector = IntelligentToolSelector()
        self.execution_engine = ToolExecutionEngine()
        
        logger.info("UnifiedToolEcosystem initialized")
    
    async def discover_and_select_tools(
        self, 
        task_context: 'SmartContext',
        execution_strategy: 'ExecutionStrategy'
    ) -> List[SelectedTool]:
        """发现和选择工具"""
        
        # 1. 自动工具发现
        available_tools = self.tool_registry.discover_tools_for_context(task_context)
        
        # 2. 智能工具选择
        selected_tools = await self.tool_selector.select_optimal_tools(
            available_tools,
            execution_strategy,
            task_context
        )
        
        logger.info(f"Selected {len(selected_tools)} tools from {len(available_tools)} available")
        return selected_tools
    
    async def execute_tools_with_strategy(
        self,
        selected_tools: List[SelectedTool],
        execution_context: 'TTContext'
    ) -> List[ToolExecutionResult]:
        """按策略执行工具"""
        return await self.execution_engine.execute_with_coordination(
            selected_tools, execution_context
        )
    
    def register_custom_tool(self, tool_def: ToolDefinition) -> bool:
        """注册自定义工具"""
        return self.tool_registry.register_tool(tool_def)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return {
            "registered_tools": len(self.tool_registry.registered_tools),
            "tool_performance": self.execution_engine.performance_stats,
            "category_distribution": {
                cat.value: len(tools) 
                for cat, tools in self.tool_registry.category_index.items()
            }
        }


# 便利函数
def create_tool_definition(
    name: str,
    category: ToolCategory,
    description: str,
    **kwargs
) -> ToolDefinition:
    """快速创建工具定义"""
    return ToolDefinition(
        name=name,
        category=category, 
        description=description,
        **kwargs
    )


__all__ = [
    "UnifiedToolEcosystem",
    "ToolRegistry",
    "IntelligentToolSelector", 
    "ToolExecutionEngine",
    "ToolDefinition",
    "SelectedTool",
    "ToolExecutionResult",
    "ToolCategory",
    "ToolPriority",
    "create_tool_definition"
]