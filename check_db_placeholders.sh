#!/bin/bash

TOKEN=$(cat /Users/shan/work/uploads/AutoReportAI/login.json | jq -r '.data.access_token')
TEMPLATE_ID="d531f144-36d1-4aac-9ba4-5b188e6744c8"

echo "========================================="
echo "检查数据库中的占位符数据"
echo "Template ID: $TEMPLATE_ID"
echo "========================================="
echo ""

# 查询占位符
echo "调用 GET /placeholders/?template_id=$TEMPLATE_ID"
RESULT=$(curl -s "http://localhost:8000/api/v1/placeholders/?template_id=$TEMPLATE_ID" \
  -H "Authorization: Bearer $TOKEN")

echo "完整响应:"
echo "$RESULT" | jq '.'
echo ""

# 统计
COUNT=$(echo "$RESULT" | jq '.data | length')
echo "返回的占位符数量: $COUNT"

if [ "$COUNT" -gt 0 ]; then
  echo ""
  echo "占位符列表 (前5个):"
  echo "$RESULT" | jq '.data[:5] | .[] | {id, name: .placeholder_name, has_sql: (.generated_sql != null and .generated_sql != "")}'
else
  echo ""
  echo "❌ 数据库中没有该模板的占位符记录"
  echo "可能的原因:"
  echo "1. 分析时保存失败"
  echo "2. template_id不匹配"
  echo "3. 数据库事务未提交"
fi
