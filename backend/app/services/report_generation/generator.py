import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.core.logging_config import get_module_logger, get_performance_logger
from ..ai_integration import EnhancedAIService
from ..data_processing import DataRetrievalService
from .composer import ReportCompositionService
from .document_pipeline import TemplateParser
from ..agents.orchestration import AgentOrchestrator
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
        self.agent_orchestrator = AgentOrchestrator()
        self.composition_service = ReportCompositionService()
        self.word_generator = WordGeneratorService()
        self.ai_service = EnhancedAIService(db)
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
                    
                    # Execute using agent orchestrator
                    agent_result = await self.agent_orchestrator.execute(placeholder_input)
                    result = agent_result.data if agent_result.success else f"[Error: {agent_result.error_message}]"

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

            # 6. Generate Word document
            os.makedirs(output_dir, exist_ok=True)
            output_filename = (
                f"report_{task.name}_{generation_result['generation_id']}.docx"
            )
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
                        ai_params = self.ai_service.interpret_description_for_tool(
                            task_type=placeholder["type"],
                            description=placeholder["description"],
                            df_columns=(
                                sample_data.columns.tolist()
                                if not sample_data.empty
                                else []
                            ),
                        )
                        analysis["ai_interpretation"] = ai_params
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

            # Check AI service availability
            try:
                ai_health = self.ai_service.health_check()
                if ai_health["status"] != "healthy":
                    validation_result["warnings"].append(
                        f"AI service not healthy: {ai_health.get('message', 'Unknown issue')}"
                    )
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
