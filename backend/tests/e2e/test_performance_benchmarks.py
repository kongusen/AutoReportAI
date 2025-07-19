"""
Performance Benchmark End-to-End Tests

This module tests system performance under various load conditions
and establishes performance benchmarks for key operations.
"""

import asyncio
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Tuple

import pytest
import requests
from requests import Session


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.performance
class TestPerformanceBenchmarks:
    """Test system performance benchmarks"""

    def test_api_response_time_benchmarks(
        self,
        authenticated_session: Session,
        api_base_url: str,
        performance_thresholds: Dict[str, float],
    ):
        """
        Test API response time benchmarks for key endpoints:
        1. Authentication endpoints
        2. CRUD operations
        3. Complex operations
        4. File operations
        """
        print("Testing API response time benchmarks...")

        # Define test endpoints with expected response times
        test_endpoints = [
            {
                "name": "Health Check",
                "method": "GET",
                "url": f"{api_base_url.replace('/api/v1', '')}/",
                "expected_time": 0.1,
                "auth_required": False
            },
            {
                "name": "User Profile",
                "method": "GET",
                "url": f"{api_base_url}/user-profile/me",
                "expected_time": 0.5,
                "auth_required": True
            },
            {
                "name": "Templates List",
                "method": "GET",
                "url": f"{api_base_url}/templates/",
                "expected_time": 1.0,
                "auth_required": True
            },
            {
                "name": "Data Sources List",
                "method": "GET",
                "url": f"{api_base_url}/data-sources/",
                "expected_time": 1.0,
                "auth_required": True
            },
            {
                "name": "AI Providers List",
                "method": "GET",
                "url": f"{api_base_url}/ai-providers/",
                "expected_time": 0.8,
                "auth_required": True
            },
            {
                "name": "ETL Jobs List",
                "method": "GET",
                "url": f"{api_base_url}/etl-jobs/",
                "expected_time": 1.2,
                "auth_required": True
            },
            {
                "name": "Tasks List",
                "method": "GET",
                "url": f"{api_base_url}/tasks/",
                "expected_time": 0.8,
                "auth_required": True
            }
        ]

        benchmark_results = {}
        
        for endpoint in test_endpoints:
            print(f"Benchmarking {endpoint['name']}...")
            
            # Perform multiple requests to get accurate timing
            response_times = []
            num_requests = 10
            
            session = authenticated_session if endpoint["auth_required"] else requests.Session()
            
            for i in range(num_requests):
                start_time = time.time()
                
                try:
                    if endpoint["method"] == "GET":
                        response = session.get(endpoint["url"], timeout=10)
                    elif endpoint["method"] == "POST":
                        response = session.post(endpoint["url"], json={}, timeout=10)
                    
                    end_time = time.time()
                    response_time = end_time - start_time
                    
                    if response.status_code in [200, 201]:
                        response_times.append(response_time)
                    else:
                        print(f"⚠️  Request {i+1} failed with status {response.status_code}")
                        
                except requests.exceptions.RequestException as e:
                    print(f"⚠️  Request {i+1} failed: {e}")
                    continue
                
                # Small delay between requests
                time.sleep(0.1)
            
            if response_times:
                avg_time = statistics.mean(response_times)
                min_time = min(response_times)
                max_time = max(response_times)
                median_time = statistics.median(response_times)
                
                benchmark_results[endpoint["name"]] = {
                    "average": avg_time,
                    "minimum": min_time,
                    "maximum": max_time,
                    "median": median_time,
                    "expected": endpoint["expected_time"],
                    "samples": len(response_times)
                }
                
                # Check against expected time
                if avg_time <= endpoint["expected_time"]:
                    print(f"✅ {endpoint['name']}: {avg_time:.3f}s (expected: {endpoint['expected_time']}s)")
                else:
                    print(f"⚠️  {endpoint['name']}: {avg_time:.3f}s (expected: {endpoint['expected_time']}s)")
            else:
                print(f"❌ {endpoint['name']}: No successful requests")

        # Generate performance report
        print("\n📊 API Performance Benchmark Report:")
        print("=" * 60)
        for name, metrics in benchmark_results.items():
            print(f"{name}:")
            print(f"  Average: {metrics['average']:.3f}s")
            print(f"  Median:  {metrics['median']:.3f}s")
            print(f"  Range:   {metrics['minimum']:.3f}s - {metrics['maximum']:.3f}s")
            print(f"  Expected: {metrics['expected']:.3f}s")
            print(f"  Status:  {'✅ PASS' if metrics['average'] <= metrics['expected'] else '⚠️  SLOW'}")
            print()

    def test_concurrent_request_performance(
        self,
        authenticated_session: Session,
        api_base_url: str,
        performance_thresholds: Dict[str, float],
    ):
        """
        Test system performance under concurrent load:
        1. Concurrent read operations
        2. Concurrent write operations
        3. Mixed read/write operations
        """
        print("Testing concurrent request performance...")

        def make_request(session: Session, endpoint: str, method: str = "GET", data: Dict = None) -> Tuple[float, int]:
            """Make a single request and return response time and status code"""
            start_time = time.time()
            try:
                if method == "GET":
                    response = session.get(endpoint, timeout=30)
                elif method == "POST":
                    response = session.post(endpoint, json=data or {}, timeout=30)
                elif method == "PUT":
                    response = session.put(endpoint, json=data or {}, timeout=30)
                
                end_time = time.time()
                return end_time - start_time, response.status_code
            except Exception as e:
                end_time = time.time()
                return end_time - start_time, 0  # 0 indicates error

        # Test 1: Concurrent read operations
        print("Test 1: Concurrent read operations...")
        read_endpoints = [
            f"{api_base_url}/templates/",
            f"{api_base_url}/data-sources/",
            f"{api_base_url}/ai-providers/",
            f"{api_base_url}/etl-jobs/",
            f"{api_base_url}/tasks/"
        ]
        
        concurrent_users = 10
        requests_per_user = 5
        
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = []
            start_time = time.time()
            
            for user in range(concurrent_users):
                for request_num in range(requests_per_user):
                    endpoint = read_endpoints[request_num % len(read_endpoints)]
                    future = executor.submit(make_request, authenticated_session, endpoint, "GET")
                    futures.append(future)
            
            # Collect results
            response_times = []
            success_count = 0
            error_count = 0
            
            for future in as_completed(futures):
                response_time, status_code = future.result()
                response_times.append(response_time)
                
                if 200 <= status_code < 300:
                    success_count += 1
                else:
                    error_count += 1
            
            end_time = time.time()
            total_time = end_time - start_time
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            max_response_time = max(response_times)
            throughput = len(futures) / total_time
            
            print(f"✅ Concurrent reads completed:")
            print(f"   Total requests: {len(futures)}")
            print(f"   Successful: {success_count}")
            print(f"   Failed: {error_count}")
            print(f"   Average response time: {avg_response_time:.3f}s")
            print(f"   Max response time: {max_response_time:.3f}s")
            print(f"   Throughput: {throughput:.2f} requests/second")
            
            # Performance assertions
            assert avg_response_time < 5.0, f"Average response time too high: {avg_response_time:.3f}s"
            assert success_count / len(futures) >= 0.95, f"Success rate too low: {success_count}/{len(futures)}"

        # Test 2: Concurrent write operations
        print("\nTest 2: Concurrent write operations...")
        
        # Create test templates concurrently
        template_data_template = {
            "name": "Concurrent Test Template {}",
            "description": "Template created during concurrent testing",
            "content": "Test content with {{placeholder}}",
            "is_active": True
        }
        
        concurrent_writes = 5
        
        with ThreadPoolExecutor(max_workers=concurrent_writes) as executor:
            futures = []
            start_time = time.time()
            
            for i in range(concurrent_writes):
                template_data = template_data_template.copy()
                template_data["name"] = template_data["name"].format(i)
                
                future = executor.submit(
                    make_request, 
                    authenticated_session, 
                    f"{api_base_url}/templates/", 
                    "POST", 
                    template_data
                )
                futures.append(future)
            
            # Collect results
            write_response_times = []
            write_success_count = 0
            write_error_count = 0
            
            for future in as_completed(futures):
                response_time, status_code = future.result()
                write_response_times.append(response_time)
                
                if status_code == 201:
                    write_success_count += 1
                else:
                    write_error_count += 1
            
            end_time = time.time()
            write_total_time = end_time - start_time
        
        if write_response_times:
            avg_write_time = statistics.mean(write_response_times)
            max_write_time = max(write_response_times)
            write_throughput = len(futures) / write_total_time
            
            print(f"✅ Concurrent writes completed:")
            print(f"   Total requests: {len(futures)}")
            print(f"   Successful: {write_success_count}")
            print(f"   Failed: {write_error_count}")
            print(f"   Average response time: {avg_write_time:.3f}s")
            print(f"   Max response time: {max_write_time:.3f}s")
            print(f"   Throughput: {write_throughput:.2f} requests/second")
            
            # Performance assertions
            assert avg_write_time < 10.0, f"Average write time too high: {avg_write_time:.3f}s"
            assert write_success_count / len(futures) >= 0.8, f"Write success rate too low: {write_success_count}/{len(futures)}"

    def test_data_processing_performance(
        self,
        authenticated_session: Session,
        api_base_url: str,
        performance_thresholds: Dict[str, float],
        cleanup_e2e_data,
    ):
        """
        Test data processing performance:
        1. Large dataset processing
        2. Complex query performance
        3. ETL job performance
        4. Report generation performance
        """
        print("Testing data processing performance...")

        # Step 1: Create large dataset for testing
        print("Step 1: Setting up large dataset...")
        large_data_source = {
            "name": "E2E Large Dataset",
            "description": "Large dataset for performance testing",
            "source_type": "database",
            "connection_string": "sqlite:///large_test.db",
            "schema_config": {
                "tables": {
                    "large_complaints": {
                        "columns": [
                            {"name": "id", "type": "integer", "primary_key": True},
                            {"name": "complaint_date", "type": "datetime"},
                            {"name": "category", "type": "string"},
                            {"name": "description", "type": "text"},
                            {"name": "status", "type": "string"},
                            {"name": "customer_id", "type": "integer"},
                        ],
                        "estimated_rows": 100000
                    }
                }
            },
            "is_active": True,
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/data-sources/", json=large_data_source
        )
        assert response.status_code == 201, f"Failed to create large data source: {response.text}"
        data_source = response.json()
        data_source_id = data_source["id"]
        print(f"✅ Large dataset created with ID: {data_source_id}")

        # Step 2: Test complex query performance
        print("Step 2: Testing complex query performance...")
        complex_queries = [
            {
                "name": "Aggregation Query",
                "query": {
                    "type": "aggregation",
                    "table": "large_complaints",
                    "group_by": ["category", "status"],
                    "aggregates": ["count", "avg(resolution_time)"],
                    "filters": {"complaint_date": {"gte": "2024-01-01"}}
                },
                "expected_time": 5.0
            },
            {
                "name": "Complex Join Query",
                "query": {
                    "type": "join",
                    "tables": ["large_complaints", "customers"],
                    "join_conditions": [{"left": "large_complaints.customer_id", "right": "customers.id"}],
                    "select": ["large_complaints.*", "customers.region"],
                    "filters": {"customers.region": {"in": ["North", "South"]}}
                },
                "expected_time": 8.0
            },
            {
                "name": "Time Series Query",
                "query": {
                    "type": "time_series",
                    "table": "large_complaints",
                    "time_column": "complaint_date",
                    "interval": "day",
                    "metrics": ["count", "avg(satisfaction_score)"],
                    "date_range": {"start": "2024-01-01", "end": "2024-01-31"}
                },
                "expected_time": 6.0
            }
        ]
        
        query_performance_results = {}
        
        for query_test in complex_queries:
            print(f"Testing {query_test['name']}...")
            
            start_time = time.time()
            response = authenticated_session.post(
                f"{api_base_url}/data-sources/{data_source_id}/query",
                json=query_test["query"]
            )
            end_time = time.time()
            
            query_time = end_time - start_time
            
            if response.status_code == 200:
                result = response.json()
                row_count = len(result.get("data", []))
                
                query_performance_results[query_test["name"]] = {
                    "execution_time": query_time,
                    "expected_time": query_test["expected_time"],
                    "row_count": row_count,
                    "status": "success"
                }
                
                if query_time <= query_test["expected_time"]:
                    print(f"✅ {query_test['name']}: {query_time:.3f}s ({row_count} rows)")
                else:
                    print(f"⚠️  {query_test['name']}: {query_time:.3f}s (expected: {query_test['expected_time']}s)")
            else:
                print(f"❌ {query_test['name']}: Query failed with status {response.status_code}")
                query_performance_results[query_test["name"]] = {
                    "execution_time": query_time,
                    "expected_time": query_test["expected_time"],
                    "status": "failed",
                    "error": response.text
                }

        # Step 3: Test ETL job performance
        print("Step 3: Testing ETL job performance...")
        etl_job_config = {
            "name": "E2E Performance ETL Job",
            "description": "ETL job for performance testing",
            "data_source_id": data_source_id,
            "schedule": "manual",
            "transformation_config": {
                "steps": [
                    {
                        "type": "extract",
                        "source_table": "large_complaints",
                        "batch_size": 1000
                    },
                    {
                        "type": "transform",
                        "operations": [
                            {"type": "aggregate", "group_by": ["category"], "metrics": ["count"]},
                            {"type": "calculate", "field": "resolution_rate", "formula": "resolved/total*100"}
                        ]
                    },
                    {
                        "type": "load",
                        "target_table": "complaint_summary",
                        "mode": "replace"
                    }
                ]
            },
            "is_active": True
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/etl-jobs/", json=etl_job_config
        )
        assert response.status_code == 201, f"Failed to create ETL job: {response.text}"
        etl_job = response.json()
        etl_job_id = etl_job["id"]
        
        # Run ETL job and measure performance
        etl_start_time = time.time()
        response = authenticated_session.post(
            f"{api_base_url}/etl-jobs/{etl_job_id}/run"
        )
        assert response.status_code == 200, f"ETL job execution failed: {response.text}"
        
        # Monitor ETL job completion
        max_wait_time = 120  # 2 minutes
        wait_interval = 5    # seconds
        waited_time = 0
        
        while waited_time < max_wait_time:
            response = authenticated_session.get(
                f"{api_base_url}/etl-jobs/{etl_job_id}/status"
            )
            if response.status_code == 200:
                status = response.json()
                if status.get("status") == "completed":
                    etl_end_time = time.time()
                    etl_execution_time = etl_end_time - etl_start_time
                    
                    processed_records = status.get("processed_records", 0)
                    throughput = processed_records / etl_execution_time if etl_execution_time > 0 else 0
                    
                    print(f"✅ ETL job completed in {etl_execution_time:.2f}s")
                    print(f"   Processed records: {processed_records}")
                    print(f"   Throughput: {throughput:.2f} records/second")
                    
                    # Performance assertion
                    expected_throughput = 100  # records per second
                    assert throughput >= expected_throughput, f"ETL throughput too low: {throughput:.2f} records/s"
                    break
                elif status.get("status") == "failed":
                    pytest.fail(f"ETL job failed: {status.get('error_message')}")
            
            time.sleep(wait_interval)
            waited_time += wait_interval
        else:
            pytest.fail("ETL job did not complete within timeout")

        # Step 4: Test report generation performance with large dataset
        print("Step 4: Testing report generation performance...")
        performance_template = {
            "name": "E2E Performance Report Template",
            "description": "Template for performance testing with large dataset",
            "content": """
            # 性能测试报告
            
            ## 数据统计
            总记录数：{{总记录数|total_records}}
            处理时间：{{处理时间|processing_time}}
            
            ## 分类统计
            {{分类统计|category_stats}}
            
            ## 趋势分析
            {{趋势分析|trend_analysis}}
            """,
            "data_source_id": data_source_id,
            "is_active": True
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/templates/", json=performance_template
        )
        assert response.status_code == 201, f"Failed to create performance template: {response.text}"
        template = response.json()
        template_id = template["id"]
        
        # Generate report and measure performance
        report_start_time = time.time()
        report_request = {
            "template_id": template_id,
            "data_source_id": data_source_id,
            "generation_config": {
                "quality_level": "standard",  # Use standard quality for performance
                "ai_enhancement": False,      # Disable AI for performance testing
                "parallel_processing": True
            },
            "parameters": {
                "total_records": 100000,
                "processing_time": "2.5 seconds"
            }
        }
        
        response = authenticated_session.post(
            f"{api_base_url}/report-generation/generate",
            json=report_request
        )
        assert response.status_code == 200, f"Report generation failed: {response.text}"
        generation_result = response.json()
        report_id = generation_result.get("report_id")
        
        # Monitor report generation
        max_wait_time = 180  # 3 minutes
        wait_interval = 5    # seconds
        waited_time = 0
        
        while waited_time < max_wait_time:
            response = authenticated_session.get(
                f"{api_base_url}/report-generation/status/{report_id}"
            )
            if response.status_code == 200:
                status = response.json()
                if status.get("status") == "completed":
                    report_end_time = time.time()
                    report_generation_time = report_end_time - report_start_time
                    
                    print(f"✅ Report generation completed in {report_generation_time:.2f}s")
                    
                    # Performance assertion
                    expected_report_time = performance_thresholds.get("report_generation_time", 60.0)
                    assert report_generation_time < expected_report_time, \
                        f"Report generation too slow: {report_generation_time:.2f}s"
                    break
                elif status.get("status") == "failed":
                    pytest.fail(f"Report generation failed: {status.get('error_message')}")
            
            time.sleep(wait_interval)
            waited_time += wait_interval
        else:
            pytest.fail("Report generation did not complete within timeout")

        # Generate performance summary
        print("\n📊 Data Processing Performance Summary:")
        print("=" * 60)
        print("Query Performance:")
        for query_name, metrics in query_performance_results.items():
            if metrics["status"] == "success":
                print(f"  {query_name}: {metrics['execution_time']:.3f}s ({metrics['row_count']} rows)")
            else:
                print(f"  {query_name}: FAILED")
        
        print(f"\nETL Performance:")
        print(f"  Execution time: {etl_execution_time:.2f}s")
        print(f"  Throughput: {throughput:.2f} records/second")
        
        print(f"\nReport Generation:")
        print(f"  Generation time: {report_generation_time:.2f}s")

    def test_memory_and_resource_usage(
        self,
        authenticated_session: Session,
        api_base_url: str,
    ):
        """
        Test memory and resource usage under load:
        1. Memory usage during large operations
        2. Connection pool management
        3. Resource cleanup
        """
        print("Testing memory and resource usage...")

        # Test 1: Monitor resource usage during intensive operations
        print("Test 1: Monitoring resource usage...")
        
        # Get initial system stats
        response = authenticated_session.get(f"{api_base_url}/system/stats")
        if response.status_code == 200:
            initial_stats = response.json()
            print(f"Initial memory usage: {initial_stats.get('memory_usage', 'N/A')}")
            print(f"Initial active connections: {initial_stats.get('active_connections', 'N/A')}")
        else:
            print("⚠️  System stats not available")
            initial_stats = {}

        # Perform memory-intensive operations
        intensive_operations = [
            {
                "name": "Large Template Analysis",
                "operation": lambda: authenticated_session.post(
                    f"{api_base_url}/template-analysis/batch",
                    json={"template_ids": list(range(1, 21))}  # Analyze 20 templates
                )
            },
            {
                "name": "Bulk Data Processing",
                "operation": lambda: authenticated_session.post(
                    f"{api_base_url}/data-processing/bulk",
                    json={"batch_size": 10000, "operations": ["aggregate", "transform"]}
                )
            }
        ]
        
        for operation in intensive_operations:
            print(f"Executing {operation['name']}...")
            
            start_time = time.time()
            try:
                response = operation["operation"]()
                end_time = time.time()
                
                if response.status_code in [200, 201, 202]:
                    print(f"✅ {operation['name']} completed in {end_time - start_time:.2f}s")
                else:
                    print(f"⚠️  {operation['name']} returned status {response.status_code}")
            except Exception as e:
                print(f"⚠️  {operation['name']} failed: {e}")
            
            # Check resource usage after operation
            response = authenticated_session.get(f"{api_base_url}/system/stats")
            if response.status_code == 200:
                current_stats = response.json()
                memory_usage = current_stats.get('memory_usage', 'N/A')
                active_connections = current_stats.get('active_connections', 'N/A')
                print(f"   Memory usage: {memory_usage}")
                print(f"   Active connections: {active_connections}")
            
            # Allow some time for cleanup
            time.sleep(2)

        # Test 2: Connection pool stress test
        print("\nTest 2: Connection pool stress test...")
        
        def make_db_request():
            """Make a request that requires database connection"""
            return authenticated_session.get(f"{api_base_url}/templates/")
        
        # Make many concurrent requests to test connection pooling
        max_concurrent = 20
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = [executor.submit(make_db_request) for _ in range(max_concurrent)]
            
            successful_requests = 0
            failed_requests = 0
            
            for future in as_completed(futures):
                try:
                    response = future.result()
                    if response.status_code == 200:
                        successful_requests += 1
                    else:
                        failed_requests += 1
                except Exception:
                    failed_requests += 1
        
        success_rate = successful_requests / (successful_requests + failed_requests)
        print(f"✅ Connection pool test: {successful_requests}/{max_concurrent} successful ({success_rate:.1%})")
        
        # Assert acceptable success rate
        assert success_rate >= 0.9, f"Connection pool success rate too low: {success_rate:.1%}"

        # Test 3: Resource cleanup verification
        print("\nTest 3: Resource cleanup verification...")
        
        # Get final system stats
        time.sleep(5)  # Allow time for cleanup
        response = authenticated_session.get(f"{api_base_url}/system/stats")
        if response.status_code == 200:
            final_stats = response.json()
            final_memory = final_stats.get('memory_usage', 0)
            final_connections = final_stats.get('active_connections', 0)
            
            print(f"Final memory usage: {final_memory}")
            print(f"Final active connections: {final_connections}")
            
            # Check for memory leaks (basic check)
            if initial_stats.get('memory_usage') and final_memory:
                memory_increase = final_memory - initial_stats['memory_usage']
                if memory_increase > 100:  # 100MB threshold
                    print(f"⚠️  Potential memory leak detected: {memory_increase}MB increase")
                else:
                    print("✅ No significant memory increase detected")
        
        print("✅ Memory and resource usage tests completed")