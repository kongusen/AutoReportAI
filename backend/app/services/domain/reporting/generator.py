import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.core.logging_config import get_module_logger, get_performance_logger
# 使用React Agent系统
from app.services.data.processing.retrieval import DataRetrievalService
from .composer import ReportCompositionService
from .document_pipeline import TemplateParser
# ServiceCoordinator功能已整合到React Agent工作流编排中
from .word_generator_service import WordGeneratorService

# Get module-specific loggers
logger = get_module_logger('report_generation')
perf_logger = get_performance_logger()


class ReportGenerationStatus:
    """Report generation status constants"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportGenerationService:
    def __init__(self, db: Session):
        self.db = db
        self.template_parser = TemplateParser()
        # 服务协调功能通过React Agent工作流编排实现
        self.composition_service = ReportCompositionService()
        self.word_generator = WordGeneratorService()
        # AI服务通过React Agent LLM选择器实现
        self.data_retrieval = DataRetrievalService()

    async def generate_report(
        self,
        task_id: int,
        template_id: int,
        data_source_id: int,
        output_dir: str = "generated_reports",
    ) -> Dict[str, Any]:
        """
        Generate a complete report based on task configuration.

        Args:
            task_id: The task ID for tracking
            template_id: Template to use for report generation
            data_source_id: Data source to pull data from
            output_dir: Directory to save generated reports

        Returns:
            Dictionary with generation results
        """
        generation_result = {
            "task_id": task_id,
            "template_id": template_id,
            "data_source_id": data_source_id,
            "status": ReportGenerationStatus.PROCESSING,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "duration_seconds": None,
            "output_path": None,
            "error_message": None,
            "placeholders_processed": 0,
            "generation_id": str(uuid.uuid4()),
        }

        try:
            # 1. Get task, template, and data source
            task = crud.task.get(self.db, id=task_id)
            if not task:
                raise ValueError("Task not found")

            template = crud.template.get(self.db, id=template_id)
            if not template:
                raise ValueError("Template not found")

            data_source = crud.data_source.get(self.db, id=data_source_id)
            if not data_source:
                raise ValueError("Data source not found")

            # 2. Parse template to extract placeholders
            template_structure = self.template_parser.parse(template.file_path)
            placeholders = template_structure.get("placeholders", [])
            generation_result["placeholders_processed"] = len(placeholders)

            # 3. Process each placeholder using AI and data tools
            placeholder_results = {}
            for placeholder in placeholders:
                placeholder_name = placeholder["name"]
                placeholder_type = placeholder["type"]
                placeholder_description = placeholder.get("description", "")

                try:
                    # Use the agent orchestrator to process the placeholder
                    placeholder_input = {
                        "placeholder_type": placeholder_type,
                        "description": placeholder_description,
                        "data_source_id": str(data_source_id),
                    }
                    
                    # 使用统一AI门面处理占位符内容生成
                    try:
                        from app.services.infrastructure.agents import execute_agent_task
                        
                        # 构建内容生成的数据上下文
                        template_parts = [{
                            "placeholder_name": placeholder_name,
                            "placeholder_type": placeholder_type,
                            "description": placeholder_description
                        }]
                        
                        data_context = {
                            "data_source_id": data_source_id,
                            "task_id": task_id,
                            "template_id": template_id
                        }
                        
                        # 使用agents系统生成内容
                        content_result = await execute_agent_task(
                            task_name="内容生成",
                            task_description=f"为占位符 {placeholder_name} 生成报告内容",
                            context_data={
                                "placeholders": {
                                    "placeholder_name": placeholder_name,
                                    "placeholder_type": placeholder_type,
                                    "placeholder_description": placeholder_description,
                                    "data_source_id": str(data_source_id),
                                    "task_id": str(task_id),
                                    "template_id": str(template_id)
                                }
                            },
                            target_agent="report_generation_agent"
                        )
                        
                        result = content_result.get("result", {}).get("generated_content", "") if content_result.get("success") else f"[生成失败: {placeholder_name}]"
                        
                    except Exception as e:
                        logger.warning(f"React Agent处理占位符失败: {str(e)}")
                        result = f"[占位符处理错误: {placeholder_name} - {str(e)}]"

                    # Format the placeholder key for replacement
                    if placeholder_type == "scalar":
                        placeholder_key = f"{{{{{placeholder_name}}}}}"
                    else:
                        placeholder_key = f"[{placeholder_type}:{placeholder_name}]"

                    placeholder_results[placeholder_key] = result

                except Exception as e:
                    # If a placeholder fails, use a fallback
                    placeholder_key = (
                        f"{{{{{placeholder_name}}}}}"
                        if placeholder_type == "scalar"
                        else f"[{placeholder_type}:{placeholder_name}]"
                    )
                    placeholder_results[placeholder_key] = (
                        f"[Error processing {placeholder_name}: {str(e)}]"
                    )

            # 4. Read template content
            with open(template.file_path, "r", encoding="utf-8") as f:
                template_content = f.read()

            # 5. Compose the final report
            composed_content = self.composition_service.compose_report(
                template_content=template_content, results=placeholder_results
            )

            # 6. Generate charts using ChartIntegrationService
            chart_results = []
            try:
                from .chart_integration_service import ChartIntegrationService
                
                chart_service = ChartIntegrationService(self.db, str(task.owner_id))
                chart_generation_result = await chart_service.generate_charts_for_task(
                    task=task,
                    data_results={"processed_data": {}, "placeholder_results": placeholder_results},
                    placeholder_data=placeholder_results
                )
                
                if chart_generation_result.get('success'):
                    chart_results = chart_generation_result.get('charts', [])
                    logger.info(f"生成了 {len(chart_results)} 个图表")
                    
            except Exception as e:
                logger.warning(f"图表生成失败，继续生成报告: {e}")

            # 7. Generate Word document with charts
            os.makedirs(output_dir, exist_ok=True)
            output_filename = (
                f"report_{task.name}_{generation_result['generation_id']}.docx"
            )
            
            try:
                # 使用完善的Word生成服务，包含图表插入功能
                report_path = self.word_generator.generate_report_from_template(
                    template_content=composed_content,
                    placeholder_values=placeholder_results,
                    title=f"{task.name}_报告",
                    chart_results=chart_results
                )
                output_path = report_path
                
            except Exception as e:
                logger.error(f"使用模板生成报告失败，降级处理: {e}")
                # 降级到原有方法
                output_path = os.path.join(output_dir, output_filename)
                self.word_generator.generate_report_from_content(
                    composed_content=composed_content, output_path=output_path
                )

            # 7. Update generation result
            generation_result["status"] = ReportGenerationStatus.COMPLETED
            generation_result["output_path"] = output_path
            generation_result["end_time"] = datetime.now().isoformat()

            # Calculate duration
            start_time = datetime.fromisoformat(generation_result["start_time"])
            end_time = datetime.fromisoformat(generation_result["end_time"])
            generation_result["duration_seconds"] = (
                end_time - start_time
            ).total_seconds()

            return generation_result

        except Exception as e:
            generation_result["status"] = ReportGenerationStatus.FAILED
            generation_result["error_message"] = str(e)
            generation_result["end_time"] = datetime.now().isoformat()

            if generation_result["start_time"]:
                start_time = datetime.fromisoformat(generation_result["start_time"])
                end_time = datetime.fromisoformat(generation_result["end_time"])
                generation_result["duration_seconds"] = (
                    end_time - start_time
                ).total_seconds()

            raise

    async def preview_report_data(
        self, template_id: int, data_source_id: int, limit: int = 5
    ) -> Dict[str, Any]:
        """
        Preview what data would be used for report generation.

        Args:
            template_id: Template to analyze
            data_source_id: Data source to preview
            limit: Number of sample records to include

        Returns:
            Dictionary with preview data
        """
        try:
            # Get template and data source
            template = crud.template.get(self.db, id=template_id)
            if not template:
                raise ValueError("Template not found")

            data_source = crud.data_source.get(self.db, id=data_source_id)
            if not data_source:
                raise ValueError("Data source not found")

            # Parse template to extract placeholders
            template_structure = self.template_parser.parse(template.file_path)
            placeholders = template_structure.get("placeholders", [])

            # Get sample data from data source
            sample_data = await self.data_retrieval.fetch_data(data_source)
            if len(sample_data) > limit:
                sample_data = sample_data.head(limit)

            # Analyze each placeholder
            placeholder_analysis = []
            for placeholder in placeholders:
                analysis = {
                    "name": placeholder["name"],
                    "type": placeholder["type"],
                    "description": placeholder.get("description", ""),
                    "available_columns": (
                        sample_data.columns.tolist() if not sample_data.empty else []
                    ),
                    "sample_values": {},
                    "ai_interpretation": None,
                }

                # Add sample values for relevant columns
                if not sample_data.empty:
                    for col in sample_data.columns[:3]:  # Show first 3 columns
                        analysis["sample_values"][col] = (
                            sample_data[col].head(3).tolist()
                        )

                # Get AI interpretation if description is provided
                if placeholder.get("description"):
                    try:
                        # 使用agents系统进行业务洞察解释
                        from app.services.infrastructure.agents import execute_agent_task
                        
                        # 构建分析结果数据
                        data_analysis_results = {
                            "placeholder_name": placeholder['name'],
                            "placeholder_type": placeholder['type'],
                            "description": placeholder['description'],
                            "available_columns": sample_data.columns.tolist() if not sample_data.empty else [],
                            "data_shape": sample_data.shape if not sample_data.empty else (0, 0)
                        }
                        
                        # 使用agents系统进行业务洞察解释
                        interpretation_result = await execute_agent_task(
                            task_name="业务洞察解释",
                            task_description=f"解释模板占位符 '{placeholder['name']}' 的业务含义",
                            context_data={
                                "placeholders": {
                                    "placeholder_name": placeholder['name'],
                                    "placeholder_type": placeholder['type'], 
                                    "placeholder_description": placeholder['description'],
                                    "analysis_results": data_analysis_results,
                                    "target_audience": "business"
                                }
                            },
                            target_agent="business_intelligence_agent"
                        )
                        
                        analysis["ai_interpretation"] = interpretation_result.get("result", {}).get("interpretation", "") if interpretation_result.get("success") else f"解释生成失败: {placeholder['name']}"
                    except Exception as e:
                        analysis["ai_interpretation"] = f"Error: {str(e)}"

                placeholder_analysis.append(analysis)

            return {
                "template_id": template_id,
                "template_name": template.name,
                "data_source_id": data_source_id,
                "data_source_name": data_source.name,
                "placeholders": placeholder_analysis,
                "sample_data_shape": (
                    {"rows": len(sample_data), "columns": len(sample_data.columns)}
                    if not sample_data.empty
                    else {"rows": 0, "columns": 0}
                ),
                "sample_data": (
                    sample_data.to_dict(orient="records")
                    if not sample_data.empty
                    else []
                ),
            }

        except Exception as e:
            return {
                "error": str(e),
                "template_id": template_id,
                "data_source_id": data_source_id,
            }

    def validate_report_configuration(
        self, template_id: int, data_source_id: int
    ) -> Dict[str, Any]:
        """
        Validate that a template and data source are compatible for report generation.

        Args:
            template_id: Template to validate
            data_source_id: Data source to validate

        Returns:
            Dictionary with validation results
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "template_id": template_id,
            "data_source_id": data_source_id,
        }

        try:
            # Check template exists and is accessible
            template = crud.template.get(self.db, id=template_id)
            if not template:
                validation_result["errors"].append("Template not found")
                validation_result["valid"] = False
            else:
                if not os.path.exists(template.file_path):
                    validation_result["errors"].append(
                        f"Template file not found: {template.file_path}"
                    )
                    validation_result["valid"] = False
                else:
                    try:
                        # Try to parse template
                        template_structure = self.template_parser.parse(
                            template.file_path
                        )
                        placeholders = template_structure.get("placeholders", [])
                        if not placeholders:
                            validation_result["warnings"].append(
                                "Template contains no placeholders"
                            )
                    except Exception as e:
                        validation_result["errors"].append(
                            f"Error parsing template: {str(e)}"
                        )
                        validation_result["valid"] = False

            # Check data source exists and is accessible
            data_source = crud.data_source.get(self.db, id=data_source_id)
            if not data_source:
                validation_result["errors"].append("Data source not found")
                validation_result["valid"] = False
            else:
                # Validate data source configuration
                if data_source.source_type.value == "sql":
                    if not data_source.connection_string:
                        validation_result["errors"].append(
                            "SQL data source requires connection string"
                        )
                        validation_result["valid"] = False
                elif data_source.source_type.value == "csv":
                    if not data_source.file_path:
                        validation_result["errors"].append(
                            "CSV data source requires file path"
                        )
                        validation_result["valid"] = False
                    elif not os.path.exists(data_source.file_path):
                        validation_result["errors"].append(
                            f"CSV file not found: {data_source.file_path}"
                        )
                        validation_result["valid"] = False
                elif data_source.source_type.value == "api":
                    if not data_source.api_url:
                        validation_result["errors"].append(
                            "API data source requires URL"
                        )
                        validation_result["valid"] = False

            # Check React Agent系统 availability
            try:
                # React Agent系统健康检查 - 简化版本，避免async调用
                from app.services.infrastructure.llm import get_pure_llm_manager
                
                llm_manager = get_pure_llm_manager()
                # 简单检查manager是否可用
                if hasattr(llm_manager, 'available_models') and llm_manager.available_models:
                    logger.info("React Agent系统健康检查通过")
                else:
                    validation_result["warnings"].append("React Agent系统可用性待确认")
            except Exception as e:
                validation_result["warnings"].append(
                    f"AI service check failed: {str(e)}"
                )

            return validation_result

        except Exception as e:
            validation_result["errors"].append(f"Validation error: {str(e)}")
            validation_result["valid"] = False
            return validation_result


# Create singleton instance
def create_report_generation_service(db: Session) -> ReportGenerationService:
    return ReportGenerationService(db)
