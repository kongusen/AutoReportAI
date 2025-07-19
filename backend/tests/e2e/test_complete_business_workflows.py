"""
Complete Business Workflow End-to-End Tests

This module tests complete user workflows from start to finish,
including data source setup, template creation, intelligent placeholder
processing, and report generation.
"""

import json
import time
from typing import Any, Dict, List

import pytest
import requests
from requests import Session


@pytest.mark.e2e
@pytest.mark.slow
class TestCompleteBusinessWorkflows:
    """Test complete business workflows end-to-end"""

    def test_complete_report_generation_workflow(
        self,
        authenticated_session: Session,
        api_base_url: str,
        sample_workflow_data: Dict[str, Any],
        performance_thresholds: Dict[str, float],
        cleanup_e2e_data,
    ):
        """
        Test the complete report generation workflow:
        1. Create data source
        2. Create template with placeholders
        3. Process intelligent placeholders
        4. Generate report
        5. Verify report quality
        """
        workflow_start_time = time.time()

        # Step 1: Create data source
        print("Step 1: Creating data source...")
        data_source_data = sample_workflow_data["data_source"]
        response = authenticated_session.post(
            f"{api_base_url}/data-sources/", json=data_source_data
        )
        assert response.status_code == 201, f"Failed to create data source: {response.text}"
        data_source = response.json()
        data_source_id = data_source["id"]
        print(f"✅ Data source created with ID: {data_source_id}")

        # Step 2: Test data source connection
        print("Step 2: Testing data source connection...")
        response = authenticated_session.post(
            f"{api_base_url}/data-sources/{data_source_id}/test"
        )
        assert response.status_code == 200, f"Data source connection test failed: {response.text}"
        connection_result = response.json()
        assert connection_result.get("success", False), "Data source connection failed"
        print("✅ Data source connection verified")

        # Step 3: Create template with intelligent placeholders
        print("Step 3: Creating template with intelligent placeholders...")
        template_data = sample_workflow_data["template"]
        template_data["data_source_id"] = data_source_id
        response = authenticated_session.post(
            f"{api_base_url}/templates/", json=template_data
        )
        assert response.status_code == 201, f"Failed to create template: {response.text}"
        template = response.json()
        template_id = template["id"]
        print(f"✅ Template created with ID: {template_id}")

        # Step 4: Analyze template for placeholders
        print("Step 4: Analyzing template for placeholders...")
        response = authenticated_session.post(
            f"{api_base_url}/templates/{template_id}/analyze"
        )
        assert response.status_code == 200, f"Template analysis failed: {response.text}"
        analysis_result = response.json()
        placeholders = analysis_result.get("placeholders", [])
        assert len(placeholders) > 0, "No placeholders found in template"
        print(f"✅ Found {len(placeholders)} placeholders in template")

        # Step 5: Process intelligent placeholders
        print("Step 5: Processing intelligent placeholders...")
        placeholder_start_time = time.time()
        
        for placeholder in placeholders:
            placeholder_data = {
                "template_id": template_id,
                "data_source_id": data_source_id,
                "placeholder_name": placeholder["name"],
                "context": placeholder.get("context", {}),
            }
            
            response = authenticated_session.post(
                f"{api_base_url}/intelligent-placeholders/process",
                json=placeholder_data
            )
            assert response.status_code == 200, f"Placeholder processing failed: {response.text}"
            processing_result = response.json()
            assert processing_result.get("success", False), "Placeholder processing failed"
            
        placeholder_end_time = time.time()
        placeholder_processing_time = placeholder_end_time - placeholder_start_time
        
        assert placeholder_processing_time < performance_thresholds["data_processing_time"], \
            f"Placeholder processing took too long: {placeholder_processing_time:.2f}s"
        print(f"✅ Intelligent placeholders processed in {placeholder_processing_time:.2f}s")

        # Step 6: Generate report
        print("Step 6: Generating report...")
        report_start_time = time.time()
        
        report_data = {
            "template_id": template_id,
            "data_source_id": data_source_id,
            "output_format": "docx",
            "parameters": {
                "date": "2024-01-15",
                "total_records": 1000
            }
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/reports/generate", json=report_data
        )
        assert response.status_code == 200, f"Report generation failed: {response.text}"
        report_result = response.json()
        
        report_end_time = time.time()
        report_generation_time = report_end_time - report_start_time
        
        assert report_generation_time < performance_thresholds["report_generation_time"], \
            f"Report generation took too long: {report_generation_time:.2f}s"
        print(f"✅ Report generated in {report_generation_time:.2f}s")

        # Step 7: Verify report quality
        print("Step 7: Verifying report quality...")
        report_id = report_result.get("report_id")
        if report_id:
            response = authenticated_session.get(
                f"{api_base_url}/reports/{report_id}/quality-check"
            )
            assert response.status_code == 200, f"Report quality check failed: {response.text}"
            quality_result = response.json()
            
            quality_score = quality_result.get("quality_score", 0)
            assert quality_score >= 0.8, f"Report quality too low: {quality_score}"
            print(f"✅ Report quality verified (score: {quality_score})")

        # Step 8: Download report
        print("Step 8: Downloading report...")
        if report_id:
            response = authenticated_session.get(
                f"{api_base_url}/reports/{report_id}/download"
            )
            assert response.status_code == 200, "Report download failed"
            assert len(response.content) > 0, "Downloaded report is empty"
            print("✅ Report downloaded successfully")

        workflow_end_time = time.time()
        total_workflow_time = workflow_end_time - workflow_start_time
        print(f"✅ Complete workflow finished in {total_workflow_time:.2f}s")

    def test_data_source_to_analytics_workflow(
        self,
        authenticated_session: Session,
        api_base_url: str,
        sample_workflow_data: Dict[str, Any],
        cleanup_e2e_data,
    ):
        """
        Test data source to analytics workflow:
        1. Create enhanced data source
        2. Run ETL job
        3. Generate analytics
        4. Create visualization
        """
        print("Testing data source to analytics workflow...")

        # Step 1: Create enhanced data source
        print("Step 1: Creating enhanced data source...")
        enhanced_data_source = {
            "name": "E2E Analytics Data Source",
            "description": "Enhanced data source for analytics testing",
            "source_type": "database",
            "connection_string": "sqlite:///analytics_test.db",
            "schema_config": {
                "tables": ["complaints", "resolutions"],
                "relationships": [
                    {"from": "complaints.id", "to": "resolutions.complaint_id"}
                ]
            },
            "is_active": True,
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/enhanced-data-sources/", json=enhanced_data_source
        )
        assert response.status_code == 201, f"Failed to create enhanced data source: {response.text}"
        enhanced_source = response.json()
        enhanced_source_id = enhanced_source["id"]
        print(f"✅ Enhanced data source created with ID: {enhanced_source_id}")

        # Step 2: Create and run ETL job
        print("Step 2: Creating and running ETL job...")
        etl_job_data = sample_workflow_data["etl_job"]
        etl_job_data["data_source_id"] = enhanced_source_id
        etl_job_data["target_schema"] = {
            "fact_table": "analytics_facts",
            "dimension_tables": ["time_dim", "category_dim"]
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/etl-jobs/", json=etl_job_data
        )
        assert response.status_code == 201, f"Failed to create ETL job: {response.text}"
        etl_job = response.json()
        etl_job_id = etl_job["id"]
        print(f"✅ ETL job created with ID: {etl_job_id}")

        # Run ETL job
        response = authenticated_session.post(
            f"{api_base_url}/etl-jobs/{etl_job_id}/run"
        )
        assert response.status_code == 200, f"ETL job execution failed: {response.text}"
        execution_result = response.json()
        
        # Wait for ETL job completion (with timeout)
        max_wait_time = 60  # seconds
        wait_interval = 2   # seconds
        waited_time = 0
        
        while waited_time < max_wait_time:
            response = authenticated_session.get(
                f"{api_base_url}/etl-jobs/{etl_job_id}/status"
            )
            if response.status_code == 200:
                status = response.json()
                if status.get("status") == "completed":
                    print("✅ ETL job completed successfully")
                    break
                elif status.get("status") == "failed":
                    pytest.fail(f"ETL job failed: {status.get('error_message')}")
            
            time.sleep(wait_interval)
            waited_time += wait_interval
        else:
            pytest.fail("ETL job did not complete within timeout")

        # Step 3: Generate analytics
        print("Step 3: Generating analytics...")
        analytics_request = {
            "data_source_id": enhanced_source_id,
            "analysis_type": "trend_analysis",
            "time_period": "last_30_days",
            "metrics": ["count", "avg_resolution_time", "satisfaction_score"]
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/analysis/generate", json=analytics_request
        )
        assert response.status_code == 200, f"Analytics generation failed: {response.text}"
        analytics_result = response.json()
        
        assert "insights" in analytics_result, "Analytics result missing insights"
        assert len(analytics_result["insights"]) > 0, "No insights generated"
        print(f"✅ Analytics generated with {len(analytics_result['insights'])} insights")

        # Step 4: Create visualization
        print("Step 4: Creating visualization...")
        visualization_request = {
            "data_source_id": enhanced_source_id,
            "chart_type": "line_chart",
            "x_axis": "date",
            "y_axis": "complaint_count",
            "title": "Complaint Trends Over Time"
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/analysis/visualize", json=visualization_request
        )
        assert response.status_code == 200, f"Visualization creation failed: {response.text}"
        visualization_result = response.json()
        
        assert "chart_data" in visualization_result, "Visualization result missing chart data"
        assert "chart_config" in visualization_result, "Visualization result missing chart config"
        print("✅ Visualization created successfully")

    def test_user_management_workflow(
        self,
        admin_session: Session,
        api_base_url: str,
        cleanup_e2e_data,
    ):
        """
        Test user management workflow:
        1. Create user
        2. Assign roles
        3. Test permissions
        4. Update user profile
        5. Deactivate user
        """
        print("Testing user management workflow...")

        # Step 1: Create new user
        print("Step 1: Creating new user...")
        new_user_data = {
            "username": "e2e_test_user_workflow",
            "email": "e2e_workflow@test.com",
            "password": "TestPassword123!",
            "is_active": True,
            "is_superuser": False
        }
        
        response = admin_session.post(
            f"{api_base_url}/users/", json=new_user_data
        )
        assert response.status_code == 201, f"Failed to create user: {response.text}"
        new_user = response.json()
        user_id = new_user["id"]
        print(f"✅ User created with ID: {user_id}")

        # Step 2: Create user profile
        print("Step 2: Creating user profile...")
        profile_data = {
            "user_id": user_id,
            "full_name": "E2E Test User",
            "department": "Quality Assurance",
            "preferences": {
                "theme": "light",
                "language": "en",
                "notifications": True
            }
        }
        
        response = admin_session.post(
            f"{api_base_url}/user-profile/", json=profile_data
        )
        assert response.status_code == 201, f"Failed to create user profile: {response.text}"
        profile = response.json()
        print("✅ User profile created successfully")

        # Step 3: Test user login
        print("Step 3: Testing user login...")
        login_data = {
            "username": new_user_data["username"],
            "password": new_user_data["password"]
        }
        
        response = requests.post(
            f"{api_base_url}/auth/access-token", data=login_data
        )
        assert response.status_code == 200, f"User login failed: {response.text}"
        token_data = response.json()
        assert "access_token" in token_data, "Access token not returned"
        print("✅ User login successful")

        # Step 4: Test user permissions
        print("Step 4: Testing user permissions...")
        user_session = requests.Session()
        user_session.headers.update({"Authorization": f"Bearer {token_data['access_token']}"})
        
        # Test read access to templates
        response = user_session.get(f"{api_base_url}/templates/")
        assert response.status_code == 200, "User should have read access to templates"
        
        # Test that user cannot access admin endpoints
        response = user_session.get(f"{api_base_url}/users/")
        assert response.status_code == 403, "User should not have admin access"
        print("✅ User permissions working correctly")

        # Step 5: Update user profile
        print("Step 5: Updating user profile...")
        updated_profile = {
            "full_name": "Updated E2E Test User",
            "department": "Data Analytics",
            "preferences": {
                "theme": "dark",
                "language": "zh",
                "notifications": False
            }
        }
        
        response = admin_session.put(
            f"{api_base_url}/user-profile/{profile['id']}", json=updated_profile
        )
        assert response.status_code == 200, f"Failed to update user profile: {response.text}"
        print("✅ User profile updated successfully")

        # Step 6: Deactivate user
        print("Step 6: Deactivating user...")
        response = admin_session.put(
            f"{api_base_url}/users/{user_id}", json={"is_active": False}
        )
        assert response.status_code == 200, f"Failed to deactivate user: {response.text}"
        
        # Verify user cannot login after deactivation
        response = requests.post(
            f"{api_base_url}/auth/access-token", data=login_data
        )
        assert response.status_code == 401, "Deactivated user should not be able to login"
        print("✅ User deactivated successfully")

    def test_template_lifecycle_workflow(
        self,
        authenticated_session: Session,
        api_base_url: str,
        sample_workflow_data: Dict[str, Any],
        cleanup_e2e_data,
    ):
        """
        Test complete template lifecycle:
        1. Create template
        2. Analyze placeholders
        3. Configure intelligent mappings
        4. Test template with sample data
        5. Version template
        6. Archive template
        """
        print("Testing template lifecycle workflow...")

        # Step 1: Create template
        print("Step 1: Creating template...")
        template_data = {
            "name": "E2E Lifecycle Template",
            "description": "Template for testing complete lifecycle",
            "content": """
            # {{report_title}}
            
            ## Summary
            This report covers the period from {{start_date}} to {{end_date}}.
            Total records processed: {{total_records}}
            
            ## Key Metrics
            - Average processing time: {{avg_processing_time}} seconds
            - Success rate: {{success_rate}}%
            - Error count: {{error_count}}
            
            ## Detailed Analysis
            {{detailed_analysis}}
            
            ## Recommendations
            {{recommendations}}
            """,
            "is_active": True,
            "category": "analytics"
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/templates/", json=template_data
        )
        assert response.status_code == 201, f"Failed to create template: {response.text}"
        template = response.json()
        template_id = template["id"]
        print(f"✅ Template created with ID: {template_id}")

        # Step 2: Analyze template placeholders
        print("Step 2: Analyzing template placeholders...")
        response = authenticated_session.post(
            f"{api_base_url}/template-analysis/{template_id}/analyze"
        )
        assert response.status_code == 200, f"Template analysis failed: {response.text}"
        analysis = response.json()
        
        placeholders = analysis.get("placeholders", [])
        assert len(placeholders) >= 7, f"Expected at least 7 placeholders, found {len(placeholders)}"
        print(f"✅ Found {len(placeholders)} placeholders")

        # Step 3: Configure intelligent mappings
        print("Step 3: Configuring intelligent mappings...")
        for placeholder in placeholders:
            mapping_data = {
                "template_id": template_id,
                "placeholder_name": placeholder["name"],
                "mapping_type": "intelligent",
                "data_source_field": f"auto_mapped_{placeholder['name']}",
                "transformation_rules": {
                    "format": "auto",
                    "validation": "auto"
                }
            }
            
            response = authenticated_session.post(
                f"{api_base_url}/mapping-management/", json=mapping_data
            )
            assert response.status_code == 201, f"Failed to create mapping for {placeholder['name']}: {response.text}"
        
        print("✅ Intelligent mappings configured")

        # Step 4: Test template with sample data
        print("Step 4: Testing template with sample data...")
        test_data = {
            "template_id": template_id,
            "sample_data": {
                "report_title": "Monthly Performance Report",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "total_records": 5000,
                "avg_processing_time": 2.5,
                "success_rate": 98.5,
                "error_count": 75,
                "detailed_analysis": "Performance was excellent this month...",
                "recommendations": "Continue current optimization strategies..."
            }
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/templates/{template_id}/test", json=test_data
        )
        assert response.status_code == 200, f"Template test failed: {response.text}"
        test_result = response.json()
        
        assert test_result.get("success", False), "Template test was not successful"
        assert "rendered_content" in test_result, "Rendered content not returned"
        print("✅ Template tested successfully")

        # Step 5: Create template version
        print("Step 5: Creating template version...")
        version_data = {
            "template_id": template_id,
            "version_notes": "Initial version after E2E testing",
            "is_major_version": True
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/templates/{template_id}/versions", json=version_data
        )
        assert response.status_code == 201, f"Failed to create template version: {response.text}"
        version = response.json()
        print(f"✅ Template version {version['version_number']} created")

        # Step 6: Archive template
        print("Step 6: Archiving template...")
        response = authenticated_session.put(
            f"{api_base_url}/templates/{template_id}", 
            json={"is_active": False, "status": "archived"}
        )
        assert response.status_code == 200, f"Failed to archive template: {response.text}"
        
        # Verify template is archived
        response = authenticated_session.get(f"{api_base_url}/templates/{template_id}")
        assert response.status_code == 200
        updated_template = response.json()
        assert updated_template["is_active"] == False
        print("✅ Template archived successfully")

        print("✅ Complete template lifecycle workflow finished")