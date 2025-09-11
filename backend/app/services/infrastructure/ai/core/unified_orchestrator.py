"""
统一编排器 v3.0 - 集成ReAct + 提示词系统 + 工具编排
================================================================

整合原有的三个系统：
1. react_orchestrator.py -> ReAct思考-执行-观察模式
2. tools/orchestrator.py -> 提示词感知的工具编排
3. prompts.py -> 企业级提示词管理

新架构特点：
- 统一的编排接口，替换原有的多个编排器
- 深度集成企业级提示词系统
- 保留ReAct的智能决策能力
- 优化的工具链协调机制
"""

import logging
import uuid
import json
from typing import Dict, Any, List, Optional, AsyncGenerator, Union
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

from .tools import ToolChain, ToolContext, ToolResult, ToolResultType
from .prompts import PromptComplexity, SQLGenerationPrompts, get_prompt_manager
from .prompt_monitor import get_prompt_monitor
from ..llm import ask_agent_for_user

logger = logging.getLogger(__name__)


class OrchestrationMode(Enum):
    """编排模式"""
    REACT_FULL = "react_full"           # 完整ReAct模式（思考-执行-观察）
    REACT_SIMPLE = "react_simple"       # 简化ReAct模式（思考-执行）
    WORKFLOW = "workflow"               # 工作流模式（预定义步骤）
    SINGLE_TOOL = "single_tool"         # 单工具执行
    AUTO = "auto"                       # 自动选择模式


class TaskComplexity(Enum):
    """任务复杂度"""
    SIMPLE = "simple"       # 单步骤，单工具
    MEDIUM = "medium"       # 多步骤，少量工具
    COMPLEX = "complex"     # 多步骤，多工具，有依赖
    CRITICAL = "critical"   # 关键任务，需要最高安全级别


@dataclass
class OrchestrationContext:
    """编排上下文"""
    goal: str
    mode: OrchestrationMode = OrchestrationMode.AUTO
    max_iterations: int = 5
    available_tools: List[str] = field(default_factory=list)
    
    # 任务信息
    task_complexity: TaskComplexity = TaskComplexity.MEDIUM
    prompt_complexity: PromptComplexity = PromptComplexity.MEDIUM
    
    # 执行状态
    current_iteration: int = 0
    execution_history: List[Dict[str, Any]] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    # 结果累积
    intermediate_results: Dict[str, Any] = field(default_factory=dict)
    final_result: Optional[Dict[str, Any]] = None


@dataclass
class OrchestrationStep:
    """编排步骤"""
    step_id: str
    step_type: str  # thinking, tool_execution, observation, workflow
    iteration: int
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # 输入输出
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    
    # 执行状态
    success: bool = False
    error: Optional[str] = None
    tool_used: Optional[str] = None
    
    # 提示词信息
    prompt_used: Optional[str] = None
    prompt_complexity: Optional[PromptComplexity] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "step_id": self.step_id,
            "step_type": self.step_type,
            "iteration": self.iteration,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "success": self.success,
            "error": self.error,
            "tool_used": self.tool_used,
            "prompt_complexity": self.prompt_complexity.value if self.prompt_complexity else None
        }


class UnifiedOrchestrator:
    """统一编排器 - 集成ReAct + 提示词 + 工具编排"""
    
    def __init__(self, tool_chain: ToolChain):
        self.tool_chain = tool_chain
        self.prompt_manager = get_prompt_manager()
        self.monitor = get_prompt_monitor()
        self.logger = logging.getLogger(f"{__name__}.UnifiedOrchestrator")
        
        # 编排统计
        self.total_orchestrations = 0
        self.success_count = 0
        
    async def orchestrate(
        self,
        goal: str,
        context: ToolContext,
        mode: OrchestrationMode = OrchestrationMode.AUTO,
        available_tools: Optional[List[str]] = None,
        max_iterations: int = 5,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        统一编排接口 - 替换原有的tt函数和所有编排器
        
        Args:
            goal: 任务目标描述
            context: 工具执行上下文
            mode: 编排模式
            available_tools: 可用工具列表
            max_iterations: 最大迭代次数
            progress_callback: 进度回调函数
            
        Returns:
            编排执行结果
        """
        
        orchestration_id = f"orch_{uuid.uuid4().hex[:8]}"
        self.total_orchestrations += 1
        
        self.logger.info(f"🚀 启动统一编排 {orchestration_id}: {goal[:100]}...")
        
        # 创建编排上下文
        orch_context = OrchestrationContext(
            goal=goal,
            mode=mode,
            max_iterations=max_iterations,
            available_tools=available_tools or self.tool_chain.list_tools()
        )
        
        # 自动评估任务复杂度
        orch_context.task_complexity = self._assess_task_complexity(goal, context)
        orch_context.prompt_complexity = self._map_to_prompt_complexity(orch_context.task_complexity)
        
        self.logger.info(f"📊 任务复杂度: {orch_context.task_complexity.value}")
        self.logger.info(f"🎯 编排模式: {orch_context.mode.value}")
        self.logger.info(f"🔧 可用工具: {len(orch_context.available_tools)} 个")
        
        try:
            # 根据模式选择编排策略
            if mode == OrchestrationMode.AUTO:
                mode = self._auto_select_mode(orch_context)
                orch_context.mode = mode
                self.logger.info(f"🤖 自动选择模式: {mode.value}")
            
            # 执行编排
            if mode == OrchestrationMode.REACT_FULL:
                result = await self._execute_react_full(orch_context, context, progress_callback)
            elif mode == OrchestrationMode.REACT_SIMPLE:
                result = await self._execute_react_simple(orch_context, context, progress_callback)
            elif mode == OrchestrationMode.WORKFLOW:
                result = await self._execute_workflow(orch_context, context, progress_callback)
            elif mode == OrchestrationMode.SINGLE_TOOL:
                result = await self._execute_single_tool(orch_context, context, progress_callback)
            else:
                raise ValueError(f"不支持的编排模式: {mode}")
            
            # 更新统计
            if result.get("status") in ["success", "partial_success"]:
                self.success_count += 1
            
            # 记录性能指标
            self._record_orchestration_metrics(orchestration_id, orch_context, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 编排执行失败 {orchestration_id}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "orchestration_id": orchestration_id,
                "context": orch_context
            }
    
    async def _execute_react_full(
        self,
        orch_context: OrchestrationContext,
        context: ToolContext,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """执行完整ReAct模式：思考-执行-观察循环"""
        
        self.logger.info("🧠 启动完整ReAct编排模式")
        
        for iteration in range(orch_context.max_iterations):
            orch_context.current_iteration = iteration
            
            if progress_callback:
                progress_callback(
                    (iteration / orch_context.max_iterations) * 100,
                    f"第{iteration + 1}轮ReAct循环",
                    "react_iteration"
                )
            
            self.logger.info(f"🔄 ====== ReAct第 {iteration + 1}/{orch_context.max_iterations} 轮开始 ======")
            
            # 阶段1: 思考
            thinking_step = await self._thinking_phase(orch_context, context)
            if not thinking_step.success:
                if iteration == 0:  # 第一轮思考失败是致命的
                    return self._build_error_result(orch_context, "首轮思考失败", thinking_step.error)
                else:  # 后续轮次可以尝试恢复
                    self.logger.warning(f"⚠️ 第{iteration + 1}轮思考失败，尝试下一轮")
                    continue
            
            # 阶段2: 工具执行
            tool_step = await self._tool_execution_phase(orch_context, context, thinking_step)
            if not tool_step.success:
                self.logger.warning(f"⚠️ 第{iteration + 1}轮工具执行失败: {tool_step.error}")
                orch_context.errors.append(f"第{iteration + 1}轮工具执行失败: {tool_step.error}")
                continue
            
            # 阶段3: 观察和决策
            observation_step = await self._observation_phase(orch_context, context, tool_step)
            if not observation_step.success:
                self.logger.warning(f"⚠️ 第{iteration + 1}轮观察失败: {observation_step.error}")
                continue
            
            # 检查是否应该停止
            should_stop = self._should_stop_iteration(orch_context, observation_step)
            if should_stop:
                self.logger.info(f"✅ ReAct编排在第{iteration + 1}轮成功完成")
                return self._build_success_result(orch_context, "ReAct编排成功完成")
        
        # 达到最大迭代次数
        return self._build_partial_result(orch_context, f"达到最大迭代次数 {orch_context.max_iterations}")
    
    async def _thinking_phase(
        self,
        orch_context: OrchestrationContext,
        context: ToolContext
    ) -> OrchestrationStep:
        """思考阶段 - 集成企业级提示词系统"""
        
        step = OrchestrationStep(
            step_id=f"think_{orch_context.current_iteration}",
            step_type="thinking",
            iteration=orch_context.current_iteration,
            start_time=datetime.utcnow()
        )
        
        self.logger.info(f"🧠 [第{orch_context.current_iteration + 1}轮] 思考阶段开始...")
        
        try:
            # 使用企业级提示词系统构建思考提示词
            thinking_prompt = self._build_thinking_prompt(orch_context, context)
            step.prompt_used = thinking_prompt[:200] + "..." if len(thinking_prompt) > 200 else thinking_prompt
            step.prompt_complexity = orch_context.prompt_complexity
            
            # 调用LLM进行思考
            response = await ask_agent_for_user(
                user_id=context.user_id,
                question=thinking_prompt,
                agent_type="react_thinking",
                task_type="orchestration",
                complexity=orch_context.prompt_complexity.value
            )
            
            # 解析思考结果
            decision = self._parse_thinking_response(response)
            
            step.output_data = decision
            step.success = decision.get("success", False)
            step.end_time = datetime.utcnow()
            
            if step.success:
                selected_tool = decision.get("selected_tool")
                self.logger.info(f"✅ 思考完成: 计划使用工具 '{selected_tool}'")
                orch_context.insights.append(f"第{orch_context.current_iteration + 1}轮选择工具: {selected_tool}")
            else:
                step.error = decision.get("error", "思考阶段决策失败")
                self.logger.error(f"❌ 思考失败: {step.error}")
            
            return step
            
        except Exception as e:
            step.error = str(e)
            step.success = False
            step.end_time = datetime.utcnow()
            self.logger.error(f"❌ 思考阶段异常: {e}")
            return step
    
    def _build_thinking_prompt(
        self,
        orch_context: OrchestrationContext,
        context: ToolContext
    ) -> str:
        """构建思考阶段的提示词 - 集成企业级提示词系统"""
        
        # 基础上下文
        prompt_context = {
            "goal": orch_context.goal,
            "available_tools": orch_context.available_tools,
            "current_iteration": orch_context.current_iteration,
            "max_iterations": orch_context.max_iterations,
            "execution_history": orch_context.execution_history[-3:],  # 最近3次历史
            "learned_insights": orch_context.insights[-5:],  # 最近5个洞察
            "errors": orch_context.errors[-3:],  # 最近3个错误
            "data_source_info": getattr(context, 'data_source_info', {}),
            "template_context": getattr(context, 'template_content', '')
        }
        
        # 使用企业级提示词管理器
        try:
            return self.prompt_manager.get_prompt(
                category="orchestration",
                prompt_type="react_thinking",
                context=prompt_context,
                complexity=orch_context.prompt_complexity
            )
        except Exception as e:
            self.logger.warning(f"获取企业级提示词失败，使用基础版本: {e}")
            return self._build_basic_thinking_prompt(orch_context, context)
    
    def _build_basic_thinking_prompt(
        self,
        orch_context: OrchestrationContext,
        context: ToolContext
    ) -> str:
        """构建基础思考提示词（回退方案）"""
        
        return f"""
你是一个智能任务编排器，需要分析任务并选择合适的工具。

【任务目标】: {orch_context.goal}

【当前状态】:
- 迭代: {orch_context.current_iteration + 1}/{orch_context.max_iterations}
- 可用工具: {', '.join(orch_context.available_tools)}

【执行历史】:
{chr(10).join([f"- {h}" for h in orch_context.execution_history[-3:]])}

【学到的经验】:
{chr(10).join([f"- {i}" for i in orch_context.insights[-3:]])}

请分析任务并选择下一步要使用的工具。
返回JSON格式: {{"selected_tool": "工具名", "tool_params": {{}}, "strategy": "策略说明", "success": true}}
"""
    
    def _parse_thinking_response(self, response: str) -> Dict[str, Any]:
        """解析思考响应"""
        try:
            # 尝试解析JSON
            if "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
                decision = json.loads(json_str)
                
                # 验证必要字段
                if "selected_tool" in decision:
                    decision["success"] = True
                    return decision
            
            # 如果JSON解析失败，尝试提取工具名
            for tool in self.tool_chain.list_tools():
                if tool in response:
                    return {
                        "selected_tool": tool,
                        "tool_params": {},
                        "strategy": "从响应中提取的工具名",
                        "success": True
                    }
            
            return {
                "success": False,
                "error": "无法从响应中解析出有效的工具选择",
                "raw_response": response[:500]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"解析思考响应失败: {str(e)}",
                "raw_response": response[:500]
            }
    
    # 其他方法继续实现...
    def _assess_task_complexity(self, goal: str, context: ToolContext) -> TaskComplexity:
        """评估任务复杂度"""
        # 简化的复杂度评估逻辑
        if len(goal.split()) < 10:
            return TaskComplexity.SIMPLE
        elif "复杂" in goal or "多个" in goal or "批量" in goal:
            return TaskComplexity.COMPLEX
        else:
            return TaskComplexity.MEDIUM
    
    def _map_to_prompt_complexity(self, task_complexity: TaskComplexity) -> PromptComplexity:
        """将任务复杂度映射到提示词复杂度"""
        mapping = {
            TaskComplexity.SIMPLE: PromptComplexity.SIMPLE,
            TaskComplexity.MEDIUM: PromptComplexity.MEDIUM,
            TaskComplexity.COMPLEX: PromptComplexity.HIGH,
            TaskComplexity.CRITICAL: PromptComplexity.CRITICAL
        }
        return mapping.get(task_complexity, PromptComplexity.MEDIUM)
    
    def _auto_select_mode(self, orch_context: OrchestrationContext) -> OrchestrationMode:
        """自动选择编排模式"""
        if len(orch_context.available_tools) == 1:
            return OrchestrationMode.SINGLE_TOOL
        elif orch_context.task_complexity == TaskComplexity.SIMPLE:
            return OrchestrationMode.REACT_SIMPLE
        else:
            return OrchestrationMode.REACT_FULL
    
    def _build_error_result(self, orch_context: OrchestrationContext, message: str, error: str) -> Dict[str, Any]:
        """构建错误结果"""
        return {
            "status": "error",
            "message": message,
            "error": error,
            "iterations_used": orch_context.current_iteration + 1,
            "insights": orch_context.insights,
            "execution_history": [step for step in orch_context.execution_history]
        }
    
    def _build_success_result(self, orch_context: OrchestrationContext, message: str) -> Dict[str, Any]:
        """构建成功结果"""
        return {
            "status": "success",
            "message": message,
            "result": orch_context.final_result,
            "iterations_used": orch_context.current_iteration + 1,
            "insights": orch_context.insights,
            "execution_history": [step for step in orch_context.execution_history],
            "intermediate_results": orch_context.intermediate_results
        }
    
    def _build_partial_result(self, orch_context: OrchestrationContext, message: str) -> Dict[str, Any]:
        """构建部分成功结果"""
        return {
            "status": "partial_success",
            "message": message,
            "result": orch_context.intermediate_results,
            "iterations_used": orch_context.current_iteration + 1,
            "insights": orch_context.insights,
            "execution_history": [step for step in orch_context.execution_history]
        }


# 全局实例和便捷函数
_unified_orchestrator: Optional[UnifiedOrchestrator] = None


def get_unified_orchestrator() -> UnifiedOrchestrator:
    """获取统一编排器实例"""
    global _unified_orchestrator
    if _unified_orchestrator is None:
        from .tools import ToolChain
        tool_chain = ToolChain()  # 这里应该从服务中获取
        _unified_orchestrator = UnifiedOrchestrator(tool_chain)
    return _unified_orchestrator


async def tt(
    goal: str,
    context: ToolContext,
    mode: OrchestrationMode = OrchestrationMode.AUTO,
    available_tools: Optional[List[str]] = None,
    max_iterations: int = 5,
    progress_callback: Optional[callable] = None
) -> Dict[str, Any]:
    """
    统一编排函数 - 替换原有的tt函数
    
    这是整个系统的统一入口点，替换：
    - 原来的react_orchestrator.tt()
    - tools/orchestrator.py的各种编排方法
    - 直接的工具调用
    """
    orchestrator = get_unified_orchestrator()
    return await orchestrator.orchestrate(
        goal=goal,
        context=context,
        mode=mode,
        available_tools=available_tools,
        max_iterations=max_iterations,
        progress_callback=progress_callback
    )


# 便捷导入
__all__ = [
    "UnifiedOrchestrator",
    "OrchestrationMode", 
    "TaskComplexity",
    "OrchestrationContext",
    "OrchestrationStep",
    "get_unified_orchestrator",
    "tt"
]