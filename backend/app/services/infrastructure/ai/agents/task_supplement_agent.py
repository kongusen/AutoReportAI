"""
任务补充机制Agent

基于AutoReportAI Agent设计的核心功能：
2. 任务补充机制: 当占位符SQL为空或过期时，Agent自动重新解析并更新

工作流程：
检测空/过期占位符 → 基于任务上下文重新解析 → 调用占位符→SQL流程 → 更新模板存储

特性：
- 智能检测：自动发现需要补充的占位符
- 上下文驱动：基于任务上下文智能推断占位符含义
- 批量处理：支持批量处理多个占位符
- 优先级排序：根据重要性和影响范围排序处理
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json

from ..llm.step_based_model_selector import (
    StepBasedModelSelector, 
    StepContext, 
    ProcessingStep,
    create_step_based_model_selector
)
from ..llm import ask_agent_for_user
from .placeholder_to_sql_agent import (
    PlaceholderToSqlAgent,
    PlaceholderContext,
    TimeContext,
    DataSourceContext,
    TaskContext,
    create_placeholder_to_sql_agent
)

logger = logging.getLogger(__name__)


class SupplementReason(Enum):
    """补充原因"""
    EMPTY_SQL = "empty_sql"                    # SQL为空
    EXPIRED_SQL = "expired_sql"                # SQL过期
    INVALID_SQL = "invalid_sql"                # SQL无效
    DEPENDENCY_CHANGED = "dependency_changed"  # 依赖变更
    USER_FEEDBACK = "user_feedback"            # 用户反馈
    SCHEMA_UPDATED = "schema_updated"          # Schema更新
    BUSINESS_RULE_CHANGED = "business_rule_changed"  # 业务规则变更


class SupplementPriority(Enum):
    """补充优先级"""
    LOW = "low"                # 低优先级
    MEDIUM = "medium"          # 中优先级
    HIGH = "high"              # 高优先级
    CRITICAL = "critical"      # 关键优先级


@dataclass
class PlaceholderSupplementRequest:
    """占位符补充请求"""
    placeholder_id: str
    placeholder_name: str
    placeholder_context: PlaceholderContext
    supplement_reason: SupplementReason
    priority: SupplementPriority
    task_context: TaskContext
    data_source_context: DataSourceContext
    time_context: Optional[TimeContext] = None
    last_attempt: Optional[datetime] = None
    attempt_count: int = 0
    error_history: List[str] = None
    
    def __post_init__(self):
        if self.error_history is None:
            self.error_history = []


@dataclass
class SupplementResult:
    """补充结果"""
    placeholder_id: str
    success: bool
    sql_query: str
    explanation: str
    confidence_score: float
    processing_time_seconds: float
    error_message: Optional[str] = None
    supplement_reason: Optional[SupplementReason] = None
    attempts_used: int = 1


@dataclass
class BatchSupplementResult:
    """批量补充结果"""
    total_requests: int
    successful_supplements: int
    failed_supplements: int
    processing_time_seconds: float
    individual_results: List[SupplementResult]
    overall_confidence: float


class TaskSupplementAgent:
    """任务补充机制Agent"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.model_selector = create_step_based_model_selector()
        self.placeholder_sql_agent = create_placeholder_to_sql_agent(user_id)
        self.supplement_history: List[SupplementResult] = []
        
    async def detect_supplements_needed(
        self,
        template_id: str,
        placeholders: List[PlaceholderContext],
        task_context: TaskContext,
        data_source_context: DataSourceContext
    ) -> List[PlaceholderSupplementRequest]:
        """
        检测需要补充的占位符
        
        返回按优先级排序的补充请求列表
        """
        try:
            logger.info(f"开始检测模板 {template_id} 的占位符补充需求")
            
            supplement_requests = []
            
            for placeholder in placeholders:
                # 检测是否需要补充
                supplement_reason, priority = await self._analyze_supplement_need(
                    placeholder,
                    task_context,
                    data_source_context
                )
                
                if supplement_reason:
                    request = PlaceholderSupplementRequest(
                        placeholder_id=f"{template_id}_{placeholder.placeholder_name}",
                        placeholder_name=placeholder.placeholder_name,
                        placeholder_context=placeholder,
                        supplement_reason=supplement_reason,
                        priority=priority,
                        task_context=task_context,
                        data_source_context=data_source_context
                    )
                    supplement_requests.append(request)
            
            # 按优先级排序
            supplement_requests.sort(key=lambda x: self._get_priority_weight(x.priority), reverse=True)
            
            logger.info(f"检测完成，发现 {len(supplement_requests)} 个需要补充的占位符")
            return supplement_requests
            
        except Exception as e:
            logger.error(f"占位符补充检测失败: {e}")
            return []
    
    async def _analyze_supplement_need(
        self,
        placeholder: PlaceholderContext,
        task_context: TaskContext,
        data_source_context: DataSourceContext
    ) -> Tuple[Optional[SupplementReason], SupplementPriority]:
        """分析占位符是否需要补充"""
        
        # 检查是否为空
        if placeholder.is_empty or not placeholder.current_value:
            if placeholder.placeholder_type in ['metric', 'filter']:
                return SupplementReason.EMPTY_SQL, SupplementPriority.HIGH
            else:
                return SupplementReason.EMPTY_SQL, SupplementPriority.MEDIUM
        
        # 检查是否过期（根据最后更新时间）
        if placeholder.last_updated:
            expiry_hours = self._get_expiry_hours(placeholder.placeholder_type)
            if datetime.now() - placeholder.last_updated > timedelta(hours=expiry_hours):
                return SupplementReason.EXPIRED_SQL, SupplementPriority.MEDIUM
        
        # 检查SQL有效性（简单验证）
        if placeholder.current_value and isinstance(placeholder.current_value, str):
            if not self._is_valid_sql_format(placeholder.current_value):
                return SupplementReason.INVALID_SQL, SupplementPriority.HIGH
        
        # 无需补充
        return None, SupplementPriority.LOW
    
    def _get_expiry_hours(self, placeholder_type: str) -> int:
        """获取占位符过期时间（小时）"""
        expiry_mapping = {
            'metric': 24,     # 指标类占位符24小时过期
            'dimension': 48,  # 维度类占位符48小时过期
            'filter': 12,     # 过滤类占位符12小时过期
            'chart': 72       # 图表类占位符72小时过期
        }
        return expiry_mapping.get(placeholder_type, 24)
    
    def _is_valid_sql_format(self, sql_value: str) -> bool:
        """简单验证SQL格式"""
        if not sql_value.strip():
            return False
        
        sql_upper = sql_value.upper().strip()
        # 基本SQL关键词检查
        return any(sql_upper.startswith(keyword) for keyword in ['SELECT', 'WITH', 'INSERT', 'UPDATE', 'DELETE'])
    
    def _get_priority_weight(self, priority: SupplementPriority) -> int:
        """获取优先级权重"""
        weights = {
            SupplementPriority.CRITICAL: 4,
            SupplementPriority.HIGH: 3,
            SupplementPriority.MEDIUM: 2,
            SupplementPriority.LOW: 1
        }
        return weights.get(priority, 1)
    
    async def supplement_single_placeholder(
        self,
        request: PlaceholderSupplementRequest,
        max_attempts: int = 2
    ) -> SupplementResult:
        """补充单个占位符"""
        
        start_time = datetime.now()
        placeholder_id = request.placeholder_id
        
        try:
            logger.info(f"开始补充占位符 {placeholder_id}, 原因: {request.supplement_reason.value}")
            
            # 使用任务上下文重新解析占位符
            enhanced_placeholder = await self._enhance_placeholder_with_context(
                request.placeholder_context,
                request.task_context,
                request.supplement_reason
            )
            
            # 生成时间上下文
            time_context = await self._generate_time_context_for_task(
                request.task_context
            )
            
            # 调用占位符→SQL转换流程
            sql_result = await self.placeholder_sql_agent.convert_placeholder_to_sql(
                enhanced_placeholder,
                request.data_source_context,
                request.task_context,
                time_context
            )
            
            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds()
            
            if sql_result.sql_query and not sql_result.validation_errors:
                logger.info(f"占位符 {placeholder_id} 补充成功")
                result = SupplementResult(
                    placeholder_id=placeholder_id,
                    success=True,
                    sql_query=sql_result.sql_query,
                    explanation=sql_result.explanation,
                    confidence_score=sql_result.confidence_score,
                    processing_time_seconds=processing_time,
                    supplement_reason=request.supplement_reason,
                    attempts_used=sql_result.correction_attempts + 1
                )
            else:
                error_msg = '; '.join(sql_result.validation_errors) if sql_result.validation_errors else "SQL生成失败"
                logger.warning(f"占位符 {placeholder_id} 补充失败: {error_msg}")
                result = SupplementResult(
                    placeholder_id=placeholder_id,
                    success=False,
                    sql_query="",
                    explanation=sql_result.explanation,
                    confidence_score=0.0,
                    processing_time_seconds=processing_time,
                    error_message=error_msg,
                    supplement_reason=request.supplement_reason
                )
            
            self.supplement_history.append(result)
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"占位符 {placeholder_id} 补充异常: {e}")
            
            error_result = SupplementResult(
                placeholder_id=placeholder_id,
                success=False,
                sql_query="",
                explanation="",
                confidence_score=0.0,
                processing_time_seconds=processing_time,
                error_message=str(e),
                supplement_reason=request.supplement_reason
            )
            
            self.supplement_history.append(error_result)
            return error_result
    
    async def _enhance_placeholder_with_context(
        self,
        placeholder: PlaceholderContext,
        task_context: TaskContext,
        supplement_reason: SupplementReason
    ) -> PlaceholderContext:
        """基于任务上下文增强占位符信息"""
        
        step_context = StepContext(
            step=ProcessingStep.TASK_SUPPLEMENT,
            task_description=f"基于任务上下文增强占位符 {placeholder.placeholder_name}",
            data_complexity="high"
        )
        
        model_selection = self.model_selector.select_model_for_step(step_context)
        
        prompt = f"""
        请基于任务上下文，重新解析和增强以下占位符的信息：
        
        占位符基础信息：
        - 名称: {placeholder.placeholder_name}
        - 描述: {placeholder.placeholder_description}
        - 类型: {placeholder.placeholder_type}
        - 期望数据类型: {placeholder.expected_data_type}
        - 当前值: {placeholder.current_value}
        - 补充原因: {supplement_reason.value}
        
        任务上下文：
        - 任务名称: {task_context.task_name}
        - 任务描述: {task_context.task_description}
        - 业务领域: {task_context.business_domain}
        - 报告类型: {task_context.report_type}
        - 优先级: {task_context.priority}
        
        请根据任务上下文，推断占位符的具体含义和需求，返回JSON格式：
        - enhanced_description: 增强后的描述
        - inferred_business_meaning: 推断的业务含义
        - suggested_calculation_logic: 建议的计算逻辑
        - related_metrics: 相关指标
        - data_requirements: 数据需求
        - time_sensitivity: 时间敏感性
        """
        
        try:
            response = await ask_agent_for_user(
                user_id=self.user_id,
                question=prompt,
                agent_type="data_analysis",
                task_type="placeholder_enhancement",
                complexity=model_selection.complexity.value
            )
            
            enhancement_data = json.loads(response)
            
            # 更新占位符描述
            if enhancement_data.get("enhanced_description"):
                placeholder.placeholder_description = enhancement_data["enhanced_description"]
            
            logger.info(f"占位符 {placeholder.placeholder_name} 上下文增强完成")
            
        except Exception as e:
            logger.error(f"占位符上下文增强失败: {e}")
        
        return placeholder
    
    async def _generate_time_context_for_task(
        self,
        task_context: TaskContext
    ) -> TimeContext:
        """为任务生成时间上下文"""
        
        # 根据任务类型推断时间范围
        now = datetime.now()
        
        if task_context.report_type in ['dashboard', 'realtime']:
            # 实时类报告使用最近1天
            start_date = now - timedelta(days=1)
            end_date = now
            granularity = "hour"
        elif task_context.report_type == 'weekly':
            # 周报使用最近7天
            start_date = now - timedelta(days=7)
            end_date = now
            granularity = "day"
        elif task_context.report_type == 'monthly':
            # 月报使用最近30天
            start_date = now - timedelta(days=30)
            end_date = now
            granularity = "day"
        else:
            # 默认使用最近30天
            start_date = now - timedelta(days=30)
            end_date = now
            granularity = "day"
        
        return TimeContext(
            report_start_date=start_date,
            report_end_date=end_date,
            time_granularity=granularity,
            auto_detected=True
        )
    
    async def supplement_batch_placeholders(
        self,
        requests: List[PlaceholderSupplementRequest],
        max_concurrent: int = 3
    ) -> BatchSupplementResult:
        """批量补充占位符"""
        
        start_time = datetime.now()
        total_requests = len(requests)
        
        logger.info(f"开始批量补充 {total_requests} 个占位符")
        
        # 按优先级分组处理
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single_request(request):
            async with semaphore:
                return await self.supplement_single_placeholder(request)
        
        # 并发处理
        tasks = [process_single_request(request) for request in requests]
        individual_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(individual_results):
            if isinstance(result, Exception):
                logger.error(f"批量处理异常: {result}")
                error_result = SupplementResult(
                    placeholder_id=requests[i].placeholder_id,
                    success=False,
                    sql_query="",
                    explanation="",
                    confidence_score=0.0,
                    processing_time_seconds=0.0,
                    error_message=str(result),
                    supplement_reason=requests[i].supplement_reason
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)
        
        # 统计结果
        successful_count = sum(1 for r in processed_results if r.success)
        failed_count = total_requests - successful_count
        
        # 计算总体信心度
        if successful_count > 0:
            overall_confidence = sum(r.confidence_score for r in processed_results if r.success) / successful_count
        else:
            overall_confidence = 0.0
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        batch_result = BatchSupplementResult(
            total_requests=total_requests,
            successful_supplements=successful_count,
            failed_supplements=failed_count,
            processing_time_seconds=processing_time,
            individual_results=processed_results,
            overall_confidence=overall_confidence
        )
        
        logger.info(f"批量补充完成: {successful_count}/{total_requests} 成功")
        return batch_result
    
    def get_supplement_statistics(self) -> Dict[str, Any]:
        """获取补充统计信息"""
        if not self.supplement_history:
            return {"total_supplements": 0}
        
        total = len(self.supplement_history)
        successful = sum(1 for r in self.supplement_history if r.success)
        
        # 按原因统计
        reason_stats = {}
        for result in self.supplement_history:
            reason = result.supplement_reason.value if result.supplement_reason else "unknown"
            reason_stats[reason] = reason_stats.get(reason, 0) + 1
        
        # 计算平均指标
        avg_processing_time = sum(r.processing_time_seconds for r in self.supplement_history) / total
        avg_confidence = sum(r.confidence_score for r in self.supplement_history if r.success) / max(successful, 1)
        
        return {
            "total_supplements": total,
            "successful_supplements": successful,
            "success_rate": successful / total,
            "reason_distribution": reason_stats,
            "average_processing_time": avg_processing_time,
            "average_confidence": avg_confidence,
            "model_selector_stats": self.model_selector.get_selection_statistics()
        }


def create_task_supplement_agent(user_id: str) -> TaskSupplementAgent:
    """创建任务补充机制Agent实例"""
    if not user_id:
        raise ValueError("user_id is required for TaskSupplementAgent")
    return TaskSupplementAgent(user_id)