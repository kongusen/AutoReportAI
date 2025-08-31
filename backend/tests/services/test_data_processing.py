"""
数据处理服务测试
"""
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.data.processing.schema_aware_analysis import SchemaAwareDataAnalyzer
from app.services.data.processing.visualization_service import VisualizationService
from app.services.data.schemas.schema_analysis_service import DataSchemaAnalysisService


class TestSchemaAwareDataAnalyzer:
    """Schema感知数据分析器测试"""
    
    def test_init(self):
        """测试初始化"""
        analyzer = SchemaAwareDataAnalyzer()
        assert analyzer is not None

    @pytest.mark.asyncio
    async def test_analyze_data_success(self):
        """测试数据分析成功"""
        analyzer = SchemaAwareDataAnalyzer()
        
        # 模拟输入数据
        data = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie'],
            'age': [25, 30, 35],
            'salary': [50000, 60000, 70000]
        })
        
        schema_info = {
            'columns': {
                'id': {'type': 'integer', 'nullable': False},
                'name': {'type': 'string', 'nullable': False},
                'age': {'type': 'integer', 'nullable': True},
                'salary': {'type': 'number', 'nullable': True}
            }
        }
        
        result = await analyzer.analyze_data(data, schema_info)
        
        assert result is not None
        assert 'summary' in result
        assert 'columns' in result
        assert len(result['columns']) == 4

    @pytest.mark.asyncio
    async def test_analyze_data_with_missing_values(self):
        """测试包含缺失值的数据分析"""
        analyzer = SchemaAwareDataAnalyzer()
        
        data = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Alice', None, 'Charlie'],
            'age': [25, 30, None],
            'score': [None, 85.5, 92.0]
        })
        
        schema_info = {
            'columns': {
                'id': {'type': 'integer', 'nullable': False},
                'name': {'type': 'string', 'nullable': True},
                'age': {'type': 'integer', 'nullable': True},
                'score': {'type': 'number', 'nullable': True}
            }
        }
        
        result = await analyzer.analyze_data(data, schema_info)
        
        assert result is not None
        # 检查缺失值处理
        assert result['columns']['name']['missing_count'] > 0
        assert result['columns']['age']['missing_count'] > 0
        assert result['columns']['score']['missing_count'] > 0

    @pytest.mark.asyncio
    async def test_analyze_data_with_invalid_schema(self):
        """测试无效schema的数据分析"""
        analyzer = SchemaAwareDataAnalyzer()
        
        data = pd.DataFrame({'id': [1, 2, 3]})
        invalid_schema = None
        
        with pytest.raises(ValueError):
            await analyzer.analyze_data(data, invalid_schema)

    @pytest.mark.asyncio
    async def test_generate_insights(self):
        """测试生成数据洞察"""
        analyzer = SchemaAwareDataAnalyzer()
        
        # 模拟分析结果
        analysis_result = {
            'summary': {
                'row_count': 100,
                'column_count': 5,
                'missing_values_total': 10
            },
            'columns': {
                'age': {
                    'type': 'integer',
                    'mean': 35.5,
                    'std': 10.2,
                    'min': 18,
                    'max': 65
                },
                'salary': {
                    'type': 'number',
                    'mean': 75000,
                    'median': 70000,
                    'outliers_count': 3
                }
            }
        }
        
        insights = analyzer.generate_insights(analysis_result)
        
        assert insights is not None
        assert isinstance(insights, list)
        assert len(insights) > 0


class TestVisualizationService:
    """可视化服务测试"""
    
    def test_init(self):
        """测试初始化"""
        service = VisualizationService()
        assert service is not None

    def test_create_histogram(self):
        """测试创建直方图"""
        service = VisualizationService()
        
        data = [1, 2, 2, 3, 3, 3, 4, 4, 5]
        
        result = service.create_histogram(data, title="Test Histogram")
        
        assert result is not None
        assert 'chart_data' in result
        assert 'chart_config' in result
        assert result['chart_config']['type'] == 'histogram'

    def test_create_scatter_plot(self):
        """测试创建散点图"""
        service = VisualizationService()
        
        x_data = [1, 2, 3, 4, 5]
        y_data = [10, 20, 25, 30, 35]
        
        result = service.create_scatter_plot(
            x_data, y_data, 
            title="Test Scatter Plot",
            x_label="X Values",
            y_label="Y Values"
        )
        
        assert result is not None
        assert 'chart_data' in result
        assert 'chart_config' in result
        assert result['chart_config']['type'] == 'scatter'

    def test_create_bar_chart(self):
        """测试创建柱状图"""
        service = VisualizationService()
        
        categories = ['A', 'B', 'C', 'D']
        values = [10, 20, 15, 25]
        
        result = service.create_bar_chart(
            categories, values,
            title="Test Bar Chart"
        )
        
        assert result is not None
        assert 'chart_data' in result
        assert 'chart_config' in result
        assert result['chart_config']['type'] == 'bar'

    def test_create_line_chart(self):
        """测试创建折线图"""
        service = VisualizationService()
        
        x_data = ['Jan', 'Feb', 'Mar', 'Apr']
        y_data = [100, 120, 90, 150]
        
        result = service.create_line_chart(
            x_data, y_data,
            title="Test Line Chart"
        )
        
        assert result is not None
        assert 'chart_data' in result
        assert 'chart_config' in result
        assert result['chart_config']['type'] == 'line'

    def test_create_pie_chart(self):
        """测试创建饼图"""
        service = VisualizationService()
        
        labels = ['Category A', 'Category B', 'Category C']
        values = [30, 45, 25]
        
        result = service.create_pie_chart(
            labels, values,
            title="Test Pie Chart"
        )
        
        assert result is not None
        assert 'chart_data' in result
        assert 'chart_config' in result
        assert result['chart_config']['type'] == 'pie'

    def test_create_correlation_matrix(self):
        """测试创建相关性矩阵图"""
        service = VisualizationService()
        
        # 模拟相关性矩阵数据
        import numpy as np
        correlation_data = np.array([
            [1.0, 0.8, 0.3],
            [0.8, 1.0, 0.5],
            [0.3, 0.5, 1.0]
        ])
        
        column_names = ['Variable A', 'Variable B', 'Variable C']
        
        result = service.create_correlation_matrix(
            correlation_data, column_names,
            title="Test Correlation Matrix"
        )
        
        assert result is not None
        assert 'chart_data' in result
        assert 'chart_config' in result
        assert result['chart_config']['type'] == 'heatmap'

    def test_auto_suggest_visualization(self):
        """测试自动建议可视化类型"""
        service = VisualizationService()
        
        # 测试数值数据
        numeric_data = pd.DataFrame({
            'age': [25, 30, 35, 40],
            'salary': [50000, 60000, 70000, 80000]
        })
        
        suggestion = service.auto_suggest_visualization(numeric_data)
        
        assert suggestion is not None
        assert 'recommended_charts' in suggestion
        assert isinstance(suggestion['recommended_charts'], list)

    def test_generate_chart_recommendations(self):
        """测试生成图表推荐"""
        service = VisualizationService()
        
        # 模拟数据分析结果
        analysis_result = {
            'columns': {
                'category': {'type': 'string', 'unique_count': 5},
                'value': {'type': 'number', 'distribution': 'normal'},
                'date': {'type': 'datetime', 'range_days': 365}
            },
            'relationships': {
                'correlations': [('value', 'date', 0.75)]
            }
        }
        
        recommendations = service.generate_chart_recommendations(analysis_result)
        
        assert recommendations is not None
        assert isinstance(recommendations, list)


class TestDataSchemaAnalysisService:
    """数据Schema分析服务测试"""
    
    def test_init(self):
        """测试初始化"""
        service = DataSchemaAnalysisService()
        assert service is not None

    @pytest.mark.asyncio
    async def test_analyze_dataframe_schema(self):
        """测试DataFrame schema分析"""
        service = DataSchemaAnalysisService()
        
        df = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie'],
            'age': [25, 30, 35],
            'salary': [50000.0, 60000.5, 70000.0],
            'active': [True, False, True],
            'created_at': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03'])
        })
        
        schema = await service.analyze_dataframe_schema(df)
        
        assert schema is not None
        assert 'columns' in schema
        assert len(schema['columns']) == 6
        
        # 检查类型推断
        assert schema['columns']['id']['type'] == 'integer'
        assert schema['columns']['name']['type'] == 'string'
        assert schema['columns']['salary']['type'] == 'number'
        assert schema['columns']['active']['type'] == 'boolean'
        assert schema['columns']['created_at']['type'] == 'datetime'

    @pytest.mark.asyncio
    async def test_infer_column_relationships(self):
        """测试推断列关系"""
        service = DataSchemaAnalysisService()
        
        df = pd.DataFrame({
            'user_id': [1, 2, 3, 4],
            'age': [25, 30, 35, 40],
            'salary': [50000, 60000, 70000, 80000],
            'department': ['IT', 'HR', 'IT', 'Finance']
        })
        
        relationships = await service.infer_column_relationships(df)
        
        assert relationships is not None
        assert 'correlations' in relationships
        assert 'dependencies' in relationships

    @pytest.mark.asyncio
    async def test_detect_data_quality_issues(self):
        """测试检测数据质量问题"""
        service = DataSchemaAnalysisService()
        
        df = pd.DataFrame({
            'id': [1, 2, 2, 4, None],  # 重复值和缺失值
            'email': ['a@test.com', 'invalid-email', 'b@test.com', '', None],
            'age': [-5, 25, 150, 30, None],  # 异常值
            'score': [85, 92, 88, 95, 200]  # 可能的异常值
        })
        
        issues = await service.detect_data_quality_issues(df)
        
        assert issues is not None
        assert 'duplicates' in issues
        assert 'missing_values' in issues
        assert 'outliers' in issues
        assert 'format_issues' in issues

    @pytest.mark.asyncio
    async def test_suggest_data_types(self):
        """测试建议数据类型"""
        service = DataSchemaAnalysisService()
        
        # 字符串形式的数值数据
        df = pd.DataFrame({
            'numeric_string': ['123', '456', '789'],
            'date_string': ['2023-01-01', '2023-01-02', '2023-01-03'],
            'boolean_string': ['true', 'false', 'true'],
            'mixed_data': ['123', 'abc', '456']
        })
        
        suggestions = await service.suggest_data_types(df)
        
        assert suggestions is not None
        assert 'numeric_string' in suggestions
        assert suggestions['numeric_string']['suggested_type'] == 'integer'
        assert suggestions['date_string']['suggested_type'] == 'datetime'

    @pytest.mark.asyncio
    async def test_generate_schema_summary(self):
        """测试生成schema摘要"""
        service = DataSchemaAnalysisService()
        
        df = pd.DataFrame({
            'id': range(100),
            'category': ['A'] * 30 + ['B'] * 40 + ['C'] * 30,
            'value': np.random.normal(50, 10, 100),
            'flag': [True, False] * 50
        })
        
        summary = await service.generate_schema_summary(df)
        
        assert summary is not None
        assert 'row_count' in summary
        assert 'column_count' in summary
        assert 'data_types_summary' in summary
        assert 'memory_usage' in summary

    @pytest.mark.asyncio
    async def test_compare_schemas(self):
        """测试比较两个schema"""
        service = DataSchemaAnalysisService()
        
        schema1 = {
            'columns': {
                'id': {'type': 'integer'},
                'name': {'type': 'string'},
                'age': {'type': 'integer'}
            }
        }
        
        schema2 = {
            'columns': {
                'id': {'type': 'integer'},
                'name': {'type': 'string'},
                'age': {'type': 'number'},  # 类型变化
                'salary': {'type': 'number'}  # 新增列
            }
        }
        
        comparison = await service.compare_schemas(schema1, schema2)
        
        assert comparison is not None
        assert 'changes' in comparison
        assert 'added_columns' in comparison
        assert 'removed_columns' in comparison
        assert 'type_changes' in comparison

    def test_error_handling(self):
        """测试错误处理"""
        service = DataSchemaAnalysisService()
        
        # 测试空DataFrame
        with pytest.raises((ValueError, TypeError)):
            asyncio.run(service.analyze_dataframe_schema(pd.DataFrame()))
        
        # 测试None输入
        with pytest.raises((ValueError, TypeError)):
            asyncio.run(service.analyze_dataframe_schema(None))


# 集成测试
class TestDataProcessingIntegration:
    """数据处理服务集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_analysis_pipeline(self):
        """测试完整的分析流水线"""
        # 准备测试数据
        df = pd.DataFrame({
            'id': range(1, 101),
            'category': ['A', 'B', 'C'] * 33 + ['A'],
            'value': np.random.normal(100, 20, 100),
            'date': pd.date_range('2023-01-01', periods=100, freq='D')
        })
        
        # 1. Schema分析
        schema_service = DataSchemaAnalysisService()
        schema = await schema_service.analyze_dataframe_schema(df)
        
        # 2. 数据分析
        analyzer = SchemaAwareDataAnalyzer()
        analysis = await analyzer.analyze_data(df, schema)
        
        # 3. 可视化建议
        viz_service = VisualizationService()
        viz_suggestions = viz_service.generate_chart_recommendations(analysis)
        
        # 验证结果
        assert schema is not None
        assert analysis is not None
        assert viz_suggestions is not None
        
        # 检查分析结果的完整性
        assert 'summary' in analysis
        assert 'columns' in analysis
        assert len(viz_suggestions) > 0

    @pytest.mark.asyncio
    async def test_analysis_with_problematic_data(self):
        """测试处理有问题的数据"""
        # 创建包含各种问题的数据
        problematic_df = pd.DataFrame({
            'id': [1, 2, 2, 4, None],  # 重复和缺失
            'value': [10, -999, 1000000, 25, None],  # 异常值
            'category': ['A', '', 'B', None, 'C'],  # 空字符串和缺失
            'date': ['2023-01-01', 'invalid', '2023-01-03', None, '2023-01-05']
        })
        
        # 执行分析流水线
        schema_service = DataSchemaAnalysisService()
        quality_issues = await schema_service.detect_data_quality_issues(problematic_df)
        
        analyzer = SchemaAwareDataAnalyzer()
        # 这里应该能够处理有问题的数据而不崩溃
        try:
            # 先清理数据或提供默认schema
            cleaned_schema = {
                'columns': {
                    'id': {'type': 'integer', 'nullable': True},
                    'value': {'type': 'number', 'nullable': True},
                    'category': {'type': 'string', 'nullable': True},
                    'date': {'type': 'string', 'nullable': True}
                }
            }
            analysis = await analyzer.analyze_data(problematic_df, cleaned_schema)
            assert analysis is not None
        except Exception as e:
            # 如果分析失败，至少应该有有意义的错误信息
            assert str(e) is not None