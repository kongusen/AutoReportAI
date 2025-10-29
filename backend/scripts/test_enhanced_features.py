"""
测试增强功能：质量评分和 TF-IDF 检索

验证：
1. EnhancedQualityScorer - 多维度质量评分
2. IntelligentSchemaRetriever - TF-IDF 智能检索
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.infrastructure.agents.quality_scorer import (
    EnhancedQualityScorer,
    QualityScorerConfig,
    QualityDimension,
    create_quality_scorer,
    create_strict_quality_scorer,
    create_lenient_quality_scorer
)

from app.services.infrastructure.agents.intelligent_retriever import (
    IntelligentSchemaRetriever,
    RetrievalConfig,
    create_intelligent_retriever,
    create_tfidf_retriever,
    create_keyword_retriever
)


def print_section(title: str):
    """打印章节标题"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_subsection(title: str):
    """打印子章节标题"""
    print(f"\n--- {title} ---")


def test_quality_scorer():
    """测试质量评分器"""
    print_section("测试 1: 增强的质量评分系统")

    # 创建质量评分器
    scorer = create_quality_scorer()

    # 测试用例 1: 优秀的 SQL
    print_subsection("用例 1: 优秀的 SQL 查询")
    sql1 = """
    SELECT
        order_id,
        customer_id,
        order_date,
        total_amount
    FROM orders
    WHERE order_date >= '2024-01-01'
    ORDER BY order_date DESC
    LIMIT 100
    """

    execution_result1 = {
        "success": True,
        "rows": [{"order_id": i, "customer_id": i * 10, "order_date": "2024-01-01", "total_amount": 100.0} for i in range(50)],
        "row_count": 50,
        "execution_time_ms": 150
    }

    tool_calls1 = [
        type('ToolCall', (), {
            'tool_name': 'schema_retrieval',
            'success': True
        })(),
        type('ToolCall', (), {
            'tool_name': 'sql_validator',
            'success': True
        })(),
        type('ToolCall', (), {
            'tool_name': 'sql_column_checker',
            'success': True
        })()
    ]

    quality_score1 = scorer.calculate_quality_score(
        content=sql1,
        execution_result=execution_result1,
        tool_call_history=tool_calls1
    )

    print(f"✅ 总体评分: {quality_score1.overall_score:.2f} ({quality_score1.grade})")
    print(f"   通过质量阈值: {'是' if quality_score1.passed else '否'}")
    print(f"\n📊 分维度评分:")
    for dimension, dim_score in quality_score1.dimension_scores.items():
        print(f"   {dimension.value:20s}: {dim_score.score:.2f} (权重: {dim_score.weight:.2f})")

    if quality_score1.suggestions:
        print(f"\n💡 改进建议:")
        for suggestion in quality_score1.suggestions[:5]:
            print(f"   - {suggestion}")

    # 测试用例 2: 有问题的 SQL
    print_subsection("用例 2: 有问题的 SQL 查询")
    sql2 = """
    SELECT order_id, customer_id
    FROM orders
    WHERE
    """  # 不完整的 SQL

    execution_result2 = {
        "success": False,
        "error": "SQL syntax error: incomplete WHERE clause"
    }

    tool_calls2 = []

    quality_score2 = scorer.calculate_quality_score(
        content=sql2,
        execution_result=execution_result2,
        tool_call_history=tool_calls2
    )

    print(f"❌ 总体评分: {quality_score2.overall_score:.2f} ({quality_score2.grade})")
    print(f"   通过质量阈值: {'是' if quality_score2.passed else '否'}")
    print(f"\n📊 分维度评分:")
    for dimension, dim_score in quality_score2.dimension_scores.items():
        print(f"   {dimension.value:20s}: {dim_score.score:.2f} (权重: {dim_score.weight:.2f})")

    if quality_score2.suggestions:
        print(f"\n💡 改进建议:")
        for suggestion in quality_score2.suggestions:
            print(f"   - {suggestion}")

    # 测试用例 3: 中等质量的 SQL
    print_subsection("用例 3: 中等质量的 SQL 查询")
    sql3 = """
    SELECT *
    FROM orders
    """

    execution_result3 = {
        "success": True,
        "rows": [{"order_id": i} for i in range(5000)],  # 数据量较大
        "row_count": 5000,
        "execution_time_ms": 3000  # 执行时间较长
    }

    tool_calls3 = [
        type('ToolCall', (), {
            'tool_name': 'sql_executor',
            'success': True
        })()
    ]

    quality_score3 = scorer.calculate_quality_score(
        content=sql3,
        execution_result=execution_result3,
        tool_call_history=tool_calls3
    )

    print(f"⚠️ 总体评分: {quality_score3.overall_score:.2f} ({quality_score3.grade})")
    print(f"   通过质量阈值: {'是' if quality_score3.passed else '否'}")
    print(f"\n📊 分维度评分:")
    for dimension, dim_score in quality_score3.dimension_scores.items():
        print(f"   {dimension.value:20s}: {dim_score.score:.2f} (权重: {dim_score.weight:.2f})")

    if quality_score3.suggestions:
        print(f"\n💡 改进建议:")
        for suggestion in quality_score3.suggestions[:5]:
            print(f"   - {suggestion}")

    # 测试不同配置
    print_subsection("用例 4: 严格评分器 vs 宽松评分器")
    strict_scorer = create_strict_quality_scorer()
    lenient_scorer = create_lenient_quality_scorer()

    strict_score = strict_scorer.calculate_quality_score(sql3, execution_result3, tool_calls3)
    lenient_score = lenient_scorer.calculate_quality_score(sql3, execution_result3, tool_calls3)

    print(f"严格评分器: {strict_score.overall_score:.2f} ({strict_score.grade}) - {'通过' if strict_score.passed else '未通过'}")
    print(f"宽松评分器: {lenient_score.overall_score:.2f} ({lenient_score.grade}) - {'通过' if lenient_score.passed else '未通过'}")

    return True


async def test_intelligent_retriever():
    """测试智能检索器"""
    print_section("测试 2: TF-IDF 智能检索系统")

    # 准备测试数据
    schema_cache = {
        "orders": {
            "table_name": "orders",
            "table_comment": "订单表，存储所有订单信息",
            "columns": [
                {"name": "order_id", "type": "BIGINT", "comment": "订单ID"},
                {"name": "customer_id", "type": "BIGINT", "comment": "客户ID"},
                {"name": "order_date", "type": "DATE", "comment": "订单日期"},
                {"name": "total_amount", "type": "DECIMAL(10,2)", "comment": "订单总金额"},
                {"name": "status", "type": "VARCHAR(20)", "comment": "订单状态"},
            ]
        },
        "customers": {
            "table_name": "customers",
            "table_comment": "客户表，存储客户基本信息",
            "columns": [
                {"name": "customer_id", "type": "BIGINT", "comment": "客户ID"},
                {"name": "customer_name", "type": "VARCHAR(100)", "comment": "客户姓名"},
                {"name": "email", "type": "VARCHAR(100)", "comment": "电子邮箱"},
                {"name": "phone", "type": "VARCHAR(20)", "comment": "联系电话"},
                {"name": "created_at", "type": "DATETIME", "comment": "创建时间"},
            ]
        },
        "products": {
            "table_name": "products",
            "table_comment": "商品表，存储商品信息",
            "columns": [
                {"name": "product_id", "type": "BIGINT", "comment": "商品ID"},
                {"name": "product_name", "type": "VARCHAR(200)", "comment": "商品名称"},
                {"name": "price", "type": "DECIMAL(10,2)", "comment": "商品价格"},
                {"name": "category", "type": "VARCHAR(50)", "comment": "商品类别"},
                {"name": "stock", "type": "INT", "comment": "库存数量"},
            ]
        },
        "order_items": {
            "table_name": "order_items",
            "table_comment": "订单明细表，存储订单中的商品明细",
            "columns": [
                {"name": "order_item_id", "type": "BIGINT", "comment": "订单明细ID"},
                {"name": "order_id", "type": "BIGINT", "comment": "订单ID"},
                {"name": "product_id", "type": "BIGINT", "comment": "商品ID"},
                {"name": "quantity", "type": "INT", "comment": "数量"},
                {"name": "unit_price", "type": "DECIMAL(10,2)", "comment": "单价"},
            ]
        },
        "payments": {
            "table_name": "payments",
            "table_comment": "支付表，存储支付记录",
            "columns": [
                {"name": "payment_id", "type": "BIGINT", "comment": "支付ID"},
                {"name": "order_id", "type": "BIGINT", "comment": "订单ID"},
                {"name": "payment_method", "type": "VARCHAR(50)", "comment": "支付方式"},
                {"name": "amount", "type": "DECIMAL(10,2)", "comment": "支付金额"},
                {"name": "payment_time", "type": "DATETIME", "comment": "支付时间"},
            ]
        }
    }

    # 测试 TF-IDF 检索
    print_subsection("用例 1: TF-IDF 检索")
    tfidf_retriever = create_tfidf_retriever(schema_cache, enable_synonyms=True)
    await tfidf_retriever.initialize()

    # 测试查询 1
    query1 = "查询最近30天的订单总金额"
    print(f"\n查询: {query1}")
    results1 = await tfidf_retriever.retrieve(query1, top_k=3)
    print(f"返回 {len(results1)} 个表:")
    for i, (table_name, score) in enumerate(results1, 1):
        print(f"   {i}. {table_name}: {score:.3f}")

    # 测试查询 2
    query2 = "统计每个用户的购买次数"
    print(f"\n查询: {query2}")
    results2 = await tfidf_retriever.retrieve(query2, top_k=3)
    print(f"返回 {len(results2)} 个表:")
    for i, (table_name, score) in enumerate(results2, 1):
        print(f"   {i}. {table_name}: {score:.3f}")

    # 测试查询 3
    query3 = "查看商品的销售情况和库存"
    print(f"\n查询: {query3}")
    results3 = await tfidf_retriever.retrieve(query3, top_k=3)
    print(f"返回 {len(results3)} 个表:")
    for i, (table_name, score) in enumerate(results3, 1):
        print(f"   {i}. {table_name}: {score:.3f}")

    # 测试关键词检索（对比）
    print_subsection("用例 2: 关键词检索（对比）")
    keyword_retriever = create_keyword_retriever(schema_cache, enable_synonyms=True)
    await keyword_retriever.initialize()

    query4 = "查询订单"
    print(f"\n查询: {query4}")
    tfidf_results = await tfidf_retriever.retrieve(query4, top_k=3)
    keyword_results = await keyword_retriever.retrieve(query4, top_k=3)

    print(f"\nTF-IDF 检索:")
    for i, (table_name, score) in enumerate(tfidf_results, 1):
        print(f"   {i}. {table_name}: {score:.3f}")

    print(f"\n关键词检索:")
    for i, (table_name, score) in enumerate(keyword_results, 1):
        print(f"   {i}. {table_name}: {score:.3f}")

    # 测试同义词扩展
    print_subsection("用例 3: 同义词扩展")
    tfidf_retriever.add_synonym("销售", ["sale", "selling", "sold"])

    query5 = "统计销售额"
    print(f"\n查询: {query5}")
    results5 = await tfidf_retriever.retrieve(query5, top_k=3)
    print(f"返回 {len(results5)} 个表:")
    for i, (table_name, score) in enumerate(results5, 1):
        print(f"   {i}. {table_name}: {score:.3f}")

    # 测试阶段感知
    print_subsection("用例 4: 阶段感知检索")
    query6 = "订单表"
    print(f"\n查询: {query6}")

    print("\n不同阶段的检索结果:")
    for stage in ["schema_discovery", "sql_generation", "sql_validation"]:
        results = await tfidf_retriever.retrieve(query6, top_k=3, stage=stage)
        print(f"\n{stage}:")
        for i, (table_name, score) in enumerate(results, 1):
            print(f"   {i}. {table_name}: {score:.3f}")

    return True


async def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("  🧪 测试增强功能：质量评分和 TF-IDF 检索")
    print("=" * 80)

    # 测试 1: 质量评分
    test1_passed = test_quality_scorer()

    # 测试 2: 智能检索
    test2_passed = await test_intelligent_retriever()

    # 总结
    print_section("测试总结")
    print(f"✅ 质量评分测试: {'通过' if test1_passed else '失败'}")
    print(f"✅ 智能检索测试: {'通过' if test2_passed else '失败'}")

    if test1_passed and test2_passed:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print("\n❌ 部分测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
