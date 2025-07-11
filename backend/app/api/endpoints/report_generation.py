import os
# No longer need requests here!
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Any, Dict
from sqlalchemy.orm import Session
import pandas as pd
from pathlib import Path

from app import crud, schemas
from app.api import deps
from app.services.word_generator_service import word_generator_service
from app.services.data_retrieval_service import data_retrieval_service
from app.services.mcp_client import mcp_client  # Import our new client
from app.services.email_service import email_service

router = APIRouter()
REPORTS_DIR = "generated_reports"

class ReportGenerationRequest(BaseModel):
    template_id: int
    report_name: str
    recipients: List[str] = []

class ReportGenerationResponse(BaseModel):
    status: str
    message: str
    report_path: str = None

def get_computation_service() -> ComputationService:
    return ComputationService()

def send_email_notification(recipients: List[str], report_name: str, file_path: str):
    """Background task to send an email notification with the report."""
    subject = f"自动化报告已生成: {report_name}"
    body = f"您好，\n\n附件中是您订阅的最新报告 '{report_name}'。\n\n此邮件由AutoReportAI系统自动发出，请勿回复。"
    email_service.send_email(
        recipients=recipients,
        subject=subject,
        body=body,
        attachment_path=Path(file_path),
    )

# The _get_data_from_source function is now obsolete and removed.

# The messy _call_ai_chart_service function is now gone.


@router.post("/generate", response_model=ReportGenerationResponse)
async def generate_report(
    *,
    db: Session = Depends(deps.get_db),
    request: ReportGenerationRequest,
    background_tasks: BackgroundTasks
):
    """
    Orchestrates the end-to-end report generation process.
    """
    # 1. Fetch Template and Mappings
    template = crud.template.get(db=db, id=request.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # 2. Process all mappings to fetch data and prepare for generation
    final_data: Dict[str, Any] = {}
    
    for mapping in template.mappings:
        if not mapping.data_source:
            final_data[mapping.placeholder_name] = f"[No data source linked for: {mapping.placeholder_name}]"
            continue

        df = await data_retrieval_service.fetch_data(mapping.data_source)
        if df.empty:
            final_data[mapping.placeholder_name] = f"[Data not found for: {mapping.placeholder_name}]"
            continue

        # Process based on the placeholder type
        if mapping.placeholder_type == "text":
            final_data[mapping.placeholder_name] = df.iloc[0, 0]
        
        elif mapping.placeholder_type in ["chart", "table"]:
            final_data[mapping.placeholder_name] = df.to_dict(orient='records')
        
        # This part is removed as computation should be a data source type
        # elif mapping.placeholder_type == "computed":
        #     ...

        else:
            final_data[mapping.placeholder_name] = "[Unsupported placeholder type]"

    # 3. Handle AI-driven Chart Generation
    chart_mappings = [m for m in template.mappings if m.placeholder_type == "chart"]
    for mapping in chart_mappings:
        chart_data_list = final_data.get(mapping.placeholder_name)
        if isinstance(chart_data_list, list):
            # The AI service expects a list of dicts
            response = mcp_client.post(
                service_name="ai_service",
                endpoint="/generate-chart",
                payload={"description": mapping.placeholder_description, "data": chart_data_list}
            )
            
            if response and response.get("image_base64"):
                final_data[mapping.placeholder_name] = response["image_base64"]
            else:
                final_data[mapping.placeholder_name] = "[AI chart generation failed]"
    
    # 4. Generate Word Document
    os.makedirs(REPORTS_DIR, exist_ok=True)
    output_path = os.path.join(REPORTS_DIR, f"{request.report_name}.docx")
    
    word_generator_service.generate_report(
        template_path=template.file_path,
        output_path=output_path,
        data=final_data
    )

    # 5. Send Email in Background
    if request.recipients:
        background_tasks.add_task(send_email_notification, request.recipients, request.report_name, output_path)

    return {
        "status": "success",
        "message": "Report generation process started.",
        "report_path": output_path
    }
