#!/bin/bash
# Agent架构精简 - 清理冗余文件脚本
# 运行前请确保已备份代码: git commit -m "backup: 重构前备份"

set -e  # 遇到错误立即退出

AGENTS_DIR="app/services/infrastructure/agents"

echo "🗑️  开始清理Agent架构冗余代码..."
echo ""

# 检查是否在backend目录
if [ ! -d "$AGENTS_DIR" ]; then
    echo "❌ 错误: 请在backend目录下运行此脚本"
    exit 1
fi

# 统计删除前的文件数
BEFORE_COUNT=$(find $AGENTS_DIR -type f -name "*.py" | wc -l | tr -d ' ')
echo "📊 删除前: $BEFORE_COUNT 个Python文件"
echo ""

# 1. 删除未集成的SQL生成组件
echo "1️⃣  删除未集成的SQL生成组件..."
if [ -d "$AGENTS_DIR/sql_generation" ]; then
    rm -rf "$AGENTS_DIR/sql_generation/"
    echo "   ✅ 删除 sql_generation/ 目录（5个文件）"
else
    echo "   ⚠️  sql_generation/ 目录不存在，跳过"
fi
echo ""

# 2. 删除适配器层
echo "2️⃣  删除适配器层..."
ADAPTERS=(
    "ai_content_adapter.py"
    "ai_sql_repair_adapter.py"
    "chart_rendering_adapter.py"
    "sql_execution_adapter.py"
    "sql_generation_adapter.py"
    "schema_discovery_adapter.py"
)

ADAPTER_COUNT=0
for adapter in "${ADAPTERS[@]}"; do
    if [ -f "$AGENTS_DIR/$adapter" ]; then
        rm "$AGENTS_DIR/$adapter"
        echo "   ✅ 删除 $adapter"
        ((ADAPTER_COUNT++))
    fi
done
echo "   📊 共删除 $ADAPTER_COUNT 个适配器文件"
echo ""

# 3. 删除生产集成重复实现
echo "3️⃣  删除生产集成重复实现..."
PRODUCTION_FILES=(
    "production_auth_provider.py"
    "production_config_provider.py"
    "production_integration_service.py"
)

PROD_COUNT=0
for prod_file in "${PRODUCTION_FILES[@]}"; do
    if [ -f "$AGENTS_DIR/$prod_file" ]; then
        rm "$AGENTS_DIR/$prod_file"
        echo "   ✅ 删除 $prod_file"
        ((PROD_COUNT++))
    fi
done
echo "   📊 共删除 $PROD_COUNT 个生产集成文件"
echo ""

# 4. 删除示例和实验性代码
echo "4️⃣  删除示例和实验性代码..."
EXAMPLE_FILES=(
    "integration_examples.py"
    "agents_context_adapter.py"
)

EXAMPLE_COUNT=0
for example_file in "${EXAMPLE_FILES[@]}"; do
    if [ -f "$AGENTS_DIR/$example_file" ]; then
        rm "$AGENTS_DIR/$example_file"
        echo "   ✅ 删除 $example_file"
        ((EXAMPLE_COUNT++))
    fi
done
echo "   📊 共删除 $EXAMPLE_COUNT 个示例文件"
echo ""

# 5. 清理executor.py中的未使用导入
echo "5️⃣  清理executor.py中的未使用代码..."
EXECUTOR_FILE="$AGENTS_DIR/executor.py"
if [ -f "$EXECUTOR_FILE" ]; then
    # 创建备份
    cp "$EXECUTOR_FILE" "$EXECUTOR_FILE.bak"

    # 删除SQLGenerationCoordinator相关导入和方法
    # 注意：这是一个简化的sed命令，实际可能需要手动清理
    echo "   ⚠️  请手动清理executor.py中的以下内容："
    echo "      - from .sql_generation import ..."
    echo "      - def _get_sql_coordinator()..."
    echo "      - def _should_use_sql_coordinator()..."
    echo "      - def _generate_sql_with_coordinator()..."
    echo "   💾 已创建备份: executor.py.bak"
else
    echo "   ⚠️  executor.py 不存在"
fi
echo ""

# 统计删除后的文件数
AFTER_COUNT=$(find $AGENTS_DIR -type f -name "*.py" | wc -l | tr -d ' ')
DELETED_COUNT=$((BEFORE_COUNT - AFTER_COUNT))
REDUCTION_PERCENT=$(awk "BEGIN {printf \"%.1f\", ($DELETED_COUNT/$BEFORE_COUNT)*100}")

echo "🎉 清理完成！"
echo ""
echo "📊 统计信息:"
echo "   - 删除前: $BEFORE_COUNT 个文件"
echo "   - 删除后: $AFTER_COUNT 个文件"
echo "   - 共删除: $DELETED_COUNT 个文件"
echo "   - 减少比例: $REDUCTION_PERCENT%"
echo ""
echo "⚠️  重要提醒:"
echo "   1. 请运行测试确保没有破坏现有功能: pytest app/tests/ -v"
echo "   2. 请手动清理executor.py中的未使用代码"
echo "   3. 如有问题，可从备份恢复: git reset --hard"
echo ""
