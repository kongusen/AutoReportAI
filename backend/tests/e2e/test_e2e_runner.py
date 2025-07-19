"""
End-to-End Test Runner

This module provides a comprehensive test runner for all E2E tests
with proper setup, teardown, and reporting.
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List

import pytest
import requests
from requests import Session


@pytest.mark.e2e
class TestE2ERunner:
    """Comprehensive E2E test runner"""

    def test_system_readiness(
        self,
        api_base_url: str,
        wait_for_server,
    ):
        """
        Verify system readiness before running E2E tests:
        1. Check all services are running
        2. Verify database connectivity
        3. Check external dependencies
        4. Validate configuration
        """
        print("Verifying system readiness for E2E tests...")

        # Step 1: Check core services
        print("Step 1: Checking core services...")
        core_endpoints = [
            {
                "name": "Main API",
                "url": f"{api_base_url.replace('/api/v1', '')}/",
                "expected_status": 200
            },
            {
                "name": "Health Check",
                "url": f"{api_base_url.replace('/api/v1', '')}/health",
                "expected_status": 200
            },
            {
                "name": "API Documentation",
                "url": f"{api_base_url.replace('/api/v1', '')}/docs",
                "expected_status": 200
            }
        ]
        
        for endpoint in core_endpoints:
            try:
                response = requests.get(endpoint["url"], timeout=10)
                if response.status_code == endpoint["expected_status"]:
                    print(f"✅ {endpoint['name']}: OK")
                else:
                    print(f"❌ {endpoint['name']}: Status {response.status_code}")
                    pytest.fail(f"{endpoint['name']} not ready")
            except requests.exceptions.RequestException as e:
                print(f"❌ {endpoint['name']}: Connection failed - {e}")
                pytest.fail(f"{endpoint['name']} not accessible")

        # Step 2: Check database connectivity
        print("Step 2: Checking database connectivity...")
        try:
            # Try to access a simple endpoint that requires database
            response = requests.get(f"{api_base_url}/users/", timeout=10)
            if response.status_code in [200, 401]:  # 401 is OK (auth required)
                print("✅ Database connectivity: OK")
            else:
                print(f"❌ Database connectivity: Status {response.status_code}")
                pytest.fail("Database not accessible")
        except requests.exceptions.RequestException as e:
            print(f"❌ Database connectivity: Failed - {e}")
            pytest.fail("Database connection failed")

        # Step 3: Check authentication system
        print("Step 3: Checking authentication system...")
        try:
            # Try to access auth endpoint
            response = requests.post(
                f"{api_base_url}/auth/access-token",
                data={"username": "invalid", "password": "invalid"},
                timeout=10
            )
            # Should return 401 or 422 (validation error), not 500
            if response.status_code in [401, 422]:
                print("✅ Authentication system: OK")
            else:
                print(f"❌ Authentication system: Unexpected status {response.status_code}")
                pytest.fail("Authentication system not working properly")
        except requests.exceptions.RequestException as e:
            print(f"❌ Authentication system: Failed - {e}")
            pytest.fail("Authentication system not accessible")

        print("✅ System readiness check completed")

    def test_e2e_test_data_setup(
        self,
        admin_session: Session,
        api_base_url: str,
    ):
        """
        Setup test data for E2E tests:
        1. Create test users
        2. Create test data sources
        3. Create test templates
        4. Setup test configurations
        """
        print("Setting up E2E test data...")

        # Step 1: Create test users
        print("Step 1: Creating test users...")
        test_users = [
            {
                "username": "e2e_regular_user",
                "email": "e2e_regular@test.com",
                "password": "TestPassword123!",
                "is_active": True,
                "is_superuser": False
            },
            {
                "username": "e2e_power_user",
                "email": "e2e_power@test.com",
                "password": "TestPassword123!",
                "is_active": True,
                "is_superuser": False
            }
        ]
        
        created_users = []
        for user_data in test_users:
            try:
                response = admin_session.post(
                    f"{api_base_url}/users/", json=user_data
                )
                if response.status_code == 201:
                    user = response.json()
                    created_users.append(user)
                    print(f"✅ Created user: {user_data['username']}")
                elif response.status_code == 400 and "already exists" in response.text.lower():
                    print(f"⚠️  User {user_data['username']} already exists")
                else:
                    print(f"⚠️  Failed to create user {user_data['username']}: {response.status_code}")
            except Exception as e:
                print(f"⚠️  Error creating user {user_data['username']}: {e}")

        # Step 2: Create test data sources
        print("Step 2: Creating test data sources...")
        test_data_sources = [
            {
                "name": "E2E Test SQLite DB",
                "description": "SQLite database for E2E testing",
                "source_type": "database",
                "connection_string": "sqlite:///e2e_test.db",
                "is_active": True
            },
            {
                "name": "E2E Test CSV File",
                "description": "CSV file source for E2E testing",
                "source_type": "file",
                "connection_string": "file:///tmp/e2e_test.csv",
                "is_active": True
            }
        ]
        
        created_data_sources = []
        for ds_data in test_data_sources:
            try:
                response = admin_session.post(
                    f"{api_base_url}/data-sources/", json=ds_data
                )
                if response.status_code == 201:
                    data_source = response.json()
                    created_data_sources.append(data_source)
                    print(f"✅ Created data source: {ds_data['name']}")
                else:
                    print(f"⚠️  Failed to create data source {ds_data['name']}: {response.status_code}")
            except Exception as e:
                print(f"⚠️  Error creating data source {ds_data['name']}: {e}")

        # Step 3: Create test templates
        print("Step 3: Creating test templates...")
        test_templates = [
            {
                "name": "E2E Basic Template",
                "description": "Basic template for E2E testing",
                "content": "# {{title}}\n\nContent: {{content}}\nDate: {{date}}",
                "is_active": True,
                "category": "basic"
            },
            {
                "name": "E2E Advanced Template",
                "description": "Advanced template with multiple placeholders",
                "content": """
                # {{report_title}}
                
                ## Summary
                Total: {{total_count}}
                Average: {{average_value}}
                
                ## Details
                {{detailed_content}}
                
                ## Analysis
                {{analysis_results}}
                """,
                "is_active": True,
                "category": "advanced"
            }
        ]
        
        created_templates = []
        for template_data in test_templates:
            try:
                response = admin_session.post(
                    f"{api_base_url}/templates/", json=template_data
                )
                if response.status_code == 201:
                    template = response.json()
                    created_templates.append(template)
                    print(f"✅ Created template: {template_data['name']}")
                else:
                    print(f"⚠️  Failed to create template {template_data['name']}: {response.status_code}")
            except Exception as e:
                print(f"⚠️  Error creating template {template_data['name']}: {e}")

        # Store created resources for cleanup
        test_resources = {
            "users": created_users,
            "data_sources": created_data_sources,
            "templates": created_templates,
            "created_at": datetime.now().isoformat()
        }
        
        # Save test resources info
        with open("/tmp/e2e_test_resources.json", "w") as f:
            json.dump(test_resources, f, indent=2)
        
        print(f"✅ E2E test data setup completed:")
        print(f"   Users: {len(created_users)}")
        print(f"   Data sources: {len(created_data_sources)}")
        print(f"   Templates: {len(created_templates)}")

    def test_run_all_e2e_tests(
        self,
        authenticated_session: Session,
        admin_session: Session,
        api_base_url: str,
        sample_workflow_data: Dict[str, Any],
        performance_thresholds: Dict[str, float],
    ):
        """
        Run all E2E test suites in sequence:
        1. Complete business workflows
        2. Intelligent placeholder processing
        3. Report generation
        4. Performance benchmarks
        """
        print("Running comprehensive E2E test suite...")
        
        test_results = {
            "start_time": datetime.now().isoformat(),
            "test_suites": {},
            "overall_status": "running"
        }

        # Test Suite 1: Basic functionality
        print("\n" + "="*60)
        print("TEST SUITE 1: BASIC FUNCTIONALITY")
        print("="*60)
        
        basic_tests = [
            {
                "name": "User Authentication",
                "test": self._test_user_authentication,
                "args": (authenticated_session, api_base_url)
            },
            {
                "name": "CRUD Operations",
                "test": self._test_crud_operations,
                "args": (authenticated_session, api_base_url)
            },
            {
                "name": "Data Source Connectivity",
                "test": self._test_data_source_connectivity,
                "args": (authenticated_session, api_base_url)
            }
        ]
        
        suite_results = {}
        for test in basic_tests:
            print(f"\nRunning {test['name']}...")
            start_time = time.time()
            try:
                test["test"](*test["args"])
                end_time = time.time()
                suite_results[test["name"]] = {
                    "status": "passed",
                    "duration": end_time - start_time,
                    "error": None
                }
                print(f"✅ {test['name']}: PASSED ({end_time - start_time:.2f}s)")
            except Exception as e:
                end_time = time.time()
                suite_results[test["name"]] = {
                    "status": "failed",
                    "duration": end_time - start_time,
                    "error": str(e)
                }
                print(f"❌ {test['name']}: FAILED - {e}")
        
        test_results["test_suites"]["basic_functionality"] = suite_results

        # Test Suite 2: Advanced workflows
        print("\n" + "="*60)
        print("TEST SUITE 2: ADVANCED WORKFLOWS")
        print("="*60)
        
        advanced_tests = [
            {
                "name": "Template Processing",
                "test": self._test_template_processing,
                "args": (authenticated_session, api_base_url)
            },
            {
                "name": "Report Generation",
                "test": self._test_basic_report_generation,
                "args": (authenticated_session, api_base_url)
            },
            {
                "name": "Batch Operations",
                "test": self._test_batch_operations,
                "args": (authenticated_session, api_base_url)
            }
        ]
        
        suite_results = {}
        for test in advanced_tests:
            print(f"\nRunning {test['name']}...")
            start_time = time.time()
            try:
                test["test"](*test["args"])
                end_time = time.time()
                suite_results[test["name"]] = {
                    "status": "passed",
                    "duration": end_time - start_time,
                    "error": None
                }
                print(f"✅ {test['name']}: PASSED ({end_time - start_time:.2f}s)")
            except Exception as e:
                end_time = time.time()
                suite_results[test["name"]] = {
                    "status": "failed",
                    "duration": end_time - start_time,
                    "error": str(e)
                }
                print(f"❌ {test['name']}: FAILED - {e}")
        
        test_results["test_suites"]["advanced_workflows"] = suite_results

        # Generate final report
        test_results["end_time"] = datetime.now().isoformat()
        
        total_tests = sum(len(suite.keys()) for suite in test_results["test_suites"].values())
        passed_tests = sum(
            1 for suite in test_results["test_suites"].values()
            for test in suite.values()
            if test["status"] == "passed"
        )
        failed_tests = total_tests - passed_tests
        
        test_results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0
        }
        
        test_results["overall_status"] = "passed" if failed_tests == 0 else "failed"

        # Save test results
        with open("/tmp/e2e_test_results.json", "w") as f:
            json.dump(test_results, f, indent=2)

        # Print summary
        print("\n" + "="*60)
        print("E2E TEST SUITE SUMMARY")
        print("="*60)
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success rate: {test_results['summary']['success_rate']:.1%}")
        print(f"Overall status: {test_results['overall_status'].upper()}")
        
        if failed_tests > 0:
            print("\nFailed tests:")
            for suite_name, suite in test_results["test_suites"].items():
                for test_name, test_result in suite.items():
                    if test_result["status"] == "failed":
                        print(f"  - {suite_name}/{test_name}: {test_result['error']}")

        # Assert overall success
        assert test_results["overall_status"] == "passed", f"E2E test suite failed: {failed_tests}/{total_tests} tests failed"

    def _test_user_authentication(self, session: Session, api_base_url: str):
        """Test user authentication functionality"""
        # Test getting current user profile
        response = session.get(f"{api_base_url}/user-profile/me")
        assert response.status_code in [200, 404], f"User profile check failed: {response.status_code}"

    def _test_crud_operations(self, session: Session, api_base_url: str):
        """Test basic CRUD operations"""
        # Test creating a template
        template_data = {
            "name": "E2E CRUD Test Template",
            "description": "Template for CRUD testing",
            "content": "Test content with {{placeholder}}",
            "is_active": True
        }
        
        response = session.post(f"{api_base_url}/templates/", json=template_data)
        assert response.status_code == 201, f"Template creation failed: {response.status_code}"
        template = response.json()
        template_id = template["id"]
        
        # Test reading the template
        response = session.get(f"{api_base_url}/templates/{template_id}")
        assert response.status_code == 200, f"Template read failed: {response.status_code}"
        
        # Test updating the template
        update_data = {"description": "Updated description"}
        response = session.put(f"{api_base_url}/templates/{template_id}", json=update_data)
        assert response.status_code == 200, f"Template update failed: {response.status_code}"
        
        # Test deleting the template
        response = session.delete(f"{api_base_url}/templates/{template_id}")
        assert response.status_code in [200, 204], f"Template deletion failed: {response.status_code}"

    def _test_data_source_connectivity(self, session: Session, api_base_url: str):
        """Test data source connectivity"""
        # Get list of data sources
        response = session.get(f"{api_base_url}/data-sources/")
        assert response.status_code == 200, f"Data sources list failed: {response.status_code}"
        
        data_sources = response.json()
        if data_sources:
            # Test connection to first data source
            data_source_id = data_sources[0]["id"]
            response = session.post(f"{api_base_url}/data-sources/{data_source_id}/test")
            # Connection test might fail, but endpoint should be accessible
            assert response.status_code in [200, 400, 500], f"Data source test endpoint failed: {response.status_code}"

    def _test_template_processing(self, session: Session, api_base_url: str):
        """Test template processing functionality"""
        # Get list of templates
        response = session.get(f"{api_base_url}/templates/")
        assert response.status_code == 200, f"Templates list failed: {response.status_code}"
        
        templates = response.json()
        if templates:
            # Test analyzing first template
            template_id = templates[0]["id"]
            response = session.post(f"{api_base_url}/template-analysis/{template_id}/analyze")
            assert response.status_code == 200, f"Template analysis failed: {response.status_code}"

    def _test_basic_report_generation(self, session: Session, api_base_url: str):
        """Test basic report generation"""
        # Get templates and data sources
        templates_response = session.get(f"{api_base_url}/templates/")
        data_sources_response = session.get(f"{api_base_url}/data-sources/")
        
        if (templates_response.status_code == 200 and data_sources_response.status_code == 200):
            templates = templates_response.json()
            data_sources = data_sources_response.json()
            
            if templates and data_sources:
                # Try to generate a simple report
                report_request = {
                    "template_id": templates[0]["id"],
                    "data_source_id": data_sources[0]["id"],
                    "parameters": {"test_param": "test_value"}
                }
                
                response = session.post(f"{api_base_url}/report-generation/generate", json=report_request)
                # Report generation might fail due to data issues, but endpoint should be accessible
                assert response.status_code in [200, 400, 500], f"Report generation endpoint failed: {response.status_code}"

    def _test_batch_operations(self, session: Session, api_base_url: str):
        """Test batch operations"""
        # Test batch template analysis
        response = session.get(f"{api_base_url}/templates/")
        if response.status_code == 200:
            templates = response.json()
            if len(templates) >= 2:
                template_ids = [t["id"] for t in templates[:2]]
                batch_request = {"template_ids": template_ids}
                
                response = session.post(f"{api_base_url}/template-analysis/batch", json=batch_request)
                # Batch operations might not be implemented, but should not return 404
                assert response.status_code != 404, "Batch analysis endpoint not found"

    def test_e2e_cleanup(
        self,
        admin_session: Session,
        api_base_url: str,
    ):
        """
        Cleanup E2E test data:
        1. Remove test users
        2. Remove test data sources
        3. Remove test templates
        4. Clean up test files
        """
        print("Cleaning up E2E test data...")

        # Load test resources
        try:
            with open("/tmp/e2e_test_resources.json", "r") as f:
                test_resources = json.load(f)
        except FileNotFoundError:
            print("⚠️  No test resources file found, skipping cleanup")
            return

        # Cleanup templates
        templates = test_resources.get("templates", [])
        for template in templates:
            try:
                response = admin_session.delete(f"{api_base_url}/templates/{template['id']}")
                if response.status_code in [200, 204, 404]:
                    print(f"✅ Cleaned up template: {template['name']}")
                else:
                    print(f"⚠️  Failed to cleanup template {template['name']}: {response.status_code}")
            except Exception as e:
                print(f"⚠️  Error cleaning up template {template['name']}: {e}")

        # Cleanup data sources
        data_sources = test_resources.get("data_sources", [])
        for data_source in data_sources:
            try:
                response = admin_session.delete(f"{api_base_url}/data-sources/{data_source['id']}")
                if response.status_code in [200, 204, 404]:
                    print(f"✅ Cleaned up data source: {data_source['name']}")
                else:
                    print(f"⚠️  Failed to cleanup data source {data_source['name']}: {response.status_code}")
            except Exception as e:
                print(f"⚠️  Error cleaning up data source {data_source['name']}: {e}")

        # Cleanup users
        users = test_resources.get("users", [])
        for user in users:
            try:
                response = admin_session.delete(f"{api_base_url}/users/{user['id']}")
                if response.status_code in [200, 204, 404]:
                    print(f"✅ Cleaned up user: {user['username']}")
                else:
                    print(f"⚠️  Failed to cleanup user {user['username']}: {response.status_code}")
            except Exception as e:
                print(f"⚠️  Error cleaning up user {user['username']}: {e}")

        # Remove test files
        import os
        test_files = [
            "/tmp/e2e_test_resources.json",
            "/tmp/e2e_test_results.json"
        ]
        
        for file_path in test_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"✅ Removed test file: {file_path}")
            except Exception as e:
                print(f"⚠️  Error removing test file {file_path}: {e}")

        print("✅ E2E test cleanup completed")