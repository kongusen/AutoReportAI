"""
Prompt管理器

统一管理prompt的创建、缓存、版本控制和性能监控
提供高级功能如prompt优化、A/B测试等
"""

import hashlib
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

from .factory import PromptFactory
from .context import TaskType, PromptContext


@dataclass
class PromptMetrics:
    """Prompt性能指标"""
    task_type: TaskType
    usage_count: int = 0
    avg_generation_time: float = 0.0
    cache_hit_rate: float = 0.0
    last_used: datetime = field(default_factory=datetime.now)
    total_generation_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0


@dataclass 
class PromptCacheEntry:
    """Prompt缓存条目"""
    prompt: str
    created_at: datetime
    hit_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    
    def touch(self):
        """更新访问时间"""
        self.hit_count += 1
        self.last_accessed = datetime.now()


class PromptManager:
    """
    Prompt管理器 - 统一管理prompt的生命周期
    
    功能：
    1. 统一prompt创建接口
    2. 智能缓存管理
    3. 性能监控和优化
    4. 版本控制和A/B测试
    """
    
    def __init__(self, 
                 enable_cache: bool = True,
                 cache_size_limit: int = 1000,
                 cache_ttl_seconds: int = 3600):
        
        self.factory = PromptFactory()
        
        # 缓存配置
        self.enable_cache = enable_cache
        self.cache_size_limit = cache_size_limit
        self.cache_ttl_seconds = cache_ttl_seconds
        
        # 缓存存储
        self._prompt_cache: Dict[str, PromptCacheEntry] = {}
        
        # 性能监控
        self._metrics: Dict[TaskType, PromptMetrics] = defaultdict(
            lambda: PromptMetrics(task_type=TaskType.SQL_ANALYSIS)
        )
        
        # 钩子函数
        self._pre_generation_hooks: List[Callable] = []
        self._post_generation_hooks: List[Callable] = []
        
        # 版本控制
        self._prompt_versions: Dict[str, int] = defaultdict(int)
    
    # ==================== 主要接口 ====================
    
    def create_prompt(self, task_type: TaskType, **kwargs) -> str:
        """统一prompt创建接口"""
        
        start_time = time.time()
        
        # 生成缓存键
        cache_key = self._generate_cache_key(task_type, kwargs)
        
        # 尝试从缓存获取
        cached_prompt = self._get_from_cache(cache_key)
        if cached_prompt:
            self._update_metrics(task_type, time.time() - start_time, cache_hit=True)
            return cached_prompt
        
        # 执行前置钩子
        self._execute_pre_hooks(task_type, kwargs)
        
        # 生成新prompt
        try:
            prompt = self._generate_prompt(task_type, kwargs)
            
            # 缓存prompt
            self._cache_prompt(cache_key, prompt)
            
            # 执行后置钩子
            self._execute_post_hooks(task_type, kwargs, prompt)
            
            # 更新指标
            generation_time = time.time() - start_time
            self._update_metrics(task_type, generation_time, cache_hit=False)
            
            return prompt
            
        except Exception as e:
            # 记录错误指标
            self._update_metrics(task_type, time.time() - start_time, cache_hit=False, error=True)
            raise e
    
    # ==================== 业务方法 (优雅接口) ====================
    
    def sql_analysis(self, business_command: str, requirements: str, target_objective: str, **kwargs) -> str:
        """SQL分析prompt - 优雅接口"""
        return self.create_prompt(
            TaskType.SQL_ANALYSIS,
            business_command=business_command,
            requirements=requirements,
            target_objective=target_objective,
            **kwargs
        )
    
    def context_update(self, task_context: str, current_task_info: str, target_objective: str, 
                      stored_placeholders: List[Dict], **kwargs) -> str:
        """上下文更新prompt - 优雅接口"""
        return self.create_prompt(
            TaskType.CONTEXT_UPDATE,
            task_context=task_context,
            current_task_info=current_task_info,
            target_objective=target_objective,
            stored_placeholders=stored_placeholders,
            **kwargs
        )
    
    def data_completion(self, placeholder_requirements: str, template_section: str, 
                       etl_data: List[Dict], **kwargs) -> str:
        """数据完成prompt - 优雅接口"""
        return self.create_prompt(
            TaskType.DATA_COMPLETION,
            placeholder_requirements=placeholder_requirements,
            template_section=template_section,
            etl_data=etl_data,
            **kwargs
        )
    
    def complexity_judge(self, **orchestration_context) -> str:
        """复杂度判断prompt - 优雅接口"""
        return self.create_prompt(TaskType.COMPLEXITY_JUDGE, **orchestration_context)
    
    def react_reasoning(self, objective: str, **kwargs) -> str:
        """ReAct推理prompt - 优雅接口"""
        return self.create_prompt(TaskType.REACT_REASONING, objective=objective, **kwargs)
    
    def react_observation(self, objective: str, tool_results: List[Dict], **kwargs) -> str:
        """ReAct观察prompt - 优雅接口"""
        return self.create_prompt(
            TaskType.REACT_OBSERVATION, 
            objective=objective, 
            tool_results=tool_results, 
            **kwargs
        )
    
    def react_reflection(self, objective: str, observation_results: List[Dict], 
                        overall_quality: float, meets_criteria: bool, **kwargs) -> str:
        """ReAct反思prompt - 优雅接口"""
        return self.create_prompt(
            TaskType.REACT_REFLECTION,
            objective=objective,
            observation_results=observation_results,
            overall_quality=overall_quality,
            meets_criteria=meets_criteria,
            **kwargs
        )
    
    # ==================== 缓存管理 ====================
    
    def _generate_cache_key(self, task_type: TaskType, kwargs: Dict[str, Any]) -> str:
        """生成缓存键"""
        
        # 排序kwargs确保一致性
        sorted_kwargs = sorted(kwargs.items())
        
        # 创建字符串表示
        key_string = f"{task_type.value}:{str(sorted_kwargs)}"
        
        # 生成哈希
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """从缓存获取prompt"""
        
        if not self.enable_cache:
            return None
        
        entry = self._prompt_cache.get(cache_key)
        if not entry:
            return None
        
        # 检查TTL
        if (datetime.now() - entry.created_at).seconds > self.cache_ttl_seconds:
            del self._prompt_cache[cache_key]
            return None
        
        # 更新访问记录
        entry.touch()
        return entry.prompt
    
    def _cache_prompt(self, cache_key: str, prompt: str):
        """缓存prompt"""
        
        if not self.enable_cache:
            return
        
        # 检查缓存大小限制
        if len(self._prompt_cache) >= self.cache_size_limit:
            self._evict_cache()
        
        # 添加到缓存
        self._prompt_cache[cache_key] = PromptCacheEntry(
            prompt=prompt,
            created_at=datetime.now()
        )
    
    def _evict_cache(self):
        """缓存淘汰策略 - LRU"""
        
        if not self._prompt_cache:
            return
        
        # 找到最久未访问的条目
        oldest_key = min(
            self._prompt_cache.keys(),
            key=lambda k: self._prompt_cache[k].last_accessed
        )
        
        del self._prompt_cache[oldest_key]
    
    # ==================== Prompt生成 ====================
    
    def _generate_prompt(self, task_type: TaskType, kwargs: Dict[str, Any]) -> str:
        """生成prompt"""
        
        if task_type == TaskType.SQL_ANALYSIS:
            return self.factory.create_sql_analysis_prompt(**kwargs)
        elif task_type == TaskType.CONTEXT_UPDATE:
            return self.factory.create_context_update_prompt(**kwargs)
        elif task_type == TaskType.DATA_COMPLETION:
            return self.factory.create_data_completion_prompt(**kwargs)
        elif task_type == TaskType.COMPLEXITY_JUDGE:
            return self.factory.create_complexity_judge_prompt(**kwargs)
        elif task_type == TaskType.REACT_REASONING:
            return self.factory.create_react_reasoning_prompt(**kwargs)
        elif task_type == TaskType.REACT_OBSERVATION:
            return self.factory.create_react_observation_prompt(**kwargs)
        elif task_type == TaskType.REACT_REFLECTION:
            return self.factory.create_react_reflection_prompt(**kwargs)
        else:
            raise ValueError(f"Unsupported task type: {task_type}")
    
    # ==================== 性能监控 ====================
    
    def _update_metrics(self, task_type: TaskType, generation_time: float, 
                       cache_hit: bool = False, error: bool = False):
        """更新性能指标"""
        
        metrics = self._metrics[task_type]
        metrics.task_type = task_type
        metrics.usage_count += 1
        metrics.last_used = datetime.now()
        
        if not error:
            metrics.total_generation_time += generation_time
            metrics.avg_generation_time = metrics.total_generation_time / metrics.usage_count
        
        if cache_hit:
            metrics.cache_hits += 1
        else:
            metrics.cache_misses += 1
        
        total_requests = metrics.cache_hits + metrics.cache_misses
        if total_requests > 0:
            metrics.cache_hit_rate = metrics.cache_hits / total_requests
    
    def get_metrics(self) -> Dict[TaskType, PromptMetrics]:
        """获取性能指标"""
        return dict(self._metrics)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        
        total_entries = len(self._prompt_cache)
        total_hits = sum(entry.hit_count for entry in self._prompt_cache.values())
        
        return {
            "enabled": self.enable_cache,
            "total_entries": total_entries,
            "size_limit": self.cache_size_limit,
            "ttl_seconds": self.cache_ttl_seconds,
            "total_hits": total_hits,
            "avg_hits_per_entry": total_hits / total_entries if total_entries > 0 else 0
        }
    
    # ==================== 钩子函数 ====================
    
    def add_pre_generation_hook(self, hook: Callable):
        """添加prompt生成前钩子"""
        self._pre_generation_hooks.append(hook)
    
    def add_post_generation_hook(self, hook: Callable):
        """添加prompt生成后钩子"""
        self._post_generation_hooks.append(hook)
    
    def _execute_pre_hooks(self, task_type: TaskType, kwargs: Dict[str, Any]):
        """执行前置钩子"""
        for hook in self._pre_generation_hooks:
            try:
                hook(task_type, kwargs)
            except Exception as e:
                # 钩子错误不应影响主流程
                pass
    
    def _execute_post_hooks(self, task_type: TaskType, kwargs: Dict[str, Any], prompt: str):
        """执行后置钩子"""
        for hook in self._post_generation_hooks:
            try:
                hook(task_type, kwargs, prompt)
            except Exception as e:
                # 钩子错误不应影响主流程
                pass
    
    # ==================== 管理接口 ====================
    
    def clear_cache(self):
        """清空缓存"""
        self._prompt_cache.clear()
    
    def reset_metrics(self):
        """重置指标"""
        self._metrics.clear()
    
    def configure_cache(self, enable: bool = True, size_limit: int = 1000, ttl_seconds: int = 3600):
        """配置缓存"""
        self.enable_cache = enable
        self.cache_size_limit = size_limit
        self.cache_ttl_seconds = ttl_seconds
        
        if not enable:
            self.clear_cache()
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        
        try:
            # 测试prompt生成
            test_prompt = self.react_reasoning("测试任务")
            
            return {
                "status": "healthy",
                "factory_available": True,
                "cache_functional": self.enable_cache,
                "total_task_types": len(self.factory.get_supported_task_types()),
                "cache_stats": self.get_cache_stats(),
                "test_prompt_length": len(test_prompt)
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "factory_available": False
            }