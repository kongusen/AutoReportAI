"""
报告工作流API端点

提供基于模板化SQL的完整报告生成接口
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.application.reporting.report_workflow_service import create_report_workflow_service

logger = logging.getLogger(__name__)

router = APIRouter()


class ReportGenerationRequest(BaseModel):
    """报告生成请求"""
    template_id: str = Field(..., description="模板ID")
    data_source_id: str = Field(..., description="数据源ID")
    period_type: str = Field(default="daily", description="周期类型 (daily/weekly/monthly)")
    output_format: str = Field(default="docx", description="输出格式")
    execution_mode: str = Field(default="production", description="执行模式 (production/test)")
    use_agent_charts: bool = Field(default=True, description="是否使用Agent生成图表")


class ScheduleReportRequest(BaseModel):
    """调度报告请求"""
    template_id: str = Field(..., description="模板ID")
    data_source_id: str = Field(..., description="数据源ID")
    period_type: str = Field(..., description="周期类型")
    cron_expression: str = Field(..., description="cron表达式")
    enabled: bool = Field(default=True, description="是否启用")


@router.post("/generate")
async def generate_report(
    request: ReportGenerationRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    生成报告

    基于模板化SQL执行完整的报告生成工作流
    """
    try:
        logger.info(f"用户 {current_user.id} 开始生成报告: {request.template_id}")

        # 创建工作流服务
        workflow_service = create_report_workflow_service(user_id=str(current_user.id))

        # 执行报告工作流
        result = await workflow_service.execute_report_workflow(
            template_id=request.template_id,
            data_source_id=request.data_source_id,
            period_type=request.period_type,
            output_format=request.output_format,
            execution_mode=request.execution_mode,
            use_agent_charts=request.use_agent_charts
        )

        if result["success"]:
            logger.info(f"✅ 报告生成成功: {current_user.id} - {request.template_id}")
            return {
                "success": True,
                "message": "报告生成成功",
                "data": result["data"],
                "output_files": result.get("output_files", [])
            }
        else:
            logger.error(f"❌ 报告生成失败: {result.get('error')}")
            raise HTTPException(
                status_code=500,
                detail=f"报告生成失败: {result.get('error', '未知错误')}"
            )

    except Exception as e:
        logger.error(f"❌ 报告生成接口异常: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"报告生成失败: {str(e)}"
        )


@router.post("/generate-async")
async def generate_report_async(
    request: ReportGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    异步生成报告

    将报告生成任务放入后台队列，立即返回任务ID
    """
    try:
        import uuid
        task_id = str(uuid.uuid4())

        logger.info(f"用户 {current_user.id} 提交异步报告生成任务: {task_id}")

        async def background_report_generation():
            try:
                workflow_service = create_report_workflow_service(user_id=str(current_user.id))
                result = await workflow_service.execute_report_workflow(
                    template_id=request.template_id,
                    data_source_id=request.data_source_id,
                    period_type=request.period_type,
                    output_format=request.output_format,
                    execution_mode=request.execution_mode,
                    use_agent_charts=request.use_agent_charts
                )
                logger.info(f"✅ 后台报告生成完成: {task_id}")
            except Exception as e:
                logger.error(f"❌ 后台报告生成失败: {task_id} - {e}")

        # 添加后台任务
        background_tasks.add_task(background_report_generation)

        return {
            "success": True,
            "message": "报告生成任务已提交",
            "task_id": task_id,
            "status": "queued"
        }

    except Exception as e:
        logger.error(f"❌ 异步报告生成接口异常: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"任务提交失败: {str(e)}"
        )


@router.post("/schedule")
async def schedule_periodic_report(
    request: ScheduleReportRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    调度周期性报告生成

    创建定时任务，按照指定的cron表达式自动生成报告
    """
    try:
        logger.info(f"用户 {current_user.id} 调度周期性报告: {request.template_id}")

        # 创建工作流服务
        workflow_service = create_report_workflow_service(user_id=str(current_user.id))

        # 调度周期性任务
        result = await workflow_service.schedule_periodic_report(
            template_id=request.template_id,
            data_source_id=request.data_source_id,
            period_type=request.period_type,
            cron_expression=request.cron_expression,
            enabled=request.enabled
        )

        if result["success"]:
            logger.info(f"✅ 周期性报告调度成功: {current_user.id} - {request.template_id}")
            return {
                "success": True,
                "message": "周期性报告调度成功",
                "data": result["data"]
            }
        else:
            logger.error(f"❌ 周期性报告调度失败: {result.get('error')}")
            raise HTTPException(
                status_code=500,
                detail=f"调度失败: {result.get('error', '未知错误')}"
            )

    except Exception as e:
        logger.error(f"❌ 周期性报告调度接口异常: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"调度失败: {str(e)}"
        )


@router.get("/template/{template_id}/preview")
async def preview_template_placeholders(
    template_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    预览模板占位符

    分析模板文件中的占位符和SQL映射
    """
    try:
        from app.services.infrastructure.document.word_template_service import create_word_template_service

        logger.info(f"用户 {current_user.id} 预览模板占位符: {template_id}")

        # 创建Word模板服务
        word_service = create_word_template_service()

        # 获取模板文件路径
        workflow_service = create_report_workflow_service(user_id=str(current_user.id))
        template_file_path = await workflow_service._get_template_file_path(template_id)

        if not template_file_path:
            raise HTTPException(
                status_code=404,
                detail=f"模板文件未找到: {template_id}"
            )

        # 验证模板格式
        validation_result = word_service.validate_template_format(template_file_path)

        # 获取SQL映射
        sql_mapping = await workflow_service._get_template_sql_mapping(template_id)

        return {
            "success": True,
            "message": "模板预览成功",
            "data": {
                "template_id": template_id,
                "template_file": template_file_path,
                "validation": validation_result,
                "sql_mapping": sql_mapping,
                "placeholders_count": len(validation_result.get("placeholders", [])),
                "chart_placeholders_count": len(validation_result.get("chart_placeholders", []))
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 模板预览接口异常: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"模板预览失败: {str(e)}"
        )


@router.post("/test-data-generation")
async def test_data_generation(
    request: ReportGenerationRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    测试数据生成

    仅执行数据生成阶段，不生成最终报告，用于调试SQL模板
    """
    try:
        logger.info(f"用户 {current_user.id} 测试数据生成: {request.template_id}")

        # 创建工作流服务
        workflow_service = create_report_workflow_service(user_id=str(current_user.id))

        # 仅执行数据生成阶段
        result = await workflow_service._generate_data_phase(
            template_id=request.template_id,
            data_source_id=request.data_source_id,
            period_type=request.period_type,
            execution_mode="test"  # 强制使用测试模式
        )

        if result["success"]:
            logger.info(f"✅ 数据生成测试成功: {current_user.id} - {request.template_id}")
            return {
                "success": True,
                "message": "数据生成测试成功",
                "data": result["data"]
            }
        else:
            logger.error(f"❌ 数据生成测试失败: {result.get('error')}")
            raise HTTPException(
                status_code=500,
                detail=f"数据生成测试失败: {result.get('error', '未知错误')}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 数据生成测试接口异常: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"数据生成测试失败: {str(e)}"
        )