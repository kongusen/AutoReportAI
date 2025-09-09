"""
图表生成服务

基于数据和配置生成各种类型的图表，支持：
1. 多种图表类型（柱状图、折线图、饼图、散点图等）
2. 图表占位符分析和数据匹配
3. 智能图表配置生成
4. 图表文件生成和存储
"""

import logging
import os
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import pandas as pd

logger = logging.getLogger(__name__)


class ChartType(Enum):
    """图表类型"""
    BAR = "bar"  # 柱状图
    LINE = "line"  # 折线图
    PIE = "pie"  # 饼图
    SCATTER = "scatter"  # 散点图
    AREA = "area"  # 面积图
    HISTOGRAM = "histogram"  # 直方图
    BOX = "box"  # 箱线图
    HEATMAP = "heatmap"  # 热力图
    WATERFALL = "waterfall"  # 瀑布图
    GAUGE = "gauge"  # 仪表盘


@dataclass
class ChartConfig:
    """图表配置"""
    chart_type: ChartType
    title: str
    x_column: str
    y_column: Union[str, List[str]]
    width: int = 800
    height: int = 600
    color_scheme: str = "default"
    show_legend: bool = True
    show_grid: bool = True
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    format_options: Optional[Dict[str, Any]] = None
    

@dataclass
class ChartGenerationResult:
    """图表生成结果"""
    success: bool
    chart_id: str
    chart_type: ChartType
    file_path: Optional[str] = None
    base64_data: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ChartGenerationService:
    """
    图表生成服务
    
    负责根据数据和配置生成各种类型的图表：
    1. 分析占位符并识别图表需求
    2. 智能生成图表配置
    3. 生成图表文件
    4. 提供图表预览和导出功能
    """
    
    def __init__(self, user_id: str):
        if not user_id:
            raise ValueError("user_id is required for ChartGenerationService")
        self.user_id = user_id
        self.output_dir = f"/tmp/charts/{user_id}"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 确保导入必要的图表库
        self._ensure_chart_dependencies()
    
    def _ensure_chart_dependencies(self):
        """确保图表依赖库可用"""
        try:
            import matplotlib
            matplotlib.use('Agg')  # 使用非交互式后端
            import matplotlib.pyplot as plt
            import seaborn as sns
            self.plt = plt
            self.sns = sns
            logger.info("图表生成依赖库加载成功")
        except ImportError as e:
            logger.warning(f"图表生成依赖库加载失败: {e}")
            self.plt = None
            self.sns = None
    
    async def analyze_chart_placeholders(
        self,
        template_id: str,
        placeholder_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        分析模板中的图表占位符
        
        Args:
            template_id: 模板ID
            placeholder_data: 占位符数据
            
        Returns:
            图表占位符分析结果
        """
        try:
            from app.crud import template_placeholder as crud_placeholder
            from app.db.session import SessionLocal
            
            db = SessionLocal()
            try:
                # 获取模板所有占位符
                placeholders = crud_placeholder.get_by_template(db, template_id=template_id)
                
                chart_placeholders = []
                
                for placeholder in placeholders:
                    # 检查是否为图表类型占位符
                    if self._is_chart_placeholder(placeholder):
                        chart_info = await self._analyze_single_chart_placeholder(
                            placeholder, placeholder_data
                        )
                        if chart_info:
                            chart_placeholders.append(chart_info)
                
                logger.info(f"分析到 {len(chart_placeholders)} 个图表占位符")
                return chart_placeholders
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"分析图表占位符失败: {e}")
            return []
    
    def _is_chart_placeholder(self, placeholder) -> bool:
        """判断是否为图表占位符"""
        chart_keywords = [
            '图表', '图', 'chart', 'graph', '柱状', '折线', '饼图', 
            '散点', '趋势', '分布', '统计图', 'bar', 'line', 'pie'
        ]
        
        placeholder_text = (placeholder.placeholder_text or '').lower()
        placeholder_name = (placeholder.placeholder_name or '').lower()
        description = (placeholder.description or '').lower()
        
        return any(
            keyword in text
            for keyword in chart_keywords
            for text in [placeholder_text, placeholder_name, description]
        )
    
    async def _analyze_single_chart_placeholder(
        self,
        placeholder,
        placeholder_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """分析单个图表占位符"""
        try:
            # 使用统一AI门面进行图表类型分析
            from app.services.infrastructure.ai.service_orchestrator import get_service_orchestrator
            
            orchestrator = get_service_orchestrator()
            
            # 构建图表分析请求
            analysis_result = await orchestrator.analyze_single_placeholder_simple(
                user_id=self.user_id,
                placeholder_name=placeholder.placeholder_name,
                placeholder_text=placeholder.placeholder_text,
                template_id=placeholder.template_id,
                template_context=f"图表占位符分析 - 识别图表类型和配置要求",
                data_source_info={},
                task_params={
                    "analysis_type": "chart_analysis",
                    "focus": "chart_type_and_config"
                }
            )
            
            if analysis_result.get('status') == 'completed':
                return {
                    "placeholder_id": placeholder.id,
                    "placeholder_name": placeholder.placeholder_name,
                    "placeholder_text": placeholder.placeholder_text,
                    "suggested_chart_type": self._extract_chart_type(analysis_result),
                    "data_requirements": self._extract_data_requirements(analysis_result),
                    "display_config": self._extract_display_config(analysis_result),
                    "ai_analysis": analysis_result
                }
            
            return None
            
        except Exception as e:
            logger.error(f"分析图表占位符失败: {placeholder.placeholder_name}, 错误: {e}")
            return None
    
    def _extract_chart_type(self, analysis_result: Dict[str, Any]) -> ChartType:
        """从AI分析结果中提取图表类型"""
        # 简单的关键词匹配逻辑
        analysis_text = str(analysis_result).lower()
        
        if any(word in analysis_text for word in ['柱状', 'bar', '条形']):
            return ChartType.BAR
        elif any(word in analysis_text for word in ['折线', 'line', '趋势']):
            return ChartType.LINE
        elif any(word in analysis_text for word in ['饼图', 'pie', '占比']):
            return ChartType.PIE
        elif any(word in analysis_text for word in ['散点', 'scatter', '分布']):
            return ChartType.SCATTER
        else:
            return ChartType.BAR  # 默认使用柱状图
    
    def _extract_data_requirements(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """提取数据要求"""
        # 这里可以实现更复杂的数据要求解析逻辑
        return {
            "x_axis": "时间或分类字段",
            "y_axis": "数值字段",
            "grouping": "可选的分组字段"
        }
    
    def _extract_display_config(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """提取显示配置"""
        return {
            "title": "自动生成的图表标题",
            "width": 800,
            "height": 600,
            "color_scheme": "default"
        }
    
    async def generate_charts_for_data(
        self,
        etl_data: Dict[str, Any],
        chart_placeholders: List[Dict[str, Any]]
    ) -> List[ChartGenerationResult]:
        """
        为数据生成图表
        
        Args:
            etl_data: ETL处理后的数据
            chart_placeholders: 图表占位符列表
            
        Returns:
            图表生成结果列表
        """
        logger.info(f"开始为 {len(chart_placeholders)} 个图表占位符生成图表")
        
        generation_results = []
        
        # 并发生成所有图表
        generation_tasks = []
        for chart_placeholder in chart_placeholders:
            task = self._generate_single_chart(chart_placeholder, etl_data)
            generation_tasks.append(task)
        
        results = await asyncio.gather(*generation_tasks, return_exceptions=True)
        
        # 处理生成结果
        for chart_placeholder, result in zip(chart_placeholders, results):
            if isinstance(result, Exception):
                generation_results.append(ChartGenerationResult(
                    success=False,
                    chart_id=chart_placeholder.get('placeholder_id', 'unknown'),
                    chart_type=ChartType.BAR,
                    error=str(result)
                ))
            else:
                generation_results.append(result)
        
        successful_charts = len([r for r in generation_results if r.success])
        logger.info(f"图表生成完成: 成功={successful_charts}, 总计={len(generation_results)}")
        
        return generation_results
    
    async def _generate_single_chart(
        self,
        chart_placeholder: Dict[str, Any],
        etl_data: Dict[str, Any]
    ) -> ChartGenerationResult:
        """生成单个图表"""
        chart_id = chart_placeholder.get('placeholder_id', 'unknown')
        placeholder_name = chart_placeholder.get('placeholder_name', '未命名图表')
        
        try:
            logger.debug(f"生成图表: {placeholder_name}")
            
            # 1. 准备数据
            chart_data = self._prepare_chart_data(etl_data, chart_placeholder)
            
            if chart_data is None or chart_data.empty:
                return ChartGenerationResult(
                    success=False,
                    chart_id=chart_id,
                    chart_type=ChartType.BAR,
                    error="无可用数据生成图表"
                )
            
            # 2. 生成图表配置
            chart_config = self._create_chart_config(chart_placeholder, chart_data)
            
            # 3. 生成图表文件
            file_path = await self._create_chart_file(chart_config, chart_data, chart_id)
            
            return ChartGenerationResult(
                success=True,
                chart_id=chart_id,
                chart_type=chart_config.chart_type,
                file_path=file_path,
                metadata={
                    "title": chart_config.title,
                    "chart_type": chart_config.chart_type.value,
                    "data_rows": len(chart_data),
                    "placeholder_name": placeholder_name
                }
            )
            
        except Exception as e:
            logger.error(f"生成图表失败: {placeholder_name}, 错误: {e}")
            return ChartGenerationResult(
                success=False,
                chart_id=chart_id,
                chart_type=ChartType.BAR,
                error=str(e)
            )
    
    def _prepare_chart_data(
        self,
        etl_data: Dict[str, Any],
        chart_placeholder: Dict[str, Any]
    ) -> Optional[pd.DataFrame]:
        """准备图表数据"""
        try:
            # 从ETL数据中提取相关数据
            # 这里实现简化的数据提取逻辑
            
            # 假设ETL数据格式为 {data_source_id: {extract: {...}, transform: {...}}}
            all_data_frames = []
            
            for data_source_id, data_info in etl_data.items():
                transform_result = data_info.get('transform', {})
                if transform_result.get('success'):
                    data = transform_result.get('data', [])
                    if data:
                        df = pd.DataFrame(data)
                        all_data_frames.append(df)
            
            if all_data_frames:
                # 合并所有数据框
                combined_df = pd.concat(all_data_frames, ignore_index=True)
                
                # 数据清理和预处理
                combined_df = self._clean_chart_data(combined_df)
                
                return combined_df
            
            return None
            
        except Exception as e:
            logger.error(f"准备图表数据失败: {e}")
            return None
    
    def _clean_chart_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理图表数据"""
        try:
            # 移除空行和空列
            df = df.dropna(how='all').dropna(axis=1, how='all')
            
            # 限制数据行数（避免图表过于复杂）
            if len(df) > 1000:
                df = df.head(1000)
                logger.warning("图表数据行数过多，已限制为前1000行")
            
            return df
            
        except Exception as e:
            logger.error(f"清理图表数据失败: {e}")
            return df
    
    def _create_chart_config(
        self,
        chart_placeholder: Dict[str, Any],
        chart_data: pd.DataFrame
    ) -> ChartConfig:
        """创建图表配置"""
        suggested_type = chart_placeholder.get('suggested_chart_type', ChartType.BAR)
        placeholder_name = chart_placeholder.get('placeholder_name', '图表')
        
        # 自动选择X和Y列
        columns = list(chart_data.columns)
        
        # 选择X轴（通常是第一列或时间列）
        x_column = columns[0] if columns else 'index'
        
        # 选择Y轴（通常是数值列）
        numeric_columns = chart_data.select_dtypes(include=['number']).columns.tolist()
        y_column = numeric_columns[0] if numeric_columns else columns[1] if len(columns) > 1 else 'value'
        
        return ChartConfig(
            chart_type=suggested_type,
            title=placeholder_name,
            x_column=x_column,
            y_column=y_column,
            width=800,
            height=600,
            color_scheme="default",
            show_legend=True,
            show_grid=True,
            x_label=x_column,
            y_label=y_column
        )
    
    async def _create_chart_file(
        self,
        config: ChartConfig,
        data: pd.DataFrame,
        chart_id: str
    ) -> str:
        """创建图表文件"""
        if not self.plt:
            raise Exception("图表生成库不可用")
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chart_{chart_id}_{timestamp}.png"
        file_path = os.path.join(self.output_dir, filename)
        
        # 设置图表样式
        self.plt.style.use('default')
        self.plt.figure(figsize=(config.width/100, config.height/100), dpi=100)
        
        try:
            # 根据图表类型生成图表
            if config.chart_type == ChartType.BAR:
                self.plt.bar(data[config.x_column], data[config.y_column])
            elif config.chart_type == ChartType.LINE:
                self.plt.plot(data[config.x_column], data[config.y_column], marker='o')
            elif config.chart_type == ChartType.PIE:
                self.plt.pie(data[config.y_column], labels=data[config.x_column], autopct='%1.1f%%')
            elif config.chart_type == ChartType.SCATTER:
                self.plt.scatter(data[config.x_column], data[config.y_column])
            else:
                # 默认使用柱状图
                self.plt.bar(data[config.x_column], data[config.y_column])
            
            # 设置标题和标签
            self.plt.title(config.title, fontsize=14, pad=20)
            if config.x_label:
                self.plt.xlabel(config.x_label)
            if config.y_label:
                self.plt.ylabel(config.y_label)
            
            # 显示网格
            if config.show_grid:
                self.plt.grid(True, alpha=0.3)
            
            # 调整布局
            self.plt.tight_layout()
            
            # 保存文件
            self.plt.savefig(file_path, dpi=150, bbox_inches='tight')
            self.plt.close()
            
            logger.debug(f"图表文件已保存: {file_path}")
            return file_path
            
        except Exception as e:
            self.plt.close()  # 确保清理资源
            raise e
    
    def get_chart_preview(self, chart_id: str) -> Optional[str]:
        """获取图表预览（Base64格式）"""
        try:
            # 查找图表文件
            chart_files = [f for f in os.listdir(self.output_dir) if f.startswith(f"chart_{chart_id}")]
            
            if not chart_files:
                return None
            
            chart_file = os.path.join(self.output_dir, chart_files[0])
            
            # 转换为Base64
            import base64
            with open(chart_file, 'rb') as f:
                return base64.b64encode(f.read()).decode()
                
        except Exception as e:
            logger.error(f"获取图表预览失败: {e}")
            return None
    
    def list_generated_charts(self) -> List[Dict[str, Any]]:
        """列出已生成的图表"""
        try:
            charts = []
            for filename in os.listdir(self.output_dir):
                if filename.startswith('chart_') and filename.endswith('.png'):
                    file_path = os.path.join(self.output_dir, filename)
                    stat = os.stat(file_path)
                    
                    charts.append({
                        "filename": filename,
                        "file_path": file_path,
                        "size_bytes": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "chart_id": filename.split('_')[1] if '_' in filename else 'unknown'
                    })
            
            return sorted(charts, key=lambda x: x['created_at'], reverse=True)
            
        except Exception as e:
            logger.error(f"列出图表失败: {e}")
            return []
    
    def cleanup_old_charts(self, days_old: int = 7):
        """清理旧图表文件"""
        try:
            cutoff_time = datetime.now().timestamp() - (days_old * 24 * 3600)
            
            removed_count = 0
            for filename in os.listdir(self.output_dir):
                file_path = os.path.join(self.output_dir, filename)
                if os.path.isfile(file_path) and os.path.getctime(file_path) < cutoff_time:
                    os.remove(file_path)
                    removed_count += 1
            
            logger.info(f"清理了 {removed_count} 个旧图表文件")
            return removed_count
            
        except Exception as e:
            logger.error(f"清理图表文件失败: {e}")
            return 0


# 工厂函数
def create_chart_generation_service(user_id: str) -> ChartGenerationService:
    """创建图表生成服务实例"""
    return ChartGenerationService(user_id=user_id)