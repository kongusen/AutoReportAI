"""
Infrastructure层DAG编排控制器

原始来源: app/services/agents/core/background_controller.py
重构为符合DDD Infrastructure层的技术基础设施服务

核心职责：
- 提供DAG编排的技术基础设施
- 决策分析和流程控制
- 模型选择和质量评估
- 为上层Agent服务提供编排支撑

技术职责：
- 纯技术实现，不包含业务逻辑
- 可被Application/Domain层的Agent调用
- 提供稳定的编排和控制服务
"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field

from .task_context import (
    AITaskContext, 
    ExecutionStep, 
    ExecutionStepType,
    ModelRequirement,
    TaskComplexity
)

logger = logging.getLogger(__name__)


class ControlDecision(Enum):
    """控制决策类型"""
    CONTINUE = "continue"      # 继续执行下一步
    RETRY = "retry"           # 重试当前步骤
    COMPLETE = "complete"     # 完成执行
    ABORT = "abort"          # 中止执行
    BRANCH = "branch"        # 分支执行
    MERGE = "merge"          # 合并结果


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "pending"       # 等待执行
    RUNNING = "running"       # 正在执行
    SUCCESS = "success"       # 成功完成
    FAILED = "failed"        # 执行失败
    RETRY = "retry"          # 重试中
    ABORTED = "aborted"      # 已中止


@dataclass 
class StepResult:
    """步骤执行结果"""
    step_id: str
    status: ExecutionStatus
    result_data: Any = None
    error_message: str = ""
    execution_time: float = 0.0
    model_used: str = ""
    confidence_score: float = 0.0
    quality_score: float = 0.0


@dataclass
class ControlContext:
    """控制上下文"""
    task_context: AITaskContext
    step_results: Dict[str, StepResult] = field(default_factory=dict)
    execution_history: List[Dict[str, Any]] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    error_count: int = 0
    retry_count: int = 0
    max_errors: int = 5
    max_retries: int = 10


class DAGController:
    """
    Infrastructure层DAG编排控制器
    
    核心职责：
    1. 分析当前执行状态和结果质量
    2. 决策是否需要执行下一步
    3. 选择Think模型还是Default模型
    4. 构建和管理DAG执行图
    5. 处理错误恢复和重试逻辑
    
    技术定位：
    - Infrastructure层技术基础设施
    - 为上层Agent提供DAG编排能力
    - 不包含具体业务逻辑
    """
    
    def __init__(self):
        # 决策规则配置
        self.decision_rules = self._build_decision_rules()
        
        # 质量阈值配置
        self.quality_thresholds = {
            "confidence_min": 0.7,
            "quality_min": 0.8,
            "error_rate_max": 0.2
        }
        
        # 性能统计
        self.execution_stats = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "avg_execution_time": 0.0,
            "model_usage": {"think": 0, "default": 0}
        }
        
        logger.info("DAG Controller Infrastructure服务初始化完成")
    
    def _build_decision_rules(self) -> Dict[str, Any]:
        """构建决策规则"""
        return {
            "continue_conditions": {
                "confidence_threshold": 0.6,
                "quality_threshold": 0.7,
                "error_rate_threshold": 0.3
            },
            "retry_conditions": {
                "max_retries": 3,
                "retry_on_low_confidence": True,
                "retry_on_validation_failure": True
            },
            "model_selection": {
                "think_triggers": [
                    "low_confidence_result",
                    "complex_sql_needed", 
                    "business_logic_required",
                    "validation_failed"
                ],
                "default_triggers": [
                    "simple_formatting",
                    "basic_calculation",
                    "data_retrieval",
                    "routine_processing"
                ]
            }
        }
    
    async def control_execution(
        self, 
        control_context: ControlContext
    ) -> Tuple[ControlDecision, Optional[ExecutionStep]]:
        """
        控制执行流程的核心方法
        
        Args:
            control_context: 控制上下文
            
        Returns:
            (控制决策, 下一步执行步骤)
        """
        try:
            task_context = control_context.task_context
            current_step = task_context.get_current_step()
            
            logger.info(f"DAG控制决策分析 - 任务: {task_context.task_id}, 当前步骤: {current_step.step_id if current_step else 'None'}")
            
            # 1. 分析当前状态
            state_analysis = await self._analyze_current_state(control_context)
            
            # 2. 评估结果质量
            quality_assessment = await self._assess_result_quality(control_context)
            
            # 3. 检查完成条件
            completion_check = await self._check_completion_conditions(control_context)
            
            # 4. 做出控制决策
            decision, next_step = await self._make_control_decision(
                control_context, state_analysis, quality_assessment, completion_check
            )
            
            # 5. 记录决策历史
            await self._record_decision(control_context, decision, state_analysis, quality_assessment)
            
            logger.info(f"DAG控制决策结果: {decision.value}, 下一步: {next_step.step_id if next_step else 'None'}")
            
            return decision, next_step
            
        except Exception as e:
            logger.error(f"DAG控制执行失败: {e}")
            return ControlDecision.ABORT, None
    
    async def _analyze_current_state(self, control_context: ControlContext) -> Dict[str, Any]:
        """分析当前执行状态"""
        task_context = control_context.task_context
        step_results = control_context.step_results
        
        analysis = {
            "completed_steps": len(step_results),
            "total_steps": len(task_context.execution_steps),
            "success_rate": 0.0,
            "avg_confidence": 0.0,
            "avg_quality": 0.0,
            "error_rate": 0.0,
            "execution_time": 0.0
        }
        
        if step_results:
            successful_steps = [r for r in step_results.values() if r.status == ExecutionStatus.SUCCESS]
            failed_steps = [r for r in step_results.values() if r.status == ExecutionStatus.FAILED]
            
            analysis["success_rate"] = len(successful_steps) / len(step_results)
            analysis["error_rate"] = len(failed_steps) / len(step_results)
            
            if successful_steps:
                analysis["avg_confidence"] = sum(r.confidence_score for r in successful_steps) / len(successful_steps)
                analysis["avg_quality"] = sum(r.quality_score for r in successful_steps) / len(successful_steps)
                analysis["execution_time"] = sum(r.execution_time for r in step_results.values())
        
        return analysis
    
    async def _assess_result_quality(self, control_context: ControlContext) -> Dict[str, Any]:
        """评估结果质量"""
        task_context = control_context.task_context
        step_results = control_context.step_results
        
        quality_assessment = {
            "overall_quality": 0.0,
            "confidence_level": "unknown",
            "validation_passed": False,
            "business_logic_valid": False,
            "data_consistency": False,
            "format_correctness": False
        }
        
        current_step = task_context.get_current_step()
        if not current_step:
            return quality_assessment
        
        # 检查当前步骤的结果
        current_result = step_results.get(current_step.step_id)
        if not current_result:
            return quality_assessment
        
        # 质量评估逻辑
        if current_result.status == ExecutionStatus.SUCCESS:
            quality_assessment["overall_quality"] = current_result.quality_score
            
            if current_result.confidence_score >= 0.8:
                quality_assessment["confidence_level"] = "high"
            elif current_result.confidence_score >= 0.6:
                quality_assessment["confidence_level"] = "medium"
            else:
                quality_assessment["confidence_level"] = "low"
            
            # 根据步骤类型进行特定验证
            if current_step.step_type == ExecutionStepType.SQL_GENERATION:
                quality_assessment["validation_passed"] = self._validate_sql_result(current_result)
            elif current_step.step_type == ExecutionStepType.BUSINESS_LOGIC:
                quality_assessment["business_logic_valid"] = self._validate_business_logic(current_result)
            elif current_step.step_type == ExecutionStepType.DATA_QUERY:
                quality_assessment["data_consistency"] = self._validate_data_consistency(current_result)
            elif current_step.step_type == ExecutionStepType.FORMATTING:
                quality_assessment["format_correctness"] = self._validate_format(current_result)
        
        return quality_assessment
    
    async def _check_completion_conditions(self, control_context: ControlContext) -> Dict[str, bool]:
        """检查完成条件"""
        task_context = control_context.task_context
        
        return {
            "all_steps_completed": task_context.is_completed(),
            "quality_threshold_met": True,  # 将根据实际质量评估结果确定
            "error_limit_exceeded": control_context.error_count >= control_context.max_errors,
            "retry_limit_exceeded": control_context.retry_count >= control_context.max_retries,
            "time_limit_exceeded": False  # 将根据时间约束确定
        }
    
    async def _make_control_decision(
        self,
        control_context: ControlContext,
        state_analysis: Dict[str, Any],
        quality_assessment: Dict[str, Any],
        completion_check: Dict[str, bool]
    ) -> Tuple[ControlDecision, Optional[ExecutionStep]]:
        """做出控制决策"""
        
        # 检查中止条件
        if completion_check["error_limit_exceeded"] or completion_check["retry_limit_exceeded"]:
            return ControlDecision.ABORT, None
        
        # 检查完成条件
        if completion_check["all_steps_completed"]:
            return ControlDecision.COMPLETE, None
        
        # 获取当前步骤和结果
        task_context = control_context.task_context
        current_step = task_context.get_current_step()
        current_result = control_context.step_results.get(current_step.step_id) if current_step else None
        
        # 如果当前步骤还没有结果，继续执行
        if not current_result:
            # 动态调整模型需求
            adjusted_step = await self._adjust_model_requirement(current_step, control_context)
            return ControlDecision.CONTINUE, adjusted_step
        
        # 如果当前步骤失败，决定是否重试
        if current_result.status == ExecutionStatus.FAILED:
            if current_step.retry_count < current_step.max_retries:
                return ControlDecision.RETRY, current_step
            else:
                # 重试次数用完，尝试降级处理或中止
                return ControlDecision.ABORT, None
        
        # 如果当前步骤成功但质量不佳，考虑重试或调整
        if current_result.status == ExecutionStatus.SUCCESS:
            if quality_assessment["confidence_level"] == "low" and current_step.retry_count < 2:
                # 低置信度结果，使用Think模型重试
                retry_step = await self._create_retry_step_with_think_model(current_step)
                return ControlDecision.RETRY, retry_step
            
            # 质量可接受，推进到下一步
            if task_context.advance_step():
                next_step = task_context.get_current_step()
                adjusted_step = await self._adjust_model_requirement(next_step, control_context)
                return ControlDecision.CONTINUE, adjusted_step
            else:
                return ControlDecision.COMPLETE, None
        
        # 默认继续执行
        return ControlDecision.CONTINUE, current_step
    
    async def _adjust_model_requirement(
        self, 
        step: ExecutionStep, 
        control_context: ControlContext
    ) -> ExecutionStep:
        """动态调整模型需求"""
        if step.model_requirement != ModelRequirement.AUTO:
            return step
        
        # 基于历史结果和当前状态选择模型
        task_context = control_context.task_context
        state_analysis = await self._analyze_current_state(control_context)
        
        # 决策逻辑
        use_think_model = False
        
        # 1. 复杂度检查
        if task_context.complexity in [TaskComplexity.HIGH, TaskComplexity.VERY_HIGH]:
            use_think_model = True
        
        # 2. 步骤类型检查
        if step.step_type in [
            ExecutionStepType.SQL_GENERATION,
            ExecutionStepType.BUSINESS_LOGIC,
            ExecutionStepType.VALIDATION
        ]:
            use_think_model = True
        
        # 3. 质量历史检查
        if state_analysis["avg_confidence"] < 0.7:
            use_think_model = True
        
        # 4. 错误率检查
        if state_analysis["error_rate"] > 0.2:
            use_think_model = True
        
        # 创建调整后的步骤
        adjusted_step = ExecutionStep(
            step_id=step.step_id,
            step_type=step.step_type,
            model_requirement=ModelRequirement.THINK if use_think_model else ModelRequirement.DEFAULT,
            tools_needed=step.tools_needed,
            dependencies=step.dependencies,
            expected_output=step.expected_output,
            retry_count=step.retry_count,
            max_retries=step.max_retries,
            timeout_seconds=step.timeout_seconds
        )
        
        logger.info(f"步骤 {step.step_id} 模型调整: {'THINK' if use_think_model else 'DEFAULT'}")
        
        return adjusted_step
    
    async def _create_retry_step_with_think_model(self, original_step: ExecutionStep) -> ExecutionStep:
        """创建使用Think模型的重试步骤"""
        retry_step = ExecutionStep(
            step_id=original_step.step_id,
            step_type=original_step.step_type,
            model_requirement=ModelRequirement.THINK,  # 强制使用Think模型
            tools_needed=original_step.tools_needed + ["enhanced_reasoning"],  # 添加增强推理工具
            dependencies=original_step.dependencies,
            expected_output=original_step.expected_output,
            retry_count=original_step.retry_count + 1,
            max_retries=original_step.max_retries,
            timeout_seconds=original_step.timeout_seconds
        )
        
        return retry_step
    
    async def _record_decision(
        self,
        control_context: ControlContext,
        decision: ControlDecision,
        state_analysis: Dict[str, Any],
        quality_assessment: Dict[str, Any]
    ):
        """记录决策历史"""
        decision_record = {
            "timestamp": time.time(),
            "decision": decision.value,
            "state_analysis": state_analysis,
            "quality_assessment": quality_assessment,
            "task_progress": control_context.task_context.get_execution_progress()
        }
        
        control_context.execution_history.append(decision_record)
        
        # 更新性能指标
        control_context.performance_metrics.update({
            "avg_step_time": state_analysis.get("execution_time", 0) / max(state_analysis.get("completed_steps", 1), 1),
            "current_success_rate": state_analysis.get("success_rate", 0),
            "current_confidence": state_analysis.get("avg_confidence", 0)
        })
    
    def _validate_sql_result(self, result: StepResult) -> bool:
        """验证SQL生成结果"""
        if not result.result_data:
            return False
        
        # 简单的SQL语法验证
        sql_text = str(result.result_data).upper()
        return any(keyword in sql_text for keyword in ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY'])
    
    def _validate_business_logic(self, result: StepResult) -> bool:
        """验证业务逻辑结果"""
        return result.confidence_score > 0.6 and result.quality_score > 0.7
    
    def _validate_data_consistency(self, result: StepResult) -> bool:
        """验证数据一致性"""
        # 检查是否有数据返回
        return result.result_data is not None and result.confidence_score > 0.5
    
    def _validate_format(self, result: StepResult) -> bool:
        """验证格式正确性"""
        return result.result_data is not None and result.quality_score > 0.8
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        return {
            "controller_stats": self.execution_stats,
            "quality_thresholds": self.quality_thresholds,
            "decision_rules": self.decision_rules
        }
    
    def update_quality_thresholds(self, new_thresholds: Dict[str, float]):
        """更新质量阈值"""
        self.quality_thresholds.update(new_thresholds)
        logger.info(f"质量阈值已更新: {self.quality_thresholds}")


def create_control_context(task_context: AITaskContext) -> ControlContext:
    """创建控制上下文"""
    return ControlContext(
        task_context=task_context,
        step_results={},
        execution_history=[],
        performance_metrics={},
        error_count=0,
        retry_count=0
    )