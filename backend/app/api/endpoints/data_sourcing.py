from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import deps
from app.services.data_retrieval_service import DataRetrievalService

router = APIRouter()


class DataResponse(BaseModel):
    data: Dict[str, Any]
    error: str = None


@router.post("/fetch-data/", response_model=DataResponse)
def fetch_data(
    data_source_id: int,
    db: Session = Depends(deps.get_db),
):
    retrieval_service = DataRetrievalService(db)
    try:
        data = retrieval_service.get_data(data_source_id)
        return DataResponse(data=data.to_dict())
    except Exception as e:
        return DataResponse(data={}, error=str(e))
