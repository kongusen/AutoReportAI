from sqlalchemy.orm import Session
from typing import List, Dict, Any
import uuid

from app import crud
from app.services.data_retrieval_service import DataRetrievalService

class ETLService:
    def __init__(self, db: Session):
        self.db = db

    def run_etl(self, data_source_id: int) -> Dict[str, Any]:
        """
        Runs a full ETL (Extract, Transform, Load) process for a given data source.

        1. Fetches the data source configuration.
        2. Uses DataRetrievalService to extract raw data.
        3. Transforms and loads the data into the local AnalyticsData table.
        """
        # 1. Fetch data source
        data_source = crud.data_source.get(self.db, id=data_source_id)
        if not data_source:
            raise ValueError(f"Data source with id {data_source_id} not found.")

        # 2. Extract data
        retrieval_service = DataRetrievalService(db=self.db)
        try:
            raw_data = retrieval_service.fetch_data(data_source_id=data_source_id)
        except Exception as e:
            raise RuntimeError(f"Failed to extract data from source {data_source_id}: {e}")

        # 3. Load data
        records_loaded = 0
        records_failed = 0
        
        # For simplicity, we assume the first column is the unique record_id.
        # In a real-world scenario, this might need to be more sophisticated.
        if not raw_data:
            return {"status": "success", "message": "No data found to load.", "records_loaded": 0, "records_failed": 0}
            
        # Try to infer a unique ID column.
        # This is a basic implementation. A more robust solution might require explicit configuration.
        first_row = raw_data[0]
        id_column_candidates = ['id', 'uuid', 'key', '订单号', '投诉ID']
        record_id_key = next((key for key in id_column_candidates if key in first_row), None)

        if not record_id_key:
            print("Warning: No standard unique ID column found. Using a generated UUID for each record.")

        for row in raw_data:
            try:
                if record_id_key:
                    record_id = str(row[record_id_key])
                else:
                    # If no unique key is found, generate one. This may lead to duplicates on re-runs.
                    record_id = str(uuid.uuid4())

                data_to_create = {
                    "record_id": record_id,
                    "data": row,
                    "data_source_id": data_source_id,
                }
                crud.analytics_data.create(self.db, obj_in=data_to_create)
                records_loaded += 1
            except Exception as e:
                print(f"Failed to load record: {row}. Error: {e}")
                records_failed += 1

        return {
            "status": "success",
            "message": f"ETL process completed for data source {data_source.name}.",
            "records_loaded": records_loaded,
            "records_failed": records_failed,
        } 