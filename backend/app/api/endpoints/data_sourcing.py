from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.services.data_retrieval_service import DataRetrievalService

router = APIRouter()


@router.post("/fetch-data/")
def fetch_data(
    data_source_id: int,
    db: Session = Depends(deps.get_db),
):
    retrieval_service = DataRetrievalService(db)
    try:
        data = retrieval_service.get_data(data_source_id)
        return {"data": data.to_dict()}
    except Exception as e:
        return {"error": str(e)}
