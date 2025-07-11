from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

from app.services.ai_service import ai_service

router = APIRouter()

class ChartRequest(BaseModel):
    description: str
    data: List[Dict[str, Any]]

class ChartResponse(BaseModel):
    image_base64: str

@router.post("/generate-chart", response_model=ChartResponse)
def generate_chart(request: ChartRequest):
    """
    Receives data and a description, and returns a base64 encoded chart image.
    """
    try:
        image_base64 = ai_service.generate_chart_from_description(
            data=request.data,
            description=request.description
        )
        return {"image_base64": image_base64}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate chart: {e}") 