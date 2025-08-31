"""
占位符系统性能测试
测试SQL生成和执行的性能表现
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from typing import Dict, Any, List
import statistics

from app.services.domain.placeholder.orchestrator import PlaceholderOrchestrator
from app.services.domain.placeholder.parsers import ParserFactory
from app.services.domain.placeholder.semantic import SemanticAnalysisEngine
from app.services.domain.placeholder.weight import WeightCalculator
from app.services.domain.placeholder.models import (
    PlaceholderSpec,
    DocumentContext,
    BusinessContext,
    StatisticalType,
    SyntaxType
)


class PerformanceMetrics:
    """性能指标收集器"""
    
    def __init__(self):
        self.metrics = {}
    
    def record_time(self, operation: str, duration: float):
        """记录操作耗时"""
        if operation not in self.metrics:
            self.metrics[operation] = []
        self.metrics[operation].append(duration)
    
    def get_stats(self, operation: str) -> Dict[str, float]:
        """获取操作的统计信息"""
        if operation not in self.metrics:
            return {}
        
        times = self.metrics[operation]
        return {
            "count": len(times),
            "min": min(times),
            "max": max(times), 
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "std": statistics.stdev(times) if len(times) > 1 else 0.0,
            "total": sum(times)
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """获取所有操作的统计信息"""
        return {op: self.get_stats(op) for op in self.metrics.keys()}


class TestPlaceholderPerformance:
    """占位符系统性能测试"""
    
    @pytest.fixture
    def performance_metrics(self):
        """性能指标收集器"""
        return PerformanceMetrics()
    
    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return Mock()
    
    @pytest.fixture 
    def orchestrator(self, mock_db_session):
        """创建占位符编排器"""
        return PlaceholderOrchestrator(db_session=mock_db_session)
    
    def generate_test_content(self, num_placeholders: int) -> str:
        """生成包含指定数量占位符的测试内容"""
        content_parts = ["# 性能测试报告\n"]
        
        for i in range(num_placeholders):
            if i % 4 == 0:
                # 基础占位符
                content_parts.append(f"基础指标{i}：{{metric_{i}}} 元\n")
            elif i % 4 == 1:
                # 参数化占位符
                content_parts.append(f"参数化指标{i}：{{metric_{i}(region='test', period='Q{(i//4)%4+1}')}} 元\n")
            elif i % 4 == 2:
                # 复合占位符
                content_parts.append(f"复合指标{i}：{{sum(metric_{i-1}, metric_{i-2})}} 元\n")
            else:
                # 条件占位符
                content_parts.append(f"条件判断{i}：{{if metric_{i-1} > 1000 then '高' else '低'}}\n")
        
        return "".join(content_parts)
    
    @pytest.mark.asyncio
    async def test_parsing_performance(self, performance_metrics):
        """测试占位符解析性能"""
        factory = ParserFactory()
        test_sizes = [10, 50, 100, 500, 1000]
        
        for size in test_sizes:
            content = self.generate_test_content(size)
            
            start_time = time.time()
            placeholders = factory.parse_with_auto_detection(content)
            end_time = time.time()
            
            duration = end_time - start_time
            performance_metrics.record_time(f"parsing_{size}", duration)
            
            # 验证解析结果
            assert len(placeholders) == size
            
            # 性能要求：每1000个占位符解析时间不超过5秒
            if size <= 1000:
                assert duration < 5.0, f"解析{size}个占位符耗时{duration:.2f}秒，超过5秒限制"
        
        # 输出性能统计
        print("\n=== 解析性能统计 ===")
        for size in test_sizes:
            stats = performance_metrics.get_stats(f"parsing_{size}")
            print(f"解析{size}个占位符: {stats['mean']:.3f}s (min:{stats['min']:.3f}s, max:{stats['max']:.3f}s)")

    @pytest.mark.asyncio
    async def test_context_analysis_performance(self, performance_metrics):
        """测试上下文分析性能"""
        from app.services.domain.placeholder.context import ContextAnalysisEngine
        
        engine = ContextAnalysisEngine()
        
        # 创建测试上下文
        document_context = DocumentContext(
            document_id="perf_test",
            title="性能测试文档",
            content="这是一个用于性能测试的文档内容",
            metadata={"type": "测试"}
        )
        
        business_context = BusinessContext(
            domain="性能测试",
            rules=["测试规则1", "测试规则2"],
            constraints={"currency": "CNY", "unit": "元"}
        )
        
        # 测试不同数量的占位符
        test_sizes = [10, 50, 100, 200]
        
        for size in test_sizes:
            content = self.generate_test_content(size)
            factory = ParserFactory()
            placeholders = factory.parse_with_auto_detection(content)
            
            start_time = time.time()
            
            # 并发分析所有占位符
            analysis_tasks = []
            for placeholder in placeholders:
                task = engine.analyze_comprehensive_context(
                    placeholder, document_context, business_context
                )
                analysis_tasks.append(task)
            
            # 这里使用同步方式模拟，实际应该是异步
            results = []
            for placeholder in placeholders:
                result = engine.analyze_comprehensive_context(
                    placeholder, document_context, business_context
                )
                results.append(result)
            
            end_time = time.time()
            
            duration = end_time - start_time
            performance_metrics.record_time(f"context_analysis_{size}", duration)
            
            # 验证分析结果
            assert len(results) == size
            
            # 性能要求：每个占位符的上下文分析平均时间不超过0.1秒
            avg_time_per_placeholder = duration / size
            assert avg_time_per_placeholder < 0.1, f"平均每个占位符上下文分析耗时{avg_time_per_placeholder:.3f}秒"
        
        # 输出性能统计
        print("\n=== 上下文分析性能统计 ===")
        for size in test_sizes:
            stats = performance_metrics.get_stats(f"context_analysis_{size}")
            avg_per_item = stats['mean'] / size
            print(f"分析{size}个占位符: 总时间{stats['mean']:.3f}s, 平均每个{avg_per_item:.4f}s")

    @pytest.mark.asyncio
    async def test_sql_generation_performance(self, orchestrator, performance_metrics):
        """测试SQL生成性能"""
        
        test_sizes = [10, 50, 100]
        
        with patch.object(orchestrator, '_get_agents_integration') as mock_agents:
            # 模拟Agent服务的SQL生成
            mock_agent_service = AsyncMock()
            
            async def mock_analyze_placeholders(placeholders, context=None):
                # 模拟SQL生成的计算耗时
                await asyncio.sleep(0.001 * len(placeholders))  # 每个占位符1ms
                
                results = []
                for i, placeholder in enumerate(placeholders):
                    results.append({
                        "content": placeholder.get("content", f"placeholder_{i}"),
                        "statistical_type": "STATISTICAL",
                        "generated_sql": f"SELECT SUM(amount) FROM table_{i} WHERE condition_{i}",
                        "confidence_score": 0.9
                    })
                
                return {
                    "success": True,
                    "placeholders": results
                }
            
            mock_agent_service.analyze_placeholders.side_effect = mock_analyze_placeholders
            mock_agents.return_value = mock_agent_service
            
            # 测试不同大小的占位符批次
            for size in test_sizes:
                content = self.generate_test_content(size)
                
                document_context = DocumentContext(
                    document_id="sql_perf_test",
                    title="SQL性能测试",
                    content=content,
                    metadata={"type": "性能测试"}
                )
                
                start_time = time.time()
                
                result = await orchestrator.process_document_placeholders(
                    content=content,
                    document_context=document_context,
                    business_context=None
                )
                
                end_time = time.time()
                
                duration = end_time - start_time
                performance_metrics.record_time(f"sql_generation_{size}", duration)
                
                # 验证SQL生成结果
                assert result["success"] is True
                assert len(result["placeholders"]) == size
                
                # 性能要求：批量SQL生成时间应该合理
                avg_time_per_sql = duration / size
                assert avg_time_per_sql < 0.05, f"平均每个SQL生成耗时{avg_time_per_sql:.3f}秒"
        
        # 输出性能统计
        print("\n=== SQL生成性能统计 ===")
        for size in test_sizes:
            stats = performance_metrics.get_stats(f"sql_generation_{size}")
            avg_per_item = stats['mean'] / size
            print(f"生成{size}个SQL: 总时间{stats['mean']:.3f}s, 平均每个{avg_per_item:.4f}s")

    @pytest.mark.asyncio
    async def test_memory_usage_performance(self, performance_metrics):
        """测试内存使用性能"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        factory = ParserFactory()
        
        # 记录初始内存使用
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 测试大量占位符处理的内存使用
        large_sizes = [1000, 2000, 5000]
        
        for size in large_sizes:
            content = self.generate_test_content(size)
            
            memory_before = process.memory_info().rss / 1024 / 1024  # MB
            
            start_time = time.time()
            placeholders = factory.parse_with_auto_detection(content)
            end_time = time.time()
            
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            memory_used = memory_after - memory_before
            
            duration = end_time - start_time
            performance_metrics.record_time(f"memory_test_{size}", duration)
            
            # 验证内存使用合理性
            assert memory_used < 100, f"处理{size}个占位符使用了{memory_used:.2f}MB内存，超过100MB限制"
            
            # 清理内存
            del placeholders
            del content
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_memory_increase = final_memory - initial_memory
        
        print(f"\n=== 内存使用统计 ===")
        print(f"初始内存: {initial_memory:.2f}MB")
        print(f"最终内存: {final_memory:.2f}MB")
        print(f"总内存增长: {total_memory_increase:.2f}MB")
        
        # 内存增长应该在合理范围内
        assert total_memory_increase < 200, f"总内存增长{total_memory_increase:.2f}MB超过200MB限制"

    @pytest.mark.asyncio
    async def test_concurrent_processing_performance(self, orchestrator, performance_metrics):
        """测试并发处理性能"""
        
        concurrent_levels = [1, 5, 10, 20]
        
        with patch.object(orchestrator, '_get_agents_integration') as mock_agents:
            mock_agent_service = AsyncMock()
            
            async def mock_analyze_placeholders(placeholders, context=None):
                # 模拟处理延迟
                await asyncio.sleep(0.1)
                return {
                    "success": True,
                    "placeholders": [
                        {
                            "content": p.get("content", "test"),
                            "statistical_type": "STATISTICAL",
                            "generated_sql": "SELECT COUNT(*) FROM test",
                            "confidence_score": 0.9
                        }
                        for p in placeholders
                    ]
                }
            
            mock_agent_service.analyze_placeholders.side_effect = mock_analyze_placeholders
            mock_agents.return_value = mock_agent_service
            
            for level in concurrent_levels:
                # 创建并发任务
                documents = [
                    f"文档{i}: {{placeholder_{i}}}" for i in range(level)
                ]
                
                document_contexts = [
                    DocumentContext(
                        document_id=f"concurrent_test_{i}",
                        title=f"并发测试文档{i}",
                        content=doc,
                        metadata={"type": "并发测试"}
                    )
                    for i, doc in enumerate(documents)
                ]
                
                start_time = time.time()
                
                # 创建并发任务
                tasks = []
                for i, (content, context) in enumerate(zip(documents, document_contexts)):
                    task = orchestrator.process_document_placeholders(
                        content=content,
                        document_context=context,
                        business_context=None
                    )
                    tasks.append(task)
                
                # 等待所有任务完成
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                end_time = time.time()
                
                duration = end_time - start_time
                performance_metrics.record_time(f"concurrent_{level}", duration)
                
                # 验证并发处理结果
                assert len(results) == level
                successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
                assert len(successful_results) == level, "所有并发任务都应该成功"
                
                # 并发性能验证：并发处理应该比串行处理快
                expected_serial_time = level * 0.1  # 每个任务0.1秒
                efficiency = expected_serial_time / duration if duration > 0 else 0
                
                print(f"并发级别{level}: 实际耗时{duration:.2f}s, 预期串行耗时{expected_serial_time:.2f}s, 效率{efficiency:.2f}x")
                
                # 并发效率应该有提升（允许一定的开销）
                if level > 1:
                    assert efficiency > 0.8, f"并发效率{efficiency:.2f}x太低"

    @pytest.mark.asyncio
    async def test_cache_performance_impact(self, orchestrator, performance_metrics):
        """测试缓存对性能的影响"""
        
        content = self.generate_test_content(50)
        document_context = DocumentContext(
            document_id="cache_test",
            title="缓存性能测试",
            content=content,
            metadata={"type": "缓存测试"}
        )
        
        with patch.object(orchestrator, '_get_agents_integration') as mock_agents:
            mock_agent_service = AsyncMock()
            mock_agent_service.analyze_placeholders.return_value = {
                "success": True,
                "placeholders": [{"content": "test", "sql": "SELECT 1"}]
            }
            mock_agents.return_value = mock_agent_service
            
            # 测试无缓存情况
            with patch.object(orchestrator, 'cache_manager') as mock_cache:
                mock_cache.get_cached_result.return_value = None
                mock_cache.cache_result.return_value = True
                
                start_time = time.time()
                result1 = await orchestrator.process_document_placeholders(
                    content=content,
                    document_context=document_context
                )
                end_time = time.time()
                
                no_cache_duration = end_time - start_time
                performance_metrics.record_time("no_cache", no_cache_duration)
            
            # 测试有缓存情况
            with patch.object(orchestrator, 'cache_manager') as mock_cache:
                # 模拟缓存命中
                mock_cache.get_cached_result.return_value = {
                    "success": True,
                    "placeholders": [{"content": "test", "sql": "SELECT 1"}],
                    "cached": True
                }
                
                start_time = time.time()
                result2 = await orchestrator.process_document_placeholders(
                    content=content,
                    document_context=document_context
                )
                end_time = time.time()
                
                with_cache_duration = end_time - start_time
                performance_metrics.record_time("with_cache", with_cache_duration)
            
            # 验证缓存性能提升
            if no_cache_duration > 0:
                speed_improvement = no_cache_duration / with_cache_duration
                print(f"\n=== 缓存性能影响 ===")
                print(f"无缓存处理时间: {no_cache_duration:.3f}s")
                print(f"有缓存处理时间: {with_cache_duration:.3f}s")
                print(f"性能提升: {speed_improvement:.2f}x")
                
                # 缓存应该显著提升性能
                assert speed_improvement > 2.0, f"缓存性能提升{speed_improvement:.2f}x不明显"

class TestScalabilityPerformance:
    """可扩展性性能测试"""
    
    @pytest.mark.asyncio
    async def test_linear_scalability(self):
        """测试线性可扩展性"""
        factory = ParserFactory()
        
        # 测试不同规模的处理时间是否呈线性增长
        sizes = [100, 200, 400, 800]
        processing_times = []
        
        for size in sizes:
            content = self.generate_test_content(size)
            
            start_time = time.time()
            placeholders = factory.parse_with_auto_detection(content)
            end_time = time.time()
            
            duration = end_time - start_time
            processing_times.append(duration)
            
            assert len(placeholders) == size
        
        # 验证时间复杂度近似线性
        for i in range(1, len(sizes)):
            ratio = processing_times[i] / processing_times[0]
            size_ratio = sizes[i] / sizes[0]
            
            # 允许一定的性能损失，但应该接近线性
            assert ratio <= size_ratio * 1.5, f"规模{sizes[i]}的处理时间比例{ratio:.2f}超过预期线性比例{size_ratio:.2f}的1.5倍"
            
        print("\n=== 可扩展性测试结果 ===")
        for i, (size, duration) in enumerate(zip(sizes, processing_times)):
            per_item = duration / size
            print(f"规模{size}: {duration:.3f}s, 每项{per_item:.6f}s")
    
    def generate_test_content(self, num_placeholders: int) -> str:
        """生成包含指定数量占位符的测试内容"""
        content_parts = ["# 可扩展性测试报告\n"]
        
        for i in range(num_placeholders):
            content_parts.append(f"指标{i}：{{metric_{i}}} 单位\n")
        
        return "".join(content_parts)

if __name__ == "__main__":
    # 运行性能测试
    pytest.main([__file__, "-v", "-s"])