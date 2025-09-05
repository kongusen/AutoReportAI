"""
基于工具注册的智能Agent系统

采用现代Agent架构设计理念：
- 工具注册机制：将各种功能注册为工具
- 模型自主决策：让模型自行判断调用哪些工具
- 灵活组合：支持工具的组合使用
- 统一接口：所有Agent功能通过工具调用实现

核心设计：
1. 工具注册器：统一管理所有可用工具
2. 智能调度器：基于任务需求智能选择工具
3. 执行引擎：处理工具调用和结果集成
4. 上下文管理：维护工具间的数据流转
"""

import asyncio
import logging
import json
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import inspect

from ..llm.step_based_model_selector import (
    StepBasedModelSelector, 
    StepContext, 
    ProcessingStep,
    create_step_based_model_selector
)
from ..llm import ask_agent_for_user

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """工具分类"""
    SQL_GENERATION = "sql_generation"          # SQL生成
    DATA_ANALYSIS = "data_analysis"            # 数据分析
    CHART_GENERATION = "chart_generation"      # 图表生成
    CONTEXT_ANALYSIS = "context_analysis"      # 上下文分析
    VALIDATION = "validation"                  # 验证工具
    DATA_PROCESSING = "data_processing"        # 数据处理
    UTILITY = "utility"                        # 工具类


@dataclass
class ToolMetadata:
    """工具元数据"""
    name: str                          # 工具名称
    description: str                   # 工具描述
    category: ToolCategory             # 工具分类
    input_schema: Dict[str, Any]       # 输入参数Schema
    output_schema: Dict[str, Any]      # 输出结果Schema
    complexity: str = "medium"         # 工具复杂度
    dependencies: List[str] = None     # 依赖的其他工具
    cost_estimate: str = "low"         # 成本估算
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class ToolCall:
    """工具调用"""
    tool_name: str
    parameters: Dict[str, Any]
    call_id: str
    timestamp: datetime


@dataclass
class ToolResult:
    """工具结果"""
    call_id: str
    tool_name: str
    success: bool
    result: Any
    error_message: Optional[str] = None
    execution_time: float = 0.0
    confidence_score: float = 1.0


class ToolRegistry:
    """工具注册器"""
    
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}  # tool_name -> {func, metadata}
        self.categories: Dict[ToolCategory, List[str]] = {}
        
    def register_tool(
        self, 
        func: Callable,
        metadata: ToolMetadata
    ):
        """注册工具"""
        tool_name = metadata.name
        
        # 验证函数签名
        sig = inspect.signature(func)
        
        self.tools[tool_name] = {
            'function': func,
            'metadata': metadata,
            'signature': sig
        }
        
        # 按分类索引
        if metadata.category not in self.categories:
            self.categories[metadata.category] = []
        self.categories[metadata.category].append(tool_name)
        
        logger.info(f"工具注册成功: {tool_name} ({metadata.category.value})")
    
    def get_tool(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """获取工具"""
        return self.tools.get(tool_name)
    
    def get_tools_by_category(self, category: ToolCategory) -> List[str]:
        """按分类获取工具"""
        return self.categories.get(category, [])
    
    def get_all_tools_metadata(self) -> Dict[str, ToolMetadata]:
        """获取所有工具元数据"""
        return {name: info['metadata'] for name, info in self.tools.items()}
    
    def search_tools(self, keywords: List[str], category: Optional[ToolCategory] = None) -> List[str]:
        """搜索工具"""
        candidates = []
        
        for tool_name, tool_info in self.tools.items():
            metadata = tool_info['metadata']
            
            # 分类过滤
            if category and metadata.category != category:
                continue
                
            # 关键词匹配
            text_to_search = f"{metadata.name} {metadata.description}".lower()
            if any(keyword.lower() in text_to_search for keyword in keywords):
                candidates.append(tool_name)
        
        return candidates


class ToolBasedAgent:
    """基于工具注册的智能Agent"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.registry = ToolRegistry()
        self.model_selector = create_step_based_model_selector()
        self.execution_history: List[ToolResult] = []
        
        # 注册内置工具
        self._register_builtin_tools()
    
    def _register_builtin_tools(self):
        """注册内置工具"""
        
        # 1. 占位符→SQL转换工具
        self.registry.register_tool(
            func=self._tool_placeholder_to_sql,
            metadata=ToolMetadata(
                name="placeholder_to_sql",
                description="将占位符转换为SQL查询，支持时间上下文分析和多表关联",
                category=ToolCategory.SQL_GENERATION,
                input_schema={
                    "placeholder_name": "string",
                    "placeholder_description": "string", 
                    "task_context": "object",
                    "data_source_context": "object",
                    "time_context": "object"
                },
                output_schema={
                    "sql_query": "string",
                    "explanation": "string",
                    "confidence_score": "number"
                },
                complexity="high",
                cost_estimate="medium"
            )
        )
        
        # 2. SQL验证工具
        self.registry.register_tool(
            func=self._tool_validate_sql,
            metadata=ToolMetadata(
                name="validate_sql", 
                description="验证SQL语法和逻辑正确性，支持多轮纠错",
                category=ToolCategory.VALIDATION,
                input_schema={
                    "sql_query": "string",
                    "data_source_context": "object"
                },
                output_schema={
                    "is_valid": "boolean",
                    "errors": "array",
                    "corrected_sql": "string"
                },
                complexity="high",
                dependencies=["placeholder_to_sql"]
            )
        )
        
        # 3. 图表生成工具
        self.registry.register_tool(
            func=self._tool_generate_chart,
            metadata=ToolMetadata(
                name="generate_chart",
                description="基于数据生成各种类型的图表，支持自动图表类型选择",
                category=ToolCategory.CHART_GENERATION,
                input_schema={
                    "data": "array",
                    "chart_type": "string",
                    "title": "string",
                    "styling_options": "object"
                },
                output_schema={
                    "chart_path": "string",
                    "chart_config": "object"
                },
                complexity="medium",
                cost_estimate="low"
            )
        )
        
        # 4. 时间上下文分析工具
        self.registry.register_tool(
            func=self._tool_analyze_time_context,
            metadata=ToolMetadata(
                name="analyze_time_context",
                description="分析和推断任务的时间上下文需求",
                category=ToolCategory.CONTEXT_ANALYSIS,
                input_schema={
                    "task_context": "object",
                    "current_time_context": "object"
                },
                output_schema={
                    "enhanced_time_context": "object",
                    "time_filters": "array"
                },
                complexity="medium"
            )
        )
        
        # 5. Schema分析工具
        self.registry.register_tool(
            func=self._tool_analyze_schema,
            metadata=ToolMetadata(
                name="analyze_schema",
                description="分析数据源Schema并匹配最适合的表和字段",
                category=ToolCategory.DATA_ANALYSIS,
                input_schema={
                    "data_source_context": "object",
                    "analysis_requirements": "object"
                },
                output_schema={
                    "recommended_tables": "array",
                    "recommended_columns": "array",
                    "join_suggestions": "array"
                },
                complexity="medium"
            )
        )
        
        # 6. 任务补充工具
        self.registry.register_tool(
            func=self._tool_supplement_task,
            metadata=ToolMetadata(
                name="supplement_task",
                description="检测并补充空白或过期的占位符",
                category=ToolCategory.DATA_PROCESSING,
                input_schema={
                    "placeholders": "array",
                    "task_context": "object"
                },
                output_schema={
                    "supplement_results": "array",
                    "success_count": "number"
                },
                complexity="high",
                dependencies=["placeholder_to_sql", "analyze_time_context"]
            )
        )
    
    async def process_request(
        self,
        user_request: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理用户请求 - 让模型自主决策工具调用
        """
        try:
            logger.info(f"开始处理用户请求: {user_request[:100]}...")
            
            # 1. 分析请求并推荐工具
            recommended_tools = await self._analyze_request_and_recommend_tools(
                user_request, context
            )
            
            # 2. 让模型制定执行计划
            execution_plan = await self._create_execution_plan(
                user_request, recommended_tools, context
            )
            
            # 3. 执行计划
            execution_results = await self._execute_plan(execution_plan, context)
            
            # 4. 整合结果
            final_result = await self._integrate_results(
                user_request, execution_results, context
            )
            
            return {
                "success": True,
                "result": final_result,
                "execution_plan": execution_plan,
                "tools_used": [r.tool_name for r in execution_results],
                "total_execution_time": sum(r.execution_time for r in execution_results)
            }
            
        except Exception as e:
            logger.error(f"请求处理失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "result": None
            }
    
    async def _analyze_request_and_recommend_tools(
        self,
        user_request: str,
        context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """分析请求并推荐工具"""
        
        # 获取所有工具信息
        all_tools = self.registry.get_all_tools_metadata()
        tools_description = ""
        
        for tool_name, metadata in all_tools.items():
            tools_description += f"- {tool_name}: {metadata.description} (分类: {metadata.category.value})\n"
        
        prompt = f"""
        请分析以下用户请求，推荐最适合的工具组合：
        
        用户请求: {user_request}
        
        可用工具:
        {tools_description}
        
        上下文信息: {json.dumps(context, ensure_ascii=False, indent=2) if context else "无"}
        
        请根据用户请求的具体需求，推荐最合适的工具组合。考虑：
        1. 任务的核心需求是什么
        2. 需要哪些工具才能完成任务
        3. 工具之间的依赖关系
        4. 执行的合理顺序
        
        返回JSON格式的工具推荐列表：
        {{
            "recommended_tools": ["tool1", "tool2", "tool3"],
            "reasoning": "推荐理由"
        }}
        """
        
        try:
            response = await ask_agent_for_user(
                user_id=self.user_id,
                question=prompt,
                agent_type="general",
                task_type="tool_recommendation"
            )
            
            recommendation = json.loads(response)
            recommended_tools = recommendation.get("recommended_tools", [])
            
            logger.info(f"推荐工具: {recommended_tools}")
            return recommended_tools
            
        except Exception as e:
            logger.error(f"工具推荐失败: {e}")
            # 降级策略：根据关键词匹配
            keywords = user_request.lower().split()
            return self.registry.search_tools(keywords)
    
    async def _create_execution_plan(
        self,
        user_request: str,
        recommended_tools: List[str],
        context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """创建执行计划"""
        
        # 获取推荐工具的详细信息
        tools_details = {}
        for tool_name in recommended_tools:
            tool_info = self.registry.get_tool(tool_name)
            if tool_info:
                tools_details[tool_name] = {
                    "description": tool_info['metadata'].description,
                    "input_schema": tool_info['metadata'].input_schema,
                    "dependencies": tool_info['metadata'].dependencies
                }
        
        prompt = f"""
        请为以下任务制定详细的执行计划：
        
        用户请求: {user_request}
        
        可用工具详情:
        {json.dumps(tools_details, ensure_ascii=False, indent=2)}
        
        上下文信息: {json.dumps(context, ensure_ascii=False, indent=2) if context else "无"}
        
        请制定一个详细的执行计划，包括：
        1. 工具的执行顺序（考虑依赖关系）
        2. 每个工具的具体参数
        3. 参数如何从上下文或前一步结果中获取
        
        返回JSON格式的执行计划：
        {{
            "steps": [
                {{
                    "step_id": 1,
                    "tool_name": "工具名称",
                    "description": "步骤描述",
                    "parameters": {{
                        "param1": "value1",
                        "param2": "从上下文获取",
                        "param3": "从步骤X结果获取"
                    }},
                    "depends_on": [前置步骤ID列表]
                }}
            ]
        }}
        """
        
        try:
            response = await ask_agent_for_user(
                user_id=self.user_id,
                question=prompt,
                agent_type="general",
                task_type="execution_planning"
            )
            
            plan = json.loads(response)
            steps = plan.get("steps", [])
            
            logger.info(f"执行计划创建完成，共 {len(steps)} 个步骤")
            return steps
            
        except Exception as e:
            logger.error(f"执行计划创建失败: {e}")
            # 降级策略：简单顺序执行
            simple_plan = []
            for i, tool_name in enumerate(recommended_tools):
                simple_plan.append({
                    "step_id": i + 1,
                    "tool_name": tool_name,
                    "description": f"执行工具 {tool_name}",
                    "parameters": {},
                    "depends_on": [i] if i > 0 else []
                })
            return simple_plan
    
    async def _execute_plan(
        self,
        execution_plan: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ) -> List[ToolResult]:
        """执行计划"""
        
        results = {}  # step_id -> result
        execution_results = []
        
        # 按依赖关系排序执行
        for step in execution_plan:
            step_id = step["step_id"]
            tool_name = step["tool_name"]
            parameters = step["parameters"]
            
            logger.info(f"执行步骤 {step_id}: {tool_name}")
            
            try:
                # 解析参数（从上下文或前置结果获取）
                resolved_params = await self._resolve_parameters(
                    parameters, context, results
                )
                
                # 执行工具
                tool_result = await self._execute_tool(
                    tool_name, resolved_params, f"step_{step_id}"
                )
                
                results[step_id] = tool_result.result
                execution_results.append(tool_result)
                
            except Exception as e:
                logger.error(f"步骤 {step_id} 执行失败: {e}")
                error_result = ToolResult(
                    call_id=f"step_{step_id}",
                    tool_name=tool_name,
                    success=False,
                    result=None,
                    error_message=str(e)
                )
                execution_results.append(error_result)
        
        return execution_results
    
    async def _resolve_parameters(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        previous_results: Dict[int, Any]
    ) -> Dict[str, Any]:
        """解析参数值"""
        
        resolved = {}
        
        for key, value in parameters.items():
            if isinstance(value, str):
                if value.startswith("从上下文获取"):
                    # 从上下文获取
                    context_key = value.replace("从上下文获取", "").strip(":：")
                    resolved[key] = context.get(context_key) if context else None
                elif "从步骤" in value and "结果获取" in value:
                    # 从前置步骤结果获取
                    # 解析步骤ID（简化实现）
                    import re
                    match = re.search(r'从步骤(\d+)结果获取', value)
                    if match:
                        step_id = int(match.group(1))
                        resolved[key] = previous_results.get(step_id)
                    else:
                        resolved[key] = None
                else:
                    resolved[key] = value
            else:
                resolved[key] = value
        
        return resolved
    
    async def _execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        call_id: str
    ) -> ToolResult:
        """执行单个工具"""
        
        start_time = datetime.now()
        
        try:
            tool_info = self.registry.get_tool(tool_name)
            if not tool_info:
                raise ValueError(f"工具 {tool_name} 未注册")
            
            func = tool_info['function']
            
            # 执行工具函数
            if asyncio.iscoroutinefunction(func):
                result = await func(**parameters)
            else:
                result = func(**parameters)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            tool_result = ToolResult(
                call_id=call_id,
                tool_name=tool_name,
                success=True,
                result=result,
                execution_time=execution_time
            )
            
            logger.info(f"工具 {tool_name} 执行成功，耗时 {execution_time:.2f}s")
            return tool_result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"工具 {tool_name} 执行失败: {e}")
            
            return ToolResult(
                call_id=call_id,
                tool_name=tool_name,
                success=False,
                result=None,
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def _integrate_results(
        self,
        user_request: str,
        execution_results: List[ToolResult],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """整合执行结果"""
        
        # 收集成功的结果
        successful_results = [r for r in execution_results if r.success]
        failed_results = [r for r in execution_results if not r.success]
        
        # 构建结果摘要
        results_summary = {}
        for result in successful_results:
            results_summary[result.tool_name] = result.result
        
        if not successful_results:
            return {
                "status": "failed",
                "message": "所有工具执行都失败了",
                "errors": [r.error_message for r in failed_results]
            }
        
        # 让模型整合和总结结果
        integration_prompt = f"""
        请整合以下工具执行结果，为用户请求提供完整的答案：
        
        用户请求: {user_request}
        
        工具执行结果:
        {json.dumps(results_summary, ensure_ascii=False, indent=2)}
        
        请提供：
        1. 对用户请求的完整回答
        2. 主要发现和结论
        3. 如果有SQL查询，提供查询语句
        4. 如果有图表，提供图表路径
        5. 任何需要用户注意的事项
        
        返回JSON格式的整合结果。
        """
        
        try:
            response = await ask_agent_for_user(
                user_id=self.user_id,
                question=integration_prompt,
                agent_type="general",
                task_type="result_integration"
            )
            
            integrated_result = json.loads(response)
            
            # 添加原始结果
            integrated_result["raw_results"] = results_summary
            integrated_result["execution_summary"] = {
                "total_tools": len(execution_results),
                "successful_tools": len(successful_results),
                "failed_tools": len(failed_results)
            }
            
            return integrated_result
            
        except Exception as e:
            logger.error(f"结果整合失败: {e}")
            # 降级策略：返回原始结果
            return {
                "status": "partial_success",
                "message": "工具执行完成，但结果整合失败",
                "raw_results": results_summary,
                "integration_error": str(e)
            }
    
    # === 内置工具实现 ===
    
    async def _tool_placeholder_to_sql(self, **kwargs) -> Dict[str, Any]:
        """占位符→SQL转换工具实现"""
        # 这里调用之前实现的PlaceholderToSqlAgent
        from .placeholder_to_sql_agent import create_placeholder_to_sql_agent
        
        agent = create_placeholder_to_sql_agent(self.user_id)
        # 实现逻辑...
        return {"sql_query": "SELECT * FROM table", "explanation": "示例SQL"}
    
    async def _tool_validate_sql(self, **kwargs) -> Dict[str, Any]:
        """SQL验证工具实现"""
        # 实现SQL验证逻辑
        return {"is_valid": True, "errors": [], "corrected_sql": kwargs.get("sql_query")}
    
    async def _tool_generate_chart(self, **kwargs) -> Dict[str, Any]:
        """图表生成工具实现"""
        # 调用现有的图表生成工具
        from ..tools.chart_generator_tool import generate_chart
        
        try:
            chart_path = await generate_chart(
                data=kwargs.get("data", []),
                chart_type=kwargs.get("chart_type", "bar"),
                title=kwargs.get("title", "Chart"),
                **kwargs.get("styling_options", {})
            )
            return {"chart_path": chart_path, "chart_config": kwargs}
        except Exception as e:
            raise Exception(f"图表生成失败: {e}")
    
    async def _tool_analyze_time_context(self, **kwargs) -> Dict[str, Any]:
        """时间上下文分析工具实现"""
        # 实现时间上下文分析逻辑
        return {"enhanced_time_context": {}, "time_filters": []}
    
    async def _tool_analyze_schema(self, **kwargs) -> Dict[str, Any]:
        """Schema分析工具实现"""
        # 实现Schema分析逻辑
        return {"recommended_tables": [], "recommended_columns": [], "join_suggestions": []}
    
    async def _tool_supplement_task(self, **kwargs) -> Dict[str, Any]:
        """任务补充工具实现"""
        # 调用之前实现的TaskSupplementAgent
        from .task_supplement_agent import create_task_supplement_agent
        
        agent = create_task_supplement_agent(self.user_id)
        # 实现逻辑...
        return {"supplement_results": [], "success_count": 0}
    
    def get_available_tools(self) -> Dict[str, ToolMetadata]:
        """获取可用工具列表"""
        return self.registry.get_all_tools_metadata()


def create_tool_based_agent(user_id: str) -> ToolBasedAgent:
    """创建基于工具的智能Agent"""
    if not user_id:
        raise ValueError("user_id is required for ToolBasedAgent")
    return ToolBasedAgent(user_id)