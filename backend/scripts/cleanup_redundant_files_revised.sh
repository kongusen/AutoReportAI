#!/bin/bash
# Agent架构精简 - 修正后的清理脚本
# 运行前请确保已备份代码: git commit -m "backup: 重构前备份"

set -e  # 遇到错误立即退出

AGENTS_DIR="app/services/infrastructure/agents"

echo "🗑️  开始清理Agent架构冗余代码（修正版）..."
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
    FILE_COUNT=$(find "$AGENTS_DIR/sql_generation" -type f -name "*.py" | wc -l | tr -d ' ')
    rm -rf "$AGENTS_DIR/sql_generation/"
    echo "   ✅ 删除 sql_generation/ 目录（$FILE_COUNT 个文件）"
else
    echo "   ⚠️  sql_generation/ 目录不存在，跳过"
fi
echo ""

# 2. 删除未使用的生产集成文件（保留production_config_provider.py）
echo "2️⃣  删除未使用的生产集成文件..."
PRODUCTION_FILES=(
    "production_auth_provider.py"
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
echo "   📊 共删除 $PROD_COUNT 个未使用的生产集成文件"
echo "   ℹ️  保留 production_config_provider.py（被llm_strategy_manager.py使用）"
echo ""

# 3. 删除示例和实验性代码
echo "3️⃣  删除示例和实验性代码..."
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

# 4. 提醒手动清理executor.py
echo "4️⃣  清理executor.py中的未使用代码..."
EXECUTOR_FILE="$AGENTS_DIR/executor.py"
if [ -f "$EXECUTOR_FILE" ]; then
    # 创建备份
    cp "$EXECUTOR_FILE" "$EXECUTOR_FILE.bak"
    echo "   💾 已创建备份: executor.py.bak"
    echo "   ⚠️  请手动清理executor.py中的以下内容："
    echo ""
    echo "      第18行 - 删除导入:"
    echo "      ❌ from .sql_generation import SQLGenerationCoordinator, SQLGenerationConfig"
    echo ""
    echo "      第37-38行 - 删除初始化:"
    echo "      ❌ self._sql_generation_config = SQLGenerationConfig()"
    echo "      ❌ self._sql_coordinator: Optional[SQLGenerationCoordinator] = None"
    echo ""
    echo "      删除以下方法:"
    echo "      ❌ def _get_sql_coordinator()..."
    echo "      ❌ def _should_use_sql_coordinator()..."
    echo "      ❌ def _generate_sql_with_coordinator()..."
    echo ""
else
    echo "   ⚠️  executor.py 不存在"
fi
echo ""

# 5. 确认适配器文件未被删除
echo "5️⃣  验证核心适配器文件完整性..."
REQUIRED_ADAPTERS=(
    "adapters/ai_content_adapter.py"
    "adapters/ai_sql_repair_adapter.py"
    "adapters/chart_rendering_adapter.py"
    "adapters/schema_discovery_adapter.py"
    "adapters/sql_execution_adapter.py"
    "adapters/sql_generation_adapter.py"
)

ALL_ADAPTERS_EXIST=true
for adapter in "${REQUIRED_ADAPTERS[@]}"; do
    if [ -f "$AGENTS_DIR/$adapter" ]; then
        echo "   ✅ $adapter 存在"
    else
        echo "   ❌ $adapter 不存在（错误！）"
        ALL_ADAPTERS_EXIST=false
    fi
done

if [ "$ALL_ADAPTERS_EXIST" = true ]; then
    echo "   ✅ 所有核心适配器完整"
else
    echo "   ❌ 部分适配器缺失，请检查！"
fi
echo ""

# 6. 确认production_config_provider.py未被删除
echo "6️⃣  验证生产配置文件..."
if [ -f "$AGENTS_DIR/production_config_provider.py" ]; then
    echo "   ✅ production_config_provider.py 存在（正确）"
else
    echo "   ❌ production_config_provider.py 不存在（错误！）"
fi
echo ""

# 统计删除后的文件数
AFTER_COUNT=$(find $AGENTS_DIR -type f -name "*.py" | wc -l | tr -d ' ')
DELETED_COUNT=$((BEFORE_COUNT - AFTER_COUNT))

if [ $BEFORE_COUNT -gt 0 ]; then
    REDUCTION_PERCENT=$(awk "BEGIN {printf \"%.1f\", ($DELETED_COUNT/$BEFORE_COUNT)*100}")
else
    REDUCTION_PERCENT="0.0"
fi

echo "🎉 清理完成！"
echo ""
echo "📊 统计信息:"
echo "   - 删除前: $BEFORE_COUNT 个文件"
echo "   - 删除后: $AFTER_COUNT 个文件"
echo "   - 共删除: $DELETED_COUNT 个文件"
echo "   - 减少比例: $REDUCTION_PERCENT%"
echo ""
echo "⚠️  重要提醒:"
echo "   1. 请手动清理executor.py中的sql_generation相关代码"
echo "   2. 运行测试: pytest app/tests/ -v -k \"placeholder\" --tb=short"
echo "   3. 检查导入: python -c \"from app.services.infrastructure.agents import facade; print('✅')\""
echo "   4. 如有问题，从备份恢复: git reset --hard HEAD~1"
echo ""
echo "✅ 已保留的核心组件:"
echo "   - adapters/ 目录（6个适配器文件）"
echo "   - production_config_provider.py"
echo "   - facade.py, orchestrator.py, executor.py等核心组件"
echo ""
