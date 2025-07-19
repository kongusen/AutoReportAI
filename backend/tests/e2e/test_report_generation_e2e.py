"""
Report Generation End-to-End Tests

This module tests the complete report generation system including
template processing, data integration, content generation, and quality checking.
"""

import json
import time
from typing import Any, Dict, List

import pytest
import requests
from requests import Session


@pytest.mark.e2e
@pytest.mark.slow
class TestReportGenerationE2E:
    """Test report generation system end-to-end"""

    def test_complete_report_generation_pipeline(
        self,
        authenticated_session: Session,
        api_base_url: str,
        sample_workflow_data: Dict[str, Any],
        performance_thresholds: Dict[str, float],
        cleanup_e2e_data,
    ):
        """
        Test complete report generation pipeline:
        1. Setup data source and template
        2. Process template analysis
        3. Generate report with AI enhancement
        4. Quality check and validation
        5. Export in multiple formats
        """
        print("Testing complete report generation pipeline...")

        # Step 1: Setup comprehensive data source
        print("Step 1: Setting up comprehensive data source...")
        comprehensive_data_source = {
            "name": "E2E Report Generation Data Source",
            "description": "Comprehensive data source for report generation testing",
            "source_type": "database",
            "connection_string": "sqlite:///report_generation_test.db",
            "schema_config": {
                "tables": {
                    "monthly_stats": {
                        "columns": [
                            {"name": "id", "type": "integer", "primary_key": True},
                            {"name": "month", "type": "string"},
                            {"name": "total_complaints", "type": "integer"},
                            {"name": "resolved_complaints", "type": "integer"},
                            {"name": "avg_resolution_time", "type": "float"},
                            {"name": "satisfaction_score", "type": "float"},
                            {"name": "category_breakdown", "type": "json"},
                            {"name": "regional_data", "type": "json"},
                        ]
                    },
                    "performance_metrics": {
                        "columns": [
                            {"name": "id", "type": "integer", "primary_key": True},
                            {"name": "metric_name", "type": "string"},
                            {"name": "metric_value", "type": "float"},
                            {"name": "target_value", "type": "float"},
                            {"name": "trend", "type": "string"},
                            {"name": "last_updated", "type": "datetime"},
                        ]
                    }
                }
            },
            "is_active": True,
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/data-sources/", json=comprehensive_data_source
        )
        assert response.status_code == 201, f"Failed to create data source: {response.text}"
        data_source = response.json()
        data_source_id = data_source["id"]
        print(f"✅ Comprehensive data source created with ID: {data_source_id}")

        # Step 2: Create comprehensive report template
        print("Step 2: Creating comprehensive report template...")
        comprehensive_template = {
            "name": "E2E Comprehensive Report Template",
            "description": "Comprehensive template for report generation testing",
            "content": """
            # {{报告标题|report_title}}
            
            **报告生成时间：** {{生成时间|generation_time}}
            **报告期间：** {{报告期间|report_period}}
            
            ## 执行摘要
            {{执行摘要|executive_summary}}
            
            ## 关键指标概览
            
            ### 投诉处理统计
            - **总投诉数：** {{总投诉数|total_complaints}}
            - **已解决投诉：** {{已解决投诉|resolved_complaints}}
            - **解决率：** {{解决率|resolution_rate}}%
            - **平均解决时间：** {{平均解决时间|avg_resolution_time}} 天
            
            ### 客户满意度
            - **整体满意度：** {{整体满意度|overall_satisfaction}}/5.0
            - **满意度趋势：** {{满意度趋势|satisfaction_trend}}
            
            ## 详细分析
            
            ### 投诉类别分析
            {{投诉类别分析|category_analysis}}
            
            ### 地区分布分析
            {{地区分布分析|regional_analysis}}
            
            ### 性能指标分析
            {{性能指标分析|performance_analysis}}
            
            ## 趋势分析
            {{趋势分析图表|trend_charts}}
            
            ## 对比分析
            {{同期对比|period_comparison}}
            
            ## 问题识别
            {{问题识别|issue_identification}}
            
            ## 改进建议
            {{改进建议|improvement_recommendations}}
            
            ## 行动计划
            {{行动计划|action_plan}}
            
            ## 附录
            
            ### 详细数据表
            {{详细数据表|detailed_data_table}}
            
            ### 统计图表
            {{统计图表|statistical_charts}}
            
            ### 技术说明
            {{技术说明|technical_notes}}
            """,
            "data_source_id": data_source_id,
            "is_active": True,
            "category": "comprehensive_report",
            "metadata": {
                "report_type": "monthly_analysis",
                "complexity": "high",
                "ai_enhancement": True
            }
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/templates/", json=comprehensive_template
        )
        assert response.status_code == 201, f"Failed to create template: {response.text}"
        template = response.json()
        template_id = template["id"]
        print(f"✅ Comprehensive template created with ID: {template_id}")

        # Step 3: Process template analysis
        print("Step 3: Processing template analysis...")
        response = authenticated_session.post(
            f"{api_base_url}/template-analysis/{template_id}/analyze"
        )
        assert response.status_code == 200, f"Template analysis failed: {response.text}"
        analysis = response.json()
        
        placeholders = analysis.get("placeholders", [])
        assert len(placeholders) >= 15, f"Expected at least 15 placeholders, found {len(placeholders)}"
        
        # Verify analysis quality
        assert "complexity_score" in analysis, "Complexity score missing"
        assert "estimated_generation_time" in analysis, "Estimated generation time missing"
        complexity_score = analysis["complexity_score"]
        assert 0 <= complexity_score <= 1, "Invalid complexity score"
        print(f"✅ Template analysis completed - Complexity: {complexity_score:.3f}")

        # Step 4: Generate report with AI enhancement
        print("Step 4: Generating report with AI enhancement...")
        generation_start_time = time.time()
        
        report_generation_request = {
            "template_id": template_id,
            "data_source_id": data_source_id,
            "generation_config": {
                "ai_enhancement": True,
                "quality_level": "high",
                "language": "zh-CN",
                "format": "comprehensive",
                "include_charts": True,
                "include_analysis": True
            },
            "parameters": {
                "report_period": "2024年1月",
                "generation_time": "2024-01-31 15:30:00",
                "report_title": "月度客户服务质量分析报告"
            },
            "output_formats": ["docx", "pdf", "html"]
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/report-generation/generate",
            json=report_generation_request
        )
        assert response.status_code == 200, f"Report generation failed: {response.text}"
        generation_result = response.json()
        
        assert generation_result.get("success", False), "Report generation unsuccessful"
        report_id = generation_result.get("report_id")
        assert report_id is not None, "No report ID returned"
        
        # Monitor generation progress
        max_wait_time = 180  # 3 minutes
        wait_interval = 5    # seconds
        waited_time = 0
        
        while waited_time < max_wait_time:
            response = authenticated_session.get(
                f"{api_base_url}/report-generation/status/{report_id}"
            )
            if response.status_code == 200:
                status = response.json()
                current_status = status.get("status")
                
                if current_status == "completed":
                    generation_end_time = time.time()
                    generation_time = generation_end_time - generation_start_time
                    print(f"✅ Report generation completed in {generation_time:.2f}s")
                    break
                elif current_status == "failed":
                    error_msg = status.get("error_message", "Unknown error")
                    pytest.fail(f"Report generation failed: {error_msg}")
                else:
                    print(f"Generation status: {current_status} ({status.get('progress', 0)}%)")
            
            time.sleep(wait_interval)
            waited_time += wait_interval
        else:
            pytest.fail("Report generation did not complete within timeout")

        # Step 5: Quality check and validation
        print("Step 5: Performing quality check and validation...")
        response = authenticated_session.post(
            f"{api_base_url}/report-generation/{report_id}/quality-check"
        )
        assert response.status_code == 200, f"Quality check failed: {response.text}"
        quality_result = response.json()
        
        assert quality_result.get("success", False), "Quality check unsuccessful"
        quality_metrics = quality_result.get("quality_metrics", {})
        
        # Validate quality metrics
        required_metrics = [
            "content_completeness",
            "data_accuracy",
            "formatting_quality",
            "language_quality",
            "overall_score"
        ]
        
        for metric in required_metrics:
            assert metric in quality_metrics, f"Quality metric '{metric}' missing"
            score = quality_metrics[metric]
            assert 0 <= score <= 1, f"Invalid score for {metric}: {score}"
        
        overall_score = quality_metrics["overall_score"]
        assert overall_score >= 0.8, f"Overall quality score too low: {overall_score}"
        print(f"✅ Quality check passed - Overall score: {overall_score:.3f}")

        # Step 6: Export in multiple formats
        print("Step 6: Exporting in multiple formats...")
        export_formats = ["docx", "pdf", "html"]
        exported_files = {}
        
        for format_type in export_formats:
            response = authenticated_session.get(
                f"{api_base_url}/report-generation/{report_id}/export/{format_type}"
            )
            assert response.status_code == 200, f"Export to {format_type} failed"
            
            # Verify file content
            content = response.content
            assert len(content) > 0, f"Exported {format_type} file is empty"
            
            # Basic format validation
            if format_type == "pdf":
                assert content.startswith(b"%PDF"), "Invalid PDF format"
            elif format_type == "html":
                assert b"<html" in content or b"<!DOCTYPE" in content, "Invalid HTML format"
            
            exported_files[format_type] = len(content)
            print(f"✅ Exported {format_type} file ({len(content)} bytes)")
        
        print(f"✅ All formats exported successfully")

        # Step 7: Verify report content
        print("Step 7: Verifying report content...")
        response = authenticated_session.get(
            f"{api_base_url}/report-generation/{report_id}/content"
        )
        assert response.status_code == 200, f"Failed to get report content: {response.text}"
        content_result = response.json()
        
        report_content = content_result.get("content", "")
        assert len(report_content) > 1000, "Report content too short"
        
        # Verify placeholder replacement
        assert "{{" not in report_content, "Unreplaced placeholders found"
        assert "}}" not in report_content, "Unreplaced placeholders found"
        
        # Verify Chinese content
        chinese_chars = sum(1 for char in report_content if '\u4e00' <= char <= '\u9fff')
        assert chinese_chars > 100, "Insufficient Chinese content"
        
        print("✅ Report content verification passed")

    def test_batch_report_generation(
        self,
        authenticated_session: Session,
        api_base_url: str,
        sample_workflow_data: Dict[str, Any],
        performance_thresholds: Dict[str, float],
        cleanup_e2e_data,
    ):
        """
        Test batch report generation:
        1. Create multiple templates
        2. Setup batch generation job
        3. Monitor batch progress
        4. Validate all reports
        """
        print("Testing batch report generation...")

        # Step 1: Create multiple templates
        print("Step 1: Creating multiple templates for batch generation...")
        templates = []
        template_configs = [
            {
                "name": "E2E Batch Template 1 - Summary",
                "content": "# 摘要报告\n总投诉数：{{total_complaints}}\n解决率：{{resolution_rate}}%",
                "category": "summary"
            },
            {
                "name": "E2E Batch Template 2 - Detailed",
                "content": "# 详细报告\n## 分析\n{{detailed_analysis}}\n## 建议\n{{recommendations}}",
                "category": "detailed"
            },
            {
                "name": "E2E Batch Template 3 - Charts",
                "content": "# 图表报告\n{{trend_chart}}\n{{category_chart}}\n{{regional_chart}}",
                "category": "charts"
            }
        ]
        
        for config in template_configs:
            template_data = {
                **config,
                "description": f"Batch generation template - {config['category']}",
                "is_active": True
            }
            
            response = authenticated_session.post(
                f"{api_base_url}/templates/", json=template_data
            )
            assert response.status_code == 201, f"Failed to create template: {response.text}"
            template = response.json()
            templates.append(template)
        
        print(f"✅ Created {len(templates)} templates for batch generation")

        # Step 2: Setup batch generation job
        print("Step 2: Setting up batch generation job...")
        batch_job_config = {
            "job_name": "E2E Batch Report Generation",
            "description": "Batch job for E2E testing",
            "templates": [
                {
                    "template_id": template["id"],
                    "output_formats": ["docx", "pdf"],
                    "parameters": {
                        "report_date": "2024-01-31",
                        "total_complaints": 1500,
                        "resolution_rate": 95.5,
                        "detailed_analysis": "详细分析内容...",
                        "recommendations": "改进建议...",
                        "trend_chart": "[趋势图表]",
                        "category_chart": "[类别图表]",
                        "regional_chart": "[地区图表]"
                    }
                }
                for template in templates
            ],
            "generation_config": {
                "parallel_processing": True,
                "max_concurrent": 3,
                "quality_check": True,
                "ai_enhancement": False  # Disable for faster batch processing
            },
            "notification_config": {
                "notify_on_completion": True,
                "notify_on_error": True
            }
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/report-generation/batch", json=batch_job_config
        )
        assert response.status_code == 200, f"Batch job creation failed: {response.text}"
        batch_result = response.json()
        
        assert batch_result.get("success", False), "Batch job creation unsuccessful"
        batch_job_id = batch_result.get("job_id")
        assert batch_job_id is not None, "No batch job ID returned"
        print(f"✅ Batch job created with ID: {batch_job_id}")

        # Step 3: Monitor batch progress
        print("Step 3: Monitoring batch progress...")
        batch_start_time = time.time()
        max_wait_time = 300  # 5 minutes
        wait_interval = 10   # seconds
        waited_time = 0
        
        while waited_time < max_wait_time:
            response = authenticated_session.get(
                f"{api_base_url}/report-generation/batch/{batch_job_id}/status"
            )
            assert response.status_code == 200, f"Failed to get batch status: {response.text}"
            status = response.json()
            
            current_status = status.get("status")
            progress = status.get("progress", {})
            
            completed = progress.get("completed", 0)
            total = progress.get("total", 0)
            failed = progress.get("failed", 0)
            
            print(f"Batch progress: {completed}/{total} completed, {failed} failed")
            
            if current_status == "completed":
                batch_end_time = time.time()
                batch_time = batch_end_time - batch_start_time
                print(f"✅ Batch generation completed in {batch_time:.2f}s")
                break
            elif current_status == "failed":
                error_msg = status.get("error_message", "Unknown error")
                pytest.fail(f"Batch generation failed: {error_msg}")
            
            time.sleep(wait_interval)
            waited_time += wait_interval
        else:
            pytest.fail("Batch generation did not complete within timeout")

        # Step 4: Validate all reports
        print("Step 4: Validating all generated reports...")
        response = authenticated_session.get(
            f"{api_base_url}/report-generation/batch/{batch_job_id}/results"
        )
        assert response.status_code == 200, f"Failed to get batch results: {response.text}"
        results = response.json()
        
        generated_reports = results.get("reports", [])
        assert len(generated_reports) == len(templates), f"Expected {len(templates)} reports, got {len(generated_reports)}"
        
        for report in generated_reports:
            report_id = report["report_id"]
            template_id = report["template_id"]
            status = report["status"]
            
            assert status == "completed", f"Report {report_id} not completed: {status}"
            
            # Validate each report
            response = authenticated_session.get(
                f"{api_base_url}/report-generation/{report_id}/content"
            )
            assert response.status_code == 200, f"Failed to get report content for {report_id}"
            content_result = response.json()
            
            content = content_result.get("content", "")
            assert len(content) > 50, f"Report {report_id} content too short"
            assert "{{" not in content, f"Unreplaced placeholders in report {report_id}"
            
            print(f"✅ Report {report_id} validated successfully")
        
        print("✅ All batch reports validated successfully")

    def test_report_generation_with_ai_enhancement(
        self,
        authenticated_session: Session,
        api_base_url: str,
        cleanup_e2e_data,
    ):
        """
        Test report generation with AI enhancement:
        1. Create AI-enhanced template
        2. Configure AI providers
        3. Generate report with AI features
        4. Validate AI-generated content
        """
        print("Testing report generation with AI enhancement...")

        # Step 1: Create AI-enhanced template
        print("Step 1: Creating AI-enhanced template...")
        ai_template = {
            "name": "E2E AI-Enhanced Report Template",
            "description": "Template with AI enhancement features",
            "content": """
            # {{报告标题|report_title}}
            
            ## AI生成的执行摘要
            {{AI摘要|ai_executive_summary|ai_generate}}
            
            ## 数据分析
            基础数据：{{基础数据|raw_data}}
            
            ## AI洞察分析
            {{AI洞察|ai_insights|ai_analyze}}
            
            ## 趋势预测
            {{趋势预测|trend_prediction|ai_predict}}
            
            ## AI生成的建议
            {{AI建议|ai_recommendations|ai_recommend}}
            
            ## 智能图表描述
            {{图表描述|chart_description|ai_describe_chart}}
            """,
            "is_active": True,
            "category": "ai_enhanced",
            "ai_config": {
                "enable_ai": True,
                "ai_features": [
                    "content_generation",
                    "data_analysis",
                    "trend_prediction",
                    "recommendation_generation",
                    "chart_description"
                ],
                "ai_model": "gpt-3.5-turbo",
                "creativity_level": 0.7,
                "language": "zh-CN"
            }
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/templates/", json=ai_template
        )
        assert response.status_code == 201, f"Failed to create AI template: {response.text}"
        template = response.json()
        template_id = template["id"]
        print(f"✅ AI-enhanced template created with ID: {template_id}")

        # Step 2: Configure AI providers (check if available)
        print("Step 2: Checking AI provider configuration...")
        response = authenticated_session.get(f"{api_base_url}/ai-providers/")
        assert response.status_code == 200, f"Failed to get AI providers: {response.text}"
        ai_providers = response.json()
        
        active_providers = [p for p in ai_providers if p.get("is_active", False)]
        if len(active_providers) == 0:
            print("⚠️  No active AI providers found, creating mock provider...")
            
            # Create a mock AI provider for testing
            mock_provider = {
                "provider_name": "Mock AI Provider",
                "provider_type": "openai",
                "api_key": "mock-api-key-for-testing",
                "api_endpoint": "https://api.mock-ai.com/v1",
                "model_config": {
                    "default_model": "mock-gpt-3.5-turbo",
                    "max_tokens": 2000,
                    "temperature": 0.7
                },
                "is_active": True
            }
            
            response = authenticated_session.post(
                f"{api_base_url}/ai-providers/", json=mock_provider
            )
            assert response.status_code == 201, f"Failed to create mock AI provider: {response.text}"
            provider = response.json()
            print(f"✅ Mock AI provider created with ID: {provider['id']}")
        else:
            print(f"✅ Found {len(active_providers)} active AI providers")

        # Step 3: Generate report with AI features
        print("Step 3: Generating report with AI features...")
        ai_generation_request = {
            "template_id": template_id,
            "generation_config": {
                "ai_enhancement": True,
                "ai_features": {
                    "generate_summary": True,
                    "analyze_data": True,
                    "predict_trends": True,
                    "generate_recommendations": True,
                    "describe_charts": True
                },
                "quality_level": "high",
                "language": "zh-CN"
            },
            "parameters": {
                "report_title": "AI增强月度分析报告",
                "raw_data": {
                    "complaints": 1200,
                    "resolutions": 1140,
                    "avg_time": 2.5,
                    "satisfaction": 4.2,
                    "categories": {
                        "service": 45,
                        "product": 30,
                        "billing": 25
                    }
                }
            },
            "ai_context": {
                "report_type": "monthly_analysis",
                "industry": "customer_service",
                "audience": "management",
                "tone": "professional"
            }
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/report-generation/generate-ai",
            json=ai_generation_request
        )
        
        # Handle case where AI features might not be fully available
        if response.status_code == 503:  # Service unavailable
            print("⚠️  AI services not available, testing fallback...")
            # Test fallback to non-AI generation
            fallback_request = {
                "template_id": template_id,
                "generation_config": {
                    "ai_enhancement": False,
                    "fallback_mode": True
                },
                "parameters": ai_generation_request["parameters"]
            }
            
            response = authenticated_session.post(
                f"{api_base_url}/report-generation/generate",
                json=fallback_request
            )
        
        assert response.status_code == 200, f"AI report generation failed: {response.text}"
        generation_result = response.json()
        
        assert generation_result.get("success", False), "AI report generation unsuccessful"
        report_id = generation_result.get("report_id")
        assert report_id is not None, "No report ID returned"
        
        # Wait for AI generation completion
        max_wait_time = 240  # 4 minutes for AI processing
        wait_interval = 10   # seconds
        waited_time = 0
        
        while waited_time < max_wait_time:
            response = authenticated_session.get(
                f"{api_base_url}/report-generation/status/{report_id}"
            )
            if response.status_code == 200:
                status = response.json()
                current_status = status.get("status")
                
                if current_status == "completed":
                    print("✅ AI-enhanced report generation completed")
                    break
                elif current_status == "failed":
                    error_msg = status.get("error_message", "Unknown error")
                    pytest.fail(f"AI report generation failed: {error_msg}")
                else:
                    ai_progress = status.get("ai_progress", {})
                    print(f"AI generation status: {current_status} - {ai_progress}")
            
            time.sleep(wait_interval)
            waited_time += wait_interval
        else:
            pytest.fail("AI report generation did not complete within timeout")

        # Step 4: Validate AI-generated content
        print("Step 4: Validating AI-generated content...")
        response = authenticated_session.get(
            f"{api_base_url}/report-generation/{report_id}/content"
        )
        assert response.status_code == 200, f"Failed to get AI report content: {response.text}"
        content_result = response.json()
        
        report_content = content_result.get("content", "")
        ai_metadata = content_result.get("ai_metadata", {})
        
        # Validate content quality
        assert len(report_content) > 500, "AI-generated content too short"
        assert "{{" not in report_content, "Unreplaced placeholders in AI report"
        
        # Validate AI metadata
        if ai_metadata:  # Only if AI was actually used
            assert "ai_features_used" in ai_metadata, "AI features metadata missing"
            assert "generation_stats" in ai_metadata, "AI generation stats missing"
            
            features_used = ai_metadata["ai_features_used"]
            assert len(features_used) > 0, "No AI features were used"
            print(f"✅ AI features used: {', '.join(features_used)}")
        
        # Validate Chinese content quality
        chinese_chars = sum(1 for char in report_content if '\u4e00' <= char <= '\u9fff')
        assert chinese_chars > 200, "Insufficient Chinese content in AI report"
        
        print("✅ AI-enhanced report content validation passed")

        # Step 5: Test AI content quality assessment
        print("Step 5: Testing AI content quality assessment...")
        response = authenticated_session.post(
            f"{api_base_url}/report-generation/{report_id}/ai-quality-check"
        )
        
        if response.status_code == 200:
            quality_result = response.json()
            
            if quality_result.get("success", False):
                ai_quality_metrics = quality_result.get("ai_quality_metrics", {})
                
                expected_metrics = [
                    "content_coherence",
                    "language_fluency",
                    "factual_accuracy",
                    "relevance_score"
                ]
                
                for metric in expected_metrics:
                    if metric in ai_quality_metrics:
                        score = ai_quality_metrics[metric]
                        assert 0 <= score <= 1, f"Invalid AI quality score for {metric}: {score}"
                
                print("✅ AI content quality assessment completed")
            else:
                print("⚠️  AI quality assessment not available")
        else:
            print("⚠️  AI quality assessment endpoint not available")

        print("✅ AI-enhanced report generation test completed")