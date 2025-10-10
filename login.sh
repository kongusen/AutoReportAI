#!/bin/bash
curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=password" | tee /Users/shan/work/uploads/AutoReportAI/login.json
