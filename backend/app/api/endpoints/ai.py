from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import deps
from app.services.ai_service import AIService

router = APIRouter()


class ChartRequest(BaseModel):
    description: str
    data: List[Dict[str, Any]]


class ChartResponse(BaseModel):
    image_base64: str


def get_ai_service(db: Session = Depends(deps.get_db)) -> AIService:
    return AIService(db)


@router.post("/generate-chart", response_model=ChartResponse)
def generate_chart(
    *, request: ChartRequest, ai_service: AIService = Depends(get_ai_service)
):
    """
    Generates a chart image from data and a description.
    This endpoint is called by other services (like report_generation) via FastMCP.
    """
    image_base64 = ai_service.generate_chart_from_description(
        data=request.data, description=request.description
    )
    return {"image_base64": image_base64}
