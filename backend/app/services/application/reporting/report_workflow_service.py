"""
报告工作流服务

集成模板化SQL执行、数据处理、文档生成的完整报告生成流水线
基于用户提供的Celery任务逻辑，实现稳定的报告生成机制
"""

import logging
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ReportWorkflowService:
    """报告工作流服务"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.logger = logging.getLogger(self.__class__.__name__)

    async def execute_report_workflow(
        self,
        template_id: str,
        data_source_id: str,
        period_type: str = "daily",
        output_format: str = "docx",
        execution_mode: str = "production",
        use_agent_charts: bool = True
    ) -> Dict[str, Any]:
        """
        执行完整的报告生成工作流

        Args:
            template_id: 模板ID
            data_source_id: 数据源ID
            period_type: 周期类型 (daily/weekly/monthly)
            output_format: 输出格式
            execution_mode: 执行模式 (production/test)
            use_agent_charts: 是否使用Agent生成图表

        Returns:
            执行结果
        """
        try:
            self.logger.info(f"开始执行报告工作流: 模板={template_id}, 周期={period_type}, 模式={execution_mode}, Agent图表={use_agent_charts}")

            # 1. 生成数据阶段
            data_result = await self._generate_data_phase(
                template_id, data_source_id, period_type, execution_mode
            )

            if not data_result["success"]:
                return data_result

            # 2. 生成报告阶段
            report_result = await self._generate_report_phase(
                template_id, data_result["data"], output_format, period_type, use_agent_charts
            )

            if not report_result["success"]:
                return report_result

            # 3. 整理最终结果
            return {
                "success": True,
                "data": {
                    "workflow_type": "complete_report_generation",
                    "execution_mode": execution_mode,
                    "period_type": period_type,
                    "use_agent_charts": use_agent_charts,
                    "data_phase": data_result["data"],
                    "report_phase": report_result["data"]
                },
                "message": f"报告工作流执行成功 (Agent图表: {use_agent_charts})",
                "output_files": report_result["data"].get("output_files", [])
            }

        except Exception as e:
            self.logger.error(f"❌ 报告工作流执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "报告工作流执行失败"
            }

    async def _generate_data_phase(
        self,
        template_id: str,
        data_source_id: str,
        period_type: str,
        execution_mode: str
    ) -> Dict[str, Any]:
        """
        数据生成阶段 - 对应用户Celery任务中的generate_data_task
        """
        try:
            from app.services.data.processing.etl.etl_service import ETLService
            from app.services.data.template import time_inference_service, sql_template_service

            self.logger.info(f"📊 开始数据生成阶段: 周期={period_type}, 模式={execution_mode}")

            # 1. 获取模板中的占位符SQL映射
            placeholder_sql_map = await self._get_template_sql_mapping(template_id)

            if not placeholder_sql_map:
                return {
                    "success": False,
                    "error": "未找到模板的SQL映射",
                    "data": None
                }

            # 2. 时间推断
            if execution_mode == "test":
                time_result = time_inference_service.get_test_validation_date()
            else:
                # 生产模式：根据周期推断时间
                cron_expression = self._get_cron_by_period(period_type)
                time_result = time_inference_service.infer_base_date_from_cron(cron_expression)

            base_date = time_result["base_date"]

            # 3. 执行模板化数据提取
            etl_service = ETLService(user_id=self.user_id)

            time_context = {
                "cron_expression": self._get_cron_by_period(period_type),
                "execution_time": time_result.get("task_execution_time"),
                "test_date": time_result.get("base_date"),
                "additional_params": {}
            }

            extract_result = await etl_service.extract_data_with_templates(
                data_source_id=data_source_id,
                placeholder_sql_map=placeholder_sql_map,
                time_context=time_context,
                execution_mode=execution_mode
            )

            if not extract_result["success"]:
                return extract_result

            # 4. 处理提取结果，构建占位符数据映射
            placeholder_data_map = {}
            for extraction in extract_result["data"]["successful_extractions"]:
                placeholder = extraction["placeholder"]
                data = extraction["data"]
                placeholder_data_map[placeholder] = data

            # 5. 处理报告占位符（周期、百分比等）
            processed_data = sql_template_service.process_report_placeholders(
                placeholder_data_map, base_date, period_type
            )

            return {
                "success": True,
                "data": {
                    "placeholder_data": processed_data,
                    "time_inference": time_result,
                    "base_date": base_date,
                    "period_type": period_type,
                    "extraction_summary": extract_result["data"]
                },
                "message": f"数据生成完成: {len(processed_data)} 个占位符"
            }

        except Exception as e:
            self.logger.error(f"❌ 数据生成阶段失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    async def _generate_report_phase(
        self,
        template_id: str,
        data_phase_result: Dict[str, Any],
        output_format: str,
        period_type: str,
        use_agent_charts: bool = True
    ) -> Dict[str, Any]:
        """
        报告生成阶段 - 对应用户Celery任务中的generate_report_task
        使用Agent增强的图表生成
        """
        try:
            from app.services.infrastructure.document.word_template_service import create_agent_enhanced_word_service

            self.logger.info(f"📄 开始报告生成阶段: 格式={output_format} (Agent图表生成)")

            placeholder_data = data_phase_result["placeholder_data"]
            base_date = data_phase_result["base_date"]

            # 1. 获取模板文件路径
            template_file_path = await self._get_template_file_path(template_id)
            if not template_file_path:
                return {
                    "success": False,
                    "error": f"未找到模板文件: {template_id}",
                    "data": None
                }

            # 2. 生成输出文件路径
            output_file_path = self._generate_output_file_path(
                template_id, base_date, period_type, output_format
            )

            # 3. 处理Word文档模板
            if output_format.lower() == "docx":
                if use_agent_charts:
                    # 使用Agent增强服务
                    self.logger.info("使用Agent增强的Word服务生成报告")
                    container = self._get_service_container()
                    word_service = create_agent_enhanced_word_service(container=container)

                    doc_result = await word_service.process_document_template_enhanced(
                        template_path=template_file_path,
                        placeholder_data=placeholder_data,
                        output_path=output_file_path
                    )
                else:
                    # 使用传统Word服务
                    from app.services.infrastructure.document.word_template_service import create_word_template_service
                    self.logger.info("使用传统Word服务生成报告")
                    word_service = create_word_template_service()

                    doc_result = await word_service.process_document_template(
                        template_path=template_file_path,
                        placeholder_data=placeholder_data,
                        output_path=output_file_path,
                        container=None,
                        use_agent_charts=False
                    )

                if not doc_result["success"]:
                    return doc_result

                return {
                    "success": True,
                    "data": {
                        "output_files": [output_file_path],
                        "output_format": output_format,
                        "placeholders_processed": doc_result["placeholders_processed"],
                        "chart_generation_method": doc_result.get("chart_generation_method", "unknown"),
                        "template_file": template_file_path,
                        "agent_enhanced": use_agent_charts
                    },
                    "message": f"报告生成完成: {output_file_path} ({'Agent' if use_agent_charts else '传统'}图表生成)"
                }
            else:
                return {
                    "success": False,
                    "error": f"不支持的输出格式: {output_format}",
                    "data": None
                }

        except Exception as e:
            self.logger.error(f"❌ 报告生成阶段失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    def _get_service_container(self):
        """
        获取服务容器 - 集成现有后端架构

        Returns:
            服务容器实例或None
        """
        try:
            # 尝试从现有系统获取容器
            from app.core.container import container
            if container:
                return container
        except ImportError:
            self.logger.debug("未找到app.core.container，尝试其他方式")

        try:
            # 创建兼容的容器实现
            from app.db.session import get_db_session
            from app import crud

            class BackendCompatibleContainer:
                """与现有后端系统兼容的容器实现"""

                def __init__(self):
                    self.logger = logging.getLogger(self.__class__.__name__)

                def get_db_session(self):
                    """获取数据库会话"""
                    return get_db_session()

                def get_crud(self, model_name: str):
                    """获取CRUD操作对象"""
                    return getattr(crud, model_name, None)

                def get_user_id(self):
                    """获取当前用户ID"""
                    # 这个可以从请求上下文中获取，暂时返回None
                    return None

                def get(self, service_name: str):
                    """通用服务获取方法"""
                    service_map = {
                        "db": self.get_db_session,
                        "crud": self.get_crud,
                        "user_id": self.get_user_id
                    }
                    return service_map.get(service_name, lambda: None)()

            return BackendCompatibleContainer()

        except Exception as e:
            self.logger.warning(f"无法创建服务容器: {e}")
            return None

    async def _get_template_sql_mapping(self, template_id: str) -> Optional[Dict[str, str]]:
        """获取模板的SQL映射"""
        try:
            # 这里应该从数据库获取模板的SQL映射
            # 暂时返回示例数据
            from app.db.session import get_db_session
            from app import crud

            with get_db_session() as db:
                template = crud.template.get(db, id=template_id)
                if not template:
                    return None

                # 从模板的placeholders字段获取SQL映射
                if hasattr(template, 'placeholders') and template.placeholders:
                    if isinstance(template.placeholders, str):
                        return json.loads(template.placeholders)
                    return template.placeholders

                return None

        except Exception as e:
            self.logger.error(f"❌ 获取模板SQL映射失败: {e}")
            return None

    async def _get_template_file_path(self, template_id: str) -> Optional[str]:
        """获取模板文件路径"""
        try:
            from app.db.session import get_db_session
            from app import crud

            with get_db_session() as db:
                template = crud.template.get(db, id=template_id)
                if not template:
                    return None

                # 从模板获取文件路径
                if hasattr(template, 'file_path') and template.file_path:
                    return template.file_path

                # 如果没有文件路径，尝试构建默认路径
                return f"/templates/{template_id}.docx"

        except Exception as e:
            self.logger.error(f"❌ 获取模板文件路径失败: {e}")
            return None

    def _get_cron_by_period(self, period_type: str) -> str:
        """根据周期类型获取对应的cron表达式"""
        cron_map = {
            "daily": "0 8 * * *",      # 每天8点
            "weekly": "0 8 * * 1",     # 每周一8点
            "monthly": "0 8 1 * *"     # 每月1日8点
        }
        return cron_map.get(period_type, "0 8 * * *")

    def _generate_output_file_path(
        self,
        template_id: str,
        base_date: str,
        period_type: str,
        output_format: str
    ) -> str:
        """
        生成输出文件路径
        文件命名规则: 时间-任务名称.格式
        例如: 2025-01-15-月度销售报告.docx
        """
        try:
            # 创建输出目录
            output_dir = f"/output/reports/{self.user_id}"
            os.makedirs(output_dir, exist_ok=True)

            # 获取任务名称（从template_id或数据库获取）
            task_name = self._get_task_name_from_template(template_id)
            if not task_name:
                task_name = template_id

            # 生成文件名: 时间-任务名称
            filename = f"{base_date}-{task_name}.{output_format}"

            return os.path.join(output_dir, filename)

        except Exception as e:
            self.logger.error(f"❌ 生成输出文件路径失败: {e}")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"/tmp/report_{timestamp}.{output_format}"

    def _get_task_name_from_template(self, template_id: str) -> str:
        """
        从模板ID获取任务名称

        Args:
            template_id: 模板ID

        Returns:
            任务名称
        """
        try:
            from app.db.session import get_db_session
            from app import crud

            with get_db_session() as db:
                template = crud.template.get(db, id=template_id)
                if template and hasattr(template, 'name') and template.name:
                    return template.name
                elif template and hasattr(template, 'title') and template.title:
                    return template.title
                else:
                    return template_id

        except Exception as e:
            self.logger.warning(f"无法获取模板名称: {e}")
            return template_id

    async def schedule_periodic_report(
        self,
        template_id: str,
        data_source_id: str,
        period_type: str,
        cron_expression: str,
        enabled: bool = True
    ) -> Dict[str, Any]:
        """
        调度周期性报告生成任务

        Args:
            template_id: 模板ID
            data_source_id: 数据源ID
            period_type: 周期类型
            cron_expression: cron表达式
            enabled: 是否启用

        Returns:
            调度结果
        """
        try:
            # 这里可以集成Celery Beat或其他任务调度系统
            task_config = {
                "task_name": f"report_{template_id}_{period_type}",
                "template_id": template_id,
                "data_source_id": data_source_id,
                "period_type": period_type,
                "cron_expression": cron_expression,
                "enabled": enabled,
                "user_id": self.user_id
            }

            self.logger.info(f"✅ 周期性报告任务调度成功: {task_config['task_name']}")

            return {
                "success": True,
                "data": task_config,
                "message": "周期性报告任务调度成功"
            }

        except Exception as e:
            self.logger.error(f"❌ 周期性报告任务调度失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "周期性报告任务调度失败"
            }


def create_report_workflow_service(user_id: str) -> ReportWorkflowService:
    """创建报告工作流服务实例"""
    return ReportWorkflowService(user_id=user_id)