"""
统一的TT递归调用接口
基于TT递归自动迭代特性，提供简化的Agent调用模式
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass

from .stage_aware_adapter import StageAwareAgentAdapter
from .types import TaskComplexity, ExecutionStage, AgentResponse
from app.core.container import Container

logger = logging.getLogger(__name__)


@dataclass
class TTRecursionRequest:
    """TT递归请求"""
    question: str
    data_source_id: int
    user_id: str
    task_type: str = "general"
    complexity: str = "medium"
    context: Optional[Dict[str, Any]] = None
    max_iterations: Optional[int] = None


@dataclass
class TTRecursionResponse:
    """TT递归响应"""
    success: bool
    result: str
    metadata: Dict[str, Any]
    iterations: int = 0
    execution_time: float = 0.0
    error: Optional[str] = None


async def execute_tt_recursion(
    question: str,
    data_source_id: int,
    user_id: str,
    stage: str = "sql_generation",
    complexity: str = "medium",
    context: Optional[Dict[str, Any]] = None,
    max_iterations: Optional[int] = None,
    container: Optional[Container] = None
) -> TTRecursionResponse:
    """
    统一的TT递归执行接口
    
    基于三步骤Agent架构，支持不同阶段的TT递归执行
    每个阶段内部都会自动迭代到满意结果
    
    Args:
        question: 用户问题或需求
        data_source_id: 数据源ID
        user_id: 用户ID
        stage: 执行阶段 (sql_generation/chart_generation/completion)
        complexity: 复杂度 (low/medium/high)
        context: 额外上下文
        max_iterations: 最大迭代次数
        container: 容器实例
        
    Returns:
        TTRecursionResponse: TT递归执行结果
    """
    import time
    start_time = time.time()

    def _build_enriched_context(base: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """构建带有 TT 提示的上下文。

        - 为递归执行提供初始 turn 计数与优先级提示（由底层 runtime 深化）
        - 与调用方上下文做浅合并，调用方键优先
        """
        base = base or {}
        tt_hints = {
            "tt": {
                "turn_counter": 1,  # 初始调用视为第 1 轮，由 runtime 继续累加
                "priority_hints": {
                    "base_instructions": "CRITICAL",
                    "tool_definitions": "HIGH",
                    "examples": "MEDIUM",
                },
                "task_type": stage,
                "complexity": complexity,
            }
        }

        enriched = {**tt_hints, **base}
        return enriched

    def _extract_result(payload: Any) -> Tuple[bool, Any, Dict[str, Any]]:
        """
        将TT递归阶段产出的不同结果格式统一为(success, content, metadata)
        兼容：
        - AgentResponse 对象
        - dict（可能包含 response/metadata/result 等字段）
        - 其他任意类型
        """
        if isinstance(payload, AgentResponse):
            return (
                payload.success,
                payload.result,
                payload.metadata or {}
            )

        if isinstance(payload, dict):
            # 优先处理嵌套的 AgentResponse
            response_obj = payload.get("response")
            if isinstance(response_obj, AgentResponse):
                return _extract_result(response_obj)

            success = payload.get("success", True)
            metadata = payload.get("metadata", {})

            if response_obj is not None:
                content = response_obj
            elif "result" in payload:
                content = payload["result"]
            elif "content" in payload:
                content = payload["content"]
            else:
                content = ""

            return success, content, metadata if isinstance(metadata, dict) else {}

        # 其他类型直接转换为字符串
        return True, payload, {}
    
    try:
        # 创建Facade（如果未提供container）
        if container is None:
            container = Container()
        
        adapter = StageAwareAgentAdapter(container=container)
        
        # 初始化
        await adapter.initialize(
            user_id=user_id,
            task_type=stage,  # 使用stage作为task_type
            task_complexity=getattr(TaskComplexity, complexity.upper(), TaskComplexity.MEDIUM)
        )
        
        # 根据阶段选择不同的执行方法
        result = None
        iterations = 0
        
        logger.info(f"🚀 开始{stage}阶段TT递归执行: {question[:100]}...")
        
        enriched_context = _build_enriched_context(context)

        if stage == "sql_generation":
            # 第一阶段：SQL生成
            result = await adapter.generate_sql(
                placeholder=question,
                data_source_id=data_source_id,
                user_id=user_id,
                context=enriched_context
            )
            
            if result.get("success"):
                logger.info(f"✅ SQL生成阶段TT递归完成")
            else:
                error_msg = result.get('error', '未知错误')
                logger.error(f"❌ SQL生成阶段TT递归失败: {error_msg}")
                raise Exception(f"SQL生成阶段TT递归失败: {error_msg}")
                
        elif stage == "chart_generation":
            # 第二阶段：图表生成
            etl_data = enriched_context.get('etl_data', {})
            chart_placeholder = enriched_context.get('chart_placeholder', question)
            
            result = await adapter.generate_chart(
                chart_placeholder=chart_placeholder,
                etl_data=etl_data,
                user_id=user_id,
                task_context=enriched_context
            )
            
            if result.get("success"):
                logger.info(f"✅ 图表生成阶段TT递归完成")
            else:
                error_msg = result.get('error', '未知错误')
                logger.error(f"❌ 图表生成阶段TT递归失败: {error_msg}")
                raise Exception(f"图表生成阶段TT递归失败: {error_msg}")
                
        elif stage == "completion":
            # 第三阶段：文档生成
            paragraph_context = enriched_context.get('paragraph_context', '')
            placeholder_data = enriched_context.get('placeholder_data', {})
            
            result = await adapter.generate_document(
                paragraph_context=paragraph_context,
                placeholder_data=placeholder_data,
                user_id=user_id,
                task_context=enriched_context
            )
            
            if result.get("success"):
                logger.info(f"✅ 文档生成阶段TT递归完成")
            else:
                error_msg = result.get('error', '未知错误')
                logger.error(f"❌ 文档生成阶段TT递归失败: {error_msg}")
                raise Exception(f"文档生成阶段TT递归失败: {error_msg}")
        else:
            raise ValueError(f"不支持的阶段: {stage}")
        
        if not result:
            raise Exception("TT递归执行未返回结果")
        
        execution_time = time.time() - start_time
        
        success, content, metadata = _extract_result(result)

        return TTRecursionResponse(
            success=success,
            result=content if isinstance(content, str) else str(content),
            metadata=metadata,
            iterations=iterations,
            execution_time=execution_time
        )
        
    except Exception as e:
        logger.error(f"❌ TT递归执行异常: {e}")
        execution_time = time.time() - start_time
        
        return TTRecursionResponse(
            success=False,
            result="",
            metadata={"error": str(e)},
            iterations=0,
            execution_time=execution_time,
            error=str(e)
        )


# 便捷函数 - 针对三步骤Agent架构
async def execute_sql_generation_tt(
    placeholder: str,
    data_source_id: int,
    user_id: str,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    第一阶段：SQL生成（placeholder中调用）
    
    对还没有SQL的占位符进行分析生成SQL
    使用TT递归自动迭代到满意结果
    
    Args:
        placeholder: 占位符内容
        data_source_id: 数据源ID
        user_id: 用户ID
        context: 额外上下文
        
    Returns:
        str: 生成的SQL
    """
    response = await execute_tt_recursion(
        question=placeholder,
        data_source_id=data_source_id,
        user_id=user_id,
        stage="sql_generation",
        complexity="medium",
        context=context
    )
    
    return response.result if response.success else ""


async def execute_chart_generation_tt(
    chart_placeholder: str,
    etl_data: Dict[str, Any],
    user_id: str,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    第二阶段：图表生成（task中调用，基于ETL结果）
    
    ETL后基于ETL的结果，对图表占位符进行图表生成
    使用TT递归自动迭代到满意结果
    
    Args:
        chart_placeholder: 图表占位符
        etl_data: ETL处理后的数据
        user_id: 用户ID
        context: 额外上下文
        
    Returns:
        str: 生成的图表
    """
    # 将etl_data添加到context中
    if context is None:
        context = {}
    context['etl_data'] = etl_data
    context['chart_placeholder'] = chart_placeholder
    
    response = await execute_tt_recursion(
        question=chart_placeholder,
        data_source_id=0,  # 图表生成阶段不需要data_source_id
        user_id=user_id,
        stage="chart_generation",
        complexity="medium",
        context=context
    )
    
    return response.result if response.success else ""


async def execute_document_generation_tt(
    paragraph_context: str,
    placeholder_data: Dict[str, Any],
    user_id: str,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    第三阶段：文档生成（基于图表数据回填模板）
    
    基于经过图表生成后的数据回填进模板，进行基于数据的小范围描述改写
    使用TT递归自动迭代到满意结果
    
    Args:
        paragraph_context: 段落上下文
        placeholder_data: 占位符数据
        user_id: 用户ID
        context: 额外上下文
        
    Returns:
        str: 生成的文档内容
    """
    # 将数据添加到context中
    if context is None:
        context = {}
    context['paragraph_context'] = paragraph_context
    context['placeholder_data'] = placeholder_data
    
    response = await execute_tt_recursion(
        question=paragraph_context,
        data_source_id=0,  # 文档生成阶段不需要data_source_id
        user_id=user_id,
        stage="completion",
        complexity="medium",
        context=context
    )
    
    return response.result if response.success else ""


# 兼容性函数（保持向后兼容）
async def analyze_data_tt(
    question: str,
    data_source_id: int,
    user_id: str,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    使用TT递归进行数据分析（兼容性函数）
    
    Args:
        question: 分析问题
        data_source_id: 数据源ID
        user_id: 用户ID
        context: 额外上下文
        
    Returns:
        str: 分析结果
    """
    response = await execute_tt_recursion(
        question=question,
        data_source_id=data_source_id,
        user_id=user_id,
        stage="sql_generation",  # 数据分析通常使用SQL生成阶段
        complexity="medium",
        context=context
    )
    
    return response.result if response.success else ""


async def generate_sql_tt(
    requirement: str,
    data_source_id: int,
    user_id: str,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    使用TT递归生成SQL（兼容性函数）
    
    Args:
        requirement: SQL需求描述
        data_source_id: 数据源ID
        user_id: 用户ID
        context: 额外上下文
        
    Returns:
        str: 生成的SQL
    """
    return await execute_sql_generation_tt(
        placeholder=f"生成SQL: {requirement}",
        data_source_id=data_source_id,
        user_id=user_id,
        context=context
    )
