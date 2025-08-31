"""
智能占位符服务
基于DAG编排架构，构建上下文工程并调用agents系统进行智能处理
职责：
1. 构建上下文工程（提供上下文信息和存储能力）
2. 调用agents系统的DAG处理流程
3. 协调上下文工程存储中间结果
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from dataclasses import asdict

from .models import (
    PlaceholderSpec, ParameterizedPlaceholder, CompositePlaceholder, ConditionalPlaceholder,
    TimeContext, BusinessContext, DocumentContext, AgentContext,
    PlaceholderAnalysisResult, BatchAnalysisResult, ContextAnalysisResult,
    ProcessingResult, ProcessedPlaceholder, WeightComponents,
    StatisticalType, SyntaxType, ProcessingStage
)
from .context.context_analysis_engine import ContextAnalysisEngine
from .weight.weight_calculator import WeightCalculator
from .parsers.parser_factory import ParserFactory
from .cache.cache_manager import CacheManager
# 导入agents DAG系统
from ...agents import execute_placeholder_with_context

logger = logging.getLogger(__name__)


class IntelligentPlaceholderService:
    """
    智能占位符服务 - 基于DAG编排架构的占位符处理服务
    
    职责划分（符合DAG架构）：
    1. 构建上下文工程 - 提供上下文信息和存储能力
    2. 调用agents系统 - 使用DAG流程进行智能处理
    3. 协助存储中间结果 - 上下文工程协调存储功能
    4. 占位符解析和预处理 - 为agents提供结构化输入
    """
    
    def __init__(self):
        # 上下文工程核心组件
        self.context_engine = ContextAnalysisEngine()
        self.weight_calculator = WeightCalculator()
        self.parser_factory = ParserFactory()
        self.cache_manager = CacheManager()  # 作为上下文工程的存储协助
        
        self.initialized = False
    
    async def initialize(self):
        """初始化上下文工程组件"""
        if self.initialized:
            return
        
        logger.info("初始化智能占位符服务（上下文工程）...")
        
        try:
            # 初始化上下文工程组件
            await self.context_engine.initialize()
            await self.weight_calculator.initialize()
            await self.cache_manager.initialize()
            
            self.initialized = True
            logger.info("占位符服务上下文工程初始化完成")
            
        except Exception as e:
            logger.error(f"占位符服务上下文工程初始化失败: {e}")
            raise
    
    async def analyze_template_placeholders(
        self,
        template_content: str,
        template_metadata: Optional[Dict[str, Any]] = None,
        time_context: Optional[TimeContext] = None,
        business_context: Optional[BusinessContext] = None,
        document_context: Optional[DocumentContext] = None,
        force_refresh: bool = False
    ) -> BatchAnalysisResult:
        """
        分析模板中的所有占位符（符合DAG架构）
        职责：
        1. 构建上下文工程
        2. 调用agents系统DAG处理
        3. 协助存储中间结果
        
        Args:
            template_content: 模板内容
            template_metadata: 模板元数据
            time_context: 时间上下文
            business_context: 业务上下文
            document_context: 文档上下文
            force_refresh: 是否强制刷新缓存
            
        Returns:
            批量分析结果
        """
        if not self.initialized:
            await self.initialize()
        
        start_time = datetime.utcnow()
        template_id = template_metadata.get("id", "unknown") if template_metadata else "unknown"
        
        logger.info(f"开始分析模板占位符（DAG架构）: {template_id}")
        
        try:
            # 1. 生成缓存键并检查缓存
            cache_key = self._generate_analysis_cache_key(
                template_content, time_context, business_context, document_context
            )
            
            if not force_refresh:
                cached_result = await self.cache_manager.get_analysis_result(cache_key)
                if cached_result:
                    logger.info(f"从上下文工程缓存获取结果: {template_id}")
                    return cached_result
            
            # 2. 构建上下文工程
            context_engine_data = await self._build_context_engine_data(
                template_content,
                time_context or self._create_default_time_context(),
                business_context or self._create_default_business_context(),
                document_context or self._create_default_document_context()
            )
            
            # 3. 提取和预处理占位符（为agents准备结构化输入）
            placeholder_specs = await self._extract_and_preprocess_placeholders(
                template_content, context_engine_data
            )
            
            # 4. 对每个占位符调用agents DAG系统处理
            enhanced_results = []
            
            for placeholder_spec in placeholder_specs:
                try:
                    # 调用agents DAG系统处理单个占位符
                    dag_result = execute_placeholder_with_context(
                        placeholder_text=placeholder_spec.raw_text,
                        statistical_type=placeholder_spec.statistical_type.value,
                        description=placeholder_spec.description,
                        context_engine=context_engine_data,  # 传递上下文工程
                        user_id=template_metadata.get("user_id", "system")
                    )
                    
                    # 将DAG结果转换为PlaceholderAnalysisResult
                    analysis_result = await self._convert_dag_result_to_analysis(
                        placeholder_spec, dag_result, context_engine_data
                    )
                    enhanced_results.append(analysis_result)
                    
                    # 存储中间结果到上下文工程
                    await self._store_intermediate_result(
                        context_engine_data, placeholder_spec, dag_result
                    )
                    
                except Exception as e:
                    logger.error(f"占位符DAG处理失败: {placeholder_spec.raw_text}, 错误: {e}")
                    # 创建错误结果
                    error_result = self._create_error_analysis_result(placeholder_spec, str(e))
                    enhanced_results.append(error_result)
            
            # 5. 构建最终结果
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            final_result = BatchAnalysisResult(
                success=len(enhanced_results) > 0,
                template_id=template_id,
                total_placeholders=len(enhanced_results),
                successfully_analyzed=sum(1 for r in enhanced_results if r.success),
                analysis_results=enhanced_results,
                overall_confidence=self._calculate_overall_confidence(enhanced_results),
                processing_time_ms=processing_time
            )
            
            # 6. 缓存结果到上下文工程
            await self.cache_manager.store_analysis_result(cache_key, final_result)
            
            logger.info(f"模板占位符DAG处理完成: {template_id}, "
                       f"成功: {final_result.successfully_analyzed}/{final_result.total_placeholders}")
            
            return final_result
            
        except Exception as e:
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            logger.error(f"模板占位符DAG处理失败: {template_id}, 错误: {e}")
            
            return BatchAnalysisResult(
                success=False,
                template_id=template_id,
                total_placeholders=0,
                successfully_analyzed=0,
                analysis_results=[],
                overall_confidence=0.0,
                processing_time_ms=processing_time,
                error_message=str(e)
            )
    
    # 新增：模板场景下的占位符处理方法
    async def analyze_template_for_sql_generation(
        self,
        template_content: str,
        template_id: str,
        user_id: str,
        time_context: Optional[TimeContext] = None,
        business_context: Optional[BusinessContext] = None,
        document_context: Optional[DocumentContext] = None
    ) -> BatchAnalysisResult:
        """模板场景：生成高质量SQL并存储"""
        
        # 构建SQL生成模式的输出控制
        output_control = {
            "mode": "sql_only",
            "sql_storage": True,
            "chart_generation": False,
            "target_system": "storage",
            "quality_level": "high"
        }
        
        # 构建上下文工程（包含控制参数）
        context_engine_data = await self._build_context_engine_data(
            template_content=template_content,
            time_context=time_context or self._create_default_time_context(),
            business_context=business_context or self._create_default_business_context(),
            document_context=document_context or self._create_default_document_context(),
            output_control=output_control,
            data_context={"scenario": "template_sql_generation", "template_id": template_id}
        )
        
        # 调用完整的占位符分析系统
        return await self._process_placeholders_with_context(
            template_content=template_content,
            context_engine_data=context_engine_data,
            template_metadata={"id": template_id, "user_id": user_id},
            scenario="template_sql_generation"
        )
    
    async def analyze_template_for_chart_testing(
        self,
        placeholder_text: str,
        template_content: str,
        stored_sql_id: str,
        test_data: Dict[str, Any],
        template_id: str,
        user_id: str,
        time_context: Optional[TimeContext] = None,
        business_context: Optional[BusinessContext] = None,
        document_context: Optional[DocumentContext] = None
    ) -> PlaceholderAnalysisResult:
        """模板场景：基于存储SQL生成图表用于前端测试"""
        
        # 构建图表测试模式的输出控制
        output_control = {
            "mode": "chart_test",
            "sql_storage": False,
            "chart_generation": True,
            "data_source": "stored_sql",
            "target_system": "frontend"
        }
        
        # 构建数据上下文（包含存储SQL和测试数据）
        data_context = {
            "scenario": "template_chart_testing",
            "template_id": template_id,
            "stored_sql_id": stored_sql_id,
            "test_data": test_data
        }
        
        # 构建上下文工程
        context_engine_data = await self._build_context_engine_data(
            template_content=template_content,
            time_context=time_context or self._create_default_time_context(),
            business_context=business_context or self._create_default_business_context(),
            document_context=document_context or self._create_default_document_context(),
            output_control=output_control,
            data_context=data_context
        )
        
        # 调用DAG系统处理单个占位符
        return await self._process_single_placeholder_with_context(
            placeholder_text=placeholder_text,
            context_engine_data=context_engine_data,
            user_id=user_id,
            scenario="template_chart_testing"
        )
    
    async def analyze_task_for_sql_validation(
        self,
        task_id: str,
        execution_date: datetime,
        template_content: str,
        task_period_config: Optional[Dict[str, Any]] = None,
        time_context: Optional[TimeContext] = None,
        business_context: Optional[BusinessContext] = None,
        document_context: Optional[DocumentContext] = None
    ) -> BatchAnalysisResult:
        """任务场景：检查存储SQL的时效性"""
        
        # 构建SQL验证模式的输出控制
        output_control = {
            "mode": "sql_validation",
            "sql_storage": False,
            "chart_generation": False,
            "target_system": "task_scheduler",
            "validation_only": True
        }
        
        # 构建数据上下文
        data_context = {
            "scenario": "task_sql_validation",
            "task_id": task_id,
            "execution_date": execution_date.isoformat(),
            "time_range_check": True,
            "task_period_config": task_period_config
        }
        
        # 构建上下文工程
        context_engine_data = await self._build_context_engine_data(
            template_content=template_content,
            time_context=time_context or self._create_time_context_for_task(execution_date, task_period_config),
            business_context=business_context or self._create_default_business_context(),
            document_context=document_context or self._create_default_document_context(),
            output_control=output_control,
            data_context=data_context
        )
        
        # 调用完整的占位符分析系统进行验证
        return await self._process_placeholders_with_context(
            template_content=template_content,
            context_engine_data=context_engine_data,
            template_metadata={"id": task_id, "user_id": "system"},
            scenario="task_sql_validation"
        )
    
    async def analyze_task_for_chart_generation(
        self,
        placeholder_text: str,
        template_content: str,
        etl_data: Dict[str, Any],
        task_id: str,
        execution_date: datetime,
        task_period_config: Optional[Dict[str, Any]] = None,
        time_context: Optional[TimeContext] = None,
        business_context: Optional[BusinessContext] = None,
        document_context: Optional[DocumentContext] = None
    ) -> PlaceholderAnalysisResult:
        """任务场景：基于ETL数据生成图表用于报告系统"""
        
        # 构建图表生成模式的输出控制
        output_control = {
            "mode": "chart_etl",
            "sql_storage": False,
            "chart_generation": True,
            "data_source": "etl_data",
            "target_system": "reporting"
        }
        
        # 构建数据上下文（包含ETL数据）
        data_context = {
            "scenario": "task_chart_generation",
            "task_id": task_id,
            "execution_date": execution_date.isoformat(),
            "etl_data": etl_data,
            "task_period_config": task_period_config
        }
        
        # 构建上下文工程
        context_engine_data = await self._build_context_engine_data(
            template_content=template_content,
            time_context=time_context or self._create_time_context_for_task(execution_date, task_period_config),
            business_context=business_context or self._create_default_business_context(),
            document_context=document_context or self._create_default_document_context(),
            output_control=output_control,
            data_context=data_context
        )
        
        # 调用DAG系统处理单个占位符
        return await self._process_single_placeholder_with_context(
            placeholder_text=placeholder_text,
            context_engine_data=context_engine_data,
            user_id="system",
            scenario="task_chart_generation"
        )
    
    async def _build_context_engine_data(
        self,
        template_content: str,
        time_context: TimeContext,
        business_context: BusinessContext,
        document_context: DocumentContext,
        output_control: Optional[Dict[str, Any]] = None,
        data_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """构建上下文工程数据（placeholder domain职责）"""
        try:
            # 构建完整的上下文工程数据
            context_data = {
                "template_content": template_content,
                "time_context": asdict(time_context),
                "business_context": asdict(business_context), 
                "document_context": asdict(document_context),
                "weight_calculator": self.weight_calculator,
                "cache_manager": self.cache_manager,  # 协助存储能力
                "context_engine": self.context_engine,  # 上下文分析能力
                "metadata": {
                    "created_at": datetime.utcnow().isoformat(),
                    "service": "intelligent_placeholder_service",
                    "architecture": "dag_orchestration"
                }
            }
            
            # 添加输出控制参数（控制agents行为）
            if output_control:
                context_data["output_control"] = output_control
            
            # 添加数据上下文（存储SQL、ETL数据等）
            if data_context:
                context_data["data_context"] = data_context
            
            return context_data
            
        except Exception as e:
            logger.error(f"构建上下文工程数据失败: {e}")
            raise
    
    async def _extract_and_preprocess_placeholders(
        self,
        template_content: str,
        context_engine_data: Dict[str, Any]
    ) -> List[PlaceholderSpec]:
        """提取和预处理占位符（为agents准备结构化输入）"""
        try:
            # 使用parser_factory提取占位符
            placeholder_specs = []
            
            # 简单的占位符提取逻辑（可以根据需要扩展）
            import re
            placeholder_pattern = r'\{\{([^}]+)\}\}'
            matches = re.findall(placeholder_pattern, template_content)
            
            for match in matches:
                try:
                    parser = self.parser_factory.create_parser(f"{{{{{match}}}}}")
                    spec = await parser.parse(f"{{{{{match}}}}}")
                    placeholder_specs.append(spec)
                except Exception as e:
                    logger.error(f"解析占位符失败: {match}, 错误: {e}")
                    # 创建基本的占位符规范
                    spec = PlaceholderSpec(
                        statistical_type=StatisticalType.STATISTICS,
                        description=match,
                        raw_text=f"{{{{{match}}}}}",
                        syntax_type=SyntaxType.BASIC,
                        confidence_score=0.5
                    )
                    placeholder_specs.append(spec)
            
            return placeholder_specs
            
        except Exception as e:
            logger.error(f"提取和预处理占位符失败: {e}")
            return []
    
    async def _convert_dag_result_to_analysis(
        self,
        placeholder_spec: PlaceholderSpec,
        dag_result: Dict[str, Any],
        context_engine_data: Dict[str, Any]
    ) -> PlaceholderAnalysisResult:
        """将DAG结果转换为PlaceholderAnalysisResult"""
        try:
            # 执行上下文分析
            context_analysis = await self.context_engine.analyze(
                placeholder_spec,
                DocumentContext(**context_engine_data.get("document_context", {})),
                BusinessContext(**context_engine_data.get("business_context", {})),
                TimeContext(**context_engine_data.get("time_context", {}))
            )
            
            # 构建分析结果
            analysis_result = PlaceholderAnalysisResult(
                success=dag_result.get("status") == "success",
                placeholder_spec=placeholder_spec,
                context_analysis=context_analysis,
                generated_sql=dag_result.get("result", {}).get("sql", ""),
                sql_quality_score=dag_result.get("result", {}).get("quality_score", 0.0),
                execution_plan=dag_result.get("execution_plan", {}),
                analysis_insights=dag_result.get("result", {}).get("insights", ""),
                confidence_score=dag_result.get("result", {}).get("confidence", placeholder_spec.confidence_score),
                agent_reasoning=dag_result.get("dag_reasoning", ""),  # DAG推理过程
                processing_time_ms=int(dag_result.get("execution_time", 0) * 1000),
                sources=["dag_agents_system", "context_engine"]
            )
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"转换DAG结果失败: {e}")
            # 返回错误结果
            return self._create_error_analysis_result(placeholder_spec, str(e))
    
    async def _store_intermediate_result(
        self,
        context_engine_data: Dict[str, Any],
        placeholder_spec: PlaceholderSpec,
        dag_result: Dict[str, Any]
    ):
        """存储中间结果到上下文工程"""
        try:
            # 使用cache_manager存储中间结果
            storage_key = f"intermediate_{placeholder_spec.raw_text}_{datetime.utcnow().timestamp()}"
            
            intermediate_data = {
                "placeholder_spec": asdict(placeholder_spec),
                "dag_result": dag_result,
                "context_data": context_engine_data["metadata"],
                "stored_at": datetime.utcnow().isoformat()
            }
            
            await self.cache_manager.store_intermediate_result(storage_key, intermediate_data)
            
        except Exception as e:
            logger.error(f"存储中间结果失败: {e}")
            # 存储失败不应该影响主流程，只记录错误
    
    def _create_error_analysis_result(
        self,
        placeholder_spec: PlaceholderSpec,
        error_message: str
    ) -> PlaceholderAnalysisResult:
        """创建错误分析结果"""
        dummy_context = ContextAnalysisResult(
            paragraph_analysis={},
            section_analysis={},
            document_analysis={},
            business_analysis={},
            integrated_context={},
            confidence_score=0.0,
            processing_time_ms=0
        )
        
        return PlaceholderAnalysisResult(
            success=False,
            placeholder_spec=placeholder_spec,
            context_analysis=dummy_context,
            generated_sql="",
            sql_quality_score=0.0,
            execution_plan={},
            analysis_insights="",
            confidence_score=0.0,
            agent_reasoning="",
            processing_time_ms=0,
            sources=["error"],
            error_message=error_message
        )
    
    async def analyze_single_placeholder(
        self,
        placeholder_text: str,
        context_data: Optional[Dict[str, Any]] = None
    ) -> PlaceholderAnalysisResult:
        """
        分析单个占位符（符合DAG架构）
        职责：构建上下文工程，调用agents DAG系统，协助存储结果
        
        Args:
            placeholder_text: 占位符文本
            context_data: 上下文数据
            
        Returns:
            占位符分析结果
        """
        if not self.initialized:
            await self.initialize()
        
        start_time = datetime.utcnow()
        
        try:
            # 1. 解析占位符（预处理）
            parser = self.parser_factory.create_parser(placeholder_text)
            placeholder_spec = await parser.parse(placeholder_text)
            
            # 2. 构建上下文工程
            time_context = self._create_default_time_context()
            business_context = self._create_default_business_context()
            document_context = self._create_default_document_context()
            
            if context_data:
                time_context = context_data.get("time_context", time_context)
                business_context = context_data.get("business_context", business_context)
                document_context = context_data.get("document_context", document_context)
            
            context_engine_data = await self._build_context_engine_data(
                placeholder_text,
                time_context,
                business_context,
                document_context
            )
            
            # 3. 调用agents DAG系统处理
            dag_result = execute_placeholder_with_context(
                placeholder_text=placeholder_text,
                statistical_type=placeholder_spec.statistical_type.value,
                description=placeholder_spec.description,
                context_engine=context_engine_data,  # 传递上下文工程
                user_id=context_data.get("user_id", "system") if context_data else "system"
            )
            
            # 4. 转换DAG结果为分析结果
            analysis_result = await self._convert_dag_result_to_analysis(
                placeholder_spec, dag_result, context_engine_data
            )
            
            # 5. 存储中间结果到上下文工程
            await self._store_intermediate_result(
                context_engine_data, placeholder_spec, dag_result
            )
            
            return analysis_result
            
        except Exception as e:
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            logger.error(f"单个占位符DAG处理失败: {placeholder_text}, 错误: {e}")
            
            # 创建错误结果
            dummy_spec = PlaceholderSpec(
                statistical_type=StatisticalType.STATISTICS,
                description=placeholder_text,
                raw_text=placeholder_text,
                syntax_type=SyntaxType.BASIC,
                confidence_score=0.0
            )
            
            return self._create_error_analysis_result(dummy_spec, str(e))
    
    async def build_context_engine_for_workflow(
        self,
        template_id: str,
        data_source_id: str,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        为工作流构建上下文工程（符合DAG架构）
        placeholder domain职责：构建上下文工程，然后由外部系统调用agents DAG
        
        Args:
            template_id: 模板ID
            data_source_id: 数据源ID
            execution_context: 执行上下文
            
        Returns:
            上下文工程数据，供agents DAG系统使用
        """
        if not self.initialized:
            await self.initialize()
        
        logger.info(f"构建占位符工作流上下文工程: template={template_id}, data_source={data_source_id}")
        
        try:
            # 构建工作流专用的上下文工程
            workflow_context = {
                "template_id": template_id,
                "data_source_id": data_source_id,
                "execution_context": execution_context or {},
                "workflow_type": "placeholder_processing",
                "context_engine": self.context_engine,
                "cache_manager": self.cache_manager,
                "weight_calculator": self.weight_calculator,
                "parser_factory": self.parser_factory,
                "metadata": {
                    "created_at": datetime.utcnow().isoformat(),
                    "service": "intelligent_placeholder_service",
                    "architecture": "dag_orchestration",
                    "workflow_id": f"{template_id}_{data_source_id}_{int(datetime.utcnow().timestamp())}"
                },
                # 上下文工程的存储和分析能力
                "storage_capabilities": {
                    "intermediate_results": True,
                    "execution_history": True,
                    "performance_metrics": True,
                    "error_tracking": True
                }
            }
            
            return workflow_context
            
        except Exception as e:
            logger.error(f"构建占位符工作流上下文工程失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "template_id": template_id,
                "data_source_id": data_source_id
            }
    
    def _generate_analysis_cache_key(
        self,
        template_content: str,
        time_context: Optional[TimeContext],
        business_context: Optional[BusinessContext],
        document_context: Optional[DocumentContext]
    ) -> str:
        """生成分析缓存键"""
        import hashlib
        
        key_components = [template_content]
        
        if time_context:
            key_components.append(time_context.get_hash())
        
        if business_context:
            key_components.append(business_context.get_hash())
        
        if document_context:
            key_components.append(document_context.get_hash())
        
        key_string = "|".join(key_components)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _calculate_overall_confidence(
        self,
        analysis_results: List[PlaceholderAnalysisResult]
    ) -> float:
        """计算整体置信度"""
        if not analysis_results:
            return 0.0
        
        successful_results = [r for r in analysis_results if r.success]
        if not successful_results:
            return 0.0
        
        return sum(r.confidence_score for r in successful_results) / len(successful_results)
    
    def _create_default_time_context(self) -> TimeContext:
        """创建默认时间上下文"""
        now = datetime.utcnow()
        return TimeContext(
            report_period=now.strftime("%Y-%m"),
            period_type="monthly",
            start_date=now.replace(day=1),
            end_date=now,
            previous_period_start=now.replace(month=now.month-1, day=1) if now.month > 1 else now.replace(year=now.year-1, month=12, day=1),
            previous_period_end=now.replace(day=1),
            fiscal_year=str(now.year),
            quarter=f"Q{(now.month-1)//3 + 1}"
        )
    
    def _create_default_business_context(self) -> BusinessContext:
        """创建默认业务上下文"""
        return BusinessContext(
            task_type="general_report",
            department="general",
            report_level="summary",
            data_granularity="daily",
            include_comparisons=True,
            target_audience="analyst"
        )
    
    def _create_default_document_context(self) -> DocumentContext:
        """创建默认文档上下文"""
        return DocumentContext(
            document_id="unknown",
            paragraph_content="",
            paragraph_index=0,
            section_title="",
            section_index=0,
            surrounding_text="",
            document_structure={}
        )
    
    def _create_time_context_for_task(
        self, 
        execution_date: datetime, 
        task_period_config: Optional[Dict[str, Any]] = None
    ) -> TimeContext:
        """为任务创建基于执行日期和任务设置的时间上下文
        
        Args:
            execution_date: 任务执行日期
            task_period_config: 任务周期配置
                {
                    "period_type": "daily|weekly|monthly|quarterly|yearly",
                    "report_offset": 1,  # 报告偏移量，如月报通常报告上一个月
                    "start_day_of_week": 1,  # 周报的开始星期几（1=Monday）
                    "fiscal_year_start_month": 1,  # 财年开始月份
                    "custom_period": {...}  # 自定义周期设置
                }
        """
        from datetime import timedelta
        import calendar
        
        # 默认配置
        if not task_period_config:
            task_period_config = {
                "period_type": "monthly",
                "report_offset": 1
            }
        
        period_type = task_period_config.get("period_type", "monthly")
        report_offset = task_period_config.get("report_offset", 1)
        
        if period_type == "daily":
            return self._create_daily_time_context(execution_date, report_offset)
        elif period_type == "weekly":
            start_day_of_week = task_period_config.get("start_day_of_week", 1)  # Monday
            return self._create_weekly_time_context(execution_date, report_offset, start_day_of_week)
        elif period_type == "monthly":
            return self._create_monthly_time_context(execution_date, report_offset)
        elif period_type == "quarterly":
            return self._create_quarterly_time_context(execution_date, report_offset)
        elif period_type == "yearly":
            fiscal_start_month = task_period_config.get("fiscal_year_start_month", 1)
            return self._create_yearly_time_context(execution_date, report_offset, fiscal_start_month)
        else:
            # 默认返回月度上下文
            return self._create_monthly_time_context(execution_date, report_offset)
    
    def _create_daily_time_context(self, execution_date: datetime, offset: int) -> TimeContext:
        """创建日报时间上下文"""
        from datetime import timedelta
        
        # 报告日期 = 执行日期 - offset天
        report_date = execution_date - timedelta(days=offset)
        previous_date = report_date - timedelta(days=1)
        
        return TimeContext(
            report_period=report_date.strftime("%Y-%m-%d"),
            period_type="daily",
            start_date=report_date,
            end_date=report_date,
            previous_period_start=previous_date,
            previous_period_end=previous_date,
            fiscal_year=str(report_date.year),
            quarter=f"Q{(report_date.month-1)//3 + 1}"
        )
    
    def _create_weekly_time_context(self, execution_date: datetime, offset: int, start_day_of_week: int) -> TimeContext:
        """创建周报时间上下文
        
        Args:
            start_day_of_week: 1=Monday, 7=Sunday
        """
        from datetime import timedelta
        
        # 计算报告周的开始日期
        days_since_start = (execution_date.weekday() - (start_day_of_week - 1)) % 7
        current_week_start = execution_date - timedelta(days=days_since_start)
        
        # 报告周 = 当前周 - offset周
        report_week_start = current_week_start - timedelta(weeks=offset)
        report_week_end = report_week_start + timedelta(days=6)
        
        # 上一周
        previous_week_start = report_week_start - timedelta(weeks=1)
        previous_week_end = previous_week_start + timedelta(days=6)
        
        return TimeContext(
            report_period=f"{report_week_start.strftime('%Y-%m-%d')}_to_{report_week_end.strftime('%Y-%m-%d')}",
            period_type="weekly",
            start_date=report_week_start,
            end_date=report_week_end,
            previous_period_start=previous_week_start,
            previous_period_end=previous_week_end,
            fiscal_year=str(report_week_start.year),
            quarter=f"Q{(report_week_start.month-1)//3 + 1}"
        )
    
    def _create_monthly_time_context(self, execution_date: datetime, offset: int) -> TimeContext:
        """创建月报时间上下文"""
        from datetime import timedelta
        import calendar
        
        # 计算报告月份
        year = execution_date.year
        month = execution_date.month - offset
        
        while month <= 0:
            month += 12
            year -= 1
        
        # 报告月的开始和结束
        report_month_start = execution_date.replace(year=year, month=month, day=1)
        last_day = calendar.monthrange(year, month)[1]
        report_month_end = report_month_start.replace(day=last_day)
        
        # 上一个月
        prev_month = month - 1
        prev_year = year
        if prev_month <= 0:
            prev_month = 12
            prev_year -= 1
        
        previous_month_start = execution_date.replace(year=prev_year, month=prev_month, day=1)
        prev_last_day = calendar.monthrange(prev_year, prev_month)[1]
        previous_month_end = previous_month_start.replace(day=prev_last_day)
        
        return TimeContext(
            report_period=report_month_start.strftime("%Y-%m"),
            period_type="monthly",
            start_date=report_month_start,
            end_date=report_month_end,
            previous_period_start=previous_month_start,
            previous_period_end=previous_month_end,
            fiscal_year=str(year),
            quarter=f"Q{(month-1)//3 + 1}"
        )
    
    def _create_quarterly_time_context(self, execution_date: datetime, offset: int) -> TimeContext:
        """创建季报时间上下文"""
        from datetime import timedelta
        import calendar
        
        # 计算当前季度
        current_quarter = (execution_date.month - 1) // 3 + 1
        current_year = execution_date.year
        
        # 报告季度 = 当前季度 - offset
        report_quarter = current_quarter - offset
        report_year = current_year
        
        while report_quarter <= 0:
            report_quarter += 4
            report_year -= 1
        
        # 报告季度的月份范围
        quarter_start_month = (report_quarter - 1) * 3 + 1
        quarter_end_month = quarter_start_month + 2
        
        report_quarter_start = execution_date.replace(year=report_year, month=quarter_start_month, day=1)
        last_day = calendar.monthrange(report_year, quarter_end_month)[1]
        report_quarter_end = execution_date.replace(year=report_year, month=quarter_end_month, day=last_day)
        
        # 上一季度
        prev_quarter = report_quarter - 1
        prev_year = report_year
        if prev_quarter <= 0:
            prev_quarter = 4
            prev_year -= 1
        
        prev_quarter_start_month = (prev_quarter - 1) * 3 + 1
        prev_quarter_end_month = prev_quarter_start_month + 2
        
        previous_quarter_start = execution_date.replace(year=prev_year, month=prev_quarter_start_month, day=1)
        prev_last_day = calendar.monthrange(prev_year, prev_quarter_end_month)[1]
        previous_quarter_end = execution_date.replace(year=prev_year, month=prev_quarter_end_month, day=prev_last_day)
        
        return TimeContext(
            report_period=f"{report_year}-Q{report_quarter}",
            period_type="quarterly",
            start_date=report_quarter_start,
            end_date=report_quarter_end,
            previous_period_start=previous_quarter_start,
            previous_period_end=previous_quarter_end,
            fiscal_year=str(report_year),
            quarter=f"Q{report_quarter}"
        )
    
    def _create_yearly_time_context(self, execution_date: datetime, offset: int, fiscal_start_month: int) -> TimeContext:
        """创建年报时间上下文
        
        Args:
            fiscal_start_month: 财年开始月份（1-12）
        """
        from datetime import timedelta
        import calendar
        
        # 计算财年
        if execution_date.month >= fiscal_start_month:
            current_fiscal_year = execution_date.year
        else:
            current_fiscal_year = execution_date.year - 1
        
        # 报告财年 = 当前财年 - offset
        report_fiscal_year = current_fiscal_year - offset
        
        # 报告财年的开始和结束
        report_year_start = execution_date.replace(year=report_fiscal_year, month=fiscal_start_month, day=1)
        
        if fiscal_start_month == 1:
            # 自然年
            report_year_end = execution_date.replace(year=report_fiscal_year, month=12, day=31)
        else:
            # 财年跨越两个自然年
            end_year = report_fiscal_year + 1
            end_month = fiscal_start_month - 1
            if end_month <= 0:
                end_month = 12
                end_year -= 1
            
            last_day = calendar.monthrange(end_year, end_month)[1]
            report_year_end = execution_date.replace(year=end_year, month=end_month, day=last_day)
        
        # 上一财年
        previous_year_start = report_year_start.replace(year=report_fiscal_year - 1)
        previous_year_end = report_year_end.replace(year=report_fiscal_year - 1)
        
        return TimeContext(
            report_period=f"FY{report_fiscal_year}",
            period_type="yearly",
            start_date=report_year_start,
            end_date=report_year_end,
            previous_period_start=previous_year_start,
            previous_period_end=previous_year_end,
            fiscal_year=str(report_fiscal_year),
            quarter=f"Q{(execution_date.month - fiscal_start_month) // 3 + 1}" if execution_date.month >= fiscal_start_month else f"Q{(execution_date.month + 12 - fiscal_start_month) // 3 + 1}"
        )
    
    async def _process_placeholders_with_context(
        self,
        template_content: str,
        context_engine_data: Dict[str, Any],
        template_metadata: Dict[str, Any],
        scenario: str
    ) -> BatchAnalysisResult:
        """使用上下文工程处理占位符（内部方法）"""
        start_time = datetime.utcnow()
        template_id = template_metadata.get("id", "unknown")
        
        try:
            # 1. 提取和预处理占位符
            placeholder_specs = await self._extract_and_preprocess_placeholders(
                template_content, context_engine_data
            )
            
            # 2. 对每个占位符调用agents DAG系统处理
            enhanced_results = []
            
            for placeholder_spec in placeholder_specs:
                try:
                    # 调用agents DAG系统处理单个占位符
                    dag_result = execute_placeholder_with_context(
                        placeholder_text=placeholder_spec.raw_text,
                        statistical_type=placeholder_spec.statistical_type.value,
                        description=placeholder_spec.description,
                        context_engine=context_engine_data,  # 传递包含控制参数的上下文工程
                        user_id=template_metadata.get("user_id", "system")
                    )
                    
                    # 将DAG结果转换为PlaceholderAnalysisResult
                    analysis_result = await self._convert_dag_result_to_analysis(
                        placeholder_spec, dag_result, context_engine_data
                    )
                    enhanced_results.append(analysis_result)
                    
                    # 存储中间结果到上下文工程
                    await self._store_intermediate_result(
                        context_engine_data, placeholder_spec, dag_result
                    )
                    
                except Exception as e:
                    logger.error(f"占位符DAG处理失败: {placeholder_spec.raw_text}, 错误: {e}")
                    error_result = self._create_error_analysis_result(placeholder_spec, str(e))
                    enhanced_results.append(error_result)
            
            # 3. 构建最终结果
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            final_result = BatchAnalysisResult(
                success=len(enhanced_results) > 0,
                template_id=template_id,
                total_placeholders=len(enhanced_results),
                successfully_analyzed=sum(1 for r in enhanced_results if r.success),
                analysis_results=enhanced_results,
                overall_confidence=self._calculate_overall_confidence(enhanced_results),
                processing_time_ms=processing_time
            )
            
            logger.info(f"{scenario}处理完成: {template_id}, "
                       f"成功: {final_result.successfully_analyzed}/{final_result.total_placeholders}")
            
            return final_result
            
        except Exception as e:
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            logger.error(f"{scenario}处理失败: {template_id}, 错误: {e}")
            
            return BatchAnalysisResult(
                success=False,
                template_id=template_id,
                total_placeholders=0,
                successfully_analyzed=0,
                analysis_results=[],
                overall_confidence=0.0,
                processing_time_ms=processing_time,
                error_message=str(e)
            )
    
    async def _process_single_placeholder_with_context(
        self,
        placeholder_text: str,
        context_engine_data: Dict[str, Any],
        user_id: str,
        scenario: str
    ) -> PlaceholderAnalysisResult:
        """使用上下文工程处理单个占位符（内部方法）"""
        try:
            # 1. 解析占位符（预处理）
            parser = self.parser_factory.create_parser(placeholder_text)
            placeholder_spec = await parser.parse(placeholder_text)
            
            # 2. 调用agents DAG系统处理
            dag_result = execute_placeholder_with_context(
                placeholder_text=placeholder_text,
                statistical_type=placeholder_spec.statistical_type.value,
                description=placeholder_spec.description,
                context_engine=context_engine_data,  # 传递包含控制参数的上下文工程
                user_id=user_id
            )
            
            # 3. 将DAG结果转换为PlaceholderAnalysisResult
            analysis_result = await self._convert_dag_result_to_analysis(
                placeholder_spec, dag_result, context_engine_data
            )
            
            # 4. 存储中间结果到上下文工程
            await self._store_intermediate_result(
                context_engine_data, placeholder_spec, dag_result
            )
            
            logger.info(f"{scenario}单个占位符处理成功: {placeholder_text}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"{scenario}单个占位符处理失败: {placeholder_text}, 错误: {e}")
            
            # 创建基本的占位符规范
            placeholder_spec = PlaceholderSpec(
                statistical_type=StatisticalType.STATISTICS,
                description=placeholder_text,
                raw_text=placeholder_text,
                syntax_type=SyntaxType.BASIC,
                confidence_score=0.5
            )
            
            return self._create_error_analysis_result(placeholder_spec, str(e))
    
    async def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        if not self.initialized:
            return {"status": "not_initialized"}
        
        try:
            agent_status = await self._agent_manager.get_manager_status()
            cache_status = await self.cache_manager.get_cache_status()
            
            return {
                "status": "running",
                "initialized": self.initialized,
                "agent_manager": agent_status,
                "cache_manager": cache_status,
                "components": {
                    "orchestrator": "initialized",
                    "context_engine": "initialized",
                    "weight_calculator": "initialized",
                    "parser_factory": "initialized"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# 全局服务实例
_global_placeholder_service: Optional[IntelligentPlaceholderService] = None


async def get_intelligent_placeholder_service() -> IntelligentPlaceholderService:
    """获取全局智能占位符服务实例"""
    global _global_placeholder_service
    if _global_placeholder_service is None:
        _global_placeholder_service = IntelligentPlaceholderService()
        await _global_placeholder_service.initialize()
    return _global_placeholder_service


# 便捷函数
async def analyze_template_placeholders(
    template_content: str,
    template_metadata: Optional[Dict[str, Any]] = None,
    context_data: Optional[Dict[str, Any]] = None
) -> BatchAnalysisResult:
    """分析模板占位符的便捷函数"""
    service = await get_intelligent_placeholder_service()
    
    # 解析上下文数据
    time_context = None
    business_context = None
    document_context = None
    
    if context_data:
        time_context = context_data.get("time_context")
        business_context = context_data.get("business_context") 
        document_context = context_data.get("document_context")
    
    return await service.analyze_template_placeholders(
        template_content=template_content,
        template_metadata=template_metadata,
        time_context=time_context,
        business_context=business_context,
        document_context=document_context
    )


async def analyze_single_placeholder(
    placeholder_text: str,
    context_data: Optional[Dict[str, Any]] = None
) -> PlaceholderAnalysisResult:
    """分析单个占位符的便捷函数"""
    service = await get_intelligent_placeholder_service()
    return await service.analyze_single_placeholder(placeholder_text, context_data)


async def execute_placeholder_workflow(
    template_id: str,
    data_source_id: str,
    execution_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """执行占位符工作流的便捷函数"""
    service = await get_intelligent_placeholder_service()
    return await service.execute_placeholder_workflow(
        template_id, data_source_id, execution_context
    )