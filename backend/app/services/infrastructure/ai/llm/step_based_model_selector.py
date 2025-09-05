"""
分步骤智能模型选择器

基于AutoReportAI Agent设计的智能模型选择机制：
- 分步骤模型选择: 每个处理步骤根据复杂度自动选择default或think模型
- 复杂度映射: 占位符分析(中等)→默认模型，SQL生成(高)→think模型，SQL纠错(关键)→think模型
- 按需求配置: 低/中等复杂度使用default模型节省成本，高/关键复杂度使用think模型确保质量
"""

import logging
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """任务复杂度级别"""
    LOW = "low"                    # 简单任务 - 使用默认模型
    MEDIUM = "medium"              # 中等复杂度 - 使用默认模型
    HIGH = "high"                  # 高复杂度 - 使用think模型
    CRITICAL = "critical"          # 关键任务 - 使用think模型


class ProcessingStep(Enum):
    """处理步骤类型"""
    # 占位符相关
    PLACEHOLDER_ANALYSIS = "placeholder_analysis"           # 中等
    PLACEHOLDER_PARSING = "placeholder_parsing"             # 低
    
    # SQL相关  
    SQL_GENERATION = "sql_generation"                       # 高
    SQL_VALIDATION = "sql_validation"                       # 高
    SQL_ERROR_CORRECTION = "sql_error_correction"           # 关键
    SQL_TESTING = "sql_testing"                            # 高
    
    # 图表相关
    CHART_SPEC_GENERATION = "chart_spec_generation"         # 中等
    CHART_VALIDATION = "chart_validation"                   # 中等
    
    # 上下文相关
    CONTEXT_ANALYSIS = "context_analysis"                   # 中等
    CONTEXT_INTEGRATION = "context_integration"             # 高
    TIME_CONTEXT_ANALYSIS = "time_context_analysis"         # 中等
    
    # 任务相关
    TASK_ANALYSIS = "task_analysis"                         # 中等
    TASK_SUPPLEMENT = "task_supplement"                     # 高
    
    # 数据相关
    DATA_SOURCE_ANALYSIS = "data_source_analysis"           # 中等
    ETL_DATA_PROCESSING = "etl_data_processing"             # 高
    
    # 通用
    GENERAL_REASONING = "general_reasoning"                 # 低
    ERROR_HANDLING = "error_handling"                       # 高


@dataclass
class ModelSelection:
    """模型选择结果"""
    model_type: str                    # 'default' 或 'think'
    complexity: TaskComplexity
    step: ProcessingStep
    reason: str                        # 选择理由
    cost_level: str                    # 成本级别: 'low', 'medium', 'high'
    quality_level: str                 # 质量级别: 'standard', 'high', 'premium'


@dataclass 
class StepContext:
    """步骤上下文信息"""
    step: ProcessingStep
    task_description: str
    previous_errors: int = 0           # 之前的错误次数
    has_user_feedback: bool = False    # 是否有用户反馈
    time_pressure: bool = False        # 是否有时间压力
    data_complexity: str = "medium"    # 数据复杂度
    custom_complexity: Optional[TaskComplexity] = None  # 自定义复杂度


class StepBasedModelSelector:
    """分步骤智能模型选择器"""
    
    # 步骤复杂度映射表
    STEP_COMPLEXITY_MAPPING = {
        # 占位符相关 - 分析需要理解，解析相对简单
        ProcessingStep.PLACEHOLDER_ANALYSIS: TaskComplexity.MEDIUM,
        ProcessingStep.PLACEHOLDER_PARSING: TaskComplexity.LOW,
        
        # SQL相关 - 生成和验证需要高质量，纠错是关键
        ProcessingStep.SQL_GENERATION: TaskComplexity.HIGH,
        ProcessingStep.SQL_VALIDATION: TaskComplexity.HIGH,
        ProcessingStep.SQL_ERROR_CORRECTION: TaskComplexity.CRITICAL,
        ProcessingStep.SQL_TESTING: TaskComplexity.HIGH,
        
        # 图表相关 - 中等复杂度
        ProcessingStep.CHART_SPEC_GENERATION: TaskComplexity.MEDIUM,
        ProcessingStep.CHART_VALIDATION: TaskComplexity.MEDIUM,
        
        # 上下文相关 - 分析中等，集成需要高质量
        ProcessingStep.CONTEXT_ANALYSIS: TaskComplexity.MEDIUM,
        ProcessingStep.CONTEXT_INTEGRATION: TaskComplexity.HIGH,
        ProcessingStep.TIME_CONTEXT_ANALYSIS: TaskComplexity.MEDIUM,
        
        # 任务相关 - 分析中等，补充需要高质量
        ProcessingStep.TASK_ANALYSIS: TaskComplexity.MEDIUM,
        ProcessingStep.TASK_SUPPLEMENT: TaskComplexity.HIGH,
        
        # 数据相关 - 分析中等，处理需要高质量
        ProcessingStep.DATA_SOURCE_ANALYSIS: TaskComplexity.MEDIUM,
        ProcessingStep.ETL_DATA_PROCESSING: TaskComplexity.HIGH,
        
        # 通用 - 推理简单，错误处理重要
        ProcessingStep.GENERAL_REASONING: TaskComplexity.LOW,
        ProcessingStep.ERROR_HANDLING: TaskComplexity.HIGH,
    }
    
    # 模型类型映射
    MODEL_TYPE_MAPPING = {
        TaskComplexity.LOW: "default",
        TaskComplexity.MEDIUM: "default", 
        TaskComplexity.HIGH: "think",
        TaskComplexity.CRITICAL: "think"
    }
    
    # 成本级别映射
    COST_LEVEL_MAPPING = {
        TaskComplexity.LOW: "low",
        TaskComplexity.MEDIUM: "low",
        TaskComplexity.HIGH: "medium", 
        TaskComplexity.CRITICAL: "high"
    }
    
    # 质量级别映射
    QUALITY_LEVEL_MAPPING = {
        TaskComplexity.LOW: "standard",
        TaskComplexity.MEDIUM: "standard",
        TaskComplexity.HIGH: "high",
        TaskComplexity.CRITICAL: "premium"
    }

    def __init__(self):
        """初始化模型选择器"""
        self.selection_history: List[ModelSelection] = []
        self.error_escalation_enabled = True  # 启用错误升级
        
    def select_model_for_step(
        self, 
        step_context: StepContext,
        force_model_type: Optional[str] = None
    ) -> ModelSelection:
        """
        为特定步骤选择最合适的模型
        
        Args:
            step_context: 步骤上下文
            force_model_type: 强制使用的模型类型
            
        Returns:
            ModelSelection: 模型选择结果
        """
        try:
            # 1. 确定基础复杂度
            base_complexity = self._get_base_complexity(step_context)
            
            # 2. 应用动态调整
            final_complexity = self._apply_dynamic_adjustments(base_complexity, step_context)
            
            # 3. 选择模型类型
            if force_model_type:
                model_type = force_model_type
                reason = f"强制指定使用 {force_model_type} 模型"
            else:
                model_type = self.MODEL_TYPE_MAPPING[final_complexity]
                reason = self._generate_selection_reason(step_context, final_complexity)
            
            # 4. 创建选择结果
            selection = ModelSelection(
                model_type=model_type,
                complexity=final_complexity,
                step=step_context.step,
                reason=reason,
                cost_level=self.COST_LEVEL_MAPPING[final_complexity],
                quality_level=self.QUALITY_LEVEL_MAPPING[final_complexity]
            )
            
            # 5. 记录选择历史
            self.selection_history.append(selection)
            
            logger.info(f"模型选择完成: {step_context.step.value} -> {model_type} ({final_complexity.value})")
            logger.debug(f"选择理由: {reason}")
            
            return selection
            
        except Exception as e:
            logger.error(f"模型选择失败: {e}")
            # 降级到默认模型
            return ModelSelection(
                model_type="default",
                complexity=TaskComplexity.MEDIUM,
                step=step_context.step,
                reason=f"选择器异常，降级到默认模型: {str(e)}",
                cost_level="low",
                quality_level="standard"
            )
    
    def _get_base_complexity(self, step_context: StepContext) -> TaskComplexity:
        """获取基础复杂度"""
        if step_context.custom_complexity:
            return step_context.custom_complexity
            
        return self.STEP_COMPLEXITY_MAPPING.get(
            step_context.step, 
            TaskComplexity.MEDIUM
        )
    
    def _apply_dynamic_adjustments(
        self, 
        base_complexity: TaskComplexity, 
        step_context: StepContext
    ) -> TaskComplexity:
        """应用动态调整"""
        current_complexity = base_complexity
        
        # 错误升级：如果之前有错误，提升复杂度
        if self.error_escalation_enabled and step_context.previous_errors > 0:
            if step_context.previous_errors >= 2:
                current_complexity = TaskComplexity.CRITICAL
            elif step_context.previous_errors == 1 and current_complexity != TaskComplexity.CRITICAL:
                if current_complexity == TaskComplexity.LOW:
                    current_complexity = TaskComplexity.MEDIUM
                elif current_complexity == TaskComplexity.MEDIUM:
                    current_complexity = TaskComplexity.HIGH
                elif current_complexity == TaskComplexity.HIGH:
                    current_complexity = TaskComplexity.CRITICAL
        
        # 用户反馈升级：有用户反馈说明任务重要
        if step_context.has_user_feedback and current_complexity == TaskComplexity.LOW:
            current_complexity = TaskComplexity.MEDIUM
            
        # 时间压力降级：有时间压力时优先速度
        if step_context.time_pressure and current_complexity == TaskComplexity.CRITICAL:
            current_complexity = TaskComplexity.HIGH
            
        # 数据复杂度调整
        if step_context.data_complexity == "high" and current_complexity in [TaskComplexity.LOW, TaskComplexity.MEDIUM]:
            current_complexity = TaskComplexity.HIGH
        elif step_context.data_complexity == "low" and current_complexity == TaskComplexity.HIGH:
            current_complexity = TaskComplexity.MEDIUM
            
        return current_complexity
    
    def _generate_selection_reason(
        self, 
        step_context: StepContext, 
        final_complexity: TaskComplexity
    ) -> str:
        """生成选择理由"""
        base_reason = f"{step_context.step.value} 步骤基础复杂度为 {self.STEP_COMPLEXITY_MAPPING[step_context.step].value}"
        
        adjustments = []
        if step_context.previous_errors > 0:
            adjustments.append(f"之前有 {step_context.previous_errors} 次错误，提升复杂度")
        if step_context.has_user_feedback:
            adjustments.append("有用户反馈，提升重要性")
        if step_context.time_pressure:
            adjustments.append("有时间压力，适度降级")
        if step_context.data_complexity != "medium":
            adjustments.append(f"数据复杂度为 {step_context.data_complexity}")
            
        if adjustments:
            reason = f"{base_reason}，经动态调整({'; '.join(adjustments)})，最终选择 {self.MODEL_TYPE_MAPPING[final_complexity]} 模型"
        else:
            reason = f"{base_reason}，选择 {self.MODEL_TYPE_MAPPING[final_complexity]} 模型"
            
        return reason
    
    def get_selection_statistics(self) -> Dict[str, Any]:
        """获取选择统计信息"""
        if not self.selection_history:
            return {"total_selections": 0}
            
        total = len(self.selection_history)
        model_type_counts = {}
        complexity_counts = {}
        step_counts = {}
        
        for selection in self.selection_history:
            # 模型类型统计
            model_type_counts[selection.model_type] = model_type_counts.get(selection.model_type, 0) + 1
            # 复杂度统计
            complexity_counts[selection.complexity.value] = complexity_counts.get(selection.complexity.value, 0) + 1
            # 步骤统计
            step_counts[selection.step.value] = step_counts.get(selection.step.value, 0) + 1
        
        return {
            "total_selections": total,
            "model_type_distribution": {k: v/total for k, v in model_type_counts.items()},
            "complexity_distribution": {k: v/total for k, v in complexity_counts.items()},
            "step_distribution": {k: v/total for k, v in step_counts.items()},
            "cost_efficiency": self._calculate_cost_efficiency()
        }
    
    def _calculate_cost_efficiency(self) -> Dict[str, Any]:
        """计算成本效率"""
        if not self.selection_history:
            return {}
            
        cost_weights = {"low": 1, "medium": 3, "high": 8}
        total_cost = sum(cost_weights.get(s.cost_level, 1) for s in self.selection_history)
        avg_cost_per_selection = total_cost / len(self.selection_history)
        
        # 计算think模型使用率
        think_count = sum(1 for s in self.selection_history if s.model_type == "think")
        think_ratio = think_count / len(self.selection_history)
        
        return {
            "average_cost_per_selection": avg_cost_per_selection,
            "think_model_usage_ratio": think_ratio,
            "cost_efficiency_score": 1.0 / avg_cost_per_selection  # 成本效率得分
        }
        
    def reset_history(self):
        """重置选择历史"""
        self.selection_history.clear()
        logger.info("模型选择历史已重置")


def create_step_based_model_selector() -> StepBasedModelSelector:
    """创建分步骤模型选择器实例"""
    return StepBasedModelSelector()


# 便捷函数
def select_model_for_placeholder_analysis(
    task_description: str,
    data_complexity: str = "medium",
    previous_errors: int = 0
) -> ModelSelection:
    """为占位符分析选择模型"""
    selector = create_step_based_model_selector()
    context = StepContext(
        step=ProcessingStep.PLACEHOLDER_ANALYSIS,
        task_description=task_description,
        data_complexity=data_complexity,
        previous_errors=previous_errors
    )
    return selector.select_model_for_step(context)


def select_model_for_sql_generation(
    task_description: str,
    data_complexity: str = "medium",
    previous_errors: int = 0,
    has_user_feedback: bool = False
) -> ModelSelection:
    """为SQL生成选择模型"""
    selector = create_step_based_model_selector()
    context = StepContext(
        step=ProcessingStep.SQL_GENERATION,
        task_description=task_description,
        data_complexity=data_complexity,
        previous_errors=previous_errors,
        has_user_feedback=has_user_feedback
    )
    return selector.select_model_for_step(context)


def select_model_for_sql_error_correction(
    task_description: str,
    previous_errors: int = 1
) -> ModelSelection:
    """为SQL纠错选择模型"""
    selector = create_step_based_model_selector()
    context = StepContext(
        step=ProcessingStep.SQL_ERROR_CORRECTION,
        task_description=task_description,
        previous_errors=previous_errors
    )
    return selector.select_model_for_step(context)