#!/bin/bash
TOKEN=$(cat /Users/shan/work/uploads/AutoReportAI/login.json | jq -r '.data.access_token')
curl -s "http://localhost:8000/api/v1/health" -H "Authorization: Bearer $TOKEN" | jq -r '.status // "DOWN"'
