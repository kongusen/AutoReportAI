import requests
import os

def trigger_report_generation(template_id: int, report_name: str, recipients: list):
    """
    Makes an API call to the backend to trigger the report generation process.
    """
    backend_url = os.getenv("BACKEND_API_URL", "http://backend:8000/api/v1")
    endpoint = f"{backend_url}/reports/generate"
    
    payload = {
        "template_id": template_id,
        "report_name": report_name,
        "recipients": recipients,
    }
    
    try:
        print(f"SCHEDULER: Triggering report generation for template_id={template_id}")
        response = requests.post(endpoint, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes
        print(f"SCHEDULER: Successfully triggered report generation. Response: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"SCHEDULER: Failed to trigger report generation for template_id={template_id}. Error: {e}")
