"""
提示词性能监控系统
===================

监控提示词使用情况、性能表现和优化建议
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class PromptUsageMetrics:
    """提示词使用指标"""
    category: str
    prompt_type: str
    complexity: str
    timestamp: datetime
    success: bool
    execution_time_ms: float
    prompt_length: int
    error_message: Optional[str] = None
    user_id: Optional[str] = None
    context_size: int = 0
    iterations: int = 1


class PromptPerformanceMonitor:
    """提示词性能监控器"""
    
    def __init__(self):
        self.metrics_buffer: List[PromptUsageMetrics] = []
        self.buffer_size = 1000
        self.logger = logger
        
        # 性能统计缓存
        self.performance_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 5分钟缓存
        self.last_cache_update = {}
    
    def record_usage(
        self,
        category: str,
        prompt_type: str,
        complexity: str,
        success: bool,
        execution_time_ms: float,
        prompt_length: int,
        error_message: Optional[str] = None,
        user_id: Optional[str] = None,
        context_size: int = 0,
        iterations: int = 1
    ):
        """记录提示词使用情况"""
        
        metric = PromptUsageMetrics(
            category=category,
            prompt_type=prompt_type,
            complexity=complexity,
            timestamp=datetime.now(),
            success=success,
            execution_time_ms=execution_time_ms,
            prompt_length=prompt_length,
            error_message=error_message,
            user_id=user_id,
            context_size=context_size,
            iterations=iterations
        )
        
        self.metrics_buffer.append(metric)
        
        # 管理缓冲区大小
        if len(self.metrics_buffer) > self.buffer_size:
            self.metrics_buffer = self.metrics_buffer[-self.buffer_size:]
        
        self.logger.debug(f"记录提示词使用: {category}.{prompt_type} - {'成功' if success else '失败'}")
    
    def get_performance_summary(
        self,
        category: Optional[str] = None,
        prompt_type: Optional[str] = None,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """获取性能摘要"""
        
        cache_key = f"{category or 'all'}_{prompt_type or 'all'}_{time_window_hours}"
        
        # 检查缓存
        if (cache_key in self.performance_cache and 
            cache_key in self.last_cache_update and
            (datetime.now() - self.last_cache_update[cache_key]).seconds < self.cache_ttl):
            return self.performance_cache[cache_key]
        
        # 计算性能指标
        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
        
        filtered_metrics = [
            m for m in self.metrics_buffer
            if m.timestamp >= cutoff_time
        ]
        
        if category:
            filtered_metrics = [m for m in filtered_metrics if m.category == category]
        
        if prompt_type:
            filtered_metrics = [m for m in filtered_metrics if m.prompt_type == prompt_type]
        
        if not filtered_metrics:
            return {
                "total_usage": 0,
                "success_rate": 0,
                "average_execution_time": 0,
                "error_analysis": {},
                "complexity_distribution": {},
                "recommendations": []
            }
        
        # 计算各项指标
        total_usage = len(filtered_metrics)
        successful_count = sum(1 for m in filtered_metrics if m.success)
        success_rate = successful_count / total_usage
        
        avg_execution_time = sum(m.execution_time_ms for m in filtered_metrics) / total_usage
        avg_prompt_length = sum(m.prompt_length for m in filtered_metrics) / total_usage
        avg_iterations = sum(m.iterations for m in filtered_metrics) / total_usage
        
        # 错误分析
        error_analysis = self._analyze_errors(filtered_metrics)
        
        # 复杂度分布
        complexity_dist = defaultdict(int)
        for m in filtered_metrics:
            complexity_dist[m.complexity] += 1
        
        complexity_distribution = dict(complexity_dist)
        
        # 生成建议
        recommendations = self._generate_recommendations(
            success_rate, avg_execution_time, avg_iterations, error_analysis
        )
        
        summary = {
            "total_usage": total_usage,
            "success_rate": success_rate,
            "successful_count": successful_count,
            "failed_count": total_usage - successful_count,
            "average_execution_time": avg_execution_time,
            "average_prompt_length": avg_prompt_length,
            "average_iterations": avg_iterations,
            "error_analysis": error_analysis,
            "complexity_distribution": complexity_distribution,
            "recommendations": recommendations,
            "time_window_hours": time_window_hours,
            "generated_at": datetime.now().isoformat()
        }
        
        # 更新缓存
        self.performance_cache[cache_key] = summary
        self.last_cache_update[cache_key] = datetime.now()
        
        return summary
    
    def _analyze_errors(self, metrics: List[PromptUsageMetrics]) -> Dict[str, Any]:
        """分析错误模式"""
        
        failed_metrics = [m for m in metrics if not m.success]
        if not failed_metrics:
            return {"total_errors": 0, "error_patterns": {}, "common_causes": []}
        
        error_patterns = defaultdict(int)
        for m in failed_metrics:
            if m.error_message:
                # 简单的错误分类
                error_msg = m.error_message.lower()
                if "table" in error_msg and "not" in error_msg:
                    error_patterns["table_not_found"] += 1
                elif "column" in error_msg and "not" in error_msg:
                    error_patterns["column_not_found"] += 1
                elif "syntax" in error_msg:
                    error_patterns["syntax_error"] += 1
                elif "timeout" in error_msg:
                    error_patterns["timeout"] += 1
                else:
                    error_patterns["other"] += 1
        
        # 识别常见原因
        common_causes = []
        if error_patterns.get("table_not_found", 0) > 2:
            common_causes.append("数据源表结构信息可能不完整或过时")
        
        if error_patterns.get("column_not_found", 0) > 2:
            common_causes.append("字段映射机制需要优化")
        
        if error_patterns.get("syntax_error", 0) > 2:
            common_causes.append("SQL生成模板需要改进")
        
        return {
            "total_errors": len(failed_metrics),
            "error_patterns": dict(error_patterns),
            "common_causes": common_causes
        }
    
    def _generate_recommendations(
        self,
        success_rate: float,
        avg_execution_time: float,
        avg_iterations: float,
        error_analysis: Dict[str, Any]
    ) -> List[str]:
        """生成优化建议"""
        
        recommendations = []
        
        # 成功率建议
        if success_rate < 0.7:
            recommendations.append("🚨 成功率过低，建议增加提示词约束或改进错误恢复机制")
        elif success_rate < 0.85:
            recommendations.append("⚠️ 成功率有待改善，可考虑优化提示词复杂度")
        else:
            recommendations.append("✅ 成功率表现良好")
        
        # 执行时间建议
        if avg_execution_time > 5000:  # 5秒
            recommendations.append("🐌 平均执行时间较长，建议优化提示词长度或复杂度")
        elif avg_execution_time > 2000:  # 2秒
            recommendations.append("⏱️ 执行时间适中，可考虑进一步优化")
        else:
            recommendations.append("⚡ 执行效率良好")
        
        # 迭代次数建议
        if avg_iterations > 3:
            recommendations.append("🔄 平均迭代次数较多，建议改进初次生成质量")
        elif avg_iterations > 2:
            recommendations.append("🔄 迭代次数适中，可优化首次成功率")
        else:
            recommendations.append("🎯 迭代效率良好")
        
        # 错误模式建议
        error_patterns = error_analysis.get("error_patterns", {})
        if error_patterns.get("table_not_found", 0) > 2:
            recommendations.append("🔍 建议加强表名验证和智能匹配机制")
        
        if error_patterns.get("column_not_found", 0) > 2:
            recommendations.append("🔍 建议优化字段映射和验证逻辑")
        
        return recommendations
    
    def export_metrics(self, format: str = "json") -> str:
        """导出监控指标"""
        
        if format.lower() == "json":
            metrics_data = [asdict(m) for m in self.metrics_buffer]
            # 转换datetime为字符串
            for metric in metrics_data:
                metric['timestamp'] = metric['timestamp'].isoformat()
            
            return json.dumps({
                "export_time": datetime.now().isoformat(),
                "total_records": len(metrics_data),
                "metrics": metrics_data
            }, indent=2, ensure_ascii=False)
        
        elif format.lower() == "csv":
            import csv
            import io
            
            output = io.StringIO()
            if self.metrics_buffer:
                writer = csv.DictWriter(output, fieldnames=asdict(self.metrics_buffer[0]).keys())
                writer.writeheader()
                
                for metric in self.metrics_buffer:
                    row = asdict(metric)
                    row['timestamp'] = row['timestamp'].isoformat()
                    writer.writerow(row)
            
            return output.getvalue()
        
        else:
            raise ValueError(f"不支持的格式: {format}")
    
    def get_real_time_dashboard_data(self) -> Dict[str, Any]:
        """获取实时仪表板数据"""
        
        # 最近1小时的数据
        recent_summary = self.get_performance_summary(time_window_hours=1)
        
        # 最近24小时的数据
        daily_summary = self.get_performance_summary(time_window_hours=24)
        
        # 趋势分析
        hourly_trends = self._calculate_hourly_trends()
        
        return {
            "real_time": {
                "timestamp": datetime.now().isoformat(),
                "recent_hour": recent_summary,
                "last_24_hours": daily_summary,
                "trends": hourly_trends
            },
            "system_health": {
                "buffer_usage": len(self.metrics_buffer) / self.buffer_size,
                "cache_hit_rate": len(self.performance_cache) / max(len(self.last_cache_update), 1),
                "active_categories": len(set(m.category for m in self.metrics_buffer[-100:])),
                "active_users": len(set(m.user_id for m in self.metrics_buffer[-100:] if m.user_id))
            }
        }
    
    def _calculate_hourly_trends(self) -> Dict[str, List[float]]:
        """计算小时趋势"""
        
        now = datetime.now()
        hourly_data = defaultdict(list)
        
        for i in range(24):
            hour_start = now - timedelta(hours=i+1)
            hour_end = now - timedelta(hours=i)
            
            hour_metrics = [
                m for m in self.metrics_buffer
                if hour_start <= m.timestamp < hour_end
            ]
            
            if hour_metrics:
                success_rate = sum(1 for m in hour_metrics if m.success) / len(hour_metrics)
                avg_time = sum(m.execution_time_ms for m in hour_metrics) / len(hour_metrics)
                total_usage = len(hour_metrics)
            else:
                success_rate = 0
                avg_time = 0
                total_usage = 0
            
            hourly_data["success_rates"].append(success_rate)
            hourly_data["execution_times"].append(avg_time)
            hourly_data["usage_counts"].append(total_usage)
        
        # 反转列表使其按时间顺序
        for key in hourly_data:
            hourly_data[key] = hourly_data[key][::-1]
        
        return dict(hourly_data)


# 全局监控实例
_monitor_instance: Optional[PromptPerformanceMonitor] = None

def get_prompt_monitor() -> PromptPerformanceMonitor:
    """获取提示词监控实例"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = PromptPerformanceMonitor()
    return _monitor_instance