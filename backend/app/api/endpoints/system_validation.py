"""
系统验证端点

验证新的报告工作流和Agent图表生成功能
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


class SystemValidationRequest(BaseModel):
    """系统验证请求"""
    test_type: str = Field(..., description="测试类型 (agent_charts/template_sql/report_workflow)")
    test_data: Dict[str, Any] = Field(default={}, description="测试数据")


@router.post("/validate-agent-charts")
async def validate_agent_charts(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    验证Agent图表生成功能
    """
    try:
        logger.info(f"用户 {current_user.id} 开始验证Agent图表生成功能")

        # 测试Agent系统是否正常
        validation_results = {
            "agent_system": False,
            "chart_tools": False,
            "orchestrator": False,
            "word_service": False,
            "errors": []
        }

        # 1. 测试Agent系统导入
        try:
            from app.services.infrastructure.agents.facade import AgentFacade
            from app.services.infrastructure.agents.types import AgentInput, PlaceholderSpec
            validation_results["agent_system"] = True
            logger.info("✅ Agent系统导入成功")
        except Exception as e:
            validation_results["errors"].append(f"Agent系统导入失败: {e}")
            logger.error(f"❌ Agent系统导入失败: {e}")

        # 2. 测试图表工具
        try:
            from app.services.infrastructure.agents.tools.chart_tools import ChartSpecTool, WordChartGeneratorTool
            validation_results["chart_tools"] = True
            logger.info("✅ 图表工具导入成功")
        except Exception as e:
            validation_results["errors"].append(f"图表工具导入失败: {e}")
            logger.error(f"❌ 图表工具导入失败: {e}")

        # 3. 测试编排器
        try:
            from app.services.infrastructure.agents.orchestrator import UnifiedOrchestrator
            validation_results["orchestrator"] = True
            logger.info("✅ 编排器导入成功")
        except Exception as e:
            validation_results["errors"].append(f"编排器导入失败: {e}")
            logger.error(f"❌ 编排器导入失败: {e}")

        # 4. 测试Word服务
        try:
            from app.services.infrastructure.document.word_template_service import (
                create_agent_enhanced_word_service
            )
            validation_results["word_service"] = True
            logger.info("✅ Word服务导入成功")
        except Exception as e:
            validation_results["errors"].append(f"Word服务导入失败: {e}")
            logger.error(f"❌ Word服务导入失败: {e}")

        # 计算总体状态
        all_systems_ok = all([
            validation_results["agent_system"],
            validation_results["chart_tools"],
            validation_results["orchestrator"],
            validation_results["word_service"]
        ])

        return {
            "success": all_systems_ok,
            "message": "Agent图表生成系统验证完成",
            "validation_results": validation_results,
            "ready_for_production": all_systems_ok and len(validation_results["errors"]) == 0
        }

    except Exception as e:
        logger.error(f"❌ Agent图表验证异常: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"验证过程异常: {str(e)}"
        )


@router.post("/validate-template-sql")
async def validate_template_sql(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    验证模板化SQL功能
    """
    try:
        logger.info(f"用户 {current_user.id} 开始验证模板化SQL功能")

        validation_results = {
            "sql_template_service": False,
            "time_inference_service": False,
            "template_query_executor": False,
            "etl_service": False,
            "errors": []
        }

        # 1. 测试SQL模板服务
        try:
            from app.services.data.template import sql_template_service, time_inference_service
            validation_results["sql_template_service"] = True
            validation_results["time_inference_service"] = True
            logger.info("✅ 模板服务导入成功")
        except Exception as e:
            validation_results["errors"].append(f"模板服务导入失败: {e}")
            logger.error(f"❌ 模板服务导入失败: {e}")

        # 2. 测试查询执行器
        try:
            from app.services.data.query.template_query_executor import TemplateQueryExecutor
            validation_results["template_query_executor"] = True
            logger.info("✅ 查询执行器导入成功")
        except Exception as e:
            validation_results["errors"].append(f"查询执行器导入失败: {e}")
            logger.error(f"❌ 查询执行器导入失败: {e}")

        # 3. 测试ETL服务
        try:
            from app.services.data.processing.etl.etl_service import ETLService
            validation_results["etl_service"] = True
            logger.info("✅ ETL服务导入成功")
        except Exception as e:
            validation_results["errors"].append(f"ETL服务导入失败: {e}")
            logger.error(f"❌ ETL服务导入失败: {e}")

        # 计算总体状态
        all_systems_ok = all(validation_results[key] for key in validation_results if key != "errors")

        return {
            "success": all_systems_ok,
            "message": "模板化SQL系统验证完成",
            "validation_results": validation_results,
            "ready_for_production": all_systems_ok and len(validation_results["errors"]) == 0
        }

    except Exception as e:
        logger.error(f"❌ 模板化SQL验证异常: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"验证过程异常: {str(e)}"
        )


@router.post("/validate-report-workflow")
async def validate_report_workflow(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    验证完整的报告工作流
    """
    try:
        logger.info(f"用户 {current_user.id} 开始验证报告工作流")

        validation_results = {
            "report_workflow_service": False,
            "api_endpoints": False,
            "dependencies": False,
            "errors": []
        }

        # 1. 测试报告工作流服务
        try:
            from app.services.application.reporting.report_workflow_service import (
                create_report_workflow_service
            )
            workflow_service = create_report_workflow_service(user_id=str(current_user.id))
            validation_results["report_workflow_service"] = True
            logger.info("✅ 报告工作流服务创建成功")
        except Exception as e:
            validation_results["errors"].append(f"报告工作流服务失败: {e}")
            logger.error(f"❌ 报告工作流服务失败: {e}")

        # 2. 测试API端点
        try:
            from app.api.endpoints import report_workflow
            validation_results["api_endpoints"] = True
            logger.info("✅ API端点导入成功")
        except Exception as e:
            validation_results["errors"].append(f"API端点导入失败: {e}")
            logger.error(f"❌ API端点导入失败: {e}")

        # 3. 测试依赖项
        try:
            from app.core.dependencies import get_current_user
            from app.models.user import User
            validation_results["dependencies"] = True
            logger.info("✅ 依赖项导入成功")
        except Exception as e:
            validation_results["errors"].append(f"依赖项导入失败: {e}")
            logger.error(f"❌ 依赖项导入失败: {e}")

        # 计算总体状态
        all_systems_ok = all(validation_results[key] for key in validation_results if key != "errors")

        return {
            "success": all_systems_ok,
            "message": "报告工作流系统验证完成",
            "validation_results": validation_results,
            "ready_for_production": all_systems_ok and len(validation_results["errors"]) == 0
        }

    except Exception as e:
        logger.error(f"❌ 报告工作流验证异常: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"验证过程异常: {str(e)}"
        )


@router.get("/system-health")
async def get_system_health(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取系统健康状态
    """
    try:
        # 运行所有验证测试
        agent_result = await validate_agent_charts(current_user)
        template_result = await validate_template_sql(current_user)
        workflow_result = await validate_report_workflow(current_user)

        overall_health = (
            agent_result["success"] and
            template_result["success"] and
            workflow_result["success"]
        )

        return {
            "overall_health": overall_health,
            "agent_charts_status": agent_result["success"],
            "template_sql_status": template_result["success"],
            "report_workflow_status": workflow_result["success"],
            "detailed_results": {
                "agent_charts": agent_result,
                "template_sql": template_result,
                "report_workflow": workflow_result
            },
            "timestamp": logger.handlers[0].formatter.formatTime(
                logger.makeRecord("", 0, "", 0, "", (), None)
            ) if logger.handlers else "unknown"
        }

    except Exception as e:
        logger.error(f"❌ 系统健康检查异常: {e}")
        return {
            "overall_health": False,
            "error": str(e),
            "timestamp": "error"
        }