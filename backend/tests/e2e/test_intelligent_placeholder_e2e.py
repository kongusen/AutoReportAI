"""
Intelligent Placeholder Processing End-to-End Tests

This module tests the complete intelligent placeholder system including
processing, adaptation, field matching, and integration with AI services.
"""

import json
import time
from typing import Any, Dict, List

import pytest
import requests
from requests import Session


@pytest.mark.e2e
@pytest.mark.slow
class TestIntelligentPlaceholderE2E:
    """Test intelligent placeholder processing end-to-end"""

    def test_intelligent_placeholder_processing_workflow(
        self,
        authenticated_session: Session,
        api_base_url: str,
        sample_workflow_data: Dict[str, Any],
        performance_thresholds: Dict[str, float],
        cleanup_e2e_data,
    ):
        """
        Test complete intelligent placeholder processing workflow:
        1. Create data source with complex schema
        2. Create template with various placeholder types
        3. Process intelligent field matching
        4. Execute placeholder adaptation
        5. Validate processing results
        """
        print("Testing intelligent placeholder processing workflow...")

        # Step 1: Create complex data source
        print("Step 1: Creating complex data source...")
        complex_data_source = {
            "name": "E2E Complex Data Source",
            "description": "Complex data source for intelligent placeholder testing",
            "source_type": "database",
            "connection_string": "sqlite:///complex_test.db",
            "schema_config": {
                "tables": {
                    "complaints": {
                        "columns": [
                            {"name": "id", "type": "integer", "primary_key": True},
                            {"name": "complaint_date", "type": "datetime"},
                            {"name": "category", "type": "string"},
                            {"name": "description", "type": "text"},
                            {"name": "status", "type": "string"},
                            {"name": "resolution_date", "type": "datetime"},
                            {"name": "satisfaction_score", "type": "float"},
                            {"name": "customer_id", "type": "integer"},
                        ]
                    },
                    "customers": {
                        "columns": [
                            {"name": "id", "type": "integer", "primary_key": True},
                            {"name": "name", "type": "string"},
                            {"name": "email", "type": "string"},
                            {"name": "phone", "type": "string"},
                            {"name": "region", "type": "string"},
                        ]
                    },
                    "resolutions": {
                        "columns": [
                            {"name": "id", "type": "integer", "primary_key": True},
                            {"name": "complaint_id", "type": "integer"},
                            {"name": "resolution_type", "type": "string"},
                            {"name": "resolution_details", "type": "text"},
                            {"name": "resolved_by", "type": "string"},
                        ]
                    }
                },
                "relationships": [
                    {"from": "complaints.customer_id", "to": "customers.id"},
                    {"from": "resolutions.complaint_id", "to": "complaints.id"}
                ]
            },
            "is_active": True,
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/data-sources/", json=complex_data_source
        )
        assert response.status_code == 201, f"Failed to create complex data source: {response.text}"
        data_source = response.json()
        data_source_id = data_source["id"]
        print(f"✅ Complex data source created with ID: {data_source_id}")

        # Step 2: Create template with intelligent placeholders
        print("Step 2: Creating template with intelligent placeholders...")
        intelligent_template = {
            "name": "E2E Intelligent Placeholder Template",
            "description": "Template with various intelligent placeholder types",
            "content": """
            # {{智能报告标题|report_title}}
            
            ## 时间范围分析
            报告期间：{{开始日期|start_date}} 至 {{结束日期|end_date}}
            
            ## 核心指标
            - 总投诉数量：{{投诉总数|total_complaints}}
            - 平均处理时间：{{平均处理时间|avg_resolution_time}} 天
            - 客户满意度：{{客户满意度|avg_satisfaction_score}}
            - 解决率：{{解决率|resolution_rate}}%
            
            ## 分类统计
            {{按类别统计|complaints_by_category}}
            
            ## 地区分布
            {{地区分布统计|regional_distribution}}
            
            ## 趋势分析
            {{月度趋势|monthly_trends}}
            
            ## 热点问题
            {{热点问题分析|hot_issues}}
            
            ## 改进建议
            {{智能建议|intelligent_recommendations}}
            
            ## 详细数据
            {{详细数据表格|detailed_data_table}}
            """,
            "data_source_id": data_source_id,
            "is_active": True,
            "category": "intelligent_analysis"
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/templates/", json=intelligent_template
        )
        assert response.status_code == 201, f"Failed to create intelligent template: {response.text}"
        template = response.json()
        template_id = template["id"]
        print(f"✅ Intelligent template created with ID: {template_id}")

        # Step 3: Analyze template for intelligent placeholders
        print("Step 3: Analyzing template for intelligent placeholders...")
        response = authenticated_session.post(
            f"{api_base_url}/template-analysis/{template_id}/analyze"
        )
        assert response.status_code == 200, f"Template analysis failed: {response.text}"
        analysis = response.json()
        
        placeholders = analysis.get("placeholders", [])
        assert len(placeholders) >= 10, f"Expected at least 10 placeholders, found {len(placeholders)}"
        
        # Verify intelligent placeholder detection
        intelligent_placeholders = [p for p in placeholders if p.get("type") == "intelligent"]
        assert len(intelligent_placeholders) > 0, "No intelligent placeholders detected"
        print(f"✅ Found {len(placeholders)} total placeholders, {len(intelligent_placeholders)} intelligent")

        # Step 4: Process intelligent field matching
        print("Step 4: Processing intelligent field matching...")
        matching_start_time = time.time()
        
        for placeholder in intelligent_placeholders:
            matching_request = {
                "template_id": template_id,
                "data_source_id": data_source_id,
                "placeholder_name": placeholder["name"],
                "chinese_name": placeholder.get("chinese_name", ""),
                "context": {
                    "surrounding_text": placeholder.get("context", ""),
                    "placeholder_type": placeholder.get("type", ""),
                    "expected_format": placeholder.get("format", "")
                }
            }
            
            response = authenticated_session.post(
                f"{api_base_url}/intelligent-placeholders/match-fields",
                json=matching_request
            )
            assert response.status_code == 200, f"Field matching failed for {placeholder['name']}: {response.text}"
            matching_result = response.json()
            
            assert matching_result.get("success", False), f"Field matching unsuccessful for {placeholder['name']}"
            assert "matched_fields" in matching_result, "No matched fields returned"
            assert len(matching_result["matched_fields"]) > 0, "No fields matched"
            
            # Verify confidence scores
            for match in matching_result["matched_fields"]:
                assert "confidence_score" in match, "Confidence score missing"
                assert 0 <= match["confidence_score"] <= 1, "Invalid confidence score"
        
        matching_end_time = time.time()
        matching_time = matching_end_time - matching_start_time
        print(f"✅ Field matching completed in {matching_time:.2f}s")

        # Step 5: Execute intelligent placeholder processing
        print("Step 5: Executing intelligent placeholder processing...")
        processing_start_time = time.time()
        
        processing_results = []
        for placeholder in intelligent_placeholders:
            processing_request = {
                "template_id": template_id,
                "data_source_id": data_source_id,
                "placeholder_name": placeholder["name"],
                "processing_mode": "intelligent",
                "context": {
                    "report_type": "monthly_analysis",
                    "language": "zh-CN",
                    "format_preference": "detailed"
                }
            }
            
            response = authenticated_session.post(
                f"{api_base_url}/intelligent-placeholders/process",
                json=processing_request
            )
            assert response.status_code == 200, f"Processing failed for {placeholder['name']}: {response.text}"
            processing_result = response.json()
            
            assert processing_result.get("success", False), f"Processing unsuccessful for {placeholder['name']}"
            assert "processed_value" in processing_result, "No processed value returned"
            assert "processing_metadata" in processing_result, "No processing metadata returned"
            
            processing_results.append({
                "placeholder": placeholder["name"],
                "result": processing_result
            })
        
        processing_end_time = time.time()
        processing_time = processing_end_time - processing_start_time
        
        assert processing_time < performance_thresholds["data_processing_time"], \
            f"Intelligent processing took too long: {processing_time:.2f}s"
        print(f"✅ Intelligent processing completed in {processing_time:.2f}s")

        # Step 6: Validate processing quality
        print("Step 6: Validating processing quality...")
        for result in processing_results:
            placeholder_name = result["placeholder"]
            processing_data = result["result"]
            
            # Check processing metadata
            metadata = processing_data["processing_metadata"]
            assert "confidence_score" in metadata, f"No confidence score for {placeholder_name}"
            assert "processing_method" in metadata, f"No processing method for {placeholder_name}"
            assert "data_sources_used" in metadata, f"No data sources info for {placeholder_name}"
            
            confidence = metadata["confidence_score"]
            assert confidence >= 0.7, f"Low confidence score for {placeholder_name}: {confidence}"
            
            # Validate processed value
            processed_value = processing_data["processed_value"]
            assert processed_value is not None, f"Null processed value for {placeholder_name}"
            assert len(str(processed_value)) > 0, f"Empty processed value for {placeholder_name}"
        
        print("✅ Processing quality validation passed")

        # Step 7: Test placeholder adaptation
        print("Step 7: Testing placeholder adaptation...")
        adaptation_request = {
            "template_id": template_id,
            "data_source_id": data_source_id,
            "adaptation_rules": {
                "language": "zh-CN",
                "format": "business_report",
                "tone": "professional",
                "detail_level": "comprehensive"
            },
            "context": {
                "report_purpose": "monthly_review",
                "audience": "management",
                "urgency": "normal"
            }
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/intelligent-placeholders/adapt",
            json=adaptation_request
        )
        assert response.status_code == 200, f"Placeholder adaptation failed: {response.text}"
        adaptation_result = response.json()
        
        assert adaptation_result.get("success", False), "Placeholder adaptation unsuccessful"
        assert "adapted_placeholders" in adaptation_result, "No adapted placeholders returned"
        
        adapted_placeholders = adaptation_result["adapted_placeholders"]
        assert len(adapted_placeholders) > 0, "No placeholders were adapted"
        
        # Verify adaptation quality
        for adapted in adapted_placeholders:
            assert "original_name" in adapted, "Original name missing"
            assert "adapted_value" in adapted, "Adapted value missing"
            assert "adaptation_metadata" in adapted, "Adaptation metadata missing"
            
            metadata = adapted["adaptation_metadata"]
            assert "adaptation_type" in metadata, "Adaptation type missing"
            assert "quality_score" in metadata, "Quality score missing"
        
        print(f"✅ Successfully adapted {len(adapted_placeholders)} placeholders")

    def test_intelligent_placeholder_learning_system(
        self,
        authenticated_session: Session,
        api_base_url: str,
        cleanup_e2e_data,
    ):
        """
        Test the intelligent placeholder learning system:
        1. Create training data
        2. Train placeholder models
        3. Test model predictions
        4. Update models with feedback
        """
        print("Testing intelligent placeholder learning system...")

        # Step 1: Create training data
        print("Step 1: Creating training data...")
        training_data = {
            "dataset_name": "E2E Placeholder Training",
            "description": "Training dataset for E2E testing",
            "training_examples": [
                {
                    "placeholder_name": "total_complaints",
                    "chinese_name": "投诉总数",
                    "context": "报告显示本月投诉总数为",
                    "data_source_fields": ["complaints.count"],
                    "expected_output": "1,234",
                    "output_type": "numeric",
                    "format": "comma_separated"
                },
                {
                    "placeholder_name": "avg_satisfaction_score",
                    "chinese_name": "平均满意度",
                    "context": "客户满意度评分平均为",
                    "data_source_fields": ["complaints.satisfaction_score"],
                    "expected_output": "4.2/5.0",
                    "output_type": "rating",
                    "format": "decimal_with_scale"
                },
                {
                    "placeholder_name": "top_complaint_category",
                    "chinese_name": "主要投诉类别",
                    "context": "最常见的投诉类别是",
                    "data_source_fields": ["complaints.category"],
                    "expected_output": "服务质量问题",
                    "output_type": "categorical",
                    "format": "text"
                }
            ]
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/learning/training-data", json=training_data
        )
        assert response.status_code == 201, f"Failed to create training data: {response.text}"
        training_dataset = response.json()
        dataset_id = training_dataset["id"]
        print(f"✅ Training dataset created with ID: {dataset_id}")

        # Step 2: Train placeholder models
        print("Step 2: Training placeholder models...")
        training_request = {
            "dataset_id": dataset_id,
            "model_type": "intelligent_placeholder",
            "training_config": {
                "algorithm": "neural_network",
                "epochs": 10,
                "batch_size": 32,
                "learning_rate": 0.001,
                "validation_split": 0.2
            }
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/learning/train-model", json=training_request
        )
        assert response.status_code == 200, f"Model training failed: {response.text}"
        training_result = response.json()
        
        assert training_result.get("success", False), "Model training unsuccessful"
        model_id = training_result.get("model_id")
        assert model_id is not None, "No model ID returned"
        
        # Wait for training completion
        max_wait_time = 120  # seconds
        wait_interval = 5    # seconds
        waited_time = 0
        
        while waited_time < max_wait_time:
            response = authenticated_session.get(
                f"{api_base_url}/learning/model-status/{model_id}"
            )
            if response.status_code == 200:
                status = response.json()
                if status.get("status") == "trained":
                    print("✅ Model training completed successfully")
                    break
                elif status.get("status") == "failed":
                    pytest.fail(f"Model training failed: {status.get('error_message')}")
            
            time.sleep(wait_interval)
            waited_time += wait_interval
        else:
            pytest.fail("Model training did not complete within timeout")

        # Step 3: Test model predictions
        print("Step 3: Testing model predictions...")
        prediction_requests = [
            {
                "model_id": model_id,
                "placeholder_name": "monthly_complaints",
                "chinese_name": "月度投诉量",
                "context": "本月收到的投诉数量为",
                "data_source_schema": {
                    "tables": ["complaints"],
                    "available_fields": ["id", "complaint_date", "category", "status"]
                }
            },
            {
                "model_id": model_id,
                "placeholder_name": "resolution_efficiency",
                "chinese_name": "解决效率",
                "context": "投诉解决效率指标显示",
                "data_source_schema": {
                    "tables": ["complaints", "resolutions"],
                    "available_fields": ["resolution_date", "complaint_date", "status"]
                }
            }
        ]
        
        for prediction_request in prediction_requests:
            response = authenticated_session.post(
                f"{api_base_url}/learning/predict", json=prediction_request
            )
            assert response.status_code == 200, f"Prediction failed: {response.text}"
            prediction_result = response.json()
            
            assert prediction_result.get("success", False), "Prediction unsuccessful"
            assert "predicted_mapping" in prediction_result, "No predicted mapping returned"
            assert "confidence_score" in prediction_result, "No confidence score returned"
            
            confidence = prediction_result["confidence_score"]
            assert 0 <= confidence <= 1, "Invalid confidence score"
            print(f"✅ Prediction successful with confidence: {confidence:.3f}")

        # Step 4: Update models with feedback
        print("Step 4: Updating models with feedback...")
        feedback_data = {
            "model_id": model_id,
            "feedback_examples": [
                {
                    "placeholder_name": "monthly_complaints",
                    "predicted_mapping": "complaints.count",
                    "actual_mapping": "complaints.id",
                    "feedback_type": "correction",
                    "user_rating": 4,
                    "comments": "Prediction was close but needed adjustment"
                },
                {
                    "placeholder_name": "resolution_efficiency",
                    "predicted_mapping": "avg(resolution_time)",
                    "actual_mapping": "avg(resolution_time)",
                    "feedback_type": "confirmation",
                    "user_rating": 5,
                    "comments": "Perfect prediction"
                }
            ]
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/learning/feedback", json=feedback_data
        )
        assert response.status_code == 200, f"Feedback submission failed: {response.text}"
        feedback_result = response.json()
        
        assert feedback_result.get("success", False), "Feedback submission unsuccessful"
        assert "model_updated" in feedback_result, "Model update status missing"
        print("✅ Model feedback submitted and processed")

        # Step 5: Verify model improvement
        print("Step 5: Verifying model improvement...")
        response = authenticated_session.get(
            f"{api_base_url}/learning/model-metrics/{model_id}"
        )
        assert response.status_code == 200, f"Failed to get model metrics: {response.text}"
        metrics = response.json()
        
        assert "accuracy" in metrics, "Accuracy metric missing"
        assert "precision" in metrics, "Precision metric missing"
        assert "recall" in metrics, "Recall metric missing"
        assert "f1_score" in metrics, "F1 score missing"
        
        accuracy = metrics["accuracy"]
        assert accuracy >= 0.7, f"Model accuracy too low: {accuracy}"
        print(f"✅ Model metrics verified - Accuracy: {accuracy:.3f}")

    def test_intelligent_placeholder_error_handling(
        self,
        authenticated_session: Session,
        api_base_url: str,
        cleanup_e2e_data,
    ):
        """
        Test error handling in intelligent placeholder processing:
        1. Invalid data source scenarios
        2. Malformed template scenarios
        3. Processing timeout scenarios
        4. Recovery mechanisms
        """
        print("Testing intelligent placeholder error handling...")

        # Step 1: Test invalid data source scenarios
        print("Step 1: Testing invalid data source scenarios...")
        
        # Test with non-existent data source
        invalid_request = {
            "template_id": 99999,
            "data_source_id": 99999,
            "placeholder_name": "test_placeholder",
            "processing_mode": "intelligent"
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/intelligent-placeholders/process",
            json=invalid_request
        )
        assert response.status_code == 404, "Should return 404 for non-existent data source"
        error_response = response.json()
        assert "error" in error_response, "Error message missing"
        print("✅ Invalid data source error handling works")

        # Step 2: Test malformed template scenarios
        print("Step 2: Testing malformed template scenarios...")
        
        # Create template with malformed placeholders
        malformed_template = {
            "name": "E2E Malformed Template",
            "description": "Template with malformed placeholders for error testing",
            "content": """
            # {{unclosed_placeholder
            ## {{nested{{placeholder}}}}
            ### {{|empty_name}}
            #### {{valid_placeholder}}
            """,
            "is_active": True
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/templates/", json=malformed_template
        )
        assert response.status_code == 201, f"Failed to create malformed template: {response.text}"
        malformed_template_obj = response.json()
        malformed_template_id = malformed_template_obj["id"]
        
        # Try to analyze malformed template
        response = authenticated_session.post(
            f"{api_base_url}/template-analysis/{malformed_template_id}/analyze"
        )
        assert response.status_code == 200, "Template analysis should handle malformed placeholders"
        analysis = response.json()
        
        # Should detect errors but not fail completely
        assert "errors" in analysis or "warnings" in analysis, "Should detect placeholder errors"
        print("✅ Malformed template error handling works")

        # Step 3: Test processing timeout scenarios
        print("Step 3: Testing processing timeout scenarios...")
        
        # Create a request that would take too long
        timeout_request = {
            "template_id": malformed_template_id,
            "data_source_id": 1,  # Assuming a valid data source exists
            "placeholder_name": "complex_calculation",
            "processing_mode": "intelligent",
            "timeout": 1,  # Very short timeout
            "context": {
                "complexity": "maximum",
                "data_size": "large"
            }
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/intelligent-placeholders/process",
            json=timeout_request
        )
        # Should either complete quickly or return timeout error
        assert response.status_code in [200, 408, 500], "Should handle timeout appropriately"
        
        if response.status_code != 200:
            error_response = response.json()
            assert "timeout" in str(error_response).lower() or "error" in error_response
        print("✅ Processing timeout error handling works")

        # Step 4: Test recovery mechanisms
        print("Step 4: Testing recovery mechanisms...")
        
        # Test graceful degradation
        degradation_request = {
            "template_id": malformed_template_id,
            "data_source_id": 1,
            "placeholder_name": "valid_placeholder",
            "processing_mode": "intelligent_with_fallback",
            "fallback_mode": "simple",
            "context": {
                "allow_degradation": True,
                "fallback_value": "Default Value"
            }
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/intelligent-placeholders/process",
            json=degradation_request
        )
        assert response.status_code == 200, f"Graceful degradation failed: {response.text}"
        result = response.json()
        
        # Should succeed with fallback
        assert result.get("success", False), "Graceful degradation should succeed"
        assert "fallback_used" in result.get("processing_metadata", {}), "Should indicate fallback was used"
        print("✅ Recovery mechanisms work correctly")

        print("✅ Intelligent placeholder error handling tests completed")