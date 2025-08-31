"""
应用层服务测试
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List

from app.services.application.facades.unified_service_facade import (
    UnifiedServiceFacade,
)
from app.services.application.workflows.enhanced_report_generation_workflow import (
    EnhancedReportGenerationWorkflow,
    ReportGenerationRequest,
    ReportQualityLevel,
    ReportGenerationStage,
    ReportGenerationConfig,
    StageResult,
)
from app.services.application.workflows.context_aware_task_service import (
    ContextAwareTaskService,
    ContextualTaskRequest,
    TaskPriority,
)
from app.services.application.context import (
    TimeContextBuilder,
    BusinessContextBuilder,
    DocumentContextBuilder,
)


class TestUnifiedServiceFacade:
    """统一服务门面测试"""
    
    @pytest.fixture
    def facade(self):
        """创建统一服务门面实例"""
        with patch('app.services.application.facades.unified_service_facade.VisualizationService'):
            with patch('app.services.application.facades.unified_service_facade.SchemaAwareAnalysisService'):
                return UnifiedServiceFacade()
    
    @pytest.mark.asyncio
    async def test_generate_charts_success(self, facade):
        """测试成功生成图表"""
        # 模拟服务依赖
        facade.visualization_service.generate_chart = MagicMock(return_value={
            'success': True,
            'image_path': '/tmp/chart.png',
            'chart_config': {'type': 'bar'},
            'echarts_config': {'title': {'text': '测试图表'}}
        })
        
        # 执行测试
        result = await facade.generate_charts(
            data_source="SELECT * FROM sales",
            requirements="生成柱状图显示销售数据",
            output_format="json"
        )
        
        # 验证结果
        assert result['success'] is True
        assert 'generated_charts' in result
        assert len(result['generated_charts']) == 1
        assert result['generated_charts'][0]['chart_type'] == 'bar_chart'
        assert 'metadata' in result
        assert result['metadata']['data_points'] == 4  # 模拟数据点数量
    
    @pytest.mark.asyncio
    async def test_generate_charts_pie_chart(self, facade):
        """测试生成饼图"""
        facade.visualization_service.generate_chart = MagicMock(return_value={
            'success': True,
            'image_path': '/tmp/pie.png',
            'chart_config': {'type': 'pie'}
        })
        
        result = await facade.generate_charts(
            data_source="SELECT category, count FROM data",
            requirements="生成饼图显示各类别占比",
            output_format="png"
        )
        
        assert result['success'] is True
        assert result['generated_charts'][0]['chart_type'] == 'pie_chart'
    
    @pytest.mark.asyncio
    async def test_generate_charts_line_chart(self, facade):
        """测试生成折线图"""
        facade.visualization_service.generate_chart = MagicMock(return_value={
            'success': True,
            'image_path': '/tmp/line.png',
            'chart_config': {'type': 'line'}
        })
        
        result = await facade.generate_charts(
            data_source="data.csv",
            requirements="生成折线图显示时间趋势",
            output_format="svg"
        )
        
        assert result['success'] is True
        assert result['generated_charts'][0]['chart_type'] == 'line_chart'
    
    @pytest.mark.asyncio
    async def test_generate_charts_no_data(self, facade):
        """测试无数据情况"""
        # 模拟数据准备失败
        with patch.object(facade, '_prepare_chart_data', return_value=[]):
            result = await facade.generate_charts(
                data_source="invalid_source",
                requirements="生成图表",
                output_format="json"
            )
        
        assert result['success'] is False
        assert 'No data available' in result['error']
    
    @pytest.mark.asyncio
    async def test_generate_charts_visualization_failure(self, facade):
        """测试可视化服务失败"""
        facade.visualization_service.generate_chart = MagicMock(return_value={
            'success': False,
            'error': 'Chart generation failed'
        })
        
        result = await facade.generate_charts(
            data_source="SELECT * FROM test",
            requirements="生成图表",
            output_format="json"
        )
        
        assert result['success'] is False
        assert 'Chart generation failed' in result['error']
    
    @pytest.mark.asyncio
    async def test_optimize_chart_success(self, facade):
        """测试图表优化成功"""
        result = await facade.optimize_chart(
            chart_path="/tmp/chart.png",
            optimization_goals=["clarity", "aesthetics", "accessibility"]
        )
        
        assert result['success'] is True
        assert len(result['improvements']) >= 3
        assert 'optimized_path' in result
        assert result['optimization_goals'] == ["clarity", "aesthetics", "accessibility"]
    
    @pytest.mark.asyncio
    async def test_optimize_chart_single_goal(self, facade):
        """测试单个优化目标"""
        result = await facade.optimize_chart(
            chart_path="/tmp/chart.png",
            optimization_goals=["clarity"]
        )
        
        assert result['success'] is True
        assert len(result['improvements']) == 2  # clarity相关的两个改进
        assert "增加图表标题清晰度" in result['improvements']
        assert "优化坐标轴标签" in result['improvements']
    
    @pytest.mark.asyncio
    async def test_analyze_data_for_charts_success(self, facade):
        """测试数据分析成功"""
        test_data = [
            {"category": "A", "value": 100},
            {"category": "B", "value": 150},
            {"category": "C", "value": 200}
        ]
        
        # 模拟分析服务
        facade.analysis_service.analyze_data_structure = AsyncMock(return_value={
            'column_types': {'category': 'object', 'value': 'int64'},
            'row_count': 3,
            'null_counts': {'category': 0, 'value': 0}
        })
        
        result = await facade.analyze_data_for_charts(
            data=test_data,
            analysis_type="exploratory"
        )
        
        assert result['success'] is True
        assert 'data_analysis' in result
        assert 'chart_recommendations' in result
        assert len(result['chart_recommendations']) > 0
        assert result['analysis_type'] == "exploratory"
    
    @pytest.mark.asyncio
    async def test_analyze_data_empty_data(self, facade):
        """测试空数据分析"""
        result = await facade.analyze_data_for_charts(
            data=[],
            analysis_type="basic"
        )
        
        assert result['success'] is False
        assert 'No data provided' in result['error']
    
    def test_chart_type_detection(self, facade):
        """测试图表类型检测"""
        # 测试饼图检测
        result = asyncio.run(facade._parse_chart_requirements("生成饼图显示各部门占比"))
        assert result['chart_type'] == 'pie_chart'
        
        # 测试折线图检测
        result = asyncio.run(facade._parse_chart_requirements("显示销售趋势的折线图"))
        assert result['chart_type'] == 'line_chart'
        
        # 测试散点图检测
        result = asyncio.run(facade._parse_chart_requirements("显示收入和支出关系的散点图"))
        assert result['chart_type'] == 'scatter_chart'
        
        # 测试雷达图检测
        result = asyncio.run(facade._parse_chart_requirements("多维能力雷达图"))
        assert result['chart_type'] == 'radar_chart'
    
    def test_chart_recommendations_logic(self, facade):
        """测试图表推荐逻辑"""
        # 测试分类+数值数据推荐
        analysis_result = {
            'column_types': {'category': 'object', 'value': 'int64'},
            'row_count': 5
        }
        
        recommendations = facade._recommend_chart_types(analysis_result)
        
        assert len(recommendations) >= 2
        # 应该推荐柱状图（置信度最高）
        assert recommendations[0]['chart_type'] == 'bar_chart'
        assert recommendations[0]['confidence'] == 0.9
        # 应该推荐饼图（数据量适中）
        pie_rec = next((r for r in recommendations if r['chart_type'] == 'pie_chart'), None)
        assert pie_rec is not None
        assert pie_rec['confidence'] == 0.8
    
    def test_multiple_numeric_columns_recommendations(self, facade):
        """测试多数值列推荐"""
        analysis_result = {
            'column_types': {
                'col1': 'int64',
                'col2': 'float64', 
                'col3': 'int64',
                'col4': 'float64'
            },
            'row_count': 100
        }
        
        recommendations = facade._recommend_chart_types(analysis_result)
        
        # 应该推荐散点图和雷达图
        chart_types = [r['chart_type'] for r in recommendations]
        assert 'scatter_chart' in chart_types
        assert 'radar_chart' in chart_types


class TestEnhancedReportGenerationWorkflow:
    """增强报告生成工作流测试"""
    
    @pytest.fixture
    def workflow_config(self):
        """创建工作流配置"""
        return ReportGenerationConfig(
            enable_intelligent_processing=True,
            enable_parallel_stages=True,
            enable_quality_optimization=True,
            max_retry_attempts=1,
            quality_threshold=0.7
        )
    
    @pytest.fixture
    def workflow(self, workflow_config):
        """创建工作流实例"""
        with patch.multiple(
            'app.services.application.workflows.enhanced_report_generation_workflow',
            IntelligentPlaceholderWorkflow=MagicMock(),
            ContextAwareTaskService=MagicMock(),
            TimeContextBuilder=MagicMock(),
            BusinessContextBuilder=MagicMock(),
            DocumentContextBuilder=MagicMock(),
            ReportGenerator=MagicMock(),
            EnhancedTemplateParser=MagicMock(),
            EnhancedTwoPhasePipeline=MagicMock()
        ):
            return EnhancedReportGenerationWorkflow(config=workflow_config)
    
    @pytest.fixture
    def sample_request(self):
        """创建示例请求"""
        return ReportGenerationRequest(
            template_id="test_template_001",
            user_id="user_123",
            report_name="测试报告",
            data_sources=["db1", "db2"],
            output_format="html",
            quality_level=ReportQualityLevel.STANDARD,
            time_constraints={"time_range": "2023-01-01 to 2023-12-31"},
            business_requirements={"department": "sales", "user_role": "manager"},
            priority=TaskPriority.NORMAL
        )
    
    @pytest.mark.asyncio
    async def test_generate_report_success(self, workflow, sample_request):
        """测试成功生成报告"""
        # 模拟依赖
        workflow._generate_request_id = MagicMock(return_value="req_12345")
        workflow._estimate_completion_time = MagicMock(
            return_value=datetime.now() + timedelta(minutes=5)
        )
        
        result = await workflow.generate_report(sample_request)
        
        assert result['status'] == 'started'
        assert result['request_id'] == 'req_12345'
        assert 'estimated_completion_time' in result
        assert result['quality_level'] == 'standard'
    
    @pytest.mark.asyncio
    async def test_generate_report_with_callback(self, workflow, sample_request):
        """测试带回调的报告生成"""
        sample_request.callback_url = "https://example.com/callback"
        workflow._generate_request_id = MagicMock(return_value="req_12345")
        workflow._estimate_completion_time = MagicMock(
            return_value=datetime.now() + timedelta(minutes=5)
        )
        
        result = await workflow.generate_report(sample_request)
        
        assert result['tracking_url'] == "/api/reports/status/req_12345"
    
    @pytest.mark.asyncio
    async def test_execute_stage_template_analysis(self, workflow, sample_request):
        """测试模板分析阶段"""
        # 模拟依赖方法
        workflow._retrieve_template_content = AsyncMock(return_value="<template>测试模板</template>")
        workflow.template_parser.parse_template = MagicMock(return_value={
            'placeholders': ['{{sales_data}}', '{{user_name}}'],
            'structure': 'complex'
        })
        workflow.document_builder.build_from_template = MagicMock(return_value=MagicMock(
            structure_complexity=0.8
        ))
        
        result = await workflow._execute_stage(
            ReportGenerationStage.TEMPLATE_ANALYSIS,
            sample_request,
            []
        )
        
        assert result.success is True
        assert result.stage == ReportGenerationStage.TEMPLATE_ANALYSIS
        assert 'template_content' in result.output_data
        assert 'template_analysis' in result.output_data
        assert result.output_data['placeholder_count'] == 2
    
    @pytest.mark.asyncio
    async def test_execute_stage_context_building(self, workflow, sample_request):
        """测试上下文构建阶段"""
        # 准备前置阶段结果
        template_result = StageResult(
            stage=ReportGenerationStage.TEMPLATE_ANALYSIS,
            success=True,
            execution_time=1.0,
            output_data={
                'document_context': MagicMock(),
                'template_analysis': {'placeholders': []}
            },
            quality_metrics={}
        )
        
        # 模拟上下文构建器
        workflow.time_builder.build_from_request = MagicMock(return_value=MagicMock())
        workflow.business_builder.build_from_user_context = MagicMock(return_value=MagicMock())
        workflow._assess_context_quality = MagicMock(return_value=0.85)
        
        result = await workflow._execute_stage(
            ReportGenerationStage.CONTEXT_BUILDING,
            sample_request,
            [template_result]
        )
        
        assert result.success is True
        assert result.stage == ReportGenerationStage.CONTEXT_BUILDING
        assert 'time_context' in result.output_data
        assert 'business_context' in result.output_data
        assert result.output_data['context_quality'] == 0.85
    
    @pytest.mark.asyncio
    async def test_execute_stage_placeholder_processing(self, workflow, sample_request):
        """测试占位符处理阶段"""
        # 准备前置阶段结果
        template_result = StageResult(
            stage=ReportGenerationStage.TEMPLATE_ANALYSIS,
            success=True,
            execution_time=1.0,
            output_data={'template_content': '<template>test</template>'},
            quality_metrics={}
        )
        
        context_result = StageResult(
            stage=ReportGenerationStage.CONTEXT_BUILDING,
            success=True,
            execution_time=1.0,
            output_data={
                'document_context': MagicMock(),
                'business_context': MagicMock(),
                'time_context': MagicMock()
            },
            quality_metrics={}
        )
        
        # 模拟占位符编排器
        mock_orchestrator = AsyncMock()
        mock_processing_result = MagicMock(
            processed_placeholders=['{{sales_data}}'],
            quality_score=0.9,
            recommendations=['提高数据质量']
        )
        mock_orchestrator.process_document = AsyncMock(return_value=mock_processing_result)
        workflow.placeholder_orchestrator = mock_orchestrator
        
        result = await workflow._execute_stage(
            ReportGenerationStage.PLACEHOLDER_PROCESSING,
            sample_request,
            [template_result, context_result]
        )
        
        assert result.success is True
        assert result.stage == ReportGenerationStage.PLACEHOLDER_PROCESSING
        assert result.output_data['intelligent_processing'] is True
        assert result.output_data['quality_score'] == 0.9
    
    @pytest.mark.asyncio
    async def test_execute_stage_data_extraction(self, workflow, sample_request):
        """测试数据提取阶段"""
        # 准备前置阶段结果
        placeholder_result = StageResult(
            stage=ReportGenerationStage.PLACEHOLDER_PROCESSING,
            success=True,
            execution_time=1.0,
            output_data={
                'processed_placeholders': [{'name': 'sales_data', 'sql': 'SELECT * FROM sales'}]
            },
            quality_metrics={}
        )
        
        context_result = StageResult(
            stage=ReportGenerationStage.CONTEXT_BUILDING,
            success=True,
            execution_time=1.0,
            output_data={'business_context': MagicMock()},
            quality_metrics={}
        )
        
        # 模拟两阶段管道
        workflow.two_phase_pipeline.execute_pipeline = AsyncMock(return_value={
            'data': {'sales_data': [{'month': 'Jan', 'amount': 1000}]},
            'quality_score': 0.85,
            'processing_time': 2.5
        })
        
        result = await workflow._execute_stage(
            ReportGenerationStage.DATA_EXTRACTION,
            sample_request,
            [MagicMock(), context_result, placeholder_result]
        )
        
        assert result.success is True
        assert result.stage == ReportGenerationStage.DATA_EXTRACTION
        assert 'extracted_data' in result.output_data
        assert result.output_data['data_quality_score'] == 0.85
    
    def test_calculate_overall_quality(self, workflow):
        """测试总体质量计算"""
        stage_results = [
            StageResult(
                stage=ReportGenerationStage.TEMPLATE_ANALYSIS,
                success=True,
                execution_time=1.0,
                output_data={},
                quality_metrics={'accuracy': 0.9, 'completeness': 0.8}
            ),
            StageResult(
                stage=ReportGenerationStage.PLACEHOLDER_PROCESSING,
                success=True,
                execution_time=2.0,
                output_data={},
                quality_metrics={'resolution_rate': 0.95, 'accuracy': 0.9}
            ),
            StageResult(
                stage=ReportGenerationStage.DATA_EXTRACTION,
                success=False,  # 失败的阶段不应影响计算
                execution_time=0.5,
                output_data={},
                quality_metrics={}
            )
        ]
        
        overall_quality = workflow._calculate_overall_quality(stage_results)
        
        assert 0.8 <= overall_quality <= 1.0  # 应该基于成功阶段的加权平均
    
    def test_get_workflow_status_active(self, workflow):
        """测试获取活跃工作流状态"""
        request_id = "req_12345"
        workflow.active_workflows[request_id] = {
            'status': 'running',
            'current_stage': 'placeholder_processing',
            'progress': 0.6,
            'started_at': datetime(2023, 1, 1, 10, 0, 0),
            'estimated_completion': datetime(2023, 1, 1, 10, 5, 0),
            'errors': [],
            'warnings': ['警告信息']
        }
        
        status = workflow.get_workflow_status(request_id)
        
        assert status['request_id'] == request_id
        assert status['status'] == 'running'
        assert status['current_stage'] == 'placeholder_processing'
        assert status['progress'] == 0.6
        assert len(status['warnings']) == 1
    
    def test_get_workflow_status_completed(self, workflow):
        """测试获取已完成工作流状态"""
        request_id = "req_67890"
        completed_result = ReportGenerationResult(
            request_id=request_id,
            success=True,
            total_execution_time=45.5,
            overall_quality_score=0.88
        )
        workflow.completed_reports[request_id] = completed_result
        
        status = workflow.get_workflow_status(request_id)
        
        assert status['request_id'] == request_id
        assert status['status'] == 'completed'
        assert status['success'] is True
        assert status['total_execution_time'] == 45.5
        assert status['overall_quality_score'] == 0.88
    
    def test_get_workflow_status_not_found(self, workflow):
        """测试获取不存在的工作流状态"""
        status = workflow.get_workflow_status("nonexistent_id")
        
        assert status['request_id'] == "nonexistent_id"
        assert status['status'] == 'not_found'
        assert 'error' in status
    
    def test_get_workflow_statistics(self, workflow):
        """测试获取工作流统计信息"""
        # 设置一些统计数据
        workflow.workflow_stats['total_requests'] = 10
        workflow.workflow_stats['successful_reports'] = 8
        workflow.active_workflows['req1'] = {}
        workflow.active_workflows['req2'] = {}
        workflow.completed_reports['comp1'] = MagicMock()
        
        stats = workflow.get_workflow_statistics()
        
        assert stats['success_rate'] == 0.8  # 8/10
        assert stats['active_workflows'] == 2
        assert stats['completed_reports'] == 1
        assert 'stage_performance' in stats
        assert 'config' in stats
        assert stats['config']['intelligent_processing'] is True
    
    def test_quality_methods(self, workflow):
        """测试质量检查方法"""
        # 测试内容完整性检查
        assert workflow._check_content_completeness("很长的内容" * 20) == 0.9
        assert workflow._check_content_completeness("短") == 0.5
        
        # 测试数据准确性检查
        assert workflow._check_data_accuracy([]) == 0.85
        
        # 测试格式合规性检查
        assert workflow._check_format_compliance("content", "html") == 0.9
        
        # 测试可读性评分
        assert workflow._check_readability("测试内容") == 0.8
        
        # 测试占位符解析率检查
        assert workflow._check_placeholder_resolution([]) == 0.95
    
    def test_request_id_generation(self, workflow):
        """测试请求ID生成"""
        request = ReportGenerationRequest(
            template_id="test",
            user_id="user123",
            report_name="test report",
            data_sources=[]
        )
        
        request_id = workflow._generate_request_id(request)
        
        assert request_id.startswith("report_user123_")
        assert len(request_id.split("_")) == 4  # report_user_timestamp_uuid
    
    def test_completion_time_estimation(self, workflow):
        """测试完成时间估算"""
        # 测试不同质量等级的估算
        standard_request = ReportGenerationRequest(
            template_id="test",
            user_id="user",
            report_name="test",
            data_sources=[],
            quality_level=ReportQualityLevel.STANDARD
        )
        
        premium_request = ReportGenerationRequest(
            template_id="test",
            user_id="user", 
            report_name="test",
            data_sources=[],
            quality_level=ReportQualityLevel.PREMIUM
        )
        
        enterprise_request = ReportGenerationRequest(
            template_id="test",
            user_id="user",
            report_name="test", 
            data_sources=[],
            quality_level=ReportQualityLevel.ENTERPRISE
        )
        
        standard_time = workflow._estimate_completion_time(standard_request)
        premium_time = workflow._estimate_completion_time(premium_request)
        enterprise_time = workflow._estimate_completion_time(enterprise_request)
        
        # 企业级应该比高级耗时更长，高级应该比标准耗时更长
        assert enterprise_time > premium_time > standard_time


class TestContextBuilders:
    """上下文构建器测试"""
    
    @pytest.fixture
    def time_builder(self):
        """时间上下文构建器"""
        with patch('app.services.application.context.time_context_builder.TimeContext'):
            return TimeContextBuilder()
    
    @pytest.fixture
    def business_builder(self):
        """业务上下文构建器"""
        with patch('app.services.application.context.business_context_builder.BusinessContext'):
            return BusinessContextBuilder()
    
    @pytest.fixture
    def document_builder(self):
        """文档上下文构建器"""
        with patch('app.services.application.context.document_context_builder.DocumentContext'):
            return DocumentContextBuilder()
    
    def test_time_context_builder_basic(self, time_builder):
        """测试时间上下文构建基础功能"""
        # 测试构建器存在并可调用
        assert hasattr(time_builder, 'build_from_request')
        
        # 由于缺少实际实现，这里主要测试接口存在性
        # 在实际实现后，应该测试具体的时间解析逻辑
    
    def test_business_context_builder_basic(self, business_builder):
        """测试业务上下文构建基础功能"""
        assert hasattr(business_builder, 'build_from_user_context')
        
        # 测试接口存在性
        # 实际实现后应该测试用户角色、部门、公司信息的解析
    
    def test_document_context_builder_basic(self, document_builder):
        """测试文档上下文构建基础功能"""
        assert hasattr(document_builder, 'build_from_template')
        
        # 测试接口存在性
        # 实际实现后应该测试模板结构分析和复杂度计算


class TestContextAwareTaskService:
    """上下文感知任务服务测试"""
    
    @pytest.fixture
    def task_service(self):
        """创建任务服务实例"""
        with patch('app.services.application.workflows.context_aware_task_service.IntelligentPlaceholderService'):
            return ContextAwareTaskService(MagicMock())
    
    def test_task_service_initialization(self, task_service):
        """测试任务服务初始化"""
        assert task_service is not None
        # 由于缺少实际实现，主要测试初始化不会出错
    
    @pytest.fixture
    def sample_task_request(self):
        """创建示例任务请求"""
        return ContextualTaskRequest(
            task_id="task_001",
            task_type="data_analysis",
            user_id="user_123",
            priority=TaskPriority.HIGH,
            context_data={"department": "sales", "time_period": "Q1"},
            deadline=datetime.now() + timedelta(hours=2)
        )
    
    def test_contextual_task_request_creation(self, sample_task_request):
        """测试上下文任务请求创建"""
        assert sample_task_request.task_id == "task_001"
        assert sample_task_request.task_type == "data_analysis"
        assert sample_task_request.priority == TaskPriority.HIGH
        assert "department" in sample_task_request.context_data
        assert sample_task_request.deadline > datetime.now()


@pytest.mark.integration
class TestApplicationServicesIntegration:
    """应用层服务集成测试"""
    
    @pytest.mark.asyncio
    async def test_unified_facade_with_workflow_integration(self):
        """测试统一门面与工作流的集成"""
        # 这个测试需要在有完整实现后进行
        # 目前作为框架预留
        pass
    
    @pytest.mark.asyncio
    async def test_context_builders_integration(self):
        """测试上下文构建器之间的集成"""
        # 测试多个上下文构建器协同工作
        pass
    
    @pytest.mark.asyncio
    async def test_end_to_end_report_generation(self):
        """测试端到端报告生成流程"""
        # 测试从请求到完成报告的完整流程
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])