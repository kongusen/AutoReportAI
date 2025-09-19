"""
ReAct (Reasoning-Acting-Observing) 执行器

实现单步骤内的自我修正和容错优化机制
支持SQL生成-查询-验证-修改等典型场景
"""

import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional, AsyncIterator, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ...types import ToolCall, ToolResult, ToolSafetyLevel, ManagedContext
from .executor import ToolExecutor
from ..prompts import PromptManager


class ReActPhase(Enum):
    """ReAct阶段"""
    REASONING = "reasoning"
    ACTING = "acting"  
    OBSERVING = "observing"
    REFLECTION = "reflection"


class LoopDecision(Enum):
    """循环决策"""
    CONTINUE = "continue"
    SUCCESS = "success"
    FAILURE = "failure"
    MAX_ATTEMPTS = "max_attempts"


@dataclass
class ReActStep:
    """ReAct步骤"""
    step_id: str
    phase: ReActPhase
    reasoning: Optional[str] = None
    action_plan: Optional[Dict[str, Any]] = None
    tool_calls: List[ToolCall] = field(default_factory=list)
    observations: List[Dict[str, Any]] = field(default_factory=list)
    reflection: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass 
class ReActSession:
    """ReAct会话"""
    session_id: str
    objective: str
    context: ManagedContext
    steps: List[ReActStep] = field(default_factory=list)
    current_attempt: int = 0
    max_attempts: int = 5
    success_criteria: Dict[str, Any] = field(default_factory=dict)
    failure_patterns: List[str] = field(default_factory=list)
    
    # 状态跟踪
    is_complete: bool = False
    final_result: Optional[Any] = None
    loop_decision: Optional[LoopDecision] = None


@dataclass
class ObservationResult:
    """观察结果"""
    observation_id: str
    tool_result: ToolResult
    quality_score: float  # 0.0-1.0
    meets_criteria: bool
    issues_found: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    confidence: float = 0.8


class ReActExecutor:
    """ReAct执行器 - 实现推理-行动-观察循环"""
    
    def __init__(self, 
                 base_executor: ToolExecutor,
                 llm_provider=None,
                 prompt_manager: PromptManager = None):
        self.base_executor = base_executor
        self.llm_provider = llm_provider
        
        # Prompt管理器 - 增强prompt工程能力
        self.prompt_manager = prompt_manager or PromptManager()
        
        # 会话管理
        self.active_sessions: Dict[str, ReActSession] = {}
        self.session_history: List[ReActSession] = []
        
        # 观察器注册表
        self.observers: Dict[str, Callable] = {
            "sql_query": self._observe_sql_result,
            "file_operation": self._observe_file_result,
            "data_analysis": self._observe_analysis_result,
            "general": self._observe_general_result
        }
        
        # 推理器注册表 - 现在使用prompt驱动
        self.reasoners: Dict[str, Callable] = {
            "sql_generation": self._reason_sql_task_with_prompts,
            "data_processing": self._reason_data_task_with_prompts,
            "general": self._reason_general_task_with_prompts
        }
        
        # 性能指标
        self.metrics = {
            "total_sessions": 0,
            "successful_sessions": 0, 
            "average_attempts": 0.0,
            "common_failure_patterns": {},
            "prompt_performance": {}
        }
    
    async def execute_with_react(self, 
                                objective: str,
                                initial_context: ManagedContext,
                                success_criteria: Dict[str, Any],
                                task_type: str = "general",
                                max_attempts: int = 5) -> AsyncIterator[Dict[str, Any]]:
        """使用ReAct机制执行任务"""
        
        session_id = self._generate_session_id()
        
        # 创建ReAct会话
        session = ReActSession(
            session_id=session_id,
            objective=objective,
            context=initial_context,
            max_attempts=max_attempts,
            success_criteria=success_criteria
        )
        
        self.active_sessions[session_id] = session
        
        yield {
            "type": "react_session_start",
            "session_id": session_id,
            "objective": objective,
            "max_attempts": max_attempts,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # 开始ReAct循环
            async for event in self._react_loop(session, task_type):
                yield event
                
            # 最终结果
            yield {
                "type": "react_session_complete",
                "session_id": session_id,
                "success": session.loop_decision == LoopDecision.SUCCESS,
                "attempts_used": session.current_attempt,
                "final_result": session.final_result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            yield {
                "type": "react_session_error",
                "session_id": session_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        
        finally:
            # 清理会话
            self._cleanup_session(session_id)
    
    async def _react_loop(self, session: ReActSession, task_type: str) -> AsyncIterator[Dict[str, Any]]:
        """ReAct主循环"""
        
        while not session.is_complete and session.current_attempt < session.max_attempts:
            session.current_attempt += 1
            step_id = f"step_{session.current_attempt}_{int(time.time())}"
            
            yield {
                "type": "react_attempt_start",
                "session_id": session.session_id,
                "attempt": session.current_attempt,
                "step_id": step_id
            }
            
            # Phase 1: 推理 (Reasoning)
            async for event in self._reasoning_phase(session, step_id, task_type):
                yield event
            
            # Phase 2: 行动 (Acting)  
            async for event in self._acting_phase(session, step_id):
                yield event
            
            # Phase 3: 观察 (Observing)
            async for event in self._observing_phase(session, step_id, task_type):
                yield event
            
            # Phase 4: 反思与决策 (Reflection)
            async for event in self._reflection_phase(session, step_id):
                yield event
                
            # 检查是否继续
            if session.loop_decision in [LoopDecision.SUCCESS, LoopDecision.FAILURE]:
                session.is_complete = True
                break
        
        # 如果达到最大尝试次数
        if session.current_attempt >= session.max_attempts and not session.is_complete:
            session.loop_decision = LoopDecision.MAX_ATTEMPTS
            session.is_complete = True
    
    async def _reasoning_phase(self, session: ReActSession, step_id: str, task_type: str) -> AsyncIterator[Dict[str, Any]]:
        """推理阶段：分析当前状态，制定行动计划"""
        
        yield {
            "type": "phase_start", 
            "phase": "reasoning",
            "step_id": step_id,
            "attempt": session.current_attempt
        }
        
        # 获取推理器
        reasoner = self.reasoners.get(task_type, self.reasoners["general"])
        
        # 执行推理
        reasoning_result = await reasoner(session)
        
        # 创建步骤记录
        step = ReActStep(
            step_id=step_id,
            phase=ReActPhase.REASONING,
            reasoning=reasoning_result["reasoning"],
            action_plan=reasoning_result["action_plan"]
        )
        
        session.steps.append(step)
        
        yield {
            "type": "reasoning_complete",
            "step_id": step_id,
            "reasoning": reasoning_result["reasoning"],
            "action_plan": reasoning_result["action_plan"],
            "confidence": reasoning_result.get("confidence", 0.8)
        }
    
    async def _acting_phase(self, session: ReActSession, step_id: str) -> AsyncIterator[Dict[str, Any]]:
        """行动阶段：执行制定的行动计划"""
        
        yield {
            "type": "phase_start",
            "phase": "acting", 
            "step_id": step_id
        }
        
        current_step = session.steps[-1]
        action_plan = current_step.action_plan
        
        if not action_plan or "tool_calls" not in action_plan:
            yield {
                "type": "acting_error",
                "step_id": step_id,
                "error": "No valid action plan found"
            }
            return
        
        # 创建工具调用
        tool_calls = []
        for tool_spec in action_plan["tool_calls"]:
            tool_call = ToolCall(
                tool_name=tool_spec["tool_name"],
                input_data=tool_spec["input_data"],
                safety_level=ToolSafetyLevel.CAUTIOUS,
                call_id=f"call_{uuid.uuid4().hex[:8]}"
            )
            tool_calls.append(tool_call)
        
        current_step.tool_calls = tool_calls
        
        # 执行工具调用
        for tool_call in tool_calls:
            yield {
                "type": "tool_execution_start",
                "step_id": step_id,
                "tool_name": tool_call.tool_name,
                "call_id": tool_call.call_id
            }
            
            try:
                # 使用基础执行器执行工具
                tool_result = await self.base_executor.execute_single_tool(tool_call)
                
                yield {
                    "type": "tool_execution_complete",
                    "step_id": step_id,
                    "tool_name": tool_call.tool_name,
                    "call_id": tool_call.call_id,
                    "success": tool_result.error is None,
                    "execution_time": tool_result.execution_time
                }
                
                # 存储结果供观察阶段使用
                current_step.observations.append({
                    "type": "tool_result",
                    "tool_call": tool_call,
                    "result": tool_result
                })
                
            except Exception as e:
                yield {
                    "type": "tool_execution_error",
                    "step_id": step_id,
                    "tool_name": tool_call.tool_name,
                    "call_id": tool_call.call_id,
                    "error": str(e)
                }
    
    async def _observing_phase(self, session: ReActSession, step_id: str, task_type: str) -> AsyncIterator[Dict[str, Any]]:
        """观察阶段：评估执行结果质量 - prompt增强版本"""
        
        yield {
            "type": "phase_start",
            "phase": "observing",
            "step_id": step_id
        }
        
        current_step = session.steps[-1]
        
        # 提取工具执行结果
        tool_results = [obs for obs in current_step.observations if obs.get("type") == "tool_result"]
        
        if not tool_results:
            yield {
                "type": "observing_error",
                "step_id": step_id,
                "error": "No tool results to observe"
            }
            return
        
        # 使用prompt增强的观察
        observations = await self._observe_with_prompts(session, step_id, task_type, tool_results)
        
        overall_quality = 0.0
        meets_all_criteria = True
        
        # 处理观察结果
        for observation in observations:
            overall_quality += observation.quality_score
            if not observation.meets_criteria:
                meets_all_criteria = False
            
            yield {
                "type": "observation_complete",
                "step_id": step_id,
                "observation_id": observation.observation_id,
                "quality_score": observation.quality_score,
                "meets_criteria": observation.meets_criteria,
                "issues_found": observation.issues_found,
                "suggestions": observation.suggestions,
                "confidence": observation.confidence
            }
        
        # 计算整体评估
        if observations:
            overall_quality /= len(observations)
        
        # 存储观察结果供反思阶段使用
        current_step.observations.extend([{
            "type": "quality_assessment",
            "overall_quality": overall_quality,
            "meets_all_criteria": meets_all_criteria,
            "individual_observations": [obs.observation_id for obs in observations],
            "detailed_observations": observations
        }])
        
        yield {
            "type": "observing_summary",
            "step_id": step_id,
            "overall_quality": overall_quality,
            "meets_criteria": meets_all_criteria,
            "total_observations": len(observations)
        }
    
    async def _reflection_phase(self, session: ReActSession, step_id: str) -> AsyncIterator[Dict[str, Any]]:
        """反思阶段：决定是否继续循环 - prompt增强版本"""
        
        yield {
            "type": "phase_start",
            "phase": "reflection",
            "step_id": step_id
        }
        
        current_step = session.steps[-1]
        
        # 分析观察结果
        quality_assessment = None
        for obs in current_step.observations:
            if obs.get("type") == "quality_assessment":
                quality_assessment = obs
                break
        
        if not quality_assessment:
            session.loop_decision = LoopDecision.FAILURE
            current_step.reflection = "未能获取质量评估结果，任务失败。"
            yield {
                "type": "reflection_error",
                "step_id": step_id,
                "error": "No quality assessment found"
            }
            return
        
        # 获取详细观察结果
        detailed_observations = quality_assessment.get("detailed_observations", [])
        
        # 使用prompt增强的反思
        reflection_result = await self._reflect_with_prompts(session, step_id, detailed_observations)
        
        # 设置决策
        decision_mapping = {
            "CONTINUE": LoopDecision.CONTINUE,
            "SUCCESS": LoopDecision.SUCCESS,
            "FAILURE": LoopDecision.FAILURE
        }
        
        decision_str = reflection_result.get("decision", "CONTINUE")
        session.loop_decision = decision_mapping.get(decision_str, LoopDecision.CONTINUE)
        
        # 处理特殊情况
        overall_quality = quality_assessment["overall_quality"]
        
        if session.current_attempt >= session.max_attempts and session.loop_decision == LoopDecision.CONTINUE:
            session.loop_decision = LoopDecision.MAX_ATTEMPTS
            reflection_result["reflection"] += f" 但已达到最大尝试次数({session.max_attempts})。"
        
        if session.loop_decision == LoopDecision.SUCCESS:
            session.final_result = self._extract_final_result(session)
        
        current_step.reflection = reflection_result["reflection"]
        current_step.phase = ReActPhase.REFLECTION
        
        yield {
            "type": "reflection_complete",
            "step_id": step_id,
            "decision": session.loop_decision.value,
            "reflection": reflection_result["reflection"],
            "quality_score": overall_quality,
            "confidence": reflection_result.get("confidence", 0.8),
            "will_continue": session.loop_decision == LoopDecision.CONTINUE
        }
    
    async def _reason_sql_task_with_prompts(self, session: ReActSession) -> Dict[str, Any]:
        """SQL任务推理器 - prompt驱动版本"""
        
        # 构建前序步骤信息
        previous_steps = []
        for step in session.steps:
            step_info = {
                "reasoning": step.reasoning,
                "action_results": self._extract_step_results(step),
                "observation": self._extract_step_observations(step),
                "reflection": step.reflection
            }
            previous_steps.append(step_info)
        
        # 构建成功标准
        success_criteria = {
            "sql_syntactic_correctness": "SQL语法必须正确",
            "data_retrieval_success": "成功检索数据",
            "result_relevance": "结果与业务目标相关",
            "performance_acceptable": "查询性能可接受"
        }
        
        # 构建失败模式（从历史步骤中学习）
        failure_patterns = []
        for step in session.steps:
            issues = self._extract_issues_from_step(step)
            failure_patterns.extend(issues)
        
        # 使用prompt管理器生成推理prompt
        reasoning_prompt = self.prompt_manager.react_reasoning(
            objective=session.objective,
            current_attempt=session.current_attempt,
            max_attempts=session.max_attempts,
            previous_steps=previous_steps,
            success_criteria=success_criteria,
            failure_patterns=failure_patterns
        )
        
        # 如果有LLM提供器，使用它来生成推理
        if self.llm_provider:
            try:
                llm_response = await self.llm_provider.generate(reasoning_prompt)
                reasoning_result = self._parse_reasoning_response(llm_response)
            except Exception as e:
                # 如果LLM失败，使用fallback逻辑
                reasoning_result = self._fallback_sql_reasoning(session)
        else:
            # 没有LLM时使用fallback逻辑
            reasoning_result = self._fallback_sql_reasoning(session)
        
        return reasoning_result
    
    async def _reason_data_task_with_prompts(self, session: ReActSession) -> Dict[str, Any]:
        """数据处理任务推理器 - prompt驱动版本"""
        
        reasoning_prompt = self.prompt_manager.react_reasoning(
            objective=session.objective,
            current_attempt=session.current_attempt,
            max_attempts=session.max_attempts
        )
        
        if self.llm_provider:
            try:
                llm_response = await self.llm_provider.generate(reasoning_prompt)
                return self._parse_reasoning_response(llm_response)
            except Exception:
                pass
        
        # Fallback逻辑
        return {
            "reasoning": f"数据处理任务第{session.current_attempt}次尝试：{session.objective}",
            "action_plan": {
                "tool_calls": [{
                    "tool_name": "data_processor",
                    "input_data": {
                        "task": session.objective,
                        "context": session.context.active_context.content
                    }
                }]
            },
            "confidence": 0.7
        }
    
    async def _reason_general_task_with_prompts(self, session: ReActSession) -> Dict[str, Any]:
        """通用任务推理器 - prompt驱动版本"""
        
        reasoning_prompt = self.prompt_manager.react_reasoning(
            objective=session.objective,
            current_attempt=session.current_attempt,
            max_attempts=session.max_attempts
        )
        
        if self.llm_provider:
            try:
                llm_response = await self.llm_provider.generate(reasoning_prompt)
                return self._parse_reasoning_response(llm_response)
            except Exception:
                pass
        
        # Fallback逻辑
        objective = session.objective
        attempt = session.current_attempt
        
        reasoning = f"通用任务第{attempt}次尝试：{objective}"
        
        # 根据目标选择合适的工具
        if "sql" in objective.lower() or "generator" in objective.lower():
            tool_name = "sql_generator"
        else:
            tool_name = "simple_query"
        
        action_plan = {
            "tool_calls": [{
                "tool_name": tool_name,
                "input_data": {
                    "objective": objective,
                    "attempt": attempt
                }
            }]
        }
        
        return {
            "reasoning": reasoning,
            "action_plan": action_plan,
            "confidence": 0.6
        }
    
    async def _observe_with_prompts(self, session: ReActSession, step_id: str, task_type: str, tool_results: List[Dict[str, Any]]) -> List[ObservationResult]:
        """使用prompt增强的观察阶段"""
        
        # 准备工具结果数据
        formatted_tool_results = []
        for tool_data in tool_results:
            tool_result = tool_data["result"]
            formatted_result = {
                "tool_name": tool_data["tool_call"].tool_name,
                "success": tool_result.error is None,
                "result": tool_result.result if tool_result.error is None else None,
                "error": tool_result.error,
                "execution_time": tool_result.execution_time
            }
            formatted_tool_results.append(formatted_result)
        
        # 生成观察prompt
        observation_prompt = self.prompt_manager.react_observation(
            objective=session.objective,
            tool_results=formatted_tool_results,
            success_criteria=session.success_criteria,
            current_attempt=session.current_attempt,
            max_attempts=session.max_attempts
        )
        
        observations = []
        
        # 如果有LLM，使用它进行智能观察
        if self.llm_provider:
            try:
                llm_response = await self.llm_provider.generate(observation_prompt)
                parsed_observations = self._parse_observation_response(llm_response, tool_results)
                observations.extend(parsed_observations)
            except Exception:
                # Fallback到基础观察器
                pass
        
        # 如果没有LLM观察结果，使用基础观察器
        if not observations:
            observer = self.observers.get(task_type, self.observers["general"])
            for tool_data in tool_results:
                tool_result = tool_data["result"]
                observation = await observer(tool_result, session.success_criteria)
                observations.append(observation)
        
        return observations
    
    async def _reflect_with_prompts(self, session: ReActSession, step_id: str, observation_results: List[ObservationResult]) -> Dict[str, Any]:
        """使用prompt增强的反思阶段"""
        
        # 计算整体质量
        overall_quality = sum(obs.quality_score for obs in observation_results) / len(observation_results) if observation_results else 0.0
        meets_criteria = all(obs.meets_criteria for obs in observation_results)
        
        # 准备观察结果数据
        formatted_observations = []
        for obs in observation_results:
            formatted_obs = {
                "item": f"工具执行_{obs.observation_id}",
                "quality_score": obs.quality_score,
                "meets_criteria": obs.meets_criteria,
                "issues": obs.issues_found,
                "suggestions": obs.suggestions
            }
            formatted_observations.append(formatted_obs)
        
        # 生成反思prompt
        reflection_prompt = self.prompt_manager.react_reflection(
            objective=session.objective,
            observation_results=formatted_observations,
            overall_quality=overall_quality,
            meets_criteria=meets_criteria,
            current_attempt=session.current_attempt,
            max_attempts=session.max_attempts,
            success_criteria=session.success_criteria
        )
        
        # 如果有LLM，使用它进行智能反思
        if self.llm_provider:
            try:
                llm_response = await self.llm_provider.generate(reflection_prompt)
                reflection_result = self._parse_reflection_response(llm_response)
                
                return {
                    "reflection": reflection_result["reflection"],
                    "decision": reflection_result["decision"],
                    "confidence": reflection_result.get("confidence", 0.8)
                }
            except Exception:
                pass
        
        # Fallback到基础反思逻辑
        return self._fallback_reflection_logic(session, overall_quality, meets_criteria)
    
    async def _observe_sql_result(self, tool_result: ToolResult, success_criteria: Dict[str, Any]) -> ObservationResult:
        """SQL结果观察器"""
        
        observation_id = f"obs_{uuid.uuid4().hex[:8]}"
        
        if tool_result.error:
            return ObservationResult(
                observation_id=observation_id,
                tool_result=tool_result,
                quality_score=0.0,
                meets_criteria=False,
                issues_found=[f"SQL执行错误: {tool_result.error}"],
                suggestions=["检查SQL语法", "验证表名和字段名", "检查数据库连接"]
            )
        
        result_data = tool_result.result
        quality_score = 0.7  # 基础分数
        issues = []
        suggestions = []
        
        # 检查结果数量
        expected_min_rows = success_criteria.get("min_rows", 0)
        expected_max_rows = success_criteria.get("max_rows", float('inf'))
        
        if isinstance(result_data, dict) and "rows" in result_data:
            row_count = len(result_data["rows"])
            
            if row_count < expected_min_rows:
                issues.append(f"结果行数({row_count})少于预期最小值({expected_min_rows})")
                quality_score -= 0.3
                suggestions.append("检查WHERE条件是否过于严格")
            
            if row_count > expected_max_rows:
                issues.append(f"结果行数({row_count})超过预期最大值({expected_max_rows})")
                quality_score -= 0.2
                suggestions.append("添加更严格的筛选条件")
            
            if row_count > 0:
                quality_score += 0.2  # 有数据加分
        
        # 检查必需字段
        required_fields = success_criteria.get("required_fields", [])
        if isinstance(result_data, dict) and "columns" in result_data:
            missing_fields = set(required_fields) - set(result_data["columns"])
            if missing_fields:
                issues.append(f"缺少必需字段: {list(missing_fields)}")
                quality_score -= 0.4
                suggestions.append(f"在SELECT中添加字段: {', '.join(missing_fields)}")
        
        quality_score = max(0.0, min(1.0, quality_score))
        meets_criteria = len(issues) == 0 and quality_score >= 0.7
        
        return ObservationResult(
            observation_id=observation_id,
            tool_result=tool_result,
            quality_score=quality_score,
            meets_criteria=meets_criteria,
            issues_found=issues,
            suggestions=suggestions,
            confidence=0.9
        )
    
    async def _observe_file_result(self, tool_result: ToolResult, success_criteria: Dict[str, Any]) -> ObservationResult:
        """文件操作结果观察器"""
        
        observation_id = f"obs_{uuid.uuid4().hex[:8]}"
        
        if tool_result.error:
            return ObservationResult(
                observation_id=observation_id,
                tool_result=tool_result,
                quality_score=0.0,
                meets_criteria=False,
                issues_found=[f"文件操作错误: {tool_result.error}"]
            )
        
        # 简化的文件结果评估
        quality_score = 0.8 if tool_result.result.get("status") == "success" else 0.3
        meets_criteria = quality_score >= 0.7
        
        return ObservationResult(
            observation_id=observation_id,
            tool_result=tool_result,
            quality_score=quality_score,
            meets_criteria=meets_criteria
        )
    
    async def _observe_analysis_result(self, tool_result: ToolResult, success_criteria: Dict[str, Any]) -> ObservationResult:
        """数据分析结果观察器"""
        
        observation_id = f"obs_{uuid.uuid4().hex[:8]}"
        
        # 简化实现
        quality_score = 0.7
        meets_criteria = tool_result.error is None
        
        return ObservationResult(
            observation_id=observation_id,
            tool_result=tool_result,
            quality_score=quality_score,
            meets_criteria=meets_criteria
        )
    
    async def _observe_general_result(self, tool_result: ToolResult, success_criteria: Dict[str, Any]) -> ObservationResult:
        """通用结果观察器"""
        
        observation_id = f"obs_{uuid.uuid4().hex[:8]}"
        
        quality_score = 0.6 if tool_result.error is None else 0.2
        meets_criteria = tool_result.error is None
        
        return ObservationResult(
            observation_id=observation_id,
            tool_result=tool_result,
            quality_score=quality_score,
            meets_criteria=meets_criteria
        )
    
    async def _generate_improvement_reflection(self, session: ReActSession, quality_assessment: Dict[str, Any]) -> str:
        """生成改进反思"""
        
        current_quality = quality_assessment["overall_quality"]
        attempt = session.current_attempt
        
        if current_quality < 0.5:
            return f"第{attempt}次尝试质量较低({current_quality:.2f})，需要重新分析需求并调整方法。"
        else:
            return f"第{attempt}次尝试部分成功({current_quality:.2f})，需要根据观察结果进行细节优化。"
    
    def _extract_issues_from_step(self, step: ReActStep) -> List[str]:
        """从步骤中提取问题列表"""
        
        issues = []
        for obs in step.observations:
            if "issues_found" in obs:
                issues.extend(obs["issues_found"])
        
        return issues
    
    def _extract_previous_sql(self, step: ReActStep) -> Optional[str]:
        """提取前一次的SQL"""
        
        for obs in step.observations:
            if obs.get("type") == "tool_result":
                tool_result = obs["result"]
                if hasattr(tool_result, 'result') and isinstance(tool_result.result, dict):
                    return tool_result.result.get("sql_query")
        
        return None
    
    def _extract_final_result(self, session: ReActSession) -> Any:
        """提取最终结果"""
        
        if not session.steps:
            return None
        
        last_step = session.steps[-1]
        for obs in last_step.observations:
            if obs.get("type") == "tool_result":
                return obs["result"].result
        
        return None
    
    def _generate_session_id(self) -> str:
        """生成会话ID"""
        return f"react_{uuid.uuid4().hex[:8]}_{int(time.time())}"
    
    def _cleanup_session(self, session_id: str):
        """清理会话"""
        
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            self.session_history.append(session)
            del self.active_sessions[session_id]
            
            # 更新指标
            self.metrics["total_sessions"] += 1
            if session.loop_decision == LoopDecision.SUCCESS:
                self.metrics["successful_sessions"] += 1
            
            # 更新平均尝试次数
            total_sessions = self.metrics["total_sessions"]
            current_avg = self.metrics["average_attempts"]
            self.metrics["average_attempts"] = (
                (current_avg * (total_sessions - 1) + session.current_attempt) / total_sessions
            )
    
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话状态"""
        
        session = self.active_sessions.get(session_id)
        if not session:
            return None
        
        return {
            "session_id": session_id,
            "objective": session.objective,
            "current_attempt": session.current_attempt,
            "max_attempts": session.max_attempts,
            "is_complete": session.is_complete,
            "loop_decision": session.loop_decision.value if session.loop_decision else None,
            "steps_completed": len(session.steps),
            "final_result": session.final_result
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取执行指标"""
        
        success_rate = (
            self.metrics["successful_sessions"] / self.metrics["total_sessions"]
        ) if self.metrics["total_sessions"] > 0 else 0
        
        return {
            "metrics": self.metrics,
            "success_rate": success_rate,
            "active_sessions": len(self.active_sessions),
            "session_history_size": len(self.session_history),
            "prompt_cache_stats": self.prompt_manager.get_cache_stats() if self.prompt_manager else {}
        }
    
    # ==================== Prompt解析辅助方法 ====================
    
    def _parse_reasoning_response(self, llm_response: str) -> Dict[str, Any]:
        """解析LLM推理响应"""
        
        # 简化实现：从响应中提取关键信息
        lines = llm_response.strip().split('\n')
        
        reasoning = ""
        action_plan = {"tool_calls": []}
        confidence = 0.7
        
        # 尝试提取推理内容
        for line in lines:
            if "推理" in line or "分析" in line:
                reasoning = line.strip()
                break
        
        if not reasoning:
            reasoning = "基于LLM分析的推理结果"
        
        # 简单的工具调用提取（实际应用中可以更复杂）
        if "sql" in llm_response.lower():
            action_plan["tool_calls"].append({
                "tool_name": "sql_generator",
                "input_data": {"objective": "LLM建议的SQL任务"}
            })
        else:
            action_plan["tool_calls"].append({
                "tool_name": "simple_query",
                "input_data": {"objective": "LLM建议的通用任务"}
            })
        
        return {
            "reasoning": reasoning,
            "action_plan": action_plan,
            "confidence": confidence
        }
    
    def _parse_observation_response(self, llm_response: str, tool_results: List[Dict[str, Any]]) -> List[ObservationResult]:
        """解析LLM观察响应"""
        
        observations = []
        
        # 为每个工具结果创建观察
        for i, tool_data in enumerate(tool_results):
            observation_id = f"llm_obs_{uuid.uuid4().hex[:8]}"
            tool_result = tool_data["result"]
            
            # 从LLM响应中提取质量评分（简化实现）
            quality_score = 0.7  # 默认分数
            if "高质量" in llm_response or "成功" in llm_response:
                quality_score = 0.9
            elif "低质量" in llm_response or "失败" in llm_response:
                quality_score = 0.3
            
            meets_criteria = tool_result.error is None and quality_score >= 0.7
            
            observation = ObservationResult(
                observation_id=observation_id,
                tool_result=tool_result,
                quality_score=quality_score,
                meets_criteria=meets_criteria,
                issues_found=[] if meets_criteria else ["LLM识别的问题"],
                suggestions=["LLM建议的改进"] if not meets_criteria else [],
                confidence=0.8
            )
            
            observations.append(observation)
        
        return observations
    
    def _parse_reflection_response(self, llm_response: str) -> Dict[str, Any]:
        """解析LLM反思响应"""
        
        # 简化实现：从响应中提取决策
        decision = "CONTINUE"
        reflection = llm_response.strip()
        confidence = 0.8
        
        if "成功" in llm_response or "SUCCESS" in llm_response.upper():
            decision = "SUCCESS"
        elif "失败" in llm_response or "FAILURE" in llm_response.upper():
            decision = "FAILURE"
        elif "继续" in llm_response or "CONTINUE" in llm_response.upper():
            decision = "CONTINUE"
        
        return {
            "reflection": reflection,
            "decision": decision,
            "confidence": confidence
        }
    
    # ==================== Fallback方法 ====================
    
    def _fallback_sql_reasoning(self, session: ReActSession) -> Dict[str, Any]:
        """SQL推理fallback逻辑"""
        
        objective = session.objective
        previous_attempts = session.steps
        
        if not previous_attempts:
            reasoning = f"首次尝试SQL任务：{objective}。需要生成SQL查询并执行。"
            action_plan = {
                "tool_calls": [{
                    "tool_name": "sql_generator",
                    "input_data": {
                        "objective": objective,
                        "context": session.context.active_context.content
                    }
                }]
            }
        else:
            last_step = previous_attempts[-1]
            issues = self._extract_issues_from_step(last_step)
            
            reasoning = f"第{session.current_attempt}次尝试。前一次的问题：{', '.join(issues)}。需要修改SQL并重新执行。"
            action_plan = {
                "tool_calls": [{
                    "tool_name": "sql_generator", 
                    "input_data": {
                        "objective": objective,
                        "previous_sql": self._extract_previous_sql(last_step),
                        "issues_to_fix": issues,
                        "context": session.context.active_context.content
                    }
                }]
            }
        
        return {
            "reasoning": reasoning,
            "action_plan": action_plan,
            "confidence": 0.8
        }
    
    def _fallback_reflection_logic(self, session: ReActSession, overall_quality: float, meets_criteria: bool) -> Dict[str, Any]:
        """反思fallback逻辑"""
        
        if meets_criteria and overall_quality >= 0.8:
            return {
                "reflection": "任务成功完成，结果满足所有成功标准。",
                "decision": "SUCCESS",
                "confidence": 0.9
            }
        elif session.current_attempt >= session.max_attempts:
            return {
                "reflection": f"已达到最大尝试次数({session.max_attempts})，任务未能完成。",
                "decision": "FAILURE",
                "confidence": 0.8
            }
        elif overall_quality < 0.3:
            return {
                "reflection": "执行结果质量过低，任务失败。",
                "decision": "FAILURE",
                "confidence": 0.7
            }
        else:
            return {
                "reflection": f"第{session.current_attempt}次尝试部分成功({overall_quality:.2f})，需要根据观察结果进行细节优化。",
                "decision": "CONTINUE",
                "confidence": 0.6
            }
    
    # ==================== 数据提取辅助方法 ====================
    
    def _extract_step_results(self, step: ReActStep) -> List[Dict[str, Any]]:
        """从步骤中提取行动结果"""
        
        results = []
        for obs in step.observations:
            if obs.get("type") == "tool_result":
                tool_result = obs["result"]
                results.append({
                    "tool_name": obs["tool_call"].tool_name,
                    "success": tool_result.error is None,
                    "result": tool_result.result,
                    "error": tool_result.error,
                    "execution_time": tool_result.execution_time
                })
        return results
    
    def _extract_step_observations(self, step: ReActStep) -> List[str]:
        """从步骤中提取观察信息"""
        
        observations = []
        for obs in step.observations:
            if obs.get("type") == "quality_assessment":
                observations.append(f"整体质量: {obs['overall_quality']:.2f}")
                if obs.get("individual_observations"):
                    observations.append(f"观察项数: {len(obs['individual_observations'])}")
        return observations