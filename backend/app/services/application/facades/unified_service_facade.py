"""
统一服务门面
解决跨层调用问题，为API层提供清晰的业务服务接口
基于纯数据库驱动架构，所有服务都需要用户身份验证
"""

import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

logger = logging.getLogger(__name__)


class UnifiedServiceFacade:
    """
    统一服务门面
    
    职责：
    1. 封装复杂的跨层调用逻辑
    2. 为API层提供清晰的业务服务接口
    3. 管理服务间的协调和事务
    4. 统一错误处理和日志记录
    5. 强制用户身份验证（纯数据库驱动架构要求）
    """
    
    def __init__(self, db: Session, user_id: str):
        if not user_id:
            raise ValueError("user_id is required for Unified Service Facade")
        
        self.db = db
        self.user_id = user_id
        self.logger = logger
        
        # 延迟初始化各层服务
        self._template_service = None
        self._placeholder_service = None
        self._data_source_service = None
        self._ai_service = None
        self._etl_service = None
        self._visualization_service = None
        self._schema_analysis_service = None
        self._placeholder_pipeline = None
    
    # === 模板相关服务 ===
    
    async def analyze_template_with_ai(
        self, 
        template_content: str, 
        analysis_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        使用AI分析模板内容
        
        Args:
            template_content: 模板内容
            analysis_options: 分析选项
            
        Returns:
            分析结果
        """
        try:
            # 获取占位符分析服务
            placeholder_service = await self._get_placeholder_service()
            
            # 获取AI服务
            ai_service = await self._get_ai_service()
            
            # 1. 占位符智能分析
            placeholder_analysis = await placeholder_service.analyze_template_placeholders(
                template_content=template_content,
                force_refresh=analysis_options.get('force_refresh', False) if analysis_options else False
            )
            
            # 2. AI增强分析
            ai_insights_result = await ai_service.analyze_template(
                user_id=self.user_id,
                template_id="template_analysis",
                template_content=template_content,
                data_source_info={"type": "business_logic_analysis"}
            )
            ai_insights = ai_insights_result.get("result", "") if isinstance(ai_insights_result, dict) else str(ai_insights_result)
            
            # 3. 合并分析结果
            result = {
                "placeholder_analysis": placeholder_analysis,
                "ai_insights": ai_insights,
                "analysis_timestamp": datetime.utcnow(),
                "user_id": self.user_id,
                "success": True
            }
            
            self.logger.info(f"模板AI分析完成，用户: {self.user_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"模板AI分析失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "user_id": self.user_id,
                "analysis_timestamp": datetime.utcnow()
            }
    
    async def generate_template_with_ai(
        self, 
        requirements: str,
        template_type: str = "report",
        generation_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        使用AI生成模板
        
        Args:
            requirements: 模板需求描述
            template_type: 模板类型
            generation_options: 生成选项
            
        Returns:
            生成的模板和相关信息
        """
        try:
            ai_service = await self._get_ai_service()
            
            # 构建生成提示
            generation_prompt = f"""
            基于以下需求生成{template_type}模板：
            {requirements}
            
            请生成包含以下要素的模板：
            1. 模板结构
            2. 占位符设计
            3. 样式建议
            4. 使用说明
            """
            
            # AI生成模板内容
            content_result = await ai_service.generate_content(
                user_id=self.user_id,
                template_parts=[{"type": template_type, "requirements": requirements}],
                data_context={"template_type": template_type},
                style_requirements={"format": "template", "structure": "professional"}
            )
            generated_content = content_result.get("result", "") if isinstance(content_result, dict) else str(content_result)
            
            result = {
                "generated_content": generated_content,
                "template_type": template_type,
                "requirements": requirements,
                "generation_timestamp": datetime.utcnow(),
                "user_id": self.user_id,
                "success": True
            }
            
            self.logger.info(f"AI模板生成完成，用户: {self.user_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"AI模板生成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "user_id": self.user_id,
                "generation_timestamp": datetime.utcnow()
            }
    
    # === 数据源相关服务 ===
    
    async def analyze_data_source_with_ai(
        self, 
        data_source_id: str,
        analysis_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """
        使用AI分析数据源
        
        Args:
            data_source_id: 数据源ID
            analysis_type: 分析类型
            
        Returns:
            分析结果
        """
        try:
            # 获取Schema分析服务
            schema_service = await self._get_schema_analysis_service()
            
            # 根据分析类型执行不同的分析
            if analysis_type == "relationships":
                result = await schema_service.analyze_table_relationships(data_source_id)
            elif analysis_type == "semantics":
                result = await schema_service.analyze_business_semantics(data_source_id)
            elif analysis_type == "quality":
                result = await schema_service.analyze_data_quality(data_source_id)
            else:  # comprehensive
                # 综合分析：执行所有类型的分析
                relationships = await schema_service.analyze_table_relationships(data_source_id)
                semantics = await schema_service.analyze_business_semantics(data_source_id)
                quality = await schema_service.analyze_data_quality(data_source_id)
                
                result = {
                    "relationships": relationships,
                    "semantics": semantics,
                    "quality": quality,
                    "analysis_type": "comprehensive",
                    "success": True
                }
            
            result["user_id"] = self.user_id
            result["data_source_id"] = data_source_id
            result["analysis_timestamp"] = datetime.utcnow()
            
            self.logger.info(f"数据源AI分析完成，用户: {self.user_id}, 数据源: {data_source_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"数据源AI分析失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "user_id": self.user_id,
                "data_source_id": data_source_id,
                "analysis_timestamp": datetime.utcnow()
            }
    
    # === 可视化服务 ===
    
    async def generate_charts(
        self,
        data_source: str,
        requirements: str,
        output_format: str = "json"
    ) -> Dict[str, Any]:
        """
        基于数据源和需求生成图表
        
        Args:
            data_source: 数据查询SQL或数据文件路径
            requirements: 图表需求描述
            output_format: 输出格式 (json, png, svg, pdf)
            
        Returns:
            图表生成结果
        """
        try:
            visualization_service = await self._get_visualization_service()
            
            # 1. 解析需求，确定图表类型
            chart_info = await self._parse_chart_requirements(requirements)
            
            # 2. 获取或处理数据
            data = await self._prepare_chart_data(data_source)
            
            if not data:
                return {
                    "success": False,
                    "error": "No data available for chart generation",
                    "user_id": self.user_id
                }
            
            # 3. 生成图表
            chart_result = visualization_service.generate_chart(
                data=data,
                chart_type=chart_info["chart_type"],
                config=chart_info["config"],
                output_format=output_format
            )
            
            if chart_result.get("success", True):
                result = {
                    "success": True,
                    "generated_charts": [{
                        "chart_type": chart_info["chart_type"],
                        "output_path": chart_result.get("image_path"),
                        "config": chart_result.get("chart_config"),
                        "echarts_config": chart_result.get("echarts_config")
                    }],
                    "metadata": {
                        "requirements_parsed": requirements,
                        "data_points": len(data),
                        "generation_time": datetime.now().isoformat(),
                        "user_id": self.user_id
                    }
                }
            else:
                result = {
                    "success": False,
                    "error": chart_result.get("error", "Chart generation failed"),
                    "user_id": self.user_id
                }
            
            self.logger.info(f"图表生成完成，用户: {self.user_id}")
            return result
                
        except Exception as e:
            self.logger.error(f"图表生成失败: {str(e)}")
            return {
                "success": False,
                "error": f"Chart generation failed: {str(e)}",
                "user_id": self.user_id
            }
    
    # === ETL相关服务 ===
    
    async def create_intelligent_etl_job(
        self, 
        source_info: Dict[str, Any],
        target_info: Dict[str, Any],
        transformation_requirements: str
    ) -> Dict[str, Any]:
        """
        创建智能ETL作业
        
        Args:
            source_info: 源信息
            target_info: 目标信息  
            transformation_requirements: 转换需求
            
        Returns:
            ETL作业信息
        """
        try:
            # 获取ETL服务
            etl_service = await self._get_etl_service()
            
            # 获取AI服务用于生成转换逻辑
            ai_service = await self._get_ai_service()
            
            # AI生成ETL转换逻辑
            etl_prompt = f"""
            基于以下信息生成ETL转换逻辑：
            
            源信息: {source_info}
            目标信息: {target_info}
            转换需求: {transformation_requirements}
            
            请生成：
            1. 数据提取策略
            2. 转换规则
            3. 加载配置
            4. 错误处理逻辑
            """
            
            etl_result = await ai_service.plan_etl_workflow(
                user_id=self.user_id,
                source_schema=source_info,
                target_schema=target_info,
                business_requirements=transformation_requirements
            )
            ai_generated_logic = etl_result.get("result", "") if isinstance(etl_result, dict) else str(etl_result)
            
            # 创建ETL作业
            etl_job_config = {
                "source_info": source_info,
                "target_info": target_info,
                "transformation_requirements": transformation_requirements,
                "ai_generated_logic": ai_generated_logic,
                "created_by": self.user_id,
                "created_at": datetime.utcnow()
            }
            
            result = {
                "etl_job_config": etl_job_config,
                "ai_generated_logic": ai_generated_logic,
                "success": True,
                "user_id": self.user_id
            }
            
            self.logger.info(f"智能ETL作业创建完成，用户: {self.user_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"智能ETL作业创建失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "user_id": self.user_id
            }
    
    # === 私有方法 - 延迟初始化服务 ===
    
    async def _get_placeholder_service(self):
        """获取占位符服务"""
        if self._placeholder_service is None:
            from app.services.application.factories import create_intelligent_placeholder_service
            self._placeholder_service = create_intelligent_placeholder_service()
            await self._placeholder_service.initialize()
        return self._placeholder_service
    
    async def _get_ai_service(self):
        """获取统一AI门面服务"""
        if self._ai_service is None:
            from app.services.infrastructure.agents import execute_agent_task
            self._ai_service = get_unified_ai_facade()
        return self._ai_service
    
    async def _get_etl_service(self):
        """获取ETL服务"""
        if self._etl_service is None:
            from app.services.data.processing.etl.etl_service import ETLService
            self._etl_service = ETLService()
        return self._etl_service
    
    async def _get_visualization_service(self):
        """获取可视化服务"""
        if self._visualization_service is None:
            from app.services.data.processing.visualization_service import VisualizationService
            self._visualization_service = VisualizationService()
        return self._visualization_service
    
    async def _get_schema_analysis_service(self):
        """获取Schema分析服务"""
        if self._schema_analysis_service is None:
            from app.services.data.schemas.schema_analysis_service import create_schema_analysis_service
            self._schema_analysis_service = create_schema_analysis_service(self.db, self.user_id)
        return self._schema_analysis_service

    async def _get_placeholder_pipeline(self):
        if self._placeholder_pipeline is None:
            from app.services.application.factories import create_placeholder_pipeline_service
            self._placeholder_pipeline = create_placeholder_pipeline_service()
        return self._placeholder_pipeline

    # === 新增：占位符流水线编排 ===
    async def etl_pre_scan_placeholders(self, template_id: str, data_source_id: str) -> Dict[str, Any]:
        pipeline = await self._get_placeholder_pipeline()
        return await pipeline.etl_pre_scan(template_id, data_source_id)

    async def generate_report_v2(
        self,
        template_id: str,
        data_source_id: str,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        output_dir: Optional[str] = None,
        schedule: Optional[Dict[str, Any]] = None,
        execution_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        pipeline = await self._get_placeholder_pipeline()
        assembled = await pipeline.assemble_report(
            template_id,
            data_source_id,
            user_id=self.user_id,  # 传递用户ID到pipeline
            start_date=start_date,
            end_date=end_date,
            schedule=schedule,
            execution_time=execution_time,
        )
        content = assembled.get("content", "")
        artifacts = assembled.get("artifacts", [])
        # 可选：调用Word生成
        try:
            from app.services.domain.reporting.word_generator_service import WordGeneratorService
            wg = WordGeneratorService()
            report_path = wg.generate_report_from_content(content, output_path=None)  # 若服务支持自动路径
        except Exception:
            report_path = None
        return {
            "success": True,
            "content_preview": content[:2000],
            "artifacts": artifacts,
            "output_path": report_path,
        }
    
    async def _parse_chart_requirements(self, requirements: str) -> Dict[str, Any]:
        """解析图表需求描述"""
        req_lower = requirements.lower()
        
        chart_type = "bar_chart"  # 默认
        config = {}
        
        if any(word in req_lower for word in ["饼图", "pie", "比例", "占比", "percentage"]):
            chart_type = "pie_chart"
        elif any(word in req_lower for word in ["折线", "line", "趋势", "trend", "时间"]):
            chart_type = "line_chart"
        elif any(word in req_lower for word in ["散点", "scatter", "关系", "correlation"]):
            chart_type = "scatter_chart"
        elif any(word in req_lower for word in ["雷达", "radar", "多维", "能力"]):
            chart_type = "radar_chart"
        elif any(word in req_lower for word in ["漏斗", "funnel", "转化", "流程"]):
            chart_type = "funnel_chart"
        
        # 提取标题
        if "标题" in requirements:
            title_part = requirements.split("标题")[1].split(",")[0].split("，")[0]
            config["title"] = title_part.strip()
        else:
            config["title"] = "数据图表"
        
        return {
            "chart_type": chart_type,
            "config": config,
            "original_requirements": requirements
        }
    
    async def _prepare_chart_data(self, data_source: str) -> List[Dict[str, Any]]:
        """准备图表数据"""
        try:
            # 如果是SQL查询
            if data_source.strip().lower().startswith("select"):
                # 执行SQL查询获取数据
                try:
                    from app.services.data.connectors.connector_factory import create_connector
                    from app.core.data_source_utils import parse_data_source_id
                    
                    # 查找数据源
                    data_source = parse_data_source_id("default", self.user_id, self.db)
                    if not data_source:
                        return []
                    
                    # 创建连接器并执行查询
                    connector = create_connector(data_source)
                    await connector.connect()
                    
                    try:
                        result = await connector.execute_query(data_source)
                        if hasattr(result, 'data') and not result.data.empty:
                            return result.data.to_dict('records')
                    finally:
                        await connector.disconnect()
                        
                except Exception as e:
                    self.logger.error(f"SQL查询失败: {e}")
                    raise ValueError(f"数据查询失败: {str(e)}")
            
            # 如果是文件路径
            elif data_source.endswith(('.csv', '.json', '.xlsx')):
                # 读取文件数据
                try:
                    from app.services.infrastructure.storage.file_storage_service import file_storage_service
                    import pandas as pd
                    from io import BytesIO
                    
                    # 下载文件数据
                    file_data, _ = file_storage_service.download_file(data_source)
                    
                    # 根据文件类型解析数据
                    if data_source.endswith('.csv'):
                        df = pd.read_csv(BytesIO(file_data))
                    elif data_source.endswith('.xlsx'):
                        df = pd.read_excel(BytesIO(file_data))
                    elif data_source.endswith('.json'):
                        df = pd.read_json(BytesIO(file_data))
                    else:
                        raise ValueError(f"不支持的文件格式: {data_source}")
                    
                    return df.to_dict('records')
                    
                except Exception as e:
                    self.logger.error(f"文件读取失败: {e}")
                    raise ValueError(f"文件数据读取失败: {str(e)}")
            
            # 其他情况抛出错误
            else:
                raise ValueError(f"不支持的数据源类型: {data_source}")
                
        except Exception as e:
            self.logger.error(f"数据准备失败: {str(e)}")
            return []


# === 工厂函数 ===

def create_unified_service_facade(db: Session, user_id: str) -> UnifiedServiceFacade:
    """创建统一服务门面实例"""
    return UnifiedServiceFacade(db, user_id)


# === 快捷服务函数 ===

async def analyze_template_for_user(
    db: Session, 
    user_id: str, 
    template_content: str,
    analysis_options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """用户专属模板分析快捷函数"""
    facade = create_unified_service_facade(db, user_id)
    return await facade.analyze_template_with_ai(template_content, analysis_options)


async def analyze_data_source_for_user(
    db: Session,
    user_id: str, 
    data_source_id: str,
    analysis_type: str = "comprehensive"
) -> Dict[str, Any]:
    """用户专属数据源分析快捷函数"""
    facade = create_unified_service_facade(db, user_id)
    return await facade.analyze_data_source_with_ai(data_source_id, analysis_type)


async def generate_charts_for_user(
    db: Session,
    user_id: str,
    data_source: str,
    requirements: str,
    output_format: str = "json"
) -> Dict[str, Any]:
    """用户专属图表生成快捷函数"""
    facade = create_unified_service_facade(db, user_id)
    return await facade.generate_charts(data_source, requirements, output_format)
