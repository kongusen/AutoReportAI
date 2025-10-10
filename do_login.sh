#!/bin/bash

cat > /tmp/login_payload.json <<'EOF'
{
  "username": "admin",
  "password": "admin123"
}
EOF

curl -s -X POST 'http://localhost:8000/api/v1/auth/login' \
  -H 'Content-Type: application/json' \
  -d @/tmp/login_payload.json > /Users/shan/work/uploads/AutoReportAI/login.json

cat /Users/shan/work/uploads/AutoReportAI/login.json | jq '.'
