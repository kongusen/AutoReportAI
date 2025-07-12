import pandas as pd
import structlog
from sqlalchemy import create_engine

from app import crud, models
from app.core.config import settings
from app.core.security_utils import ConnectionStringError, validate_connection_string
from app.db.session import get_db_session
from app.services.data_sanitization_service import data_sanitizer
from app.services.etl_engine_service import ETLTransformationEngine

logger = structlog.get_logger(__name__)


class ETLService:
    def run_job(self, job_id: str) -> None:
        """
        Runs a specific ETL job using a secure, structured transformation engine.
        This method is designed to be called by the scheduler and manages its own
        database session.
        """
        log = logger.bind(job_id=job_id)
        log.info("etl_job.run.started")
        with get_db_session() as db:
            try:
                # 1. Get ETL Job configuration
                etl_job = crud.etl_job.get(db, id=job_id)
                if not etl_job:
                    log.error("etl_job.run.error", reason="job_not_found")
                    raise ValueError("ETL Job not found")

                log = log.bind(job_name=etl_job.name)

                if not etl_job.enabled:
                    log.warning("etl_job.run.skipped", reason="job_disabled")
                    return

                # 2. Get source database connection details
                source_db = crud.data_source.get(db, id=etl_job.source_data_source_id)
                if not source_db:
                    log.error(
                        "etl_job.run.error",
                        reason="source_db_not_found",
                        source_id=etl_job.source_data_source_id,
                    )
                    raise ValueError("Source data source not found")

                # Validate the connection string before use
                try:
                    validate_connection_string(source_db.connection_string)
                except ConnectionStringError as e:
                    log.error(
                        "etl_job.run.error",
                        reason="invalid_connection_string",
                        error=str(e),
                    )
                    raise ValueError(f"Invalid source connection string: {e}")

                source_engine = create_engine(source_db.connection_string)

                # 3. Read data from source using the predefined query
                query = etl_job.source_query
                if not query:
                    log.error("etl_job.run.error", reason="no_source_query")
                    raise ValueError("ETL Job has no source_query defined.")

                log.info("etl_job.source.reading_data")
                df = pd.read_sql(query, source_engine)
                log.info("etl_job.source.data_loaded", row_count=len(df))

                # Sanitize the loaded data as an early security measure
                df = data_sanitizer.sanitize_dataframe(df)
                log.info("etl_job.source.data_sanitized", row_count=len(df))

                # 4. Execute transformations using the secure engine
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
                    )
                else:
                    transformed_df = df  # No transformations to apply
                    log.info(
                        "etl_job.transform.skipped", reason="no_operations_defined"
                    )

                # 5. Write transformed data to destination
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
            except Exception as e:
                log.exception("etl_job.run.failed")
                # We raise the exception so APScheduler can log it as a job failure.
                raise


etl_service = ETLService()
