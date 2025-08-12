
import requests
import time
import os
import json

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "admin"
PASSWORD = "password"

def get_token():
    login_data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    if response.status_code == 200:
        token_data = response.json()
        return token_data["data"]["access_token"]
    else:
        print(f"Failed to get token: {response.status_code} - {response.text}")
        return None

TOKEN = get_token()
if not TOKEN:
    print("Could not obtain authentication token")
    exit(1)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Use existing IDs from the query results
DATA_SOURCE_ID = "5f848786-bb94-4ec0-b2f7-fda8d84a820e"  # Test Doris for Intelligent WF
TEMPLATE_ID = "1ee49d77-a172-4c1a-ad51-d760b3642f9e"  # 投诉数据分析报告 (正确ID)

def create_data_source():
    print("Attempting to find or create a test Doris data source...")
    ds_name = "Test Doris for Intelligent WF"
    
    # First, try to find by name
    response = requests.get(f"{BASE_URL}/data-sources/", headers=HEADERS, params={"search": ds_name})
    if response.status_code == 200:
        sources = response.json().get("data", {}).get("items", [])
        if sources:
            source_id = sources[0]['id']
            print(f"Found existing data source. ID: {source_id}")
            return source_id

    print("Existing data source not found. Creating a new one...")
    ds_data = {
        "name": ds_name,
        "source_type": "doris",
        "doris_fe_hosts": ["192.168.61.30"],
        "doris_username": "root",
        "doris_password": "yjg@123456",
        "doris_database": "yjg",
        "is_active": True
    }
    response = requests.post(f"{BASE_URL}/data-sources/", headers=HEADERS, json=ds_data)
    
    if response.status_code == 201:
        data_source = response.json()
        ds_id = data_source.get('id')
        if ds_id:
            print(f"Data source created successfully. ID: {ds_id}")
            return ds_id

    # If creation failed, maybe it was created in a race condition or the error message was unexpected.
    # Let's try to find it again.
    print(f"Creation might have failed or returned an unexpected status ({response.status_code}). Retrying find...")
    response_find = requests.get(f"{BASE_URL}/data-sources/", headers=HEADERS, params={"search": ds_name})
    if response_find.status_code == 200:
        sources = response_find.json().get("data", {}).get("items", [])
        if sources:
            source_id = sources[0]['id']
            print(f"Found existing data source on second attempt. ID: {source_id}")
            return source_id

    print(f"Could not find or create the data source. Final create response: {response.status_code} - {response.text}")
    return None

def create_template():
    print("Attempting to find or create a test template...")
    template_name = "Intelligent Workflow Test Template"

    # First, try to find by name
    response = requests.get(f"{BASE_URL}/templates/", headers=HEADERS, params={"search": template_name})
    if response.status_code == 200:
        templates = response.json().get("data", {}).get("items", [])
        if templates:
            template_id = templates[0]['id']
            print(f"Found existing template. ID: {template_id}")
            return template_id

    print("Existing template not found. Creating a new one...")
    template_data = {
        "name": template_name,
        "content": "Report for {{customer_name}}. Total sales: {{total_sales}}. Sales by region: {{sales_by_region_table}}",
        "is_public": True,
    }
    response = requests.post(f"{BASE_URL}/templates/", headers=HEADERS, json=template_data)
    if response.status_code == 201:
        template = response.json()
        template_id = template.get('id')
        if template_id:
            print(f"Template created successfully. ID: {template_id}")
            return template_id

    # If creation failed, maybe it was created in a race condition or the error message was unexpected.
    # Let's try to find it again.
    print(f"Creation might have failed or returned an unexpected status ({response.status_code}). Retrying find...")
    response_find = requests.get(f"{BASE_URL}/templates/", headers=HEADERS, params={"search": template_name})
    if response_find.status_code == 200:
        templates = response_find.json().get("data", {}).get("items", [])
        if templates:
            template_id = templates[0]['id']
            print(f"Found existing template on second attempt. ID: {template_id}")
            return template_id

    print(f"Could not find or create the template. Final create response: {response.status_code} - {response.text}")
    return None

def create_task(template_id, data_source_id):
    print("Step 1: Creating a new task...")
    task_data = {
        "name": f"Intelligent Placeholder Test Task - {time.time()}",
        "description": "A test task for the intelligent placeholder workflow.",
        "template_id": template_id,
        "data_source_id": data_source_id,
        "is_active": True
    }
    response = requests.post(f"{BASE_URL}/tasks/", headers=HEADERS, json=task_data)
    if response.status_code == 200:
        result = response.json()
        if result.get('success') and result.get('data'):
            task = result['data']
            print(f"Task created successfully. Task ID: {task['id']}")
            return task['id']
        else:
            print(f"Unexpected response format: {result}")
            return None
    else:
        print(f"Failed to create task. Status: {response.status_code}, Response: {response.text}")
        return None

def execute_intelligent_task(task_id):
    print(f"Step 2: Executing task {task_id} with intelligent placeholders...")
    response = requests.post(f"{BASE_URL}/tasks/{task_id}/execute?use_intelligent_placeholders=true", headers=HEADERS)
    if response.status_code == 200:
        result = response.json().get('data')
        print("Task execution started successfully.")
        print(f"  Celery Task ID: {result.get('celery_task_id')}")
        print(f"  Processing Mode: {result.get('processing_mode')}")
        return True
    else:
        print(f"Failed to execute task. Status: {response.status_code}, Response: {response.text}")
        return False

def check_task_status(task_id):
    print(f"Step 3: Checking status for task {task_id}...")
    while True:
        response = requests.get(f"{BASE_URL}/tasks/{task_id}/status", headers=HEADERS)
        if response.status_code == 200:
            status_data = response.json().get('data', {})
            status = status_data.get('status')
            progress = status_data.get('progress')
            message = status_data.get('message')
            print(f"  Status: {status}, Progress: {progress}%, Message: {message}")
            if status in ['completed', 'failed']:
                if status == 'completed':
                    print("Task completed successfully!")
                    print("Final report path:", status_data.get('report_path'))
                else:
                    print("Task failed.")
                    print("Error details:", status_data)
                break
        else:
            print(f"Failed to get task status. Status: {response.status_code}, Response: {response.text}")
            break
        time.sleep(5)

def main():
    print("Starting intelligent task workflow test...")
    print(f"Using existing data source ID: {DATA_SOURCE_ID}")
    print(f"Using existing template ID: {TEMPLATE_ID}")
    
    task_id = create_task(TEMPLATE_ID, DATA_SOURCE_ID)
    if task_id:
        if execute_intelligent_task(task_id):
            check_task_status(task_id)

if __name__ == "__main__":
    main()
