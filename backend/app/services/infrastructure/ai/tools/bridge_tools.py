"""
工具名称桥接 - 修复ReAct orchestrator工具名称不匹配问题
================================================================

ReAct orchestrator 期望的工具名称和实际注册的工具名称不匹配，这个文件提供桥接工具。

期望的工具名称:
- template_info_tool
- data_analyzer_tool  
- sql_generator_tool

实际的工具:
- AdvancedSQLGenerator
- SmartDataAnalyzer
- IntelligentReportGenerator
"""

import logging
from typing import Dict, Any, AsyncGenerator, List

from ..core.tools import BaseTool, ToolContext, ToolResult, ToolResultType
from .sql_generator import AdvancedSQLGenerator
from .data_analyzer import SmartDataAnalyzer

logger = logging.getLogger(__name__)


class TemplateInfoTool(BaseTool):
    """模板信息获取工具 - 桥接到现有的数据分析器"""
    
    def __init__(self):
        super().__init__(
            tool_name="template_info_tool",
            tool_category="template_analysis"
        )
        self.data_analyzer = SmartDataAnalyzer()
    
    async def execute(
        self,
        input_data: Dict[str, Any],
        context: ToolContext
    ) -> AsyncGenerator[ToolResult, None]:
        """执行模板信息提取 - 优化的上下文注入机制"""
        try:
            self.logger.info(f"🔧 template_info_tool 开始执行: {list(input_data.keys())}")
            
            # 🔍 从输入和上下文中提取模板信息
            template_context = (
                input_data.get('template_context', '') or 
                getattr(context, 'template_content', '') or
                getattr(context, 'context_data', {}).get('template_context', '')
            )
            
            placeholder_name = (
                input_data.get('placeholder_name', '') or
                input_data.get('name', '')
            )
            
            placeholder_text = (
                input_data.get('placeholder_text', '') or
                input_data.get('text', '') or
                f"{{{{{placeholder_name}}}}}"
            )
            
            # 🔧 从上下文获取额外信息
            template_id = getattr(context, 'template_id', None) or input_data.get('template_id')
            data_source_info = getattr(context, 'data_source_info', {}) or input_data.get('data_source_info', {})
            
            self.logger.info(f"📝 解析模板信息:")
            self.logger.info(f"   - 占位符: {placeholder_name}")
            self.logger.info(f"   - 模板ID: {template_id}")
            self.logger.info(f"   - 上下文长度: {len(template_context)} 字符")
            
            # 🔧 构建增强的分析器输入（基于examples参考）
            analyzer_input = {
                "analysis_type": "template_info_extraction",
                "template_analysis_request": {
                    "placeholder_name": placeholder_name,
                    "placeholder_text": placeholder_text,
                    "template_id": template_id,
                    "template_context": template_context
                },
                "context_data": {
                    "data_source_info": data_source_info,
                    "analysis_depth": "comprehensive",
                    "extraction_mode": "enhanced"
                }
            }
            
            # 调用数据分析器
            results = []
            final_result = None
            
            async for result in self.data_analyzer.execute(analyzer_input, context):
                results.append(result)
                
                # 转发进度结果
                if result.type == ToolResultType.PROGRESS:
                    yield ToolResult(
                        type=ToolResultType.PROGRESS,
                        data=f"模板解析进度: {result.data}"
                    )
                    
                elif result.type == ToolResultType.RESULT:
                    final_result = result
                    analysis_data = result.data or {}
                    
                    # 🔧 构建标准化的模板信息格式
                    template_info = {
                        "placeholder_name": placeholder_name,
                        "placeholder_text": placeholder_text,
                        "placeholder_type": self._analyze_placeholder_type(placeholder_text),
                        "business_meaning": self._extract_business_meaning(placeholder_name, template_context),
                        "data_requirements": self._extract_data_requirements(placeholder_name, data_source_info),
                        "template_context": template_context,
                        "template_id": template_id,
                        "analysis_result": analysis_data,
                        "extraction_success": True,
                        "confidence": getattr(result, 'confidence', 0.8),
                        "tool_used": "template_info_tool",
                        "metadata": {
                            "context_length": len(template_context),
                            "data_sources_available": len(data_source_info.get('tables', [])),
                            "analysis_timestamp": context.timestamp.isoformat() if hasattr(context, 'timestamp') else None
                        }
                    }
                    
                    self.logger.info(f"✅ template_info_tool 成功完成，置信度: {template_info['confidence']}")
                    
                    yield ToolResult(
                        type=ToolResultType.RESULT,
                        data=template_info
                    )
                    return
                    
                elif result.type == ToolResultType.ERROR:
                    error_msg = getattr(result, 'error_details', {}).get('message', str(result.data))
                    self.logger.error(f"❌ 数据分析器返回错误: {error_msg}")
                    yield ToolResult(
                        type=ToolResultType.ERROR,
                        data=f"模板信息提取失败: {error_msg}"
                    )
                    return
            
            # 如果没有得到最终结果，提供基础的模板信息
            self.logger.warning(f"⚠️ template_info_tool 未获得分析器结果，提供基础信息")
            
            basic_template_info = {
                "placeholder_name": placeholder_name,
                "placeholder_text": placeholder_text,
                "placeholder_type": self._analyze_placeholder_type(placeholder_text),
                "business_meaning": self._extract_business_meaning(placeholder_name, template_context),
                "data_requirements": self._extract_data_requirements(placeholder_name, {}),
                "template_context": template_context,
                "template_id": template_id,
                "extraction_success": True,
                "confidence": 0.6,  # 较低置信度，因为是基础分析
                "tool_used": "template_info_tool",
                "note": "基础分析，未使用数据分析器"
            }
            
            yield ToolResult(
                type=ToolResultType.RESULT,
                data=basic_template_info
            )
            
        except Exception as e:
            self.logger.error(f"❌ template_info_tool 执行异常: {e}", exc_info=True)
            yield ToolResult(
                type=ToolResultType.ERROR,
                data=f"模板信息提取异常: {str(e)}"
            )
    
    def _analyze_placeholder_type(self, placeholder_text: str) -> str:
        """分析占位符类型"""
        text_lower = placeholder_text.lower()
        
        if any(keyword in text_lower for keyword in ['统计', '计数', 'count', '数量']):
            return "统计类"
        elif any(keyword in text_lower for keyword in ['图表', 'chart', '可视化', '图形']):
            return "图表类"
        elif any(keyword in text_lower for keyword in ['时间', '日期', 'date', '周期']):
            return "时间类"
        elif any(keyword in text_lower for keyword in ['区域', '地区', 'region', '地点']):
            return "区域类"
        else:
            return "文本类"
    
    def _extract_business_meaning(self, placeholder_name: str, template_context: str) -> str:
        """提取业务含义"""
        # 基于占位符名称和模板上下文推断业务含义
        if "投诉" in placeholder_name or "投诉" in template_context:
            if "开始" in placeholder_name:
                return "用于定义投诉统计的起始日期"
            elif "结束" in placeholder_name:
                return "用于定义投诉统计的结束日期"
            else:
                return "与投诉数据分析相关的业务指标"
        else:
            return f"业务占位符: {placeholder_name}"
    
    def _extract_data_requirements(self, placeholder_name: str, data_source_info: Dict) -> List[str]:
        """提取数据需求"""
        requirements = []
        
        # 基于占位符名称推断数据需求
        if "时间" in placeholder_name or "日期" in placeholder_name:
            requirements.extend(["时间字段", "日期筛选"])
        
        if "统计" in placeholder_name:
            requirements.extend(["聚合计算", "数值字段"])
        
        if "区域" in placeholder_name:
            requirements.extend(["地理位置字段", "区域维度"])
        
        # 基于可用表推断
        tables = data_source_info.get('tables', [])
        if 'ods_complain' in tables:
            requirements.append("投诉数据表访问")
        
        return requirements or ["基础数据查询"]


class DataAnalyzerTool(BaseTool):
    """数据分析工具 - 桥接到SmartDataAnalyzer"""
    
    def __init__(self):
        super().__init__(
            tool_name="data_analyzer_tool",
            tool_category="data_analysis"
        )
        self.analyzer = SmartDataAnalyzer()
    
    async def execute(
        self,
        input_data: Dict[str, Any],
        context: ToolContext
    ) -> AsyncGenerator[ToolResult, None]:
        """执行数据分析 - 优化的上下文注入机制"""
        try:
            self.logger.info(f"🔧 data_analyzer_tool 开始执行: {list(input_data.keys())}")
            
            # 🔍 增强输入数据，确保包含完整上下文
            enhanced_input = input_data.copy()
            
            # 从上下文补充数据源信息
            if hasattr(context, 'data_source_info') and context.data_source_info:
                if 'data_source_info' not in enhanced_input:
                    enhanced_input['data_source_info'] = context.data_source_info
                    self.logger.info("📋 从上下文补充数据源信息")
            
            # 从上下文补充模板信息
            if hasattr(context, 'template_content') and context.template_content:
                if 'template_context' not in enhanced_input:
                    enhanced_input['template_context'] = context.template_content
                    self.logger.info("📄 从上下文补充模板内容")
            
            # 添加分析元数据
            enhanced_input['analysis_metadata'] = {
                'user_id': context.user_id,
                'task_id': context.task_id,
                'session_id': context.session_id,
                'timestamp': getattr(context, 'timestamp', datetime.now()).isoformat(),
                'analysis_mode': 'enhanced_bridge',
                'tool_chain': 'data_analyzer_tool'
            }
            
            self.logger.info(f"📊 增强输入数据构建完成:")
            self.logger.info(f"   - 输入键: {list(enhanced_input.keys())}")
            self.logger.info(f"   - 数据源表: {len(enhanced_input.get('data_source_info', {}).get('tables', []))}")
            
            # 调用分析器
            results = []
            final_result = None
            
            async for result in self.analyzer.execute(enhanced_input, context):
                results.append(result)
                
                # 转发结果，保持工具名称标识
                if result.type == ToolResultType.PROGRESS:
                    yield ToolResult(
                        type=ToolResultType.PROGRESS,
                        data=f"数据分析进度: {result.data}"
                    )
                    
                elif result.type == ToolResultType.RESULT:
                    final_result = result
                    analysis_data = result.data or {}
                    
                    # 🔧 增强结果格式
                    enhanced_result = {
                        "analysis_result": analysis_data,
                        "tool_used": "data_analyzer_tool",
                        "confidence": getattr(result, 'confidence', 0.8),
                        "analysis_type": enhanced_input.get('analysis_type', 'general'),
                        "processing_time": None,  # 可以添加处理时间
                        "insights": getattr(result, 'insights', []),
                        "metadata": enhanced_input.get('analysis_metadata', {})
                    }
                    
                    self.logger.info(f"✅ data_analyzer_tool 成功完成，置信度: {enhanced_result['confidence']}")
                    
                    yield ToolResult(
                        type=ToolResultType.RESULT,
                        data=enhanced_result
                    )
                    return
                    
                elif result.type == ToolResultType.ERROR:
                    error_msg = getattr(result, 'error_details', {}).get('message', str(result.data))
                    self.logger.error(f"❌ 数据分析器返回错误: {error_msg}")
                    yield ToolResult(
                        type=ToolResultType.ERROR,
                        data=f"数据分析失败: {error_msg}"
                    )
                    return
            
            # 如果没有得到最终结果
            self.logger.warning(f"⚠️ data_analyzer_tool 未获得有效结果，共收到 {len(results)} 个中间结果")
            if results:
                last_result = results[-1]
                self.logger.warning(f"最后结果类型: {last_result.type.value}, 数据: {str(last_result.data)[:100]}")
            
            # 提供基础的分析结果
            basic_analysis = {
                "analysis_result": {
                    "status": "partial",
                    "message": "分析器未返回完整结果，提供基础分析"
                },
                "tool_used": "data_analyzer_tool",
                "confidence": 0.5,
                "analysis_type": enhanced_input.get('analysis_type', 'fallback'),
                "note": "基础分析结果"
            }
            
            yield ToolResult(
                type=ToolResultType.RESULT,
                data=basic_analysis
            )
            
        except Exception as e:
            self.logger.error(f"❌ data_analyzer_tool 执行异常: {e}", exc_info=True)
            yield ToolResult(
                type=ToolResultType.ERROR,
                data=f"数据分析异常: {str(e)}"
            )


class SqlGeneratorTool(BaseTool):
    """SQL生成工具 - 桥接到AdvancedSQLGenerator"""
    
    def __init__(self):
        super().__init__(
            tool_name="sql_generator_tool",
            tool_category="sql_generation"
        )
        self.sql_generator = AdvancedSQLGenerator()
    
    async def execute(
        self,
        input_data: Dict[str, Any],
        context: ToolContext
    ) -> AsyncGenerator[ToolResult, None]:
        """执行SQL生成 - 优化的上下文注入机制"""
        try:
            self.logger.info(f"🔧 sql_generator_tool 开始执行: {list(input_data.keys())}")
            
            # 🔍 分析输入数据结构
            placeholder = input_data.get('placeholder', {})
            data_source_info = input_data.get('data_source_info', {})
            
            # 🔧 从上下文中补充数据源信息
            if not data_source_info and hasattr(context, 'data_source_info') and context.data_source_info:
                data_source_info = context.data_source_info
                self.logger.info("📋 从上下文获取数据源信息")
            
            if not placeholder:
                self.logger.error("❌ sql_generator_tool 缺少placeholder参数")
                yield ToolResult(
                    type=ToolResultType.ERROR,
                    data="SQL生成失败: 缺少placeholder参数"
                )
                return
            
            # 🔧 标准化数据源信息格式（参考examples/enhanced_sql_generation_demo.py）
            standardized_data_source = self._standardize_data_source_info(data_source_info)
            
            # 🔧 构建SQL生成器的输入格式（基于examples参考）
            generator_input = {
                "placeholders": [placeholder],  # 转为列表格式
                "data_source_info": standardized_data_source,
                "generation_mode": "enhanced",  # 使用增强模式
                "generation_strategy": input_data.get('generation_strategy', 'standard'),
                "template_context": getattr(context, 'template_content', '') or input_data.get('template_context', '')
            }
            
            # 🔧 更新上下文数据源信息（确保一致性）
            if hasattr(context, 'data_source_info'):
                context.data_source_info = standardized_data_source
            
            self.logger.info(f"📝 生成SQL: placeholder={placeholder.get('name', 'unknown')}")
            self.logger.info(f"📊 数据源表: {len(standardized_data_source.get('tables', []))} 个")
            self.logger.info(f"📈 表详情: {len(standardized_data_source.get('table_details', []))} 个")
            
            # 调用SQL生成器
            results = []
            final_result = None
            
            async for result in self.sql_generator.execute(generator_input, context):
                results.append(result)
                
                # 转发进度结果
                if result.type == ToolResultType.PROGRESS:
                    yield ToolResult(
                        type=ToolResultType.PROGRESS,
                        data=f"SQL生成进度: {result.data}"
                    )
                    
                elif result.type == ToolResultType.RESULT:
                    final_result = result
                    sql_result = result.data
                    
                    # 🔧 标准化结果格式
                    if isinstance(sql_result, dict):
                        standardized_result = {
                            "generated_sql": sql_result.get('generated_sql', '') or sql_result.get('sql', ''),
                            "placeholder_name": placeholder.get('name', ''),
                            "placeholder": placeholder,
                            "table_used": sql_result.get('table_used', '') or sql_result.get('selected_table', ''),
                            "confidence": getattr(result, 'confidence', 0.8),
                            "iterations": sql_result.get('iterations', 1),
                            "success": True,
                            "tool_used": "sql_generator_tool",
                            "reasoning": sql_result.get('reasoning', ''),
                            "metadata": {
                                "generation_time": sql_result.get('generation_time'),
                                "complexity": sql_result.get('complexity', 'medium')
                            }
                        }
                    else:
                        # 处理非字典结果
                        standardized_result = {
                            "generated_sql": str(sql_result) if sql_result else "",
                            "placeholder_name": placeholder.get('name', ''),
                            "placeholder": placeholder,
                            "success": True,
                            "tool_used": "sql_generator_tool"
                        }
                    
                    self.logger.info(f"✅ sql_generator_tool 成功生成SQL: {len(standardized_result['generated_sql'])} 字符")
                    
                    yield ToolResult(
                        type=ToolResultType.RESULT,
                        data=standardized_result
                    )
                    return
                    
                elif result.type == ToolResultType.ERROR:
                    error_msg = getattr(result, 'error_details', {}).get('message', str(result.data))
                    self.logger.error(f"❌ SQL生成器返回错误: {error_msg}")
                    yield ToolResult(
                        type=ToolResultType.ERROR,
                        data=f"SQL生成失败: {error_msg}"
                    )
                    return
            
            # 如果没有得到最终结果
            self.logger.warning(f"⚠️ sql_generator_tool 未获得有效结果，共收到 {len(results)} 个中间结果")
            if results:
                last_result = results[-1]
                self.logger.warning(f"最后结果类型: {last_result.type.value}, 数据: {str(last_result.data)[:100]}")
            
            yield ToolResult(
                type=ToolResultType.ERROR,
                data="SQL生成失败，生成器未返回最终结果"
            )
            
        except Exception as e:
            self.logger.error(f"❌ sql_generator_tool 执行异常: {e}", exc_info=True)
            yield ToolResult(
                type=ToolResultType.ERROR,
                data=f"SQL生成异常: {str(e)}"
            )
    
    def _standardize_data_source_info(self, data_source_info: Dict[str, Any]) -> Dict[str, Any]:
        """标准化数据源信息格式（基于examples参考）"""
        
        if not data_source_info:
            return {}
        
        # 确保有tables列表
        tables = data_source_info.get('tables', [])
        if isinstance(tables, str):
            tables = [tables]
        
        # 确保有table_details列表
        table_details = data_source_info.get('table_details', [])
        
        # 如果table_details为空但有tables，尝试构建基本的table_details
        if not table_details and tables:
            table_details = []
            for table_name in tables:
                table_details.append({
                    "name": table_name,
                    "columns_count": 0,
                    "estimated_rows": 0,
                    "all_columns": [],
                    "business_category": "未分类"
                })
        
        # 构建标准化格式
        standardized = {
            "id": data_source_info.get('id', 'unknown'),
            "type": data_source_info.get('type', 'doris'),
            "database": data_source_info.get('database', ''),
            "name": data_source_info.get('name', ''),
            "tables": tables,
            "table_details": table_details
        }
        
        return standardized


# 数据源信息工具
class DataSourceInfoTool(BaseTool):
    """数据源信息工具 - 处理数据源相关查询"""
    
    def __init__(self):
        super().__init__(
            tool_name="data_source_info_tool",
            tool_category="data_source"
        )
    
    async def execute(
        self,
        input_data: Dict[str, Any],
        context: ToolContext
    ) -> AsyncGenerator[ToolResult, None]:
        """执行数据源信息获取"""
        try:
            self.logger.info(f"🔧 data_source_info_tool 开始执行: {input_data.keys()}")
            
            # 从输入或上下文中获取数据源信息
            data_source_info = input_data.get('data_source_info')
            
            if not data_source_info and hasattr(context, 'data_source_info'):
                data_source_info = context.data_source_info
            
            if not data_source_info:
                self.logger.warning("⚠️ 未找到数据源信息")
                yield ToolResult(
                    type=ToolResultType.ERROR,
                    data="未找到数据源信息"
                )
                return
            
            # 处理和验证数据源信息
            processed_info = {
                "data_source_type": data_source_info.get('type', 'unknown'),
                "database": data_source_info.get('database', ''),
                "tables": data_source_info.get('tables', []),
                "table_details": data_source_info.get('table_details', []),
                "validation_success": True,
                "tool_used": "data_source_info_tool"
            }
            
            self.logger.info(f"✅ data_source_info_tool 成功处理 {len(processed_info.get('tables', []))} 个表")
            
            yield ToolResult(
                type=ToolResultType.RESULT,
                data=processed_info
            )
            
        except Exception as e:
            self.logger.error(f"❌ data_source_info_tool 执行异常: {e}")
            yield ToolResult(
                type=ToolResultType.ERROR,
                data=f"数据源信息处理异常: {str(e)}"
            )


# 工具注册函数
def register_bridge_tools(tool_chain):
    """注册桥接工具到工具链"""
    try:
        # 注册所有桥接工具
        template_tool = TemplateInfoTool()
        data_analyzer = DataAnalyzerTool()
        sql_generator = SqlGeneratorTool()
        data_source_tool = DataSourceInfoTool()
        
        tool_chain.register_tool(template_tool)
        tool_chain.register_tool(data_analyzer)
        tool_chain.register_tool(sql_generator)
        tool_chain.register_tool(data_source_tool)
        
        logger.info("✅ 所有桥接工具已注册")
        
        return {
            "template_info_tool": template_tool,
            "data_analyzer_tool": data_analyzer,
            "sql_generator_tool": sql_generator,
            "data_source_info_tool": data_source_tool
        }
        
    except Exception as e:
        logger.error(f"❌ 桥接工具注册失败: {e}")
        raise


# 便捷导入
__all__ = [
    "TemplateInfoTool",
    "DataAnalyzerTool", 
    "SqlGeneratorTool",
    "DataSourceInfoTool",
    "register_bridge_tools"
]