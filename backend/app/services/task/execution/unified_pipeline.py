"""
Unified Report Generation Pipeline

统一的报告生成流水线接口，基于两阶段架构实现
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from enum import Enum

# 移除对旧pipeline的依赖，统一使用两阶段架构
from .two_phase_pipeline import (
    execute_two_phase_pipeline, 
    create_pipeline_config, 
    PipelineConfiguration,
    ExecutionMode as TwoPhaseExecutionMode
)

logger = logging.getLogger(__name__)


class PipelineMode(Enum):
    """流水线模式"""
    STANDARD = "standard"          # 标准智能流水线（向后兼容）
    ENHANCED = "enhanced"          # 增强版智能流水线（向后兼容）
    OPTIMIZED = "optimized"        # 优化版流水线（向后兼容）
    TWO_PHASE = "two_phase"        # 新的两阶段架构流水线
    AUTO = "auto"                  # 自动选择最优模式


def unified_report_generation_pipeline(
    task_id: int,
    user_id: str,
    mode: PipelineMode = PipelineMode.AUTO,
    force_reanalyze: bool = False,
    optimization_enabled: Optional[bool] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    统一的报告生成流水线接口 - 基于两阶段架构
    
    Args:
        task_id: 任务ID
        user_id: 用户ID
        mode: 流水线模式
        force_reanalyze: 是否强制重新分析
        optimization_enabled: 是否启用优化（None为自动检测）
        **kwargs: 额外参数
        
    Returns:
        生成结果，包含执行模式信息
    """
    logger.info(f"开始统一报告生成流水线 - 任务ID: {task_id}, 模式: {mode.value}")
    
    try:
        # 根据模式选择合适的流水线实现
        selected_mode = _select_pipeline_mode(mode, optimization_enabled)
        
        if selected_mode == PipelineMode.TWO_PHASE:
            # 使用新的两阶段架构
            logger.info(f"使用两阶段架构流水线执行任务: {task_id}")
            
            # 创建两阶段流水线配置
            config = create_pipeline_config(
                execution_mode=TwoPhaseExecutionMode.SMART_EXECUTION,
                force_reanalyze=force_reanalyze,
                enable_caching=optimization_enabled if optimization_enabled is not None else True,
                **kwargs
            )
            
            # 执行两阶段流水线
            pipeline_result = asyncio.run(execute_two_phase_pipeline(task_id, user_id, config))
            
            # 转换为统一格式
            result = {
                "status": "completed" if pipeline_result.success else "failed",
                "pipeline_mode": "two_phase",
                "optimization_used": True,
                "pipeline_id": pipeline_result.pipeline_id,
                "execution_time": pipeline_result.total_execution_time,
                "performance_metrics": pipeline_result.performance_metrics,
                "cache_statistics": pipeline_result.cache_statistics
            }
            
            if pipeline_result.success:
                result.update({
                    "report_path": pipeline_result.report_path,
                    "report_id": pipeline_result.final_output.get("report_id") if pipeline_result.final_output else None,
                    "message": "两阶段流水线执行成功"
                })
            else:
                result["error"] = pipeline_result.error
                
            return result
            
        elif selected_mode == PipelineMode.OPTIMIZED:
            logger.info(f"使用优化模式（基于两阶段架构）执行任务: {task_id}")
            # 使用智能执行模式，启用更积极的缓存策略
            config = create_pipeline_config(
                execution_mode=TwoPhaseExecutionMode.SMART_EXECUTION,
                enable_caching=True,
                cache_ttl_hours=48,  # 更长的缓存时间
                force_reanalyze=force_reanalyze
            )
            pipeline_result = asyncio.run(execute_two_phase_pipeline(
                task_id=task_id,
                user_id=user_id,
                config=config
            ))
            
            result = {
                "success": pipeline_result.success,
                "pipeline_mode": "optimized_two_phase",
                "optimization_used": True,
                "execution_mode": config.execution_mode.value,
                "cache_enabled": config.enable_caching,
                "data": pipeline_result.data if pipeline_result.success else None,
                "message": "优化模式（两阶段架构）执行成功" if pipeline_result.success else pipeline_result.error
            }
            if not pipeline_result.success:
                result["error"] = pipeline_result.error
            
        elif selected_mode == PipelineMode.ENHANCED:
            logger.info(f"使用增强模式（基于两阶段架构）执行任务: {task_id}")
            # 使用完整流水线模式，中等缓存策略
            config = create_pipeline_config(
                execution_mode=TwoPhaseExecutionMode.FULL_PIPELINE,
                enable_caching=True,
                cache_ttl_hours=24,
                force_reanalyze=force_reanalyze
            )
            pipeline_result = asyncio.run(execute_two_phase_pipeline(
                task_id=task_id,
                user_id=user_id,
                config=config
            ))
            
            result = {
                "success": pipeline_result.success,
                "pipeline_mode": "enhanced_two_phase",
                "optimization_used": True,
                "execution_mode": config.execution_mode.value,
                "cache_enabled": config.enable_caching,
                "data": pipeline_result.data if pipeline_result.success else None,
                "message": "增强模式（两阶段架构）执行成功" if pipeline_result.success else pipeline_result.error
            }
            if not pipeline_result.success:
                result["error"] = pipeline_result.error
            
        else:  # STANDARD
            logger.info(f"使用标准模式（基于两阶段架构）执行任务: {task_id}")
            # 使用智能执行模式，保守的缓存策略
            config = create_pipeline_config(
                execution_mode=TwoPhaseExecutionMode.SMART_EXECUTION,
                enable_caching=True,
                cache_ttl_hours=12,  # 较短的缓存时间
                force_reanalyze=force_reanalyze
            )
            pipeline_result = asyncio.run(execute_two_phase_pipeline(
                task_id=task_id,
                user_id=user_id,
                config=config
            ))
            
            result = {
                "success": pipeline_result.success,
                "pipeline_mode": "standard_two_phase",
                "optimization_used": True,
                "execution_mode": config.execution_mode.value,
                "cache_enabled": config.enable_caching,
                "data": pipeline_result.data if pipeline_result.success else None,
                "message": "标准模式（两阶段架构）执行成功" if pipeline_result.success else pipeline_result.error
            }
            if not pipeline_result.success:
                result["error"] = pipeline_result.error
        
        logger.info(f"统一流水线执行完成 - 任务ID: {task_id}, 使用模式: {result['pipeline_mode']}")
        return result
        
    except Exception as e:
        logger.error(f"统一流水线执行失败 - 任务ID: {task_id}: {e}")
        
        # 在出错时尝试降级到基础两阶段模式
        if mode not in [PipelineMode.STANDARD]:
            logger.warning(f"尝试降级到标准模式（两阶段架构）执行任务: {task_id}")
            try:
                # 使用最基础的两阶段配置
                fallback_config = create_pipeline_config(
                    execution_mode=TwoPhaseExecutionMode.SMART_EXECUTION,
                    enable_caching=False,  # 禁用缓存避免缓存相关错误
                    force_reanalyze=True   # 强制重新分析
                )
                fallback_pipeline_result = asyncio.run(execute_two_phase_pipeline(
                    task_id=task_id,
                    user_id=user_id,
                    config=fallback_config
                ))
                
                fallback_result = {
                    "success": fallback_pipeline_result.success,
                    "pipeline_mode": "fallback_two_phase",
                    "optimization_used": False,
                    "execution_mode": fallback_config.execution_mode.value,
                    "cache_enabled": False,
                    "data": fallback_pipeline_result.data if fallback_pipeline_result.success else None,
                    "message": "降级模式执行成功" if fallback_pipeline_result.success else fallback_pipeline_result.error,
                    "fallback_reason": str(e)
                }
                if not fallback_pipeline_result.success:
                    fallback_result["error"] = fallback_pipeline_result.error
                
                return fallback_result
                
            except Exception as fallback_error:
                logger.error(f"降级执行也失败 - 任务ID: {task_id}: {fallback_error}")
        
        raise


def _select_pipeline_mode(
    requested_mode: PipelineMode,
    optimization_enabled: Optional[bool] = None
) -> PipelineMode:
    """选择最适合的流水线模式"""
    
    # 如果明确指定了模式且不是AUTO，直接使用
    if requested_mode != PipelineMode.AUTO:
        return requested_mode
    
    # AUTO模式：优先使用两阶段架构
    if optimization_enabled is not False:
        # 默认或优化启用时，使用两阶段架构
        return PipelineMode.TWO_PHASE
    else:
        # 明确禁用优化时，使用增强版
        return PipelineMode.ENHANCED


def get_available_pipeline_modes() -> Dict[str, Dict[str, Any]]:
    """获取可用的流水线模式信息"""
    return {
        "standard": {
            "name": "标准智能流水线",
            "description": "基础的占位符驱动报告生成（向后兼容）",
            "features": ["占位符替换", "Agent处理", "基础错误处理"],
            "legacy": True
        },
        "enhanced": {
            "name": "增强版智能流水线",
            "description": "包含用户AI配置和详细进度管理（向后兼容）",
            "features": ["用户AI配置", "详细进度跟踪", "增强错误处理", "通知系统"],
            "legacy": True
        },
        "optimized": {
            "name": "优化版流水线",
            "description": "带缓存的报告生成流水线（向后兼容）",
            "features": ["占位符缓存", "Agent分析缓存", "性能优化"],
            "legacy": True
        },
        "two_phase": {
            "name": "两阶段架构流水线",
            "description": "基于Template→Placeholder→Agent→ETL的先进两阶段架构",
            "features": [
                "严格的两阶段分离",
                "智能执行模式选择", 
                "占位符持久化",
                "Agent分析缓存",
                "缓存优先数据提取",
                "性能指标监控",
                "智能降级机制",
                "详细进度跟踪"
            ],
            "recommended": True
        },
        "auto": {
            "name": "自动选择模式",
            "description": "根据配置自动选择最优流水线（默认两阶段架构）",
            "features": ["智能选择", "自动降级", "配置感知", "性能优化"]
        }
    }


# 向后兼容的别名函数
def execute_report_generation(task_id: int, user_id: str, optimization: bool = True) -> Dict[str, Any]:
    """向后兼容的报告生成执行函数"""
    mode = PipelineMode.TWO_PHASE if optimization else PipelineMode.ENHANCED
    return unified_report_generation_pipeline(task_id, user_id, mode)


def execute_optimized_report_generation(task_id: int, user_id: str, force_reanalyze: bool = False) -> Dict[str, Any]:
    """向后兼容的优化报告生成执行函数 - 现在使用两阶段架构"""
    return unified_report_generation_pipeline(
        task_id, user_id, PipelineMode.TWO_PHASE, force_reanalyze
    )


def execute_two_phase_report_generation(
    task_id: int, 
    user_id: str, 
    force_reanalyze: bool = False,
    **config_kwargs
) -> Dict[str, Any]:
    """直接执行两阶段架构流水线"""
    return unified_report_generation_pipeline(
        task_id, user_id, PipelineMode.TWO_PHASE, force_reanalyze, **config_kwargs
    )