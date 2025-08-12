#!/usr/bin/env python3
"""
简单检查任务状态
"""

import requests
import json

# 检查所有已知的任务ID
task_ids = [
    "3365581a-0af9-4b68-b925-3b46a096cd23",  # 最新的
    "e349c527-0c09-4c4d-a066-58fc4cdd944c",  # 之前的
    "535b643b-1c57-4063-996a-064250f0b750",  # 更早的
]

AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTQ5NjgzNzQsInN1YiI6IjJmZjkzNmY3LTg4YWItNDVhYS1hMDU2LTIyOWQ5YTFjNjcxZCJ9.Ah2EplbqNxyhPr_nRkq9fPfZQfs0Fjsl7djsvbZ06Vw"

for task_id in task_ids:
    try:
        response = requests.get(
            f"http://localhost:8000/api/v1/intelligent-placeholders/task/{task_id}/status",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            task_data = data.get("data", {})
            status = task_data.get("status", "unknown")
            result = task_data.get("result")
            
            print(f"Task {task_id}: {status}")
            if result:
                print(f"  - Has result: {type(result)}")
                if isinstance(result, dict):
                    if 'generated_content' in result:
                        content = result['generated_content']
                        print(f"  - Generated content: {content[:100]}...")
                    if 'placeholder_data' in result:
                        placeholder_data = result['placeholder_data']
                        print(f"  - Placeholder data: {placeholder_data}")
            else:
                print(f"  - No result available")
        else:
            print(f"Task {task_id}: Error {response.status_code}")
            
    except Exception as e:
        print(f"Task {task_id}: Exception {e}")
    
    print()