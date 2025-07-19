import re
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.services.ai_integration import EnhancedAIService
from app.services.data_processing import DataAnalysisService
from app.services.tool_dispatcher_service import ToolDispatcherService
from app.schemas.base import APIResponse, create_success_response, create_error_response

router = APIRouter()


def get_ai_service(db: Session = Depends(deps.get_db)) -> EnhancedAIService:
    return EnhancedAIService(db)


class AnalysisRequest(BaseModel):
    placeholder: str = Field(
        ...,
        example="{{count:上月投诉数量}}",
        description="The placeholder string from the template, e.g., {{type:description}}",
    )


class AnalysisResponse(BaseModel):
    placeholder: str
    task_type: str
    description: str
    ai_generated_params: Dict[str, Any]
    result: Dict[str, Any]


class AnalysisStatusResponse(BaseModel):
    message: str


@router.post("/experimental-analysis", response_model=APIResponse[AnalysisResponse])
def run_experimental_analysis(
    *,
    db: Session = Depends(deps.get_db),
    ai_service: EnhancedAIService = Depends(get_ai_service),
    request: AnalysisRequest,
) -> Any:
    """
    An experimental endpoint to test the AI-driven tool dispatcher pipeline.

    This simulates the full AI orchestrator workflow:
    1. Parses a `{{type:description}}` placeholder.
    2. **Uses a real AI** to interpret the `description` and create tool parameters.
    3. Uses the `ToolDispatcherService` to execute the task.
    """
    # 1. Parse the placeholder
    match = re.match(r"\{\{(\w+):(.+)\}\}", request.placeholder)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid placeholder format. Expected '{{type:description}}'.",
        )

    task_type, description = match.groups()

    # 2. **AI-Powered Parameter Generation**
    # The AI service interprets the description to generate tool parameters.
    try:
        params = ai_service.interpret_description_for_tool(
            task_type=task_type, description=description
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"AI parameter generation failed: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during AI processing: {str(e)}",
        )

    # 3. Dispatch the task using the Tool Dispatcher
    try:
        dispatcher = ToolDispatcherService(db=db)
        result = dispatcher.dispatch(task_type=task_type, params=params)

        analysis_result = AnalysisResponse(
            placeholder=request.placeholder,
            task_type=task_type,
            description=description,
            ai_generated_params=params,
            result=result,
        )
        
        return APIResponse[AnalysisResponse](
            success=True,
            message="实验性分析完成",
            data=analysis_result
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        )


@router.post("/run-analysis/{data_source_id}", response_model=APIResponse[AnalysisStatusResponse])
def run_analysis(
    data_source_id: int,
    db: Session = Depends(deps.get_db),
):
    try:
        analysis_service = DataAnalysisService(db)
        # For simplicity, returning a success message.
        # In a real-world scenario, you might return some analysis results.
        status_result = AnalysisStatusResponse(
            message=f"Analysis started for data source {data_source_id}"
        )
        return APIResponse[AnalysisStatusResponse](
            success=True,
            message="数据分析任务已启动",
            data=status_result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
