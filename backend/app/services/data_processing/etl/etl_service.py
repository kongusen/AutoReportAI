from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd
import structlog
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import crud, models
from app.core.config import settings
from app.core.security_utils import ConnectionStringError, validate_connection_string
from app.db.session import get_db_session
from ...data_sanitization_service import data_sanitizer
from .etl_engine_service import ETLTransformationEngine
from .intelligent_etl_executor import (
    ETLInstructions,
    intelligent_etl_executor,
)

logger = structlog.get_logger(__name__)


class ETLJobStatus:
    """ETL Job status constants"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ETLService:
    def __init__(self):
        self.logger = logger

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get the current status of an ETL job"""
        with get_db_session() as db:
            etl_job = crud.etl_job.get(db, id=job_id)
            if not etl_job:
                raise ValueError("ETL Job not found")

            # Check if job is currently running (you could use Redis or database for this)
            # For now, we'll just return the job configuration
            return {
                "job_id": job_id,
                "name": etl_job.name,
                "status": ETLJobStatus.PENDING,  # Default status
                "enabled": etl_job.enabled,
                "schedule": etl_job.schedule,
                "last_run": None,  # TODO: Track last run time
                "next_run": None,  # TODO: Calculate next run time
            }

    def validate_job_configuration(self, job_id: str) -> Dict[str, Any]:
        """Validate ETL job configuration before execution"""
        with get_db_session() as db:
            etl_job = crud.etl_job.get(db, id=job_id)
            if not etl_job:
                raise ValueError("ETL Job not found")

            validation_results = {"valid": True, "errors": [], "warnings": []}

            # Check if job is enabled
            if not etl_job.enabled:
                validation_results["errors"].append("Job is disabled")
                validation_results["valid"] = False

            # Check source data source
            source_db = crud.data_source.get(db, id=etl_job.source_data_source_id)
            if not source_db:
                validation_results["errors"].append("Source data source not found")
                validation_results["valid"] = False
            else:
                # Validate connection string
                try:
                    if source_db.source_type.value == "sql":
                        if not source_db.connection_string:
                            validation_results["errors"].append(
                                "SQL data source requires connection string"
                            )
                            validation_results["valid"] = False
                        else:
                            validate_connection_string(source_db.connection_string)
                except ConnectionStringError as e:
                    validation_results["errors"].append(
                        f"Invalid connection string: {e}"
                    )
                    validation_results["valid"] = False

            # Check source query
            if not etl_job.source_query:
                validation_results["errors"].append("Source query is required")
                validation_results["valid"] = False

            # Check destination table name
            if not etl_job.destination_table_name:
                validation_results["errors"].append(
                    "Destination table name is required"
                )
                validation_results["valid"] = False

            # Validate transformation config
            if etl_job.transformation_config:
                try:
                    config = etl_job.transformation_config
                    if not isinstance(config, dict):
                        validation_results["errors"].append(
                            "Transformation config must be a dictionary"
                        )
                        validation_results["valid"] = False
                    elif "operations" in config:
                        operations = config["operations"]
                        if not isinstance(operations, list):
                            validation_results["errors"].append(
                                "Transformation operations must be a list"
                            )
                            validation_results["valid"] = False
                        else:
                            # Validate each operation
                            for i, op in enumerate(operations):
                                if not isinstance(op, dict):
                                    validation_results["errors"].append(
                                        f"Operation {i} must be a dictionary"
                                    )
                                    validation_results["valid"] = False
                                elif "operation" not in op:
                                    validation_results["errors"].append(
                                        f"Operation {i} missing 'operation' field"
                                    )
                                    validation_results["valid"] = False
                except Exception as e:
                    validation_results["errors"].append(
                        f"Error validating transformation config: {e}"
                    )
                    validation_results["valid"] = False

            return validation_results

    def run_job(self, job_id: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Runs a specific ETL job using a secure, structured transformation engine.

        Args:
            job_id: The ID of the ETL job to run
            dry_run: If True, validates and prepares but doesn't execute

        Returns:
            Dictionary with execution results
        """
        log = self.logger.bind(job_id=job_id, dry_run=dry_run)
        log.info("etl_job.run.started")

        execution_result = {
            "job_id": job_id,
            "status": ETLJobStatus.RUNNING,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "duration_seconds": None,
            "rows_processed": 0,
            "rows_output": 0,
            "error_message": None,
            "validation_results": None,
        }

        try:
            with get_db_session() as db:
                # 1. Get ETL Job configuration
                etl_job = crud.etl_job.get(db, id=job_id)
                if not etl_job:
                    raise ValueError("ETL Job not found")

                log = log.bind(job_name=etl_job.name)

                # 2. Validate job configuration
                validation_results = self.validate_job_configuration(job_id)
                execution_result["validation_results"] = validation_results

                if not validation_results["valid"]:
                    raise ValueError(
                        f"Job validation failed: {validation_results['errors']}"
                    )

                if dry_run:
                    log.info("etl_job.dry_run.completed")
                    execution_result["status"] = ETLJobStatus.SUCCESS
                    execution_result["end_time"] = datetime.now().isoformat()
                    return execution_result

                # 3. Get source database connection details
                source_db = crud.data_source.get(db, id=etl_job.source_data_source_id)

                # Create source engine based on data source type
                if source_db.source_type.value == "sql":
                    source_engine = create_engine(source_db.connection_string)
                else:
                    # For non-SQL sources, we'll use the data retrieval service
                    from ..retrieval import DataRetrievalService

                    data_service = DataRetrievalService()

                # 4. Read data from source
                query = etl_job.source_query
                log.info("etl_job.source.reading_data")

                if source_db.source_type.value == "sql":
                    df = pd.read_sql(query, source_engine)
                else:
                    # For CSV/API sources, use the data retrieval service
                    from ..retrieval import DataRetrievalService

                    data_service = DataRetrievalService()

                    # Use synchronous data fetching for non-SQL sources
                    if source_db.source_type.value == "csv":
                        if not source_db.file_path:
                            raise ValueError("CSV data source requires file path")
                        df = pd.read_csv(source_db.file_path)
                    elif source_db.source_type.value == "api":
                        # For API sources, we need to handle this differently
                        # For now, we'll skip API sources in ETL jobs
                        raise ValueError(
                            "API data sources not yet supported in ETL jobs"
                        )
                    else:
                        raise ValueError(
                            f"Unsupported data source type: {source_db.source_type}"
                        )

                    # Apply query-like filtering if needed
                    # This is a simplified approach - in production you'd want more sophisticated querying
                    if query and query.strip().upper().startswith("SELECT"):
                        log.warning(
                            "etl_job.source.query_ignored",
                            reason="Query not supported for non-SQL sources",
                        )

                log.info("etl_job.source.data_loaded", row_count=len(df))
                execution_result["rows_processed"] = len(df)

                # 5. Sanitize the loaded data
                df = data_sanitizer.sanitize_dataframe(df)
                log.info("etl_job.source.data_sanitized", row_count=len(df))

                # 6. Execute transformations
                log.info("etl_job.transform.started")
                config = etl_job.transformation_config
                if config and config.get("operations"):
                    engine = ETLTransformationEngine(
                        transformation_config=config, df=df
                    )
                    transformed_df = engine.run()
                    log.info(
                        "etl_job.transform.finished",
                        operation_count=len(config["operations"]),
                        output_rows=len(transformed_df),
                    )
                else:
                    transformed_df = df  # No transformations to apply
                    log.info(
                        "etl_job.transform.skipped", reason="no_operations_defined"
                    )

                execution_result["rows_output"] = len(transformed_df)

                # 7. Write transformed data to destination
                log.info(
                    "etl_job.load.started",
                    table=etl_job.destination_table_name,
                    row_count=len(transformed_df),
                )
                dest_engine = create_engine(settings.DATABASE_URL)
                transformed_df.to_sql(
                    etl_job.destination_table_name,
                    dest_engine,
                    if_exists="replace",
                    index=False,
                )
                log.info("etl_job.load.finished")

                # 8. Update execution result
                execution_result["status"] = ETLJobStatus.SUCCESS
                execution_result["end_time"] = datetime.now().isoformat()

                # Calculate duration
                start_time = datetime.fromisoformat(execution_result["start_time"])
                end_time = datetime.fromisoformat(execution_result["end_time"])
                execution_result["duration_seconds"] = (
                    end_time - start_time
                ).total_seconds()

                log.info(
                    "etl_job.run.completed",
                    duration_seconds=execution_result["duration_seconds"],
                    rows_processed=execution_result["rows_processed"],
                    rows_output=execution_result["rows_output"],
                )

                return execution_result

        except Exception as e:
            log.exception("etl_job.run.failed")
            execution_result["status"] = ETLJobStatus.FAILED
            execution_result["error_message"] = str(e)
            execution_result["end_time"] = datetime.now().isoformat()

            if execution_result["start_time"]:
                start_time = datetime.fromisoformat(execution_result["start_time"])
                end_time = datetime.fromisoformat(execution_result["end_time"])
                execution_result["duration_seconds"] = (
                    end_time - start_time
                ).total_seconds()

            # Re-raise the exception so APScheduler can log it as a job failure
            raise

    async def run_intelligent_etl(
        self,
        instructions: ETLInstructions,
        data_source_id: int,
        task_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        运行智能ETL处理

        Args:
            instructions: ETL指令
            data_source_id: 数据源ID
            task_config: 任务配置

        Returns:
            处理结果
        """
        log = self.logger.bind(
            instruction_id=instructions.instruction_id, data_source_id=data_source_id
        )
        log.info("intelligent_etl.run.started")

        try:
            # 使用智能ETL执行器
            result = await intelligent_etl_executor.execute_etl(
                instructions, data_source_id, task_config
            )

            log.info(
                "intelligent_etl.run.completed",
                processing_time=result.processing_time,
                rows_processed=result.rows_processed,
                confidence=result.confidence,
            )

            return {
                "success": True,
                "instruction_id": instructions.instruction_id,
                "processed_value": result.processed_value,
                "metadata": result.metadata,
                "processing_time": result.processing_time,
                "confidence": result.confidence,
                "query_executed": result.query_executed,
                "rows_processed": result.rows_processed,
            }

        except Exception as e:
            log.exception("intelligent_etl.run.failed")
            return {
                "success": False,
                "instruction_id": instructions.instruction_id,
                "error": str(e),
                "processing_time": 0.0,
                "confidence": 0.0,
            }

    def generate_etl_instructions_from_placeholder(
        self,
        placeholder_info: Dict[str, Any],
        field_mapping: Dict[str, Any],
        data_source_schema: Dict[str, Any],
    ) -> ETLInstructions:
        """
        从占位符信息生成ETL指令

        Args:
            placeholder_info: 占位符信息
            field_mapping: 字段映射结果
            data_source_schema: 数据源结构

        Returns:
            ETL指令
        """
        from app.services.intelligent_etl_executor import (
            AggregationConfig,
            ETLInstructions,
            RegionFilterConfig,
            TimeFilterConfig,
        )

        placeholder_type = placeholder_info.get("placeholder_type", "")
        description = placeholder_info.get("description", "")
        matched_field = field_mapping.get("matched_field", "")

        # 生成指令ID
        instruction_id = f"etl_{hash(placeholder_info.get('placeholder_text', ''))}"

        # 确定查询类型
        if placeholder_type == "统计":
            query_type = "aggregate"
        elif placeholder_type == "图表":
            query_type = "select_for_chart"
        else:
            query_type = "select"

        # 源字段
        source_fields = [matched_field] if matched_field else []

        # 过滤条件
        filters = []

        # 聚合配置
        aggregations = []
        if placeholder_type == "统计":
            # 根据描述确定聚合函数
            if "总数" in description or "合计" in description:
                agg_function = "sum"
            elif "数量" in description or "件数" in description:
                agg_function = "count"
            elif "平均" in description:
                agg_function = "avg"
            else:
                agg_function = "sum"  # 默认

            aggregations.append(
                AggregationConfig(function=agg_function, field=matched_field)
            )

        # 时间配置
        time_config = None
        if placeholder_type == "周期":
            time_config = TimeFilterConfig(
                field="date_field",  # 需要根据实际情况调整
                period="monthly",
                relative_period="this_month",
            )

        # 区域配置
        region_config = None
        if placeholder_type == "区域":
            region_config = RegionFilterConfig(
                field="region_field",  # 需要根据实际情况调整
                region_value=description,
                region_type="contains",
            )

        # 数据转换
        transformations = []
        if field_mapping.get("requires_transformation"):
            transformation_config = field_mapping.get("transformation_config", {})
            transformations.append(
                {
                    "type": transformation_config.get("type", "none"),
                    "field": matched_field,
                    "formula": transformation_config.get("formula"),
                }
            )

        # 输出格式
        if placeholder_type == "统计":
            output_format = "scalar"
        elif placeholder_type == "图表":
            output_format = "json"
        else:
            output_format = "dataframe"

        return ETLInstructions(
            instruction_id=instruction_id,
            query_type=query_type,
            source_fields=source_fields,
            filters=filters,
            aggregations=aggregations,
            transformations=transformations,
            time_config=time_config,
            region_config=region_config,
            output_format=output_format,
            performance_hints=["使用索引优化查询性能", "考虑数据缓存策略"],
        )

    def list_available_tables(self, data_source_id: int) -> Dict[str, Any]:
        """List available tables/data from a data source"""
        with get_db_session() as db:
            source_db = crud.data_source.get(db, id=data_source_id)
            if not source_db:
                raise ValueError("Data source not found")

            try:
                if source_db.source_type.value == "sql":
                    if not source_db.connection_string:
                        raise ValueError("SQL data source requires connection string")

                    validate_connection_string(source_db.connection_string)
                    engine = create_engine(source_db.connection_string)

                    # Get table names
                    query = """
                    SELECT table_name, table_schema 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    ORDER BY table_name
                    """
                    tables_df = pd.read_sql(query, engine)

                    return {
                        "data_source_id": data_source_id,
                        "data_source_type": "sql",
                        "tables": tables_df.to_dict(orient="records"),
                    }

                elif source_db.source_type.value == "csv":
                    # For CSV, return column information
                    if not source_db.file_path:
                        raise ValueError("CSV data source requires file path")

                    df = pd.read_csv(source_db.file_path, nrows=1)
                    return {
                        "data_source_id": data_source_id,
                        "data_source_type": "csv",
                        "columns": df.columns.tolist(),
                        "file_path": source_db.file_path,
                    }

                elif source_db.source_type.value == "api":
                    # For API, return structure information
                    return {
                        "data_source_id": data_source_id,
                        "data_source_type": "api",
                        "api_url": source_db.api_url,
                        "api_method": source_db.api_method,
                        "note": "Use preview endpoint to see data structure",
                    }
                else:
                    raise ValueError(
                        f"Unsupported data source type: {source_db.source_type}"
                    )

            except Exception as e:
                raise ValueError(f"Failed to list tables: {str(e)}")


# Create singleton instance
etl_service = ETLService()
