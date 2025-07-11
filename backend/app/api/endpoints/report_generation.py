import os
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Any, Dict
from sqlalchemy.orm import Session

from app import crud, schemas
from app.api import deps
from app.services.ai_service import ai_service
from app.services.word_generator_service import word_generator_service

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

def send_email_notification(email: str, report_name: str, file_path: str):
    print(f"BACKGROUND TASK: Sending email to {email} for report {report_name} with attachment {file_path}...")
    # Real email logic (e.g., using smtplib) would go here
    print("Email sent.")

def _get_data_from_source(sql_query: str) -> List[Dict[str, Any]]:
    """ Mock function to simulate fetching data from a business database. """
    print(f"Executing SQL: {sql_query}")
    if "region" in sql_query.lower():
        return [
            {"region": "昆明", "sales": 520000},
            {"region": "大理", "sales": 410000},
            {"region": "丽江", "sales": 630000},
            {"region": "西双版纳", "sales": 350000},
            {"region": "香格里拉", "sales": 280000},
        ]
    elif "total_sales" in sql_query.lower():
        return [{"total": 2190000}]
    return []


@router.post("/generate", response_model=ReportGenerationResponse)
def generate_report(
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

    # 2. Fetch data for all placeholders
    final_data = {}
    for mapping in template.mappings:
        # MOCK DATABASE CALL
        raw_data = _get_data_from_source(mapping.source_logic)
        
        if mapping.placeholder_type in ["chart", "table"]:
            final_data[mapping.placeholder_name] = raw_data
        elif mapping.placeholder_type == "query" and raw_data:
            # For scalar queries, assume the first column of the first row is the value
            final_data[mapping.placeholder_name] = list(raw_data[0].values())[0]

    # 3. Call AI Service for charts
    for mapping in template.mappings:
        if mapping.placeholder_type == "chart":
            chart_data = final_data.get(mapping.placeholder_name)
            if chart_data:
                b64_image = ai_service.generate_chart_from_description(chart_data, mapping.description)
                # Replace data with base64 image for the generator service
                final_data[mapping.placeholder_name] = b64_image
    
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
        for email in request.recipients:
            background_tasks.add_task(send_email_notification, email, request.report_name, output_path)

    return {
        "status": "success",
        "message": "Report generation process started.",
        "report_path": output_path
    }
