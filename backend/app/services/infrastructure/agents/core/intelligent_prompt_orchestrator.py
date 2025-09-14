"""
智能Prompt编排器
====================

基于Prompt系统的智能决策引擎，实现动态策略生成和任务适配。
遵循Claude Code TT控制循环的设计原则，将Prompt系统作为智能决策的核心驱动。
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """任务复杂度枚举"""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    EXPERT = "expert"


class WorkflowType(Enum):
    """工作流类型枚举"""
    DATA_PIPELINE = "data_pipeline"
    SYSTEM_MAINTENANCE = "system_maintenance"
    CODE_ANALYSIS = "code_analysis"
    BUSINESS_INTELLIGENCE = "business_intelligence"
    TEMPLATE_PROCESSING = "template_processing"


@dataclass
class ExecutionStrategy:
    """执行策略数据类"""
    strategy_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    # 阶段配置
    stage_configuration: Dict[str, Any] = field(default_factory=dict)
    
    # 工具选择
    tool_selection: List[str] = field(default_factory=list)
    tool_parameters: Dict[str, Any] = field(default_factory=dict)
    
    # 优化提示
    optimization_hints: List[str] = field(default_factory=list)
    
    # 终止条件
    termination_conditions: Dict[str, Any] = field(default_factory=dict)
    
    # 兜底策略
    fallback_strategies: List[Dict[str, Any]] = field(default_factory=list)
    
    # 上下文适配
    context_adaptations: Dict[str, Any] = field(default_factory=dict)
    
    # 性能配置
    performance_config: Dict[str, Any] = field(default_factory=dict)
    
    # 元数据
    generated_at: datetime = field(default_factory=datetime.utcnow)
    confidence_score: float = 0.8
    
    @classmethod
    def from_llm_result(cls, llm_result: Dict[str, Any]) -> 'ExecutionStrategy':
        """从LLM结果创建执行策略"""
        try:
            # 尝试解析JSON结果
            if isinstance(llm_result, str):
                import re
                json_match = re.search(r'```json\s*(.*?)\s*```', llm_result, re.DOTALL)
                if json_match:
                    strategy_data = json.loads(json_match.group(1))
                else:
                    strategy_data = json.loads(llm_result)
            else:
                strategy_data = llm_result
            
            return cls(
                stage_configuration=strategy_data.get("stage_configuration", {}),
                tool_selection=strategy_data.get("tool_selection", []),
                tool_parameters=strategy_data.get("tool_parameters", {}),
                optimization_hints=strategy_data.get("optimization_hints", []),
                termination_conditions=strategy_data.get("termination_conditions", {}),
                fallback_strategies=strategy_data.get("fallback_strategies", []),
                context_adaptations=strategy_data.get("context_adaptations", {}),
                performance_config=strategy_data.get("performance_config", {}),
                confidence_score=strategy_data.get("confidence_score", 0.8)
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse LLM strategy result: {e}")
            # 返回默认策略
            return cls()


@dataclass 
class SmartContext:
    """智能上下文数据类"""
    task_description: str
    context_data: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    
    # 智能分析结果
    scenario: str = "general"
    complexity_level: TaskComplexity = TaskComplexity.MEDIUM
    optimal_agent_type: str = "data_analysis"
    available_tools: List[str] = field(default_factory=list)
    workflow_type: WorkflowType = WorkflowType.DATA_PIPELINE
    
    # 用户和环境
    user_role: str = "analyst"
    data_sensitivity: str = "medium"
    resource_constraints: Dict[str, Any] = field(default_factory=dict)
    
    # 业务上下文
    data_sources: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)


class IntelligentPromptOrchestrator:
    """
    智能Prompt编排器
    
    核心功能：
    1. 基于Prompt系统的智能决策
    2. 动态执行策略生成
    3. 上下文感知的任务适配
    4. 工具选择策略优化
    """
    
    def __init__(self):
        # 导入Prompt系统
        from ..prompts import prompt_manager
        self.prompt_manager = prompt_manager
        
        # 策略缓存
        self.strategy_cache: Dict[str, ExecutionStrategy] = {}
        self.cache_ttl = 300  # 5分钟缓存
        
        # LLM工具
        self.llm_tool = None
        self._initialize_llm_tool()
        
        # 策略模板
        self.strategy_templates = {
            "placeholder_analysis": self._get_placeholder_analysis_template,
            "data_analysis": self._get_data_analysis_template, 
            "sql_generation": self._get_sql_generation_template,
            "report_generation": self._get_report_generation_template,
            "system_maintenance": self._get_system_maintenance_template
        }
        
        logger.info("IntelligentPromptOrchestrator initialized")
    
    def _initialize_llm_tool(self):
        """初始化LLM工具"""
        try:
            from ..tools.llm import get_llm_reasoning_tool
            self.llm_tool = get_llm_reasoning_tool()
        except Exception as e:
            logger.error(f"Failed to initialize LLM tool: {e}")
            self.llm_tool = None
    
    async def generate_execution_strategy(
        self, 
        context: SmartContext,
        force_regenerate: bool = False
    ) -> ExecutionStrategy:
        """
        基于Prompt系统生成智能执行策略
        
        Args:
            context: 智能上下文
            force_regenerate: 强制重新生成策略
            
        Returns:
            ExecutionStrategy: 优化的执行策略
        """
        
        # 生成缓存键
        cache_key = self._generate_cache_key(context)
        
        # 检查缓存
        if not force_regenerate and cache_key in self.strategy_cache:
            cached_strategy = self.strategy_cache[cache_key]
            if (datetime.utcnow() - cached_strategy.generated_at).seconds < self.cache_ttl:
                logger.info(f"Using cached strategy: {cached_strategy.strategy_id}")
                return cached_strategy
        
        try:
            logger.info(f"Generating new execution strategy for scenario: {context.scenario}")
            
            # 1. 获取上下文感知的Prompt
            context_prompt = self._build_context_aware_prompt(context)
            
            # 2. 获取专业化Agent指令  
            agent_instructions = self._build_agent_instructions(context)
            
            # 3. 获取工作流指令
            workflow_prompt = self._build_workflow_prompt(context)
            
            # 4. 构建综合策略生成Prompt
            strategy_generation_prompt = self._build_strategy_generation_prompt(
                context, context_prompt, agent_instructions, workflow_prompt
            )
            
            # 5. 执行LLM策略生成
            if self.llm_tool:
                strategy_result = await self._execute_llm_strategy_generation(
                    strategy_generation_prompt, context
                )
                execution_strategy = ExecutionStrategy.from_llm_result(strategy_result)
            else:
                # 兜底：使用模板策略
                execution_strategy = self._generate_template_strategy(context)
            
            # 6. 后处理和优化
            execution_strategy = self._post_process_strategy(execution_strategy, context)
            
            # 7. 缓存策略
            self.strategy_cache[cache_key] = execution_strategy
            
            logger.info(f"Generated strategy {execution_strategy.strategy_id} with confidence {execution_strategy.confidence_score}")
            return execution_strategy
            
        except Exception as e:
            logger.error(f"Failed to generate execution strategy: {e}")
            # 返回兜底策略
            return self._generate_fallback_strategy(context)
    
    def _build_context_aware_prompt(self, context: SmartContext) -> str:
        """构建上下文感知的Prompt"""
        
        # 构建资源约束描述
        resource_constraints = context.resource_constraints or {}
        constraints_desc = []
        if resource_constraints.get("memory_limited"):
            constraints_desc.append("内存受限")
        if resource_constraints.get("time_limited"):
            constraints_desc.append("时间紧急")
        if resource_constraints.get("compute_limited"):
            constraints_desc.append("计算资源受限")
        
        return self.prompt_manager.get_context_aware_prompt({
            "task_type": context.scenario,
            "complexity": context.complexity_level.value,
            "user_role": context.user_role,
            "data_sensitivity": context.data_sensitivity,
            "urgency": "high" if resource_constraints.get("time_limited") else "normal",
            "resource_constraints": {
                "memory_limited": resource_constraints.get("memory_limited", False),
                "time_limited": resource_constraints.get("time_limited", False),
                "compute_limited": resource_constraints.get("compute_limited", False)
            }
        })
    
    def _build_agent_instructions(self, context: SmartContext) -> str:
        """构建Agent指令"""
        return self.prompt_manager.get_agent_instructions(
            agent_type=context.optimal_agent_type,
            tools=context.available_tools
        )
    
    def _build_workflow_prompt(self, context: SmartContext) -> str:
        """构建工作流Prompt"""
        return self.prompt_manager.get_workflow_prompt(context.workflow_type.value)
    
    def _build_strategy_generation_prompt(
        self,
        context: SmartContext,
        context_prompt: str,
        agent_instructions: str, 
        workflow_prompt: str
    ) -> str:
        """构建策略生成的综合Prompt"""
        
        return f"""
{agent_instructions}

{context_prompt}

{workflow_prompt}

# 智能执行策略生成

基于以下任务上下文，生成最优的TT控制循环执行策略：

## 任务信息
- 任务描述: {context.task_description}
- 业务场景: {context.scenario}
- 复杂度等级: {context.complexity_level.value}
- 用户角色: {context.user_role}
- 数据敏感性: {context.data_sensitivity}

## 上下文资源
- 推荐Agent类型: {context.optimal_agent_type}
- 可用工具列表: {', '.join(context.available_tools) if context.available_tools else '需要动态发现'}
- 推荐工作流: {context.workflow_type.value}
- 数据源: {', '.join(context.data_sources) if context.data_sources else '待确定'}

## 约束条件
- 资源限制: {context.resource_constraints}
- 业务约束: {', '.join(context.constraints) if context.constraints else '无特殊约束'}
- 成功标准: {', '.join(context.success_criteria) if context.success_criteria else '任务完成'}

## 策略生成要求

请基于TT控制循环的六阶段模式，生成智能化的执行策略：

### 阶段配置优化
1. **意图理解阶段**: LLM参与程度、复杂度阈值
2. **上下文分析阶段**: 分析深度、数据范围
3. **结构规划阶段**: 规划策略、优化建议  
4. **实现执行阶段**: 工具选择、执行顺序
5. **优化审查阶段**: 质量检查、性能优化
6. **综合整合阶段**: 结果合成、输出格式

### 智能工具选择
- 基于场景的最优工具组合
- 工具执行顺序和参数配置
- 工具间数据传递策略

### 性能优化策略
- 并行执行机会识别
- 缓存利用策略
- 资源使用优化

### 兜底和错误处理
- 关键失败点识别
- 替代执行路径
- 降级处理方案

## 输出格式

请返回JSON格式的执行策略：

```json
{{
    "stage_configuration": {{
        "intent_understanding": {{
            "llm_participation": "high|medium|low",
            "complexity_threshold": 0.8,
            "analysis_depth": "detailed|basic"
        }},
        "context_analysis": {{
            "analysis_scope": "comprehensive|focused|minimal", 
            "llm_enhanced": true,
            "data_validation": true
        }},
        "structure_planning": {{
            "planning_strategy": "llm_assisted|rule_based|hybrid",
            "optimization_level": "advanced|standard|basic"
        }},
        "implementation": {{
            "execution_mode": "parallel|sequential|mixed",
            "tool_coordination": "smart|simple"
        }},
        "optimization": {{
            "review_depth": "comprehensive|standard|basic",
            "performance_focus": true
        }},
        "synthesis": {{
            "integration_mode": "llm_driven|rule_based",
            "output_format": "detailed|summary"
        }}
    }},
    "tool_selection": [
        "primary_tool",
        "secondary_tool", 
        "fallback_tool"
    ],
    "tool_parameters": {{
        "tool_name": {{
            "parameter": "value",
            "priority": "high|medium|low"
        }}
    }},
    "optimization_hints": [
        "Use parallel execution where possible",
        "Cache intermediate results",
        "Optimize for {context.complexity_level.value} complexity"
    ],
    "termination_conditions": {{
        "success_criteria": [
            "Task completion signal received",
            "Quality threshold met"
        ],
        "failure_criteria": [
            "Maximum retries exceeded", 
            "Timeout reached"
        ],
        "early_termination": {{
            "context_sufficient": true,
            "confidence_threshold": 0.9
        }}
    }},
    "fallback_strategies": [
        {{
            "trigger": "LLM analysis failure",
            "action": "Use rule-based analysis",
            "priority": 1
        }},
        {{
            "trigger": "Tool execution failure", 
            "action": "Switch to backup tool",
            "priority": 2
        }}
    ],
    "context_adaptations": {{
        "memory_optimization": {str(context.resource_constraints.get('memory_limited', False)).lower()},
        "time_optimization": {str(context.resource_constraints.get('time_limited', False)).lower()},
        "data_sensitivity_handling": "{context.data_sensitivity}"
    }},
    "performance_config": {{
        "max_parallel_tools": 3,
        "timeout_per_stage": 60,
        "cache_enabled": true,
        "streaming_enabled": true
    }},
    "confidence_score": 0.9
}}
```

请基于任务的具体特点，生成最适合的执行策略。重点关注：
1. 上下文是否已包含足够信息（避免不必要的数据库查询）
2. 工具选择的智能化和效率
3. 适合任务复杂度的处理深度
4. 用户角色和数据敏感性的考虑
"""
    
    async def _execute_llm_strategy_generation(
        self,
        strategy_prompt: str,
        context: SmartContext
    ) -> Dict[str, Any]:
        """执行LLM策略生成"""
        
        from ..tools.core.base import ToolExecutionContext
        
        tool_context = ToolExecutionContext(user_id=context.user_id)
        
        strategy_result = None
        async for llm_result in self.llm_tool.execute(
            {
                "problem": strategy_prompt,
                "reasoning_depth": "detailed" if context.complexity_level in [TaskComplexity.HIGH, TaskComplexity.EXPERT] else "basic"
            },
            tool_context
        ):
            if llm_result.success and not llm_result.is_partial:
                strategy_result = llm_result.result
                break
        
        return strategy_result or {}
    
    def _generate_template_strategy(self, context: SmartContext) -> ExecutionStrategy:
        """使用模板生成兜底策略"""
        
        template_name = context.scenario
        if template_name in self.strategy_templates:
            template_func = self.strategy_templates[template_name]
            return template_func(context)
        else:
            return self._get_default_template(context)
    
    def _get_placeholder_analysis_template(self, context: SmartContext) -> ExecutionStrategy:
        """占位符分析模板策略"""
        return ExecutionStrategy(
            stage_configuration={
                "intent_understanding": {"llm_participation": "medium", "analysis_depth": "focused"},
                "context_analysis": {"analysis_scope": "focused", "llm_enhanced": True},
                "structure_planning": {"planning_strategy": "rule_based", "optimization_level": "standard"},
                "implementation": {"execution_mode": "sequential", "tool_coordination": "simple"},
                "optimization": {"review_depth": "standard", "performance_focus": False},
                "synthesis": {"integration_mode": "rule_based", "output_format": "detailed"}
            },
            tool_selection=["placeholder_analyzer", "context_extractor"],
            optimization_hints=["Check context sufficiency first", "Avoid unnecessary database queries"],
            termination_conditions={
                "early_termination": {"context_sufficient": True, "confidence_threshold": 0.8}
            }
        )
    
    def _get_data_analysis_template(self, context: SmartContext) -> ExecutionStrategy:
        """数据分析模板策略"""
        return ExecutionStrategy(
            stage_configuration={
                "intent_understanding": {"llm_participation": "high", "analysis_depth": "detailed"},
                "context_analysis": {"analysis_scope": "comprehensive", "llm_enhanced": True},
                "structure_planning": {"planning_strategy": "llm_assisted", "optimization_level": "advanced"},
                "implementation": {"execution_mode": "parallel", "tool_coordination": "smart"},
                "optimization": {"review_depth": "comprehensive", "performance_focus": True},
                "synthesis": {"integration_mode": "llm_driven", "output_format": "detailed"}
            },
            tool_selection=["data_analyzer", "sql_generator", "reasoning_tool"],
            optimization_hints=["Use statistical validation", "Optimize for data quality"]
        )
    
    def _get_sql_generation_template(self, context: SmartContext) -> ExecutionStrategy:
        """SQL生成模板策略"""
        return ExecutionStrategy(
            tool_selection=["sql_generator", "sql_validator", "query_optimizer"],
            optimization_hints=["Validate syntax and semantics", "Optimize for performance"]
        )
    
    def _get_report_generation_template(self, context: SmartContext) -> ExecutionStrategy:
        """报告生成模板策略"""
        return ExecutionStrategy(
            tool_selection=["data_analyzer", "report_generator", "visualization_tool"],
            optimization_hints=["Include visual elements", "Focus on business insights"]
        )
    
    def _get_system_maintenance_template(self, context: SmartContext) -> ExecutionStrategy:
        """系统维护模板策略"""
        return ExecutionStrategy(
            tool_selection=["system_monitor", "file_manager", "bash_tool"],
            optimization_hints=["Use safe mode first", "Create backups before changes"]
        )
    
    def _get_default_template(self, context: SmartContext) -> ExecutionStrategy:
        """默认模板策略"""
        return ExecutionStrategy(
            tool_selection=["reasoning_tool"],
            optimization_hints=["Use basic analysis approach"]
        )
    
    def _post_process_strategy(
        self, 
        strategy: ExecutionStrategy, 
        context: SmartContext
    ) -> ExecutionStrategy:
        """后处理和优化策略"""
        
        # 1. 确保工具选择合理
        if not strategy.tool_selection:
            strategy.tool_selection = context.available_tools[:3] if context.available_tools else ["reasoning_tool"]
        
        # 2. 调整复杂度相关配置
        if context.complexity_level == TaskComplexity.LOW:
            strategy.performance_config["timeout_per_stage"] = 30
            strategy.stage_configuration.setdefault("optimization", {})["review_depth"] = "basic"
        elif context.complexity_level == TaskComplexity.HIGH:
            strategy.performance_config["timeout_per_stage"] = 120
            strategy.stage_configuration.setdefault("optimization", {})["review_depth"] = "comprehensive"
        
        # 3. 根据资源约束调整
        if context.resource_constraints.get("time_limited"):
            strategy.performance_config["max_parallel_tools"] = 5
            strategy.stage_configuration.setdefault("implementation", {})["execution_mode"] = "parallel"
        
        if context.resource_constraints.get("memory_limited"):
            strategy.performance_config["cache_enabled"] = False
            strategy.optimization_hints.append("Use memory-efficient algorithms")
        
        return strategy
    
    def _generate_fallback_strategy(self, context: SmartContext) -> ExecutionStrategy:
        """生成兜底策略"""
        logger.warning("Using fallback strategy due to generation failure")
        
        return ExecutionStrategy(
            stage_configuration={
                "intent_understanding": {"llm_participation": "low", "analysis_depth": "basic"},
                "context_analysis": {"analysis_scope": "minimal", "llm_enhanced": False},
                "structure_planning": {"planning_strategy": "rule_based", "optimization_level": "basic"},
                "implementation": {"execution_mode": "sequential", "tool_coordination": "simple"},
                "optimization": {"review_depth": "basic", "performance_focus": False},
                "synthesis": {"integration_mode": "rule_based", "output_format": "summary"}
            },
            tool_selection=["reasoning_tool"],
            optimization_hints=["Use basic processing approach"],
            confidence_score=0.6
        )
    
    def _generate_cache_key(self, context: SmartContext) -> str:
        """生成策略缓存键"""
        import hashlib
        
        key_data = f"{context.scenario}:{context.complexity_level.value}:{context.optimal_agent_type}:{len(context.available_tools)}"
        return hashlib.md5(key_data.encode()).hexdigest()[:16]
    
    async def get_strategy_explanation(self, strategy: ExecutionStrategy) -> str:
        """获取策略解释"""
        if not self.llm_tool:
            return "Strategy generated using template-based approach"
        
        explanation_prompt = f"""
请解释以下执行策略的设计思路和优化点：

策略配置：
- 工具选择: {', '.join(strategy.tool_selection)}
- 优化提示: {', '.join(strategy.optimization_hints)}
- 置信度: {strategy.confidence_score}

请简要说明这个策略的核心特点和预期效果。
"""
        
        try:
            from ..tools.core.base import ToolExecutionContext
            tool_context = ToolExecutionContext(user_id="system")
            
            async for result in self.llm_tool.execute({"problem": explanation_prompt}, tool_context):
                if result.success and not result.is_partial:
                    return result.result
        except Exception as e:
            logger.error(f"Failed to generate strategy explanation: {e}")
        
        return f"Strategy {strategy.strategy_id} with {len(strategy.tool_selection)} tools selected"
    
    def clear_cache(self):
        """清空策略缓存"""
        self.strategy_cache.clear()
        logger.info("Strategy cache cleared")


# 便利函数
def create_smart_context(
    task_description: str,
    context_data: Dict[str, Any] = None,
    user_id: str = None,
    **kwargs
) -> SmartContext:
    """快速创建智能上下文"""
    return SmartContext(
        task_description=task_description,
        context_data=context_data or {},
        user_id=user_id,
        **kwargs
    )


__all__ = [
    "IntelligentPromptOrchestrator",
    "ExecutionStrategy", 
    "SmartContext",
    "TaskComplexity",
    "WorkflowType",
    "create_smart_context"
]