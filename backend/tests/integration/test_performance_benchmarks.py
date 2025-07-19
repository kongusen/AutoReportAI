"""
Performance Benchmark Tests for Intelligent Placeholder Processing.

Tests system performance under various conditions:
- Processing time benchmarks
- Memory usage optimization
- Concurrent processing capacity
- Scalability testing
- Resource utilization monitoring
- Load testing scenarios
"""

import asyncio
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock

import psutil
import pytest

from app.services.intelligent_placeholder.adapter import (
    IntelligentPlaceholderProcessor,
    LLMPlaceholderService,
)
from app.services.intelligent_placeholder.matcher import IntelligentFieldMatcher
from app.services.data_processing.etl.intelligent_etl_executor import IntelligentETLExecutor


@dataclass
class PerformanceMetrics:
    """Performance metrics for benchmarking."""

    processing_time: float
    memory_usage_mb: float
    cpu_usage_percent: float
    throughput_per_second: float
    success_rate: float
    error_count: int


@dataclass
class BenchmarkScenario:
    """Benchmark test scenario configuration."""

    name: str
    template_complexity: str  # simple, medium, complex
    placeholder_count: int
    data_size_mb: float
    concurrent_requests: int
    expected_max_time: float
    expected_max_memory_mb: float


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.performance
class TestPerformanceBenchmarks:
    """Performance benchmark tests for intelligent placeholder processing."""

    @pytest.fixture(autouse=True)
    async def setup_performance_testing(self):
        """Set up performance testing environment."""
        # Mock services with performance tracking
        self.mock_ai_service = Mock()
        self.mock_ai_service.generate_completion = AsyncMock()

        # Initialize services
        self.llm_service = LLMPlaceholderService(self.mock_ai_service)
        self.field_matcher = IntelligentFieldMatcher()
        self.etl_executor = Mock(spec=IntelligentETLExecutor)

        self.processor = IntelligentPlaceholderProcessor(
            llm_service=self.llm_service,
            field_matcher=self.field_matcher,
            etl_executor=self.etl_executor,
        )

        # Performance monitoring
        self.performance_data = []

    @pytest.fixture
    def benchmark_scenarios(self) -> List[BenchmarkScenario]:
        """Define benchmark scenarios for testing."""
        return [
            BenchmarkScenario(
                name="simple_single_placeholder",
                template_complexity="simple",
                placeholder_count=1,
                data_size_mb=0.1,
                concurrent_requests=1,
                expected_max_time=2.0,
                expected_max_memory_mb=50,
            ),
            BenchmarkScenario(
                name="medium_multiple_placeholders",
                template_complexity="medium",
                placeholder_count=5,
                data_size_mb=1.0,
                concurrent_requests=1,
                expected_max_time=8.0,
                expected_max_memory_mb=100,
            ),
            BenchmarkScenario(
                name="complex_many_placeholders",
                template_complexity="complex",
                placeholder_count=15,
                data_size_mb=5.0,
                concurrent_requests=1,
                expected_max_time=25.0,
                expected_max_memory_mb=200,
            ),
            BenchmarkScenario(
                name="concurrent_simple",
                template_complexity="simple",
                placeholder_count=3,
                data_size_mb=0.5,
                concurrent_requests=5,
                expected_max_time=10.0,
                expected_max_memory_mb=150,
            ),
            BenchmarkScenario(
                name="concurrent_complex",
                template_complexity="medium",
                placeholder_count=8,
                data_size_mb=2.0,
                concurrent_requests=10,
                expected_max_time=30.0,
                expected_max_memory_mb=300,
            ),
            BenchmarkScenario(
                name="high_load_stress_test",
                template_complexity="complex",
                placeholder_count=20,
                data_size_mb=10.0,
                concurrent_requests=20,
                expected_max_time=60.0,
                expected_max_memory_mb=500,
            ),
        ]

    def generate_template_by_complexity(
        self, complexity: str, placeholder_count: int
    ) -> str:
        """Generate test templates based on complexity level."""
        if complexity == "simple":
            placeholders = [f"{{{{统计:数值{i}}}}}" for i in range(placeholder_count)]
            return f"简单报告：{' '.join(placeholders)}"

        elif complexity == "medium":
            template_parts = []
            for i in range(placeholder_count):
                if i % 3 == 0:
                    template_parts.append(f"统计数据：{{{{统计:数值{i}}}}}")
                elif i % 3 == 1:
                    template_parts.append(f"时间周期：{{{{周期:时间{i}}}}}")
                else:
                    template_parts.append(f"区域信息：{{{{区域:地区{i}}}}}")

            return f"""中等复杂度报告
            
一、数据概述
{template_parts[0] if len(template_parts) > 0 else ''}

二、详细分析
{' '.join(template_parts[1:3]) if len(template_parts) > 2 else ''}

三、结论
{' '.join(template_parts[3:]) if len(template_parts) > 3 else ''}
"""

        else:  # complex
            sections = [
                "一、执行摘要",
                "二、数据概述",
                "三、详细分析",
                "四、趋势分析",
                "五、区域分析",
                "六、对比分析",
                "七、结论建议",
            ]

            template_parts = []
            for i, section in enumerate(sections):
                section_placeholders = []
                start_idx = i * (placeholder_count // len(sections))
                end_idx = min(
                    (i + 1) * (placeholder_count // len(sections)), placeholder_count
                )

                for j in range(start_idx, end_idx):
                    placeholder_type = ["统计", "周期", "区域", "图表", "分析"][j % 5]
                    section_placeholders.append(f"{{{{{placeholder_type}:项目{j}}}}}")

                if section_placeholders:
                    template_parts.append(
                        f"{section}\n{' '.join(section_placeholders)}"
                    )

            return "\n\n".join(template_parts)

    async def measure_performance(self, func, *args, **kwargs) -> PerformanceMetrics:
        """Measure performance metrics for a function execution."""
        # Get initial system metrics
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        initial_cpu = process.cpu_percent()

        start_time = time.time()

        try:
            # Execute function
            result = await func(*args, **kwargs)
            success = True
            error_count = 0
        except Exception as e:
            result = None
            success = False
            error_count = 1

        end_time = time.time()
        processing_time = end_time - start_time

        # Get final system metrics
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        final_cpu = process.cpu_percent()

        return PerformanceMetrics(
            processing_time=processing_time,
            memory_usage_mb=final_memory - initial_memory,
            cpu_usage_percent=final_cpu,
            throughput_per_second=1.0 / processing_time if processing_time > 0 else 0,
            success_rate=1.0 if success else 0.0,
            error_count=error_count,
        )

    async def test_single_placeholder_processing_benchmark(
        self, benchmark_scenarios: List[BenchmarkScenario]
    ):
        """Benchmark single placeholder processing performance."""
        single_scenarios = [
            s for s in benchmark_scenarios if s.concurrent_requests == 1
        ]

        for scenario in single_scenarios:
            # Generate test template
            template = self.generate_template_by_complexity(
                scenario.template_complexity, scenario.placeholder_count
            )

            # Mock fast LLM responses
            self.mock_ai_service.generate_completion.return_value = (
                '{"result": "test", "confidence": 0.9}'
            )

            # Mock ETL executor
            self.etl_executor.execute_etl = AsyncMock(
                return_value=Mock(
                    processed_value="test_value", metadata={"confidence": 0.9}
                )
            )

            # Measure performance
            metrics = await self.measure_performance(
                self.processor.process_template,
                template_content=template,
                data_schema={"fields": []},
            )

            # Verify performance requirements
            assert (
                metrics.processing_time <= scenario.expected_max_time
            ), f"Scenario {scenario.name}: {metrics.processing_time:.2f}s > {scenario.expected_max_time}s"

            assert (
                metrics.memory_usage_mb <= scenario.expected_max_memory_mb
            ), f"Scenario {scenario.name}: {metrics.memory_usage_mb:.2f}MB > {scenario.expected_max_memory_mb}MB"

            assert (
                metrics.success_rate == 1.0
            ), f"Scenario {scenario.name}: Success rate {metrics.success_rate} < 1.0"

            # Record performance data
            self.performance_data.append(
                {"scenario": scenario.name, "metrics": metrics}
            )

            print(
                f"✓ {scenario.name}: {metrics.processing_time:.2f}s, "
                f"{metrics.memory_usage_mb:.1f}MB, "
                f"{metrics.throughput_per_second:.2f} req/s"
            )

    async def test_concurrent_processing_benchmark(
        self, benchmark_scenarios: List[BenchmarkScenario]
    ):
        """Benchmark concurrent processing performance."""
        concurrent_scenarios = [
            s for s in benchmark_scenarios if s.concurrent_requests > 1
        ]

        for scenario in concurrent_scenarios:
            # Generate test template
            template = self.generate_template_by_complexity(
                scenario.template_complexity, scenario.placeholder_count
            )

            # Mock responses for concurrent processing
            self.mock_ai_service.generate_completion.return_value = (
                '{"result": "concurrent_test", "confidence": 0.9}'
            )
            self.etl_executor.execute_etl = AsyncMock(
                return_value=Mock(
                    processed_value="concurrent_value", metadata={"confidence": 0.9}
                )
            )

            # Create concurrent tasks
            async def process_single():
                return await self.processor.process_template(
                    template_content=template, data_schema={"fields": []}
                )

            tasks = [process_single() for _ in range(scenario.concurrent_requests)]

            # Measure concurrent performance
            start_time = time.time()
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024

            results = await asyncio.gather(*tasks, return_exceptions=True)

            end_time = time.time()
            final_memory = process.memory_info().rss / 1024 / 1024

            # Calculate metrics
            processing_time = end_time - start_time
            memory_usage = final_memory - initial_memory
            successful_results = [
                r for r in results if not isinstance(r, Exception) and r and r.success
            ]
            success_rate = len(successful_results) / len(results)
            throughput = (
                len(successful_results) / processing_time if processing_time > 0 else 0
            )

            concurrent_metrics = PerformanceMetrics(
                processing_time=processing_time,
                memory_usage_mb=memory_usage,
                cpu_usage_percent=0,  # Not measured in concurrent test
                throughput_per_second=throughput,
                success_rate=success_rate,
                error_count=len(results) - len(successful_results),
            )

            # Verify concurrent performance requirements
            assert (
                concurrent_metrics.processing_time <= scenario.expected_max_time
            ), f"Concurrent {scenario.name}: {concurrent_metrics.processing_time:.2f}s > {scenario.expected_max_time}s"

            assert (
                concurrent_metrics.memory_usage_mb <= scenario.expected_max_memory_mb
            ), f"Concurrent {scenario.name}: {concurrent_metrics.memory_usage_mb:.2f}MB > {scenario.expected_max_memory_mb}MB"

            assert (
                concurrent_metrics.success_rate >= 0.9
            ), f"Concurrent {scenario.name}: Success rate {concurrent_metrics.success_rate} < 0.9"

            print(
                f"✓ Concurrent {scenario.name}: {concurrent_metrics.processing_time:.2f}s, "
                f"{concurrent_metrics.throughput_per_second:.2f} req/s, "
                f"{concurrent_metrics.success_rate:.2%} success"
            )

    async def test_memory_usage_optimization(self):
        """Test memory usage optimization under different loads."""
        memory_test_scenarios = [
            {"name": "small_data", "data_size": 100, "expected_memory_mb": 20},
            {"name": "medium_data", "data_size": 1000, "expected_memory_mb": 50},
            {"name": "large_data", "data_size": 10000, "expected_memory_mb": 150},
            {"name": "very_large_data", "data_size": 50000, "expected_memory_mb": 300},
        ]

        for scenario in memory_test_scenarios:
            # Generate large template with many placeholders
            placeholder_count = scenario["data_size"] // 100
            template = self.generate_template_by_complexity(
                "complex", placeholder_count
            )

            # Mock data processing
            self.mock_ai_service.generate_completion.return_value = (
                '{"result": "memory_test", "confidence": 0.9}'
            )
            self.etl_executor.execute_etl = AsyncMock(
                return_value=Mock(
                    processed_value="large_data_value",
                    metadata={"confidence": 0.9, "data_size": scenario["data_size"]},
                )
            )

            # Measure memory usage
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024

            result = await self.processor.process_template(
                template_content=template,
                data_schema={
                    "fields": [f"field_{i}" for i in range(scenario["data_size"])]
                },
            )

            final_memory = process.memory_info().rss / 1024 / 1024
            memory_usage = final_memory - initial_memory

            # Verify memory optimization
            assert (
                memory_usage <= scenario["expected_memory_mb"]
            ), f"Memory scenario {scenario['name']}: {memory_usage:.1f}MB > {scenario['expected_memory_mb']}MB"

            print(
                f"✓ Memory {scenario['name']}: {memory_usage:.1f}MB for {scenario['data_size']} data points"
            )

    async def test_scalability_limits(self):
        """Test system scalability limits."""
        scalability_tests = [
            {"concurrent_users": 5, "expected_degradation": 0.1},
            {"concurrent_users": 10, "expected_degradation": 0.2},
            {"concurrent_users": 20, "expected_degradation": 0.4},
            {"concurrent_users": 50, "expected_degradation": 0.7},
        ]

        baseline_template = "基准测试：{{统计:基准数值}}"

        # Establish baseline performance
        self.mock_ai_service.generate_completion.return_value = (
            '{"result": "baseline", "confidence": 0.9}'
        )
        self.etl_executor.execute_etl = AsyncMock(
            return_value=Mock(
                processed_value="baseline_value", metadata={"confidence": 0.9}
            )
        )

        baseline_metrics = await self.measure_performance(
            self.processor.process_template,
            template_content=baseline_template,
            data_schema={"fields": []},
        )

        baseline_time = baseline_metrics.processing_time

        # Test scalability at different loads
        for test in scalability_tests:
            concurrent_users = test["concurrent_users"]

            # Create concurrent tasks
            tasks = [
                self.processor.process_template(
                    template_content=f"用户{i}测试：{{{{统计:数值{i}}}}}",
                    data_schema={"fields": []},
                )
                for i in range(concurrent_users)
            ]

            # Measure concurrent performance
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()

            avg_time_per_request = (end_time - start_time) / concurrent_users
            performance_degradation = (
                avg_time_per_request - baseline_time
            ) / baseline_time

            # Verify scalability requirements
            assert (
                performance_degradation <= test["expected_degradation"]
            ), f"Scalability test {concurrent_users} users: degradation {performance_degradation:.2%} > {test['expected_degradation']:.2%}"

            successful_results = [r for r in results if not isinstance(r, Exception)]
            success_rate = len(successful_results) / len(results)

            assert (
                success_rate >= 0.95
            ), f"Scalability test {concurrent_users} users: success rate {success_rate:.2%} < 95%"

            print(
                f"✓ Scalability {concurrent_users} users: {performance_degradation:.1%} degradation, "
                f"{success_rate:.1%} success rate"
            )

    async def test_resource_utilization_monitoring(self):
        """Test resource utilization monitoring during processing."""
        monitoring_duration = 30  # seconds
        sample_interval = 1  # second

        # Resource monitoring data
        cpu_samples = []
        memory_samples = []

        # Start resource monitoring
        def monitor_resources():
            process = psutil.Process()
            for _ in range(monitoring_duration):
                cpu_samples.append(process.cpu_percent())
                memory_samples.append(process.memory_info().rss / 1024 / 1024)  # MB
                time.sleep(sample_interval)

        # Start monitoring in background
        monitor_thread = threading.Thread(target=monitor_resources)
        monitor_thread.start()

        # Generate continuous load
        self.mock_ai_service.generate_completion.return_value = (
            '{"result": "monitoring", "confidence": 0.9}'
        )
        self.etl_executor.execute_etl = AsyncMock(
            return_value=Mock(
                processed_value="monitoring_value", metadata={"confidence": 0.9}
            )
        )

        # Process multiple templates concurrently
        async def continuous_processing():
            tasks = []
            for i in range(monitoring_duration):
                template = f"监控测试{i}：{{{{统计:数值{i}}}}}"
                task = self.processor.process_template(
                    template_content=template, data_schema={"fields": []}
                )
                tasks.append(task)

                if len(tasks) >= 5:  # Process in batches
                    await asyncio.gather(*tasks, return_exceptions=True)
                    tasks = []

                await asyncio.sleep(0.5)  # Throttle requests

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        # Run continuous processing
        await continuous_processing()

        # Wait for monitoring to complete
        monitor_thread.join()

        # Analyze resource utilization
        avg_cpu = statistics.mean(cpu_samples) if cpu_samples else 0
        max_cpu = max(cpu_samples) if cpu_samples else 0
        avg_memory = statistics.mean(memory_samples) if memory_samples else 0
        max_memory = max(memory_samples) if memory_samples else 0

        # Verify resource utilization is within acceptable limits
        assert avg_cpu <= 80.0, f"Average CPU usage {avg_cpu:.1f}% > 80%"
        assert max_cpu <= 95.0, f"Peak CPU usage {max_cpu:.1f}% > 95%"
        assert avg_memory <= 500.0, f"Average memory usage {avg_memory:.1f}MB > 500MB"
        assert max_memory <= 1000.0, f"Peak memory usage {max_memory:.1f}MB > 1000MB"

        print(
            f"✓ Resource utilization: CPU avg={avg_cpu:.1f}% max={max_cpu:.1f}%, "
            f"Memory avg={avg_memory:.1f}MB max={max_memory:.1f}MB"
        )

    async def test_performance_regression_detection(self):
        """Test detection of performance regressions."""
        # Historical performance baseline
        historical_benchmarks = {
            "simple_processing": 1.5,  # seconds
            "medium_processing": 5.0,
            "complex_processing": 15.0,
            "concurrent_5_users": 8.0,
            "memory_usage_mb": 100.0,
        }

        # Current performance measurements
        current_measurements = {}

        # Test scenarios
        test_scenarios = [
            {
                "name": "simple_processing",
                "template": "简单：{{统计:数值}}",
                "complexity": "simple",
            },
            {
                "name": "medium_processing",
                "template": "中等：{{统计:数值1}} {{周期:时间}} {{区域:地区}}",
                "complexity": "medium",
            },
            {
                "name": "complex_processing",
                "template": self.generate_template_by_complexity("complex", 10),
                "complexity": "complex",
            },
        ]

        # Mock processing
        self.mock_ai_service.generate_completion.return_value = (
            '{"result": "regression_test", "confidence": 0.9}'
        )
        self.etl_executor.execute_etl = AsyncMock(
            return_value=Mock(
                processed_value="regression_value", metadata={"confidence": 0.9}
            )
        )

        # Measure current performance
        for scenario in test_scenarios:
            metrics = await self.measure_performance(
                self.processor.process_template,
                template_content=scenario["template"],
                data_schema={"fields": []},
            )
            current_measurements[scenario["name"]] = metrics.processing_time

        # Test concurrent processing
        concurrent_tasks = [
            self.processor.process_template(
                template_content="并发测试：{{统计:数值}}", data_schema={"fields": []}
            )
            for _ in range(5)
        ]

        start_time = time.time()
        await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        concurrent_time = time.time() - start_time
        current_measurements["concurrent_5_users"] = concurrent_time

        # Detect regressions
        regressions = []
        improvements = []

        for benchmark_name, historical_time in historical_benchmarks.items():
            if benchmark_name == "memory_usage_mb":
                continue  # Skip memory for this test

            current_time = current_measurements.get(benchmark_name, 0)
            if current_time > 0:
                change_percent = (current_time - historical_time) / historical_time

                if change_percent > 0.2:  # 20% regression threshold
                    regressions.append(
                        {
                            "benchmark": benchmark_name,
                            "historical": historical_time,
                            "current": current_time,
                            "regression_percent": change_percent,
                        }
                    )
                elif change_percent < -0.1:  # 10% improvement threshold
                    improvements.append(
                        {
                            "benchmark": benchmark_name,
                            "historical": historical_time,
                            "current": current_time,
                            "improvement_percent": abs(change_percent),
                        }
                    )

        # Report results
        print(f"\nPerformance Regression Analysis:")
        if regressions:
            print("  Regressions detected:")
            for regression in regressions:
                print(
                    f"    {regression['benchmark']}: {regression['historical']:.2f}s → "
                    f"{regression['current']:.2f}s ({regression['regression_percent']:.1%} slower)"
                )

        if improvements:
            print("  Improvements detected:")
            for improvement in improvements:
                print(
                    f"    {improvement['benchmark']}: {improvement['historical']:.2f}s → "
                    f"{improvement['current']:.2f}s ({improvement['improvement_percent']:.1%} faster)"
                )

        if not regressions and not improvements:
            print("  No significant performance changes detected")

        # Assert no critical regressions
        critical_regressions = [
            r for r in regressions if r["regression_percent"] > 0.5
        ]  # 50% regression
        assert (
            len(critical_regressions) == 0
        ), f"Critical performance regressions detected: {critical_regressions}"

    def generate_performance_report(self) -> str:
        """Generate comprehensive performance report."""
        if not self.performance_data:
            return "No performance data available"

        report = "Intelligent Placeholder Processing - Performance Report\n"
        report += "=" * 60 + "\n\n"

        # Summary statistics
        processing_times = [
            data["metrics"].processing_time for data in self.performance_data
        ]
        memory_usages = [
            data["metrics"].memory_usage_mb for data in self.performance_data
        ]
        throughputs = [
            data["metrics"].throughput_per_second for data in self.performance_data
        ]

        report += f"Summary Statistics:\n"
        report += (
            f"  Average Processing Time: {statistics.mean(processing_times):.2f}s\n"
        )
        report += f"  Max Processing Time: {max(processing_times):.2f}s\n"
        report += f"  Average Memory Usage: {statistics.mean(memory_usages):.1f}MB\n"
        report += f"  Max Memory Usage: {max(memory_usages):.1f}MB\n"
        report += f"  Average Throughput: {statistics.mean(throughputs):.2f} req/s\n"
        report += f"  Max Throughput: {max(throughputs):.2f} req/s\n\n"

        # Detailed results
        report += "Detailed Results:\n"
        for data in self.performance_data:
            scenario = data["scenario"]
            metrics = data["metrics"]
            report += f"  {scenario}:\n"
            report += f"    Processing Time: {metrics.processing_time:.2f}s\n"
            report += f"    Memory Usage: {metrics.memory_usage_mb:.1f}MB\n"
            report += f"    Throughput: {metrics.throughput_per_second:.2f} req/s\n"
            report += f"    Success Rate: {metrics.success_rate:.1%}\n\n"

        return report

    async def test_generate_final_performance_report(self):
        """Generate and validate final performance report."""
        # Ensure we have performance data
        if not self.performance_data:
            # Run a quick benchmark to generate data
            await self.test_single_placeholder_processing_benchmark(
                [
                    BenchmarkScenario(
                        name="final_test",
                        template_complexity="simple",
                        placeholder_count=1,
                        data_size_mb=0.1,
                        concurrent_requests=1,
                        expected_max_time=5.0,
                        expected_max_memory_mb=100,
                    )
                ]
            )

        # Generate report
        report = self.generate_performance_report()

        # Validate report content
        assert "Performance Report" in report
        assert "Summary Statistics" in report
        assert "Detailed Results" in report

        # Print report
        print(f"\n{report}")

        # Verify performance meets minimum standards
        if self.performance_data:
            avg_processing_time = statistics.mean(
                [d["metrics"].processing_time for d in self.performance_data]
            )
            avg_success_rate = statistics.mean(
                [d["metrics"].success_rate for d in self.performance_data]
            )

            assert (
                avg_processing_time <= 30.0
            ), f"Average processing time {avg_processing_time:.2f}s > 30s"
            assert (
                avg_success_rate >= 0.95
            ), f"Average success rate {avg_success_rate:.2%} < 95%"
