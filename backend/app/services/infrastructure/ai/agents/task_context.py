"""
Infrastructure层AI任务上下文

原始来源: app/services/agents/core/placeholder_task_context.py
重构为符合DDD Infrastructure层的AI任务上下文管理

核心职责：
- 提供AI任务上下文的技术管理
- 定义执行步骤和模型需求
- 管理任务状态和执行进度
- 为上层Agent提供任务上下文支撑

技术职责：
- 纯技术实现，不包含业务逻辑
- 可被Application/Domain层的Agent使用
- 提供稳定的任务上下文管理服务
"""

import logging
import hashlib
from typing import Dict, List, Any, Optional, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """AI任务复杂度"""
    SIMPLE = "simple"        # 简单统计，基础查询
    MEDIUM = "medium"        # 一般分析，单表查询
    HIGH = "high"           # 复杂分析，多表关联
    VERY_HIGH = "very_high" # 极复杂，需要深度推理


class ExecutionStepType(Enum):
    """执行步骤类型"""
    PARSE = "parse"                    # 解析占位符
    CONTEXT_ANALYSIS = "context_analysis"  # 上下文分析
    SQL_GENERATION = "sql_generation"   # SQL生成
    DATA_QUERY = "data_query"          # 数据查询
    BUSINESS_LOGIC = "business_logic"   # 业务逻辑处理
    CALCULATION = "calculation"        # 计算处理
    VALIDATION = "validation"          # 结果验证
    FORMATTING = "formatting"          # 格式化输出
    AGGREGATION = "aggregation"        # 聚合处理


class ModelRequirement(Enum):
    """模型需求类型"""
    DEFAULT = "default"      # 使用Default模型
    THINK = "think"         # 使用Think模型
    AUTO = "auto"           # 自动选择模型


@dataclass
class ExecutionStep:
    """执行步骤定义"""
    step_id: str
    step_type: ExecutionStepType
    model_requirement: ModelRequirement
    tools_needed: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # 依赖的步骤ID
    expected_output: str = ""
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: Optional[int] = None


@dataclass
class AITaskContext:
    """
    Infrastructure层AI任务上下文
    承载AI任务的执行上下文和状态管理（符合DDD Infrastructure层定位）
    """
    # 基本信息
    task_id: str
    placeholder_text: str
    statistical_type: str
    description: str
    
    # 上下文工程分析结果（由业务层Agent分析产生）
    context_analysis: Dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 0.5
    
    # 上下文工程数据（用于协助存储中间结果）
    context_engine: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    # 任务特征 (从上下文分析中提取)
    complexity: TaskComplexity = TaskComplexity.MEDIUM
    business_domain: str = "general"
    time_dimension: bool = False
    
    # 技术需求分析
    requires_sql_generation: bool = False
    requires_data_analysis: bool = False
    requires_business_logic: bool = False
    has_multiple_tables: bool = False
    has_complex_conditions: bool = False
    has_aggregation: bool = False
    
    # 执行计划
    execution_steps: List[ExecutionStep] = field(default_factory=list)
    estimated_execution_time: float = 0.0
    
    # 执行约束
    quality_requirement: str = "standard"  # standard, high, premium
    time_constraint: Optional[float] = None
    user_id: str = "system"
    
    # 运行时状态
    current_step_index: int = 0
    execution_results: Dict[str, Any] = field(default_factory=dict)
    execution_started_at: Optional[datetime] = None
    execution_completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.task_id:
            self.task_id = self._generate_task_id()
        
        # 从上下文分析结果中提取任务特征
        self._extract_task_features()
        
        # 如果没有预定义执行步骤，生成默认步骤
        if not self.execution_steps:
            self.execution_steps = self._generate_default_steps()
    
    def _generate_task_id(self) -> str:
        """生成任务ID"""
        content = f"{self.placeholder_text}|{self.statistical_type}|{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _extract_task_features(self):
        """从上下文分析结果中提取任务特征"""
        if not self.context_analysis:
            return
        
        # 提取复杂度
        if 'integrated_context' in self.context_analysis:
            integrated = self.context_analysis['integrated_context']
            
            # 业务领域
            if 'business_dimension' in integrated:
                business_info = integrated['business_dimension']
                self.business_domain = business_info.get('domain', 'general')
            
            # 时间维度
            if 'time_dimension' in integrated:
                time_info = integrated['time_dimension']
                self.time_dimension = bool(time_info.get('detected_periods'))
            
            # 数据维度分析
            if 'data_dimension' in integrated:
                data_info = integrated['data_dimension']
                self.requires_sql_generation = bool(data_info.get('sources'))
                self.has_multiple_tables = len(data_info.get('sources', [])) > 1
            
            # 语义维度分析
            if 'semantic_dimension' in integrated:
                semantic_info = integrated['semantic_dimension']
                concepts = semantic_info.get('concepts', [])
                self.requires_business_logic = any('逻辑' in c or '规则' in c for c in concepts)
                self.has_complex_conditions = any('条件' in c or '筛选' in c for c in concepts)
                self.has_aggregation = any('总' in c or '平均' in c or '汇总' in c for c in concepts)
        
        # 根据置信度和特征评估复杂度
        self._evaluate_complexity()
    
    def _evaluate_complexity(self):
        """评估任务复杂度"""
        complexity_score = 0
        
        # 基于置信度
        if self.confidence_score < 0.6:
            complexity_score += 2
        elif self.confidence_score < 0.8:
            complexity_score += 1
        
        # 基于技术特征
        if self.has_multiple_tables:
            complexity_score += 2
        if self.has_complex_conditions:
            complexity_score += 1
        if self.requires_business_logic:
            complexity_score += 2
        if self.time_dimension:
            complexity_score += 1
        if self.has_aggregation:
            complexity_score += 1
        
        # 映射到复杂度等级
        if complexity_score >= 7:
            self.complexity = TaskComplexity.VERY_HIGH
        elif complexity_score >= 4:
            self.complexity = TaskComplexity.HIGH
        elif complexity_score >= 2:
            self.complexity = TaskComplexity.MEDIUM
        else:
            self.complexity = TaskComplexity.SIMPLE
    
    def _generate_default_steps(self) -> List[ExecutionStep]:
        """根据任务特征生成默认执行步骤"""
        steps = []
        step_counter = 1
        
        # 1. 解析步骤 (总是需要)
        steps.append(ExecutionStep(
            step_id=f"step_{step_counter}",
            step_type=ExecutionStepType.PARSE,
            model_requirement=ModelRequirement.DEFAULT,
            tools_needed=["placeholder_parser"],
            expected_output="parsed_placeholder_spec"
        ))
        step_counter += 1
        
        # 2. 上下文分析步骤 (如果置信度低)
        if self.confidence_score < 0.8:
            steps.append(ExecutionStep(
                step_id=f"step_{step_counter}",
                step_type=ExecutionStepType.CONTEXT_ANALYSIS,
                model_requirement=ModelRequirement.THINK,
                tools_needed=["context_analyzer"],
                dependencies=[steps[-1].step_id],
                expected_output="enhanced_context"
            ))
            step_counter += 1
        
        # 3. SQL生成步骤 (如果需要)
        if self.requires_sql_generation:
            model_req = ModelRequirement.THINK if self.has_multiple_tables or self.has_complex_conditions else ModelRequirement.DEFAULT
            steps.append(ExecutionStep(
                step_id=f"step_{step_counter}",
                step_type=ExecutionStepType.SQL_GENERATION,
                model_requirement=model_req,
                tools_needed=["sql_generator", "schema_analyzer"],
                dependencies=[steps[-1].step_id],
                expected_output="sql_query"
            ))
            step_counter += 1
        
        # 4. 数据查询步骤
        steps.append(ExecutionStep(
            step_id=f"step_{step_counter}",
            step_type=ExecutionStepType.DATA_QUERY,
            model_requirement=ModelRequirement.DEFAULT,
            tools_needed=["data_executor"],
            dependencies=[steps[-1].step_id],
            expected_output="raw_data"
        ))
        step_counter += 1
        
        # 5. 业务逻辑处理步骤 (如果需要)
        if self.requires_business_logic:
            steps.append(ExecutionStep(
                step_id=f"step_{step_counter}",
                step_type=ExecutionStepType.BUSINESS_LOGIC,
                model_requirement=ModelRequirement.THINK,
                tools_needed=["business_processor"],
                dependencies=[steps[-1].step_id],
                expected_output="processed_data"
            ))
            step_counter += 1
        
        # 6. 计算处理步骤 (如果有聚合)
        if self.has_aggregation:
            steps.append(ExecutionStep(
                step_id=f"step_{step_counter}",
                step_type=ExecutionStepType.CALCULATION,
                model_requirement=ModelRequirement.DEFAULT,
                tools_needed=["calculator"],
                dependencies=[steps[-1].step_id],
                expected_output="calculated_result"
            ))
            step_counter += 1
        
        # 7. 验证步骤 (复杂任务需要)
        if self.complexity in [TaskComplexity.HIGH, TaskComplexity.VERY_HIGH]:
            steps.append(ExecutionStep(
                step_id=f"step_{step_counter}",
                step_type=ExecutionStepType.VALIDATION,
                model_requirement=ModelRequirement.THINK,
                tools_needed=["result_validator"],
                dependencies=[steps[-1].step_id],
                expected_output="validated_result"
            ))
            step_counter += 1
        
        # 8. 格式化步骤 (总是需要)
        steps.append(ExecutionStep(
            step_id=f"step_{step_counter}",
            step_type=ExecutionStepType.FORMATTING,
            model_requirement=ModelRequirement.DEFAULT,
            tools_needed=["formatter"],
            dependencies=[steps[-1].step_id],
            expected_output="final_result"
        ))
        
        return steps
    
    def get_current_step(self) -> Optional[ExecutionStep]:
        """获取当前执行步骤"""
        if 0 <= self.current_step_index < len(self.execution_steps):
            return self.execution_steps[self.current_step_index]
        return None
    
    def advance_step(self) -> bool:
        """推进到下一步"""
        self.current_step_index += 1
        return self.current_step_index < len(self.execution_steps)
    
    def is_completed(self) -> bool:
        """检查是否完成"""
        return self.current_step_index >= len(self.execution_steps)
    
    def add_result(self, step_id: str, result: Any):
        """添加步骤执行结果"""
        self.execution_results[step_id] = result
    
    def get_result(self, step_id: str) -> Any:
        """获取步骤执行结果"""
        return self.execution_results.get(step_id)
    
    def get_cache_key(self) -> str:
        """获取缓存键"""
        key_str = f"{self.placeholder_text}|{self.statistical_type}|{self.complexity.value}|{self.confidence_score}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get_task_summary(self) -> str:
        """获取任务摘要"""
        return f"[{self.statistical_type}] {self.description[:50]}{'...' if len(self.description) > 50 else ''}"
    
    def get_execution_progress(self) -> Dict[str, Any]:
        """获取执行进度"""
        total_steps = len(self.execution_steps)
        completed_steps = self.current_step_index
        
        return {
            "task_id": self.task_id,
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "progress_percentage": (completed_steps / total_steps * 100) if total_steps > 0 else 0,
            "current_step": self.get_current_step().step_type.value if self.get_current_step() else "completed",
            "complexity": self.complexity.value,
            "estimated_time": self.estimated_execution_time
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "placeholder_text": self.placeholder_text,
            "statistical_type": self.statistical_type,
            "description": self.description,
            "complexity": self.complexity.value,
            "business_domain": self.business_domain,
            "confidence_score": self.confidence_score,
            "execution_progress": self.get_execution_progress(),
            "context_analysis": self.context_analysis
        }


def create_ai_task_context_from_placeholder_analysis(
    placeholder_text: str,
    statistical_type: str, 
    description: str,
    context_analysis: Dict[str, Any],
    user_id: str = "system",
    context_engine: Optional[Dict[str, Any]] = None
) -> AITaskContext:
    """
    从placeholder上下文工程分析结果创建AI任务上下文（符合Infrastructure层定位）
    
    Args:
        placeholder_text: 占位符文本
        statistical_type: 统计类型
        description: 需求描述
        context_analysis: 业务层Agent分析的上下文结果
        user_id: 用户ID
        context_engine: placeholder domain构建的上下文工程数据
    
    Returns:
        AITaskContext实例
    """
    # 提取置信度
    confidence_score = context_analysis.get('confidence_score', 0.5)
    
    # 创建AI任务上下文
    task_context = AITaskContext(
        task_id="",  # 将在__post_init__中生成
        placeholder_text=placeholder_text,
        statistical_type=statistical_type,
        description=description,
        context_analysis=context_analysis,
        confidence_score=confidence_score,
        context_engine=context_engine or {},  # 传递上下文工程数据
        user_id=user_id
    )
    
    logger.info(f"创建AI任务上下文（Infrastructure层）: {task_context.get_task_summary()}, 复杂度: {task_context.complexity.value}")
    
    return task_context