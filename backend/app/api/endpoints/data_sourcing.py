from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any

from app.db.session import get_db
from app.services.etl_service import ETLService

router = APIRouter()

def get_etl_service(db: Session = Depends(get_db)) -> ETLService:
    return ETLService(db)

@router.post("/run-etl/{data_source_id}", response_model=dict, status_code=status.HTTP_200_OK)
def run_etl_for_data_source(
    data_source_id: int,
    etl_service: ETLService = Depends(get_etl_service),
) -> Any:
    """
    Manually trigger the ETL process for a specific data source.
    This will extract data from the source and load it into the local analytics table.
    """
    try:
        result = etl_service.run_etl(data_source_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during the ETL process: {str(e)}",
        )
