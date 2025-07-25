"""
Service Interactions Integration Tests

Tests the integration between different service modules and their interactions.
Verifies that services work together correctly in complex scenarios.
"""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.services.intelligent_placeholder.processor import PlaceholderProcessor
from app.services.report_generation.generator import ReportGenerationService
from app.services.data_processing.retrieval import DataRetrievalService
from app.services.ai_integration.llm_service import LLMProviderManager
from app.models.user import User
from app.models.template import Template
from app.models.data_source import DataSource


class TestIntelligentPlaceholderServiceIntegration:
    """Test intelligent placeholder service integration with other services"""

    def test_placeholder_processing_with_data_retrieval(
        self, 
        db_session: Session,
        test_user: User,
        test_template: Template,
        test_data_source: DataSource
    ):
        """Test placeholder processing integrated with data retrieval"""
        # Mock dependencies
        mock_llm_service = Mock(spec=LLMProviderManager)
        mock_data_retrieval = Mock(spec=DataRetrievalService)
        
        # Setup mock responses
        mock_data_retrieval.get_available_fields.return_value = [
            {"name": "customer_name", "type": "string"},
            {"name": "order_date", "type": "date"},
            {"name": "total_amount", "type": "decimal"}
        ]
        
        mock_llm_service.analyze_placeholder_context.return_value = {
            "suggested_field": "customer_name",
            "confidence": 0.95,
            "reasoning": "Field name matches placeholder semantically"
        }
        
        # Create processor with mocked dependencies
        processor = PlaceholderProcessor(
            llm_service=mock_llm_service,
            data_retrieval_service=mock_data_retrieval,
            db_session=db_session
        )
        
        # Test placeholder processing
        placeholder_info = {
            "name": "customer_name",
            "template_id": test_template.id,
            "data_source_id": test_data_source.id
        }
        
        result = processor.process_placeholder(placeholder_info)
        
        # Verify service interactions
        mock_data_retrieval.get_available_fields.assert_called_once_with(test_data_source.id)
        mock_llm_service.analyze_placeholder_context.assert_called_once()
        
        # Verify result
        assert result is not None
        assert "suggested_mapping" in result
        assert result["suggested_mapping"]["field_name"] == "customer_name"

    def test_placeholder_processing_error_handling(
        self,
        db_session: Session,
        test_template: Template,
        test_data_source: EnhancedDataSource
    ):
        """Test error handling in placeholder processing service integration"""
        # Mock dependencies with error scenarios
        mock_llm_service = Mock(spec=LLMProviderManager)
        mock_data_retrieval = Mock(spec=DataRetrievalService)
        
        # Setup mock to raise exception
        mock_data_retrieval.get_available_fields.side_effect = Exception("Data source connection failed")
        
        processor = PlaceholderProcessor(
            llm_service=mock_llm_service,
            data_retrieval_service=mock_data_retrieval,
            db_session=db_session
        )
        
        placeholder_info = {
            "name": "test_placeholder",
            "template_id": test_template.id,
            "data_source_id": test_data_source.id
        }
        
        # Test error handling
        with pytest.raises(Exception) as exc_info:
            processor.process_placeholder(placeholder_info)
        
        assert "Data source connection failed" in str(exc_info.value)

    def test_placeholder_batch_processing(
        self,
        db_session: Session,
        test_template: Template,
        test_data_source: EnhancedDataSource
    ):
        """Test batch processing of multiple placeholders"""
        mock_llm_service = Mock(spec=LLMProviderManager)
        mock_data_retrieval = Mock(spec=DataRetrievalService)
        
        # Setup mock responses for batch processing
        mock_data_retrieval.get_available_fields.return_value = [
            {"name": "customer_name", "type": "string"},
            {"name": "order_date", "type": "date"},
            {"name": "total_amount", "type": "decimal"}
        ]
        
        mock_llm_service.analyze_placeholder_context.side_effect = [
            {"suggested_field": "customer_name", "confidence": 0.95},
            {"suggested_field": "order_date", "confidence": 0.90},
            {"suggested_field": "total_amount", "confidence": 0.85}
        ]
        
        processor = PlaceholderProcessor(
            llm_service=mock_llm_service,
            data_retrieval_service=mock_data_retrieval,
            db_session=db_session
        )
        
        # Test batch processing
        placeholders = [
            {"name": "customer_name", "template_id": test_template.id, "data_source_id": test_data_source.id},
            {"name": "order_date", "template_id": test_template.id, "data_source_id": test_data_source.id},
            {"name": "total_amount", "template_id": test_template.id, "data_source_id": test_data_source.id}
        ]
        
        results = processor.process_placeholders_batch(placeholders)
        
        assert len(results) == 3
        assert all("suggested_mapping" in result for result in results)
        
        # Verify service was called for each placeholder
        assert mock_llm_service.analyze_placeholder_context.call_count == 3


class TestReportGenerationServiceIntegration:
    """Test report generation service integration with other services"""

    def test_report_generation_with_placeholder_processing(
        self,
        db_session: Session,
        test_user: User,
        test_template: Template,
        test_data_source: EnhancedDataSource
    ):
        """Test report generation integrated with placeholder processing"""
        # Mock dependencies
        mock_placeholder_processor = Mock(spec=PlaceholderProcessor)
        mock_data_retrieval = Mock(spec=DataRetrievalService)
        
        # Setup mock responses
        mock_placeholder_processor.process_template_placeholders.return_value = {
            "customer_name": {"value": "John Doe", "source_field": "customer_name"},
            "order_date": {"value": "2024-01-15", "source_field": "order_date"}
        }
        
        mock_data_retrieval.get_data_for_report.return_value = {
            "customer_name": "John Doe",
            "order_date": "2024-01-15",
            "total_amount": 150.00
        }
        
        # Create report generator with mocked dependencies
        report_generator = ReportGenerationService(
            placeholder_processor=mock_placeholder_processor,
            data_retrieval_service=mock_data_retrieval,
            db_session=db_session
        )
        
        # Test report generation
        report_request = {
            "template_id": test_template.id,
            "data_source_id": test_data_source.id,
            "user_id": test_user.id,
            "output_format": "pdf"
        }
        
        result = report_generator.generate_report(report_request)
        
        # Verify service interactions
        mock_placeholder_processor.process_template_placeholders.assert_called_once()
        mock_data_retrieval.get_data_for_report.assert_called_once()
        
        # Verify result
        assert result is not None
        assert "report_id" in result
        assert "status" in result
        assert result["status"] == "completed"

    def test_report_generation_with_ai_enhancement(
        self,
        db_session: Session,
        test_template: Template,
        test_data_source: EnhancedDataSource
    ):
        """Test report generation with AI content enhancement"""
        # Mock dependencies
        mock_placeholder_processor = Mock(spec=PlaceholderProcessor)
        mock_data_retrieval = Mock(spec=DataRetrievalService)
        mock_llm_service = Mock(spec=LLMProviderManager)
        
        # Setup mock responses
        mock_placeholder_processor.process_template_placeholders.return_value = {
            "summary": {"value": "Basic summary", "source_field": "summary"}
        }
        
        mock_data_retrieval.get_data_for_report.return_value = {
            "summary": "Basic summary",
            "metrics": [1, 2, 3, 4, 5]
        }
        
        mock_llm_service.enhance_content.return_value = {
            "enhanced_summary": "Enhanced AI-generated summary with insights",
            "recommendations": ["Recommendation 1", "Recommendation 2"]
        }
        
        report_generator = ReportGenerationService(
            placeholder_processor=mock_placeholder_processor,
            data_retrieval_service=mock_data_retrieval,
            llm_service=mock_llm_service,
            db_session=db_session
        )
        
        # Test report generation with AI enhancement
        report_request = {
            "template_id": test_template.id,
            "data_source_id": test_data_source.id,
            "enable_ai_enhancement": True,
            "output_format": "pdf"
        }
        
        result = report_generator.generate_report(report_request)
        
        # Verify AI enhancement was called
        mock_llm_service.enhance_content.assert_called_once()
        
        # Verify enhanced content in result
        assert result is not None
        assert "enhanced_content" in result

    def test_report_generation_error_recovery(
        self,
        db_session: Session,
        test_template: Template,
        test_data_source: EnhancedDataSource
    ):
        """Test error recovery in report generation service integration"""
        # Mock dependencies with partial failures
        mock_placeholder_processor = Mock(spec=PlaceholderProcessor)
        mock_data_retrieval = Mock(spec=DataRetrievalService)
        
        # Setup mock to succeed for placeholder processing but fail for data retrieval
        mock_placeholder_processor.process_template_placeholders.return_value = {
            "customer_name": {"value": "fallback_value", "source_field": "customer_name"}
        }
        
        mock_data_retrieval.get_data_for_report.side_effect = Exception("Data retrieval failed")
        
        report_generator = ReportGenerationService(
            placeholder_processor=mock_placeholder_processor,
            data_retrieval_service=mock_data_retrieval,
            db_session=db_session
        )
        
        report_request = {
            "template_id": test_template.id,
            "data_source_id": test_data_source.id,
            "output_format": "pdf"
        }
        
        # Test error recovery
        result = report_generator.generate_report(report_request)
        
        # Should handle error gracefully and provide fallback
        assert result is not None
        assert result["status"] == "partial_failure"
        assert "error_details" in result


class TestDataProcessingServiceIntegration:
    """Test data processing service integration"""

    def test_data_retrieval_with_etl_processing(
        self,
        db_session: Session,
        test_data_source: EnhancedDataSource
    ):
        """Test data retrieval integrated with ETL processing"""
        from app.services.data_processing.etl import ETLService
        
        # Mock ETL service
        mock_etl_service = Mock(spec=ETLService)
        mock_etl_service.process_data_source.return_value = {
            "processed_records": 100,
            "status": "success",
            "data_quality_score": 0.95
        }
        
        # Create data retrieval service with ETL integration
        data_retrieval = DataRetrievalService(
            etl_service=mock_etl_service,
            db_session=db_session
        )
        
        # Test data retrieval with ETL processing
        result = data_retrieval.get_processed_data(
            data_source_id=test_data_source.id,
            apply_etl=True
        )
        
        # Verify ETL service was called
        mock_etl_service.process_data_source.assert_called_once_with(test_data_source.id)
        
        # Verify result includes ETL processing info
        assert result is not None
        assert "etl_info" in result
        assert result["etl_info"]["processed_records"] == 100

    def test_data_validation_and_cleaning_integration(
        self,
        db_session: Session,
        test_data_source: EnhancedDataSource
    ):
        """Test data validation and cleaning service integration"""
        from app.services.data_processing.validation import DataValidationService
        from app.services.data_processing.cleaning import DataCleaningService
        
        # Mock validation and cleaning services
        mock_validation_service = Mock(spec=DataValidationService)
        mock_cleaning_service = Mock(spec=DataCleaningService)
        
        # Setup mock responses
        mock_validation_service.validate_data.return_value = {
            "is_valid": False,
            "errors": ["Missing required field: customer_name"],
            "warnings": ["Date format inconsistent"]
        }
        
        mock_cleaning_service.clean_data.return_value = {
            "cleaned_records": 95,
            "removed_records": 5,
            "cleaning_operations": ["remove_duplicates", "standardize_dates"]
        }
        
        # Create data retrieval service with validation and cleaning
        data_retrieval = DataRetrievalService(
            validation_service=mock_validation_service,
            cleaning_service=mock_cleaning_service,
            db_session=db_session
        )
        
        # Test data retrieval with validation and cleaning
        result = data_retrieval.get_validated_and_cleaned_data(
            data_source_id=test_data_source.id
        )
        
        # Verify services were called in correct order
        mock_validation_service.validate_data.assert_called_once()
        mock_cleaning_service.clean_data.assert_called_once()
        
        # Verify result includes validation and cleaning info
        assert result is not None
        assert "validation_info" in result
        assert "cleaning_info" in result


class TestAIIntegrationServiceInteractions:
    """Test AI integration service interactions"""

    def test_llm_service_with_content_generation(self, db_session: Session):
        """Test LLM service integrated with content generation"""
        from app.services.ai_integration.content_generator import ContentGeneratorService
        
        # Mock content generator
        mock_content_generator = Mock(spec=ContentGeneratorService)
        mock_content_generator.generate_summary.return_value = {
            "summary": "AI-generated summary of the data",
            "key_insights": ["Insight 1", "Insight 2"],
            "confidence": 0.92
        }
        
        # Create LLM service with content generation
        llm_service = LLMProviderManager(
            content_generator=mock_content_generator,
            db_session=db_session
        )
        
        # Test LLM service with content generation
        data_context = {
            "data": {"sales": 1000, "customers": 50},
            "template_context": "Monthly sales report"
        }
        
        result = llm_service.generate_intelligent_content(data_context)
        
        # Verify content generator was called
        mock_content_generator.generate_summary.assert_called_once()
        
        # Verify result
        assert result is not None
        assert "generated_content" in result
        assert result["generated_content"]["summary"] is not None

    def test_ai_service_error_handling_and_fallbacks(self, db_session: Session):
        """Test AI service error handling and fallback mechanisms"""
        from app.services.ai_integration.content_generator import ContentGeneratorService
        
        # Mock content generator with failure
        mock_content_generator = Mock(spec=ContentGeneratorService)
        mock_content_generator.generate_summary.side_effect = Exception("AI service unavailable")
        
        llm_service = LLMProviderManager(
            content_generator=mock_content_generator,
            db_session=db_session,
            enable_fallbacks=True
        )
        
        data_context = {
            "data": {"sales": 1000, "customers": 50},
            "template_context": "Monthly sales report"
        }
        
        # Test error handling with fallbacks
        result = llm_service.generate_intelligent_content(data_context)
        
        # Should provide fallback content instead of failing
        assert result is not None
        assert "fallback_content" in result or "error_handled" in result


class TestCrossServiceWorkflows:
    """Test complex workflows involving multiple services"""

    def test_complete_report_generation_workflow(
        self,
        db_session: Session,
        test_user: User,
        test_template: Template,
        test_data_source: EnhancedDataSource
    ):
        """Test complete report generation workflow with all services"""
        # Mock all required services
        mock_placeholder_processor = Mock(spec=PlaceholderProcessor)
        mock_data_retrieval = Mock(spec=DataRetrievalService)
        mock_llm_service = Mock(spec=LLMProviderManager)
        mock_report_generator = Mock(spec=ReportGenerationService)
        
        # Setup mock responses for complete workflow
        mock_placeholder_processor.analyze_template.return_value = {
            "placeholders": ["customer_name", "order_total", "summary"]
        }
        
        mock_data_retrieval.get_data_for_placeholders.return_value = {
            "customer_name": "John Doe",
            "order_total": 150.00,
            "raw_data": {"orders": [{"id": 1, "amount": 150.00}]}
        }
        
        mock_llm_service.generate_summary.return_value = {
            "summary": "Customer John Doe has an order total of $150.00"
        }
        
        mock_report_generator.compile_report.return_value = {
            "report_id": "report_123",
            "status": "completed",
            "file_path": "/tmp/report_123.pdf"
        }
        
        # Create workflow orchestrator
        from app.services.workflow_orchestrator import WorkflowOrchestrator
        
        orchestrator = WorkflowOrchestrator(
            placeholder_processor=mock_placeholder_processor,
            data_retrieval=mock_data_retrieval,
            llm_service=mock_llm_service,
            report_generator=mock_report_generator,
            db_session=db_session
        )
        
        # Execute complete workflow
        workflow_request = {
            "template_id": test_template.id,
            "data_source_id": test_data_source.id,
            "user_id": test_user.id,
            "enable_ai_enhancement": True,
            "output_format": "pdf"
        }
        
        result = orchestrator.execute_report_generation_workflow(workflow_request)
        
        # Verify all services were called in correct order
        mock_placeholder_processor.analyze_template.assert_called_once()
        mock_data_retrieval.get_data_for_placeholders.assert_called_once()
        mock_llm_service.generate_summary.assert_called_once()
        mock_report_generator.compile_report.assert_called_once()
        
        # Verify final result
        assert result is not None
        assert result["status"] == "completed"
        assert "report_id" in result

    def test_workflow_partial_failure_handling(
        self,
        db_session: Session,
        test_template: Template,
        test_data_source: EnhancedDataSource
    ):
        """Test workflow handling when some services fail"""
        # Mock services with mixed success/failure
        mock_placeholder_processor = Mock(spec=PlaceholderProcessor)
        mock_data_retrieval = Mock(spec=DataRetrievalService)
        mock_llm_service = Mock(spec=LLMProviderManager)
        mock_report_generator = Mock(spec=ReportGenerationService)
        
        # Setup mixed responses
        mock_placeholder_processor.analyze_template.return_value = {
            "placeholders": ["customer_name", "summary"]
        }
        
        mock_data_retrieval.get_data_for_placeholders.return_value = {
            "customer_name": "John Doe"
        }
        
        # LLM service fails
        mock_llm_service.generate_summary.side_effect = Exception("AI service timeout")
        
        # Report generator handles partial data
        mock_report_generator.compile_report.return_value = {
            "report_id": "report_124",
            "status": "partial_success",
            "warnings": ["AI enhancement failed, using fallback content"]
        }
        
        from app.services.workflow_orchestrator import WorkflowOrchestrator
        
        orchestrator = WorkflowOrchestrator(
            placeholder_processor=mock_placeholder_processor,
            data_retrieval=mock_data_retrieval,
            llm_service=mock_llm_service,
            report_generator=mock_report_generator,
            db_session=db_session
        )
        
        workflow_request = {
            "template_id": test_template.id,
            "data_source_id": test_data_source.id,
            "enable_ai_enhancement": True,
            "output_format": "pdf"
        }
        
        # Execute workflow with partial failure
        result = orchestrator.execute_report_generation_workflow(workflow_request)
        
        # Should handle partial failure gracefully
        assert result is not None
        assert result["status"] == "partial_success"
        assert "warnings" in result
        assert len(result["warnings"]) > 0

    def test_service_dependency_injection_integration(self, db_session: Session):
        """Test service dependency injection and integration"""
        from app.api.deps import get_placeholder_processor, get_data_retrieval_service
        from app.core.container import Container
        
        # Test dependency injection container
        container = Container()
        container.wire(modules=["app.api.deps"])
        
        # Get services through dependency injection
        placeholder_processor = get_placeholder_processor()
        data_retrieval_service = get_data_retrieval_service()
        
        # Verify services are properly injected and configured
        assert placeholder_processor is not None
        assert data_retrieval_service is not None
        
        # Test that services have their dependencies properly injected
        assert hasattr(placeholder_processor, 'llm_service')
        assert hasattr(placeholder_processor, 'data_retrieval_service')
        assert hasattr(data_retrieval_service, 'db_session')