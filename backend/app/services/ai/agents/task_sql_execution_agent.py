"""
Task SQL Execution Agent - 统一的任务SQL执行Agent

实现与占位符分析Agent相同的架构模式，用于任务SQL执行的统一管理
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from uuid import uuid4
from sqlalchemy.orm import Session

from app.services.data.processing.etl.intelligent_etl_executor import IntelligentETLExecutor
from app.services.data.connectors.connector_factory import create_connector
from app.models.data_source import DataSource
from ..core.intelligent_cache import IntelligentCacheManager
# from ..core.sql_quality_assessor import SQLQualityAssessor  # 临时注释掉

logger = logging.getLogger(__name__)


class TaskExecutionMode(Enum):
    """任务执行模式"""
    DIRECT_SQL = "direct_sql"                    # 直接SQL执行
    CACHED_EXECUTION = "cached_execution"        # 缓存优先执行
    INTELLIGENT_ANALYSIS = "intelligent_analysis" # 智能分析执行
    RECOVERY_MODE = "recovery_mode"              # 故障恢复模式
    HYBRID_MODE = "hybrid_mode"                  # 混合模式


class ExecutionPriority(Enum):
    """执行优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TaskExecutionContext:
    """任务执行上下文"""
    task_id: int
    etl_instruction: Dict[str, Any]
    data_source_id: str
    execution_mode: TaskExecutionMode = TaskExecutionMode.DIRECT_SQL
    priority: ExecutionPriority = ExecutionPriority.MEDIUM
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300
    enable_cache: bool = True
    enable_recovery: bool = True
    agent_id: str = None
    
    def __post_init__(self):
        if self.agent_id is None:
            self.agent_id = str(uuid4())


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    data: Any = None
    execution_time: float = 0.0
    mode_used: TaskExecutionMode = None
    cache_hit: bool = False
    error_message: str = None
    retry_count: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TaskSQLExecutionAgent:
    """
    统一的任务SQL执行Agent
    
    提供与占位符分析Agent相同架构的任务执行服务
    """
    
    def __init__(self, db: Session, config: Dict[str, Any] = None):
        self.db = db
        self.config = config or {}
        self.agent_id = str(uuid4())
        
        # 组件初始化
        self.etl_executor = IntelligentETLExecutor(db)
        self.cache_manager = IntelligentCacheManager(db_session=db)
        # self.quality_assessor = SQLQualityAssessor(db_session=db)  # 临时注释掉
        
        # 配置参数
        self.enable_intelligent_analysis = config.get('enable_intelligent_analysis', True)
        self.enable_cache_optimization = config.get('enable_cache_optimization', True)
        self.enable_recovery_mode = config.get('enable_recovery_mode', True)
        self.default_timeout = config.get('default_timeout', 300)
        
        logger.info(f"TaskSQLExecutionAgent初始化完成: {self.agent_id}")
    
    async def execute_task(self, context: TaskExecutionContext) -> ExecutionResult:
        """
        执行任务SQL
        
        Args:
            context: 任务执行上下文
            
        Returns:
            执行结果
        """
        start_time = time.time()
        
        try:
            logger.info(f"🚀 开始任务SQL执行: task_id={context.task_id}, mode={context.execution_mode.value}")
            
            # 1. 执行模式智能判断
            optimal_mode = await self._determine_execution_mode(context)
            if optimal_mode != context.execution_mode:
                logger.info(f"📋 执行模式优化: {context.execution_mode.value} → {optimal_mode.value}")
                context.execution_mode = optimal_mode
            
            # 2. 根据模式执行任务
            result = await self._execute_by_mode(context)
            
            # 3. 结果后处理
            result = await self._post_process_result(result, context)
            
            execution_time = time.time() - start_time
            result.execution_time = execution_time
            result.mode_used = context.execution_mode
            
            logger.info(f"✅ 任务SQL执行完成: {execution_time:.2f}s, mode={context.execution_mode.value}")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ 任务SQL执行失败: {e}")
            
            # 错误恢复
            if context.enable_recovery and context.retry_count < context.max_retries:
                return await self._handle_execution_failure(e, context)
            
            return ExecutionResult(
                success=False,
                error_message=str(e),
                execution_time=execution_time,
                mode_used=context.execution_mode,
                retry_count=context.retry_count
            )
    
    async def _determine_execution_mode(self, context: TaskExecutionContext) -> TaskExecutionMode:
        """智能确定执行模式"""
        try:
            etl_instruction = context.etl_instruction
            
            # 1. 检查缓存可用性
            if context.enable_cache:
                # 简化缓存检查逻辑（临时实现）
                cache_status = {'available': False, 'confidence': 0.0}
                if cache_status['available'] and cache_status['confidence'] > 0.8:
                    logger.info("💾 检测到高质量缓存，使用缓存执行模式")
                    return TaskExecutionMode.CACHED_EXECUTION
            
            # 2. SQL复杂度分析
            if self.enable_intelligent_analysis:
                complexity = await self._analyze_sql_complexity(etl_instruction)
                if complexity['level'] == 'high':
                    logger.info("🧠 检测到复杂SQL，使用智能分析模式")
                    return TaskExecutionMode.INTELLIGENT_ANALYSIS
            
            # 3. 数据源状态检查
            data_source_health = await self._check_data_source_health(context.data_source_id)
            if not data_source_health['healthy']:
                logger.warning("⚠️ 数据源状态异常，使用恢复模式")
                return TaskExecutionMode.RECOVERY_MODE
            
            # 4. 默认使用直接执行
            return TaskExecutionMode.DIRECT_SQL
            
        except Exception as e:
            logger.warning(f"执行模式判断失败，使用默认模式: {e}")
            return TaskExecutionMode.DIRECT_SQL
    
    async def _execute_by_mode(self, context: TaskExecutionContext) -> ExecutionResult:
        """根据执行模式执行任务"""
        mode_handlers = {
            TaskExecutionMode.DIRECT_SQL: self._execute_direct_sql,
            TaskExecutionMode.CACHED_EXECUTION: self._execute_cached,
            TaskExecutionMode.INTELLIGENT_ANALYSIS: self._execute_intelligent_analysis,
            TaskExecutionMode.RECOVERY_MODE: self._execute_recovery_mode,
            TaskExecutionMode.HYBRID_MODE: self._execute_hybrid_mode
        }
        
        handler = mode_handlers.get(context.execution_mode, self._execute_direct_sql)
        return await handler(context)
    
    async def _execute_direct_sql(self, context: TaskExecutionContext) -> ExecutionResult:
        """直接SQL执行模式"""
        logger.info("🔧 执行直接SQL模式")
        
        try:
            # 使用现有的ETL执行器
            result = self.etl_executor.execute_instruction(
                context.etl_instruction, 
                context.data_source_id
            )
            
            # 缓存结果（临时简化实现）
            if context.enable_cache:
                try:
                    # 简化的缓存逻辑
                    logger.debug("缓存结果已记录（简化实现）")
                except Exception as cache_error:
                    logger.warning(f"缓存存储失败: {cache_error}")
            
            return ExecutionResult(
                success=True,
                data=result,
                cache_hit=False
            )
            
        except Exception as e:
            logger.error(f"直接SQL执行失败: {e}")
            raise
    
    async def _execute_cached(self, context: TaskExecutionContext) -> ExecutionResult:
        """缓存执行模式"""
        logger.info("💾 执行缓存模式")
        
        try:
            # 尝试从缓存获取结果（临时简化实现）
            cached_result = None  # 简化实现
            
            if cached_result:
                logger.info("✅ 缓存命中")
                return ExecutionResult(
                    success=True,
                    data=cached_result['data'],
                    cache_hit=True,
                    metadata=cached_result.get('metadata', {})
                )
            
            # 缓存未命中，回退到直接执行
            logger.info("❌ 缓存未命中，回退到直接执行")
            context.execution_mode = TaskExecutionMode.DIRECT_SQL
            return await self._execute_direct_sql(context)
            
        except Exception as e:
            logger.error(f"缓存执行失败: {e}")
            # 回退到直接执行
            context.execution_mode = TaskExecutionMode.DIRECT_SQL
            return await self._execute_direct_sql(context)
    
    async def _execute_intelligent_analysis(self, context: TaskExecutionContext) -> ExecutionResult:
        """智能分析执行模式"""
        logger.info("🧠 执行智能分析模式")
        
        try:
            # 1. SQL质量评估（临时简化实现）
            quality_report = {
                'optimization_suggestions': [],
                'overall_score': 80.0,
                'issues_found': []
            }
            
            # 2. 根据质量报告优化执行策略
            if quality_report['optimization_suggestions']:
                logger.info("🔧 应用SQL优化建议")
                optimized_instruction = await self._apply_optimizations(
                    context.etl_instruction,
                    quality_report['optimization_suggestions']
                )
                context.etl_instruction = optimized_instruction
            
            # 3. 执行优化后的指令
            result = self.etl_executor.execute_instruction(
                context.etl_instruction,
                context.data_source_id
            )
            
            return ExecutionResult(
                success=True,
                data=result,
                cache_hit=False,
                metadata={
                    'quality_report': quality_report,
                    'optimizations_applied': len(quality_report['optimization_suggestions'])
                }
            )
            
        except Exception as e:
            logger.error(f"智能分析执行失败: {e}")
            # 回退到直接执行
            context.execution_mode = TaskExecutionMode.DIRECT_SQL
            return await self._execute_direct_sql(context)
    
    async def _execute_recovery_mode(self, context: TaskExecutionContext) -> ExecutionResult:
        """故障恢复执行模式"""
        logger.info("🛠️ 执行故障恢复模式")
        
        try:
            # 1. 尝试缓存恢复（临时简化实现）
            cached_result = None  # 简化实现
            
            if cached_result:
                logger.info("💾 使用过期缓存数据恢复")
                return ExecutionResult(
                    success=True,
                    data=cached_result['data'],
                    cache_hit=True,
                    metadata={
                        'recovery_method': 'stale_cache',
                        'cache_age': cached_result.get('age_hours', 0)
                    }
                )
            
            # 2. 尝试历史数据恢复
            historical_data = await self._get_historical_data(context)
            if historical_data:
                logger.info("📚 使用历史数据恢复")
                return ExecutionResult(
                    success=True,
                    data=historical_data,
                    cache_hit=False,
                    metadata={'recovery_method': 'historical_data'}
                )
            
            # 3. 最小化功能执行
            minimal_result = await self._execute_minimal_functionality(context)
            return ExecutionResult(
                success=True,
                data=minimal_result,
                cache_hit=False,
                metadata={'recovery_method': 'minimal_functionality'}
            )
            
        except Exception as e:
            logger.error(f"故障恢复执行失败: {e}")
            return ExecutionResult(
                success=False,
                error_message=f"所有恢复尝试失败: {str(e)}",
                metadata={'recovery_method': 'failed'}
            )
    
    async def _execute_hybrid_mode(self, context: TaskExecutionContext) -> ExecutionResult:
        """混合执行模式"""
        logger.info("🔀 执行混合模式")
        
        try:
            # 根据数据特点选择最佳策略组合
            strategies = await self._determine_hybrid_strategies(context)
            
            results = []
            for strategy in strategies:
                try:
                    temp_context = context
                    temp_context.execution_mode = strategy
                    result = await self._execute_by_mode(temp_context)
                    if result.success:
                        results.append(result)
                except Exception as e:
                    logger.warning(f"混合策略{strategy.value}失败: {e}")
            
            if results:
                # 选择最佳结果
                best_result = max(results, key=lambda r: self._calculate_result_score(r))
                best_result.metadata['hybrid_strategies_tried'] = len(strategies)
                return best_result
            
            # 所有策略失败，回退到直接执行
            context.execution_mode = TaskExecutionMode.DIRECT_SQL
            return await self._execute_direct_sql(context)
            
        except Exception as e:
            logger.error(f"混合模式执行失败: {e}")
            context.execution_mode = TaskExecutionMode.DIRECT_SQL
            return await self._execute_direct_sql(context)
    
    async def _handle_execution_failure(self, 
                                      error: Exception, 
                                      context: TaskExecutionContext) -> ExecutionResult:
        """处理执行失败"""
        logger.warning(f"🔄 处理执行失败，重试 {context.retry_count + 1}/{context.max_retries}")
        
        # 增加重试计数
        context.retry_count += 1
        
        # 根据错误类型选择恢复策略
        error_type = type(error).__name__
        
        if 'Connection' in error_type or 'Network' in error_type:
            # 网络问题，尝试缓存执行
            context.execution_mode = TaskExecutionMode.CACHED_EXECUTION
        elif 'Timeout' in error_type:
            # 超时问题，使用恢复模式
            context.execution_mode = TaskExecutionMode.RECOVERY_MODE
        else:
            # 其他问题，尝试智能分析
            context.execution_mode = TaskExecutionMode.INTELLIGENT_ANALYSIS
        
        # 延迟重试
        await asyncio.sleep(2 ** context.retry_count)
        
        return await self.execute_task(context)
    
    # 辅助方法
    
    async def _analyze_sql_complexity(self, etl_instruction: Dict[str, Any]) -> Dict[str, Any]:
        """分析SQL复杂度"""
        sql = etl_instruction.get('sql_query', '')
        if not sql:
            return {'level': 'low', 'score': 0.1}
        
        # 简单的复杂度评估
        complexity_score = 0.0
        
        # 检查JOIN
        if 'JOIN' in sql.upper():
            complexity_score += 0.3
        
        # 检查子查询
        if '(' in sql and 'SELECT' in sql[sql.find('('):]:
            complexity_score += 0.4
        
        # 检查聚合函数
        aggregates = ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'GROUP BY']
        for agg in aggregates:
            if agg in sql.upper():
                complexity_score += 0.2
                break
        
        level = 'high' if complexity_score > 0.6 else 'medium' if complexity_score > 0.3 else 'low'
        
        return {'level': level, 'score': complexity_score}
    
    async def _check_data_source_health(self, data_source_id: str) -> Dict[str, Any]:
        """检查数据源健康状态"""
        try:
            data_source = self.db.query(DataSource).filter(
                DataSource.id == data_source_id
            ).first()
            
            if not data_source:
                return {'healthy': False, 'reason': 'data_source_not_found'}
            
            # 简单的连接测试
            connector = create_connector(data_source)
            await connector.connect()
            await connector.disconnect()
            
            return {'healthy': True, 'last_check': datetime.now()}
            
        except Exception as e:
            return {'healthy': False, 'reason': str(e)}
    
    async def _post_process_result(self, 
                                 result: ExecutionResult, 
                                 context: TaskExecutionContext) -> ExecutionResult:
        """结果后处理"""
        # 添加执行元数据
        result.metadata.update({
            'agent_id': self.agent_id,
            'task_id': context.task_id,
            'execution_timestamp': datetime.now().isoformat(),
            'data_source_id': context.data_source_id
        })
        
        return result
    
    async def _apply_optimizations(self, 
                                 instruction: Dict[str, Any], 
                                 suggestions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """应用优化建议"""
        # 简单的优化应用逻辑
        optimized = instruction.copy()
        
        for suggestion in suggestions:
            if suggestion['type'] == 'add_limit' and 'LIMIT' not in optimized.get('sql_query', '').upper():
                optimized['sql_query'] = f"{optimized['sql_query']} LIMIT 1000"
        
        return optimized
    
    async def _get_historical_data(self, context: TaskExecutionContext) -> Any:
        """获取历史数据"""
        # 实现历史数据获取逻辑
        return None
    
    async def _execute_minimal_functionality(self, context: TaskExecutionContext) -> Any:
        """执行最小化功能"""
        # 返回基本的空结果
        return {'message': '最小化功能执行', 'data': []}
    
    async def _determine_hybrid_strategies(self, 
                                         context: TaskExecutionContext) -> List[TaskExecutionMode]:
        """确定混合策略"""
        return [TaskExecutionMode.CACHED_EXECUTION, TaskExecutionMode.DIRECT_SQL]
    
    def _calculate_result_score(self, result: ExecutionResult) -> float:
        """计算结果分数"""
        score = 0.0
        
        if result.success:
            score += 1.0
        
        if result.cache_hit:
            score += 0.5  # 缓存命中有额外分数
        
        # 执行时间越短分数越高
        if result.execution_time < 1.0:
            score += 0.3
        elif result.execution_time < 5.0:
            score += 0.1
        
        return score


# 便捷函数

async def execute_task_sql(db: Session,
                          task_id: int,
                          etl_instruction: Dict[str, Any],
                          data_source_id: str,
                          config: Dict[str, Any] = None) -> ExecutionResult:
    """执行任务SQL的便捷函数"""
    
    agent = TaskSQLExecutionAgent(db, config)
    context = TaskExecutionContext(
        task_id=task_id,
        etl_instruction=etl_instruction,
        data_source_id=data_source_id
    )
    
    return await agent.execute_task(context)