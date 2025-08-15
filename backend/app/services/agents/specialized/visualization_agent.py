"""
Visualization Agent

Creates charts and visualizations from data.
Replaces chart generation functionality from the intelligent_placeholder system.

Features:
- Multiple chart types (bar, line, pie, scatter, histogram, etc.)
- Dynamic chart configuration based on data
- Export to various formats (PNG, SVG, HTML)
- Interactive and static chart generation
- Chart customization and theming
"""

import json
import os
import tempfile
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
import asyncio

try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import seaborn as sns
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.offline import plot
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

from ..core_types import BaseAgent, AgentConfig, AgentResult, AgentType, AgentError


@dataclass
class ChartRequest:
    """Chart generation request"""
    data: Union[List[Dict[str, Any]], Dict[str, Any]] = None
    chart_type: str = "bar"  # "bar", "line", "pie", "scatter", "histogram", "box", "heatmap"
    title: str = ""
    x_field: str = ""
    y_field: str = ""
    color_field: str = ""
    size_field: str = ""
    output_format: str = "png"  # "png", "svg", "html", "json"
    output_dir: str = ""
    width: int = 800
    height: int = 600
    theme: str = "default"
    interactive: bool = False
    custom_config: Dict[str, Any] = None


@dataclass
class ChartResult:
    """Chart generation result"""
    success: bool
    chart_type: str
    file_path: Optional[str] = None
    html_content: Optional[str] = None
    chart_data: Optional[Dict[str, Any]] = None
    description: str = ""
    metadata: Dict[str, Any] = None
    error_message: Optional[str] = None


class VisualizationAgent(BaseAgent):
    """
    Agent for creating charts and visualizations
    """
    
    def __init__(self, config: AgentConfig = None):
        if config is None:
            config = AgentConfig(
                agent_id="visualization_agent",
                agent_type=AgentType.VISUALIZATION,
                name="Visualization Agent",
                description="Creates charts and visualizations from data",
                timeout_seconds=45,
                enable_caching=True,
                cache_ttl_seconds=1200  # 20-minute cache for charts
            )
        
        super().__init__(config)
        self.chart_generators = self._register_chart_generators()
        self.themes = self._load_chart_themes()
        
        # Set up default output directory
        self.default_output_dir = os.path.join(tempfile.gettempdir(), "autoreport_charts")
        os.makedirs(self.default_output_dir, exist_ok=True)
    
    def _register_chart_generators(self) -> Dict[str, callable]:
        """Register available chart generation functions"""
        return {
            "bar": self._generate_bar_chart,
            "line": self._generate_line_chart,
            "pie": self._generate_pie_chart,
            "scatter": self._generate_scatter_chart,
            "histogram": self._generate_histogram,
            "box": self._generate_box_plot,
            "heatmap": self._generate_heatmap,
            "area": self._generate_area_chart,
            "donut": self._generate_donut_chart
        }
    
    def _load_chart_themes(self) -> Dict[str, Dict[str, Any]]:
        """Load chart themes"""
        return {
            "default": {
                "colors": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", 
                          "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"],
                "background": "#ffffff",
                "text_color": "#000000",
                "grid_color": "#e0e0e0"
            },
            "professional": {
                "colors": ["#2E86AB", "#A23B72", "#F18F01", "#C73E1D", "#592941",
                          "#4A5568", "#2D3748", "#1A202C", "#718096", "#A0AEC0"],
                "background": "#ffffff",
                "text_color": "#2D3748", 
                "grid_color": "#E2E8F0"
            },
            "modern": {
                "colors": ["#667eea", "#764ba2", "#f093fb", "#f5576c", "#4facfe",
                          "#00f2fe", "#43e97b", "#38f9d7", "#ffecd2", "#fcb69f"],
                "background": "#fafafa",
                "text_color": "#424242",
                "grid_color": "#e8e8e8"
            },
            "dark": {
                "colors": ["#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4", "#feca57",
                          "#ff9ff3", "#54a0ff", "#5f27cd", "#00d2d3", "#ff9f43"],
                "background": "#2c3e50",
                "text_color": "#ecf0f1",
                "grid_color": "#34495e"
            }
        }
    
    async def execute(
        self,
        input_data: Union[ChartRequest, Dict[str, Any]],
        context: Dict[str, Any] = None
    ) -> AgentResult:
        """
        Execute chart generation
        
        Args:
            input_data: ChartRequest or dict with chart parameters
            context: Additional context information
            
        Returns:
            AgentResult with chart generation results
        """
        try:
            # Parse input data
            if isinstance(input_data, dict):
                # Filter out unsupported parameters
                supported_params = {
                    'data', 'chart_type', 'title', 'x_field', 'y_field', 'color_field',
                    'size_field', 'output_format', 'output_dir', 'width', 'height',
                    'theme', 'interactive', 'custom_config'
                }
                filtered_data = {k: v for k, v in input_data.items() if k in supported_params}
                chart_request = ChartRequest(**filtered_data)
            else:
                chart_request = input_data
            
            self.logger.info(
                "Generating chart",
                agent_id=self.agent_id,
                chart_type=chart_request.chart_type,
                output_format=chart_request.output_format,
                data_size=len(str(chart_request.data))
            )
            
            # Validate chart type
            if chart_request.chart_type not in self.chart_generators:
                raise AgentError(
                    f"Unsupported chart type: {chart_request.chart_type}",
                    self.agent_id,
                    "UNSUPPORTED_CHART_TYPE"
                )
            
            # Check if data is provided
            if chart_request.data is None or (isinstance(chart_request.data, (list, dict)) and len(chart_request.data) == 0):
                raise AgentError(
                    "未提供图表生成所需的数据",
                    self.agent_id,
                    "NO_DATA_PROVIDED"
                )
            
            # Prepare data
            prepared_data = self._prepare_chart_data(chart_request.data)
            
            # Auto-detect fields if not specified
            if not chart_request.x_field or not chart_request.y_field:
                auto_fields = self._auto_detect_fields(prepared_data, chart_request.chart_type)
                chart_request.x_field = chart_request.x_field or auto_fields.get("x_field", "")
                chart_request.y_field = chart_request.y_field or auto_fields.get("y_field", "")
            
            # Generate chart
            chart_generator = self.chart_generators[chart_request.chart_type]
            chart_result = await chart_generator(prepared_data, chart_request)
            
            return AgentResult(
                success=True,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                data=chart_result,
                metadata={
                    "chart_type": chart_request.chart_type,
                    "output_format": chart_request.output_format,
                    "data_points": len(prepared_data) if isinstance(prepared_data, list) else 1,
                    "file_path": chart_result.file_path
                }
            )
            
        except Exception as e:
            error_msg = f"Chart generation failed: {str(e)}"
            self.logger.error(error_msg, agent_id=self.agent_id, exc_info=True)
            
            return AgentResult(
                success=False,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                error_message=error_msg
            )
    
    def _prepare_chart_data(self, data: Union[List[Dict], Dict]) -> List[Dict[str, Any]]:
        """Prepare and validate data for chart generation"""
        if isinstance(data, dict):
            # Convert single dict to list of key-value pairs
            return [{"key": k, "value": v} for k, v in data.items()]
        elif isinstance(data, list):
            # Ensure all items are dictionaries
            return [item for item in data if isinstance(item, dict)]
        else:
            raise AgentError(
                f"Unsupported data type for chart generation: {type(data)}",
                self.agent_id,
                "INVALID_CHART_DATA"
            )
    
    def _auto_detect_fields(self, data: List[Dict[str, Any]], chart_type: str) -> Dict[str, str]:
        """Auto-detect appropriate fields for chart based on data and chart type"""
        if not data:
            return {"x_field": "", "y_field": ""}
        
        fields = list(data[0].keys())
        
        # Categorize fields
        numeric_fields = []
        categorical_fields = []
        datetime_fields = []
        
        for field in fields:
            sample_values = [item.get(field) for item in data[:5] if item.get(field) is not None]
            
            if self._is_numeric_field(sample_values):
                numeric_fields.append(field)
            elif self._is_datetime_field(sample_values):
                datetime_fields.append(field)
            else:
                categorical_fields.append(field)
        
        # Auto-select fields based on chart type
        if chart_type in ["bar", "column"]:
            x_field = categorical_fields[0] if categorical_fields else fields[0]
            y_field = numeric_fields[0] if numeric_fields else fields[1] if len(fields) > 1 else fields[0]
        elif chart_type == "line":
            x_field = datetime_fields[0] if datetime_fields else categorical_fields[0] if categorical_fields else fields[0]
            y_field = numeric_fields[0] if numeric_fields else fields[1] if len(fields) > 1 else fields[0]
        elif chart_type == "pie":
            x_field = categorical_fields[0] if categorical_fields else fields[0]
            y_field = numeric_fields[0] if numeric_fields else fields[1] if len(fields) > 1 else fields[0]
        elif chart_type == "scatter":
            x_field = numeric_fields[0] if len(numeric_fields) >= 2 else fields[0]
            y_field = numeric_fields[1] if len(numeric_fields) >= 2 else fields[1] if len(fields) > 1 else fields[0]
        elif chart_type == "histogram":
            x_field = numeric_fields[0] if numeric_fields else fields[0]
            y_field = ""
        else:
            x_field = fields[0]
            y_field = fields[1] if len(fields) > 1 else fields[0]
        
        return {"x_field": x_field, "y_field": y_field}
    
    def _is_numeric_field(self, sample_values: List[Any]) -> bool:
        """Check if field contains numeric values"""
        if not sample_values:
            return False
        
        numeric_count = 0
        for value in sample_values:
            try:
                float(value)
                numeric_count += 1
            except (ValueError, TypeError):
                continue
        
        return numeric_count / len(sample_values) > 0.8
    
    def _is_datetime_field(self, sample_values: List[Any]) -> bool:
        """Check if field contains datetime values"""
        if not sample_values:
            return False
        
        datetime_count = 0
        for value in sample_values:
            if self._is_datetime_like(value):
                datetime_count += 1
        
        return datetime_count / len(sample_values) > 0.8
    
    def _is_datetime_like(self, value: Any) -> bool:
        """Check if value looks like a datetime"""
        from datetime import datetime
        
        if isinstance(value, datetime):
            return True
        
        if isinstance(value, str):
            datetime_patterns = [
                r'\d{4}-\d{2}-\d{2}',
                r'\d{4}/\d{2}/\d{2}',
                r'\d{2}/\d{2}/\d{4}',
                r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
            ]
            
            import re
            for pattern in datetime_patterns:
                if re.match(pattern, value):
                    return True
        
        return False
    
    async def _generate_bar_chart(
        self, 
        data: List[Dict[str, Any]], 
        request: ChartRequest
    ) -> ChartResult:
        """Generate bar chart"""
        try:
            # Extract data for chart
            x_values = []
            y_values = []
            
            for item in data:
                if request.x_field in item and request.y_field in item:
                    x_val = str(item[request.x_field])
                    try:
                        y_val = float(item[request.y_field])
                        x_values.append(x_val)
                        y_values.append(y_val)
                    except (ValueError, TypeError):
                        continue
            
            if not x_values:
                raise AgentError("No valid data points for bar chart", self.agent_id)
            
            # Choose rendering engine
            if request.interactive and HAS_PLOTLY:
                return await self._create_plotly_bar_chart(x_values, y_values, request)
            elif HAS_MATPLOTLIB:
                return await self._create_matplotlib_bar_chart(x_values, y_values, request)
            else:
                return await self._create_text_chart(x_values, y_values, request, "bar")
                
        except Exception as e:
            return ChartResult(
                success=False,
                chart_type="bar",
                error_message=f"Bar chart generation failed: {str(e)}"
            )
    
    async def _generate_line_chart(
        self,
        data: List[Dict[str, Any]],
        request: ChartRequest
    ) -> ChartResult:
        """Generate line chart"""
        try:
            # Extract and sort data
            chart_data = []
            for item in data:
                if request.x_field in item and request.y_field in item:
                    try:
                        x_val = item[request.x_field]
                        y_val = float(item[request.y_field])
                        chart_data.append((x_val, y_val))
                    except (ValueError, TypeError):
                        continue
            
            if not chart_data:
                raise AgentError("No valid data points for line chart", self.agent_id)
            
            # Sort by x values if they are sortable
            try:
                chart_data.sort(key=lambda x: x[0])
            except TypeError:
                pass  # Keep original order if x values can't be sorted
            
            x_values, y_values = zip(*chart_data)
            
            # Choose rendering engine
            if request.interactive and HAS_PLOTLY:
                return await self._create_plotly_line_chart(x_values, y_values, request)
            elif HAS_MATPLOTLIB:
                return await self._create_matplotlib_line_chart(x_values, y_values, request)
            else:
                return await self._create_text_chart(x_values, y_values, request, "line")
                
        except Exception as e:
            return ChartResult(
                success=False,
                chart_type="line",
                error_message=f"Line chart generation failed: {str(e)}"
            )
    
    async def _generate_pie_chart(
        self,
        data: List[Dict[str, Any]],
        request: ChartRequest
    ) -> ChartResult:
        """Generate pie chart"""
        try:
            # Aggregate data for pie chart
            categories = {}
            for item in data:
                if request.x_field in item:
                    category = str(item[request.x_field])
                    
                    if request.y_field and request.y_field in item:
                        try:
                            value = float(item[request.y_field])
                            categories[category] = categories.get(category, 0) + value
                        except (ValueError, TypeError):
                            continue
                    else:
                        # Count occurrences
                        categories[category] = categories.get(category, 0) + 1
            
            if not categories:
                raise AgentError("No valid data for pie chart", self.agent_id)
            
            labels = list(categories.keys())
            values = list(categories.values())
            
            # Choose rendering engine
            if request.interactive and HAS_PLOTLY:
                return await self._create_plotly_pie_chart(labels, values, request)
            elif HAS_MATPLOTLIB:
                return await self._create_matplotlib_pie_chart(labels, values, request)
            else:
                return await self._create_text_chart(labels, values, request, "pie")
                
        except Exception as e:
            return ChartResult(
                success=False,
                chart_type="pie",
                error_message=f"Pie chart generation failed: {str(e)}"
            )
    
    async def _generate_scatter_chart(
        self,
        data: List[Dict[str, Any]],
        request: ChartRequest
    ) -> ChartResult:
        """Generate scatter plot"""
        try:
            x_values = []
            y_values = []
            colors = []
            sizes = []
            
            for item in data:
                if request.x_field in item and request.y_field in item:
                    try:
                        x_val = float(item[request.x_field])
                        y_val = float(item[request.y_field])
                        x_values.append(x_val)
                        y_values.append(y_val)
                        
                        # Optional color and size fields
                        if request.color_field and request.color_field in item:
                            colors.append(str(item[request.color_field]))
                        
                        if request.size_field and request.size_field in item:
                            try:
                                sizes.append(float(item[request.size_field]))
                            except (ValueError, TypeError):
                                sizes.append(20)  # Default size
                        
                    except (ValueError, TypeError):
                        continue
            
            if not x_values:
                raise AgentError("No valid data points for scatter plot", self.agent_id)
            
            # Choose rendering engine
            if request.interactive and HAS_PLOTLY:
                return await self._create_plotly_scatter_chart(
                    x_values, y_values, request, colors, sizes
                )
            elif HAS_MATPLOTLIB:
                return await self._create_matplotlib_scatter_chart(
                    x_values, y_values, request, colors, sizes
                )
            else:
                return await self._create_text_chart(x_values, y_values, request, "scatter")
                
        except Exception as e:
            return ChartResult(
                success=False,
                chart_type="scatter",
                error_message=f"Scatter plot generation failed: {str(e)}"
            )
    
    async def _generate_histogram(
        self,
        data: List[Dict[str, Any]],
        request: ChartRequest
    ) -> ChartResult:
        """Generate histogram"""
        try:
            values = []
            for item in data:
                if request.x_field in item:
                    try:
                        values.append(float(item[request.x_field]))
                    except (ValueError, TypeError):
                        continue
            
            if not values:
                raise AgentError("No valid numeric data for histogram", self.agent_id)
            
            # Choose rendering engine
            if request.interactive and HAS_PLOTLY:
                return await self._create_plotly_histogram(values, request)
            elif HAS_MATPLOTLIB:
                return await self._create_matplotlib_histogram(values, request)
            else:
                return await self._create_text_histogram(values, request)
                
        except Exception as e:
            return ChartResult(
                success=False,
                chart_type="histogram",
                error_message=f"Histogram generation failed: {str(e)}"
            )
    
    async def _generate_box_plot(
        self,
        data: List[Dict[str, Any]],
        request: ChartRequest
    ) -> ChartResult:
        """Generate box plot"""
        # Implementation for box plot
        return ChartResult(
            success=False,
            chart_type="box",
            error_message="Box plot generation not yet implemented"
        )
    
    async def _generate_heatmap(
        self,
        data: List[Dict[str, Any]],
        request: ChartRequest
    ) -> ChartResult:
        """Generate heatmap"""
        # Implementation for heatmap
        return ChartResult(
            success=False,
            chart_type="heatmap",
            error_message="Heatmap generation not yet implemented"
        )
    
    async def _generate_area_chart(
        self,
        data: List[Dict[str, Any]],
        request: ChartRequest
    ) -> ChartResult:
        """Generate area chart"""
        # Similar to line chart but filled
        line_result = await self._generate_line_chart(data, request)
        line_result.chart_type = "area"
        return line_result
    
    async def _generate_donut_chart(
        self,
        data: List[Dict[str, Any]],
        request: ChartRequest
    ) -> ChartResult:
        """Generate donut chart"""
        # Similar to pie chart but with hole in center
        pie_result = await self._generate_pie_chart(data, request)
        pie_result.chart_type = "donut"
        return pie_result
    
    # Matplotlib implementations
    async def _create_matplotlib_bar_chart(
        self,
        x_values: List[str],
        y_values: List[float],
        request: ChartRequest
    ) -> ChartResult:
        """Create bar chart using matplotlib"""
        if not HAS_MATPLOTLIB:
            raise AgentError("Matplotlib not available", self.agent_id)
        
        plt.figure(figsize=(request.width/100, request.height/100))
        
        # Apply theme
        theme = self.themes.get(request.theme, self.themes["default"])
        plt.style.use('default')
        
        # Create bar chart
        bars = plt.bar(x_values, y_values, color=theme["colors"][:len(x_values)])
        
        # Customize chart
        if request.title:
            plt.title(request.title, color=theme["text_color"])
        plt.xlabel(request.x_field, color=theme["text_color"])
        plt.ylabel(request.y_field, color=theme["text_color"])
        
        # Rotate x-axis labels if needed
        if len(max(x_values, key=len)) > 10:
            plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        
        # Save chart
        output_dir = request.output_dir or self.default_output_dir
        filename = f"bar_chart_{request.chart_type}_{hash(str(x_values + y_values))}.{request.output_format}"
        file_path = os.path.join(output_dir, filename)
        
        plt.savefig(file_path, format=request.output_format, 
                   facecolor=theme["background"], edgecolor='none')
        plt.close()
        
        description = f"柱状图显示了{request.x_field}和{request.y_field}之间的关系，包含{len(x_values)}个数据点。"
        
        return ChartResult(
            success=True,
            chart_type="bar",
            file_path=file_path,
            description=description,
            metadata={
                "rendering_engine": "matplotlib",
                "data_points": len(x_values),
                "theme": request.theme
            }
        )
    
    async def _create_matplotlib_line_chart(
        self,
        x_values: List[Any],
        y_values: List[float],
        request: ChartRequest
    ) -> ChartResult:
        """Create line chart using matplotlib"""
        if not HAS_MATPLOTLIB:
            raise AgentError("Matplotlib not available", self.agent_id)
        
        plt.figure(figsize=(request.width/100, request.height/100))
        
        # Apply theme
        theme = self.themes.get(request.theme, self.themes["default"])
        
        # Create line chart
        plt.plot(x_values, y_values, color=theme["colors"][0], linewidth=2, marker='o')
        
        # Customize chart
        if request.title:
            plt.title(request.title, color=theme["text_color"])
        plt.xlabel(request.x_field, color=theme["text_color"])
        plt.ylabel(request.y_field, color=theme["text_color"])
        plt.grid(True, color=theme["grid_color"], alpha=0.3)
        
        plt.tight_layout()
        
        # Save chart
        output_dir = request.output_dir or self.default_output_dir
        filename = f"line_chart_{hash(str(x_values + y_values))}.{request.output_format}"
        file_path = os.path.join(output_dir, filename)
        
        plt.savefig(file_path, format=request.output_format,
                   facecolor=theme["background"], edgecolor='none')
        plt.close()
        
        description = f"折线图展示了{request.x_field}随{request.y_field}的变化趋势，包含{len(x_values)}个数据点。"
        
        return ChartResult(
            success=True,
            chart_type="line",
            file_path=file_path,
            description=description,
            metadata={
                "rendering_engine": "matplotlib",
                "data_points": len(x_values),
                "theme": request.theme
            }
        )
    
    async def _create_matplotlib_pie_chart(
        self,
        labels: List[str],
        values: List[float],
        request: ChartRequest
    ) -> ChartResult:
        """Create pie chart using matplotlib"""
        if not HAS_MATPLOTLIB:
            raise AgentError("Matplotlib not available", self.agent_id)
        
        plt.figure(figsize=(request.width/100, request.height/100))
        
        # Apply theme
        theme = self.themes.get(request.theme, self.themes["default"])
        
        # Create pie chart
        plt.pie(values, labels=labels, colors=theme["colors"][:len(labels)], 
               autopct='%1.1f%%', startangle=90)
        
        # Customize chart
        if request.title:
            plt.title(request.title, color=theme["text_color"])
        
        plt.axis('equal')  # Equal aspect ratio ensures circular pie
        
        # Save chart
        output_dir = request.output_dir or self.default_output_dir
        filename = f"pie_chart_{hash(str(labels + values))}.{request.output_format}"
        file_path = os.path.join(output_dir, filename)
        
        plt.savefig(file_path, format=request.output_format,
                   facecolor=theme["background"], edgecolor='none')
        plt.close()
        
        description = f"饼图显示了{request.x_field}的分布情况，包含{len(labels)}个类别。"
        
        return ChartResult(
            success=True,
            chart_type="pie",
            file_path=file_path,
            description=description,
            metadata={
                "rendering_engine": "matplotlib",
                "categories": len(labels),
                "theme": request.theme
            }
        )
    
    async def _create_matplotlib_scatter_chart(
        self,
        x_values: List[float],
        y_values: List[float],
        request: ChartRequest,
        colors: List[str] = None,
        sizes: List[float] = None
    ) -> ChartResult:
        """Create scatter plot using matplotlib"""
        if not HAS_MATPLOTLIB:
            raise AgentError("Matplotlib not available", self.agent_id)
        
        plt.figure(figsize=(request.width/100, request.height/100))
        
        # Apply theme
        theme = self.themes.get(request.theme, self.themes["default"])
        
        # Create scatter plot
        scatter = plt.scatter(
            x_values, y_values,
            c=colors if colors else theme["colors"][0],
            s=sizes if sizes else [50] * len(x_values),
            alpha=0.7
        )
        
        # Customize chart
        if request.title:
            plt.title(request.title, color=theme["text_color"])
        plt.xlabel(request.x_field, color=theme["text_color"])
        plt.ylabel(request.y_field, color=theme["text_color"])
        plt.grid(True, color=theme["grid_color"], alpha=0.3)
        
        plt.tight_layout()
        
        # Save chart
        output_dir = request.output_dir or self.default_output_dir
        filename = f"scatter_chart_{hash(str(x_values + y_values))}.{request.output_format}"
        file_path = os.path.join(output_dir, filename)
        
        plt.savefig(file_path, format=request.output_format,
                   facecolor=theme["background"], edgecolor='none')
        plt.close()
        
        description = f"散点图显示了{request.x_field}和{request.y_field}之间的关系，包含{len(x_values)}个数据点。"
        
        return ChartResult(
            success=True,
            chart_type="scatter",
            file_path=file_path,
            description=description,
            metadata={
                "rendering_engine": "matplotlib",
                "data_points": len(x_values),
                "theme": request.theme
            }
        )
    
    async def _create_matplotlib_histogram(
        self,
        values: List[float],
        request: ChartRequest
    ) -> ChartResult:
        """Create histogram using matplotlib"""
        if not HAS_MATPLOTLIB:
            raise AgentError("Matplotlib not available", self.agent_id)
        
        plt.figure(figsize=(request.width/100, request.height/100))
        
        # Apply theme
        theme = self.themes.get(request.theme, self.themes["default"])
        
        # Create histogram
        plt.hist(values, bins=20, color=theme["colors"][0], alpha=0.7, edgecolor='black')
        
        # Customize chart
        if request.title:
            plt.title(request.title, color=theme["text_color"])
        plt.xlabel(request.x_field, color=theme["text_color"])
        plt.ylabel("频次", color=theme["text_color"])
        plt.grid(True, color=theme["grid_color"], alpha=0.3)
        
        plt.tight_layout()
        
        # Save chart
        output_dir = request.output_dir or self.default_output_dir
        filename = f"histogram_{hash(str(values))}.{request.output_format}"
        file_path = os.path.join(output_dir, filename)
        
        plt.savefig(file_path, format=request.output_format,
                   facecolor=theme["background"], edgecolor='none')
        plt.close()
        
        description = f"直方图显示了{request.x_field}的分布情况，包含{len(values)}个数据点。"
        
        return ChartResult(
            success=True,
            chart_type="histogram",
            file_path=file_path,
            description=description,
            metadata={
                "rendering_engine": "matplotlib",
                "data_points": len(values),
                "theme": request.theme
            }
        )
    
    # Plotly implementations (for interactive charts)
    async def _create_plotly_bar_chart(
        self,
        x_values: List[str],
        y_values: List[float],
        request: ChartRequest
    ) -> ChartResult:
        """Create interactive bar chart using plotly"""
        if not HAS_PLOTLY:
            raise AgentError("Plotly not available", self.agent_id)
        
        theme = self.themes.get(request.theme, self.themes["default"])
        
        fig = go.Figure(data=[
            go.Bar(
                x=x_values,
                y=y_values,
                marker_color=theme["colors"][:len(x_values)]
            )
        ])
        
        fig.update_layout(
            title=request.title,
            xaxis_title=request.x_field,
            yaxis_title=request.y_field,
            plot_bgcolor=theme["background"],
            paper_bgcolor=theme["background"],
            font=dict(color=theme["text_color"])
        )
        
        # Save chart
        output_dir = request.output_dir or self.default_output_dir
        
        if request.output_format == "html":
            filename = f"bar_chart_{hash(str(x_values + y_values))}.html"
            file_path = os.path.join(output_dir, filename)
            fig.write_html(file_path)
        else:
            filename = f"bar_chart_{hash(str(x_values + y_values))}.{request.output_format}"
            file_path = os.path.join(output_dir, filename)
            fig.write_image(file_path)
        
        description = f"交互式柱状图显示了{request.x_field}和{request.y_field}之间的关系。"
        
        return ChartResult(
            success=True,
            chart_type="bar",
            file_path=file_path,
            description=description,
            metadata={
                "rendering_engine": "plotly",
                "interactive": True,
                "data_points": len(x_values)
            }
        )
    
    # Fallback text-based chart implementations
    async def _create_text_chart(
        self,
        x_values: List[Any],
        y_values: List[float],
        request: ChartRequest,
        chart_type: str
    ) -> ChartResult:
        """Create simple text-based chart representation"""
        
        if chart_type == "bar":
            chart_text = self._create_text_bar_chart(x_values, y_values)
        elif chart_type == "line":
            chart_text = self._create_text_line_chart(x_values, y_values)
        elif chart_type == "pie":
            chart_text = self._create_text_pie_chart(x_values, y_values)
        else:
            chart_text = f"简单{chart_type}图表：\n" + "\n".join([
                f"{x}: {y}" for x, y in zip(x_values[:10], y_values[:10])
            ])
        
        # Save as text file
        output_dir = request.output_dir or self.default_output_dir
        filename = f"text_chart_{chart_type}_{hash(str(x_values + y_values))}.txt"
        file_path = os.path.join(output_dir, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(chart_text)
        
        description = f"文本格式的{chart_type}图表，显示了数据的基本分布。"
        
        return ChartResult(
            success=True,
            chart_type=chart_type,
            file_path=file_path,
            description=description,
            metadata={
                "rendering_engine": "text",
                "data_points": len(x_values)
            }
        )
    
    def _create_text_bar_chart(self, labels: List[str], values: List[float]) -> str:
        """Create simple ASCII bar chart"""
        if not values:
            return "无数据可显示"
        
        max_val = max(values)
        max_width = 50
        
        chart_lines = ["文本柱状图", "=" * 60]
        
        for label, value in zip(labels, values):
            bar_length = int((value / max_val) * max_width) if max_val > 0 else 0
            bar = "█" * bar_length
            chart_lines.append(f"{label[:15]:15} |{bar} {value}")
        
        return "\n".join(chart_lines)
    
    def _create_text_line_chart(self, x_values: List[Any], y_values: List[float]) -> str:
        """Create simple ASCII line representation"""
        chart_lines = ["文本折线图", "=" * 60]
        
        for x, y in zip(x_values, y_values):
            chart_lines.append(f"{str(x)[:20]:20} : {y}")
        
        return "\n".join(chart_lines)
    
    def _create_text_pie_chart(self, labels: List[str], values: List[float]) -> str:
        """Create simple text pie chart representation"""
        total = sum(values)
        chart_lines = ["文本饼图", "=" * 60]
        
        for label, value in zip(labels, values):
            percentage = (value / total * 100) if total > 0 else 0
            chart_lines.append(f"{label[:20]:20} : {value:8.1f} ({percentage:5.1f}%)")
        
        return "\n".join(chart_lines)
    
    async def _create_text_histogram(self, values: List[float], request: ChartRequest) -> ChartResult:
        """Create text histogram"""
        if not values:
            chart_text = "无数据可显示"
        else:
            # Create bins
            min_val = min(values)
            max_val = max(values)
            bin_count = 10
            bin_width = (max_val - min_val) / bin_count if max_val > min_val else 1
            
            bins = {}
            for value in values:
                bin_idx = int((value - min_val) / bin_width)
                bin_idx = min(bin_idx, bin_count - 1)  # Ensure within bounds
                bins[bin_idx] = bins.get(bin_idx, 0) + 1
            
            chart_lines = ["文本直方图", "=" * 60]
            max_count = max(bins.values()) if bins else 1
            
            for i in range(bin_count):
                bin_start = min_val + i * bin_width
                bin_end = bin_start + bin_width
                count = bins.get(i, 0)
                bar_length = int((count / max_count) * 30) if max_count > 0 else 0
                bar = "█" * bar_length
                chart_lines.append(f"{bin_start:6.1f}-{bin_end:6.1f} |{bar} {count}")
            
            chart_text = "\n".join(chart_lines)
        
        # Save as text file
        output_dir = request.output_dir or self.default_output_dir
        filename = f"histogram_{hash(str(values))}.txt"
        file_path = os.path.join(output_dir, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(chart_text)
        
        description = f"文本格式的直方图，显示了{request.x_field}的分布情况。"
        
        return ChartResult(
            success=True,
            chart_type="histogram",
            file_path=file_path,
            description=description,
            metadata={
                "rendering_engine": "text",
                "data_points": len(values)
            }
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check for visualization agent"""
        health = await super().health_check()
        
        # Check available rendering engines
        health["matplotlib_available"] = HAS_MATPLOTLIB
        health["plotly_available"] = HAS_PLOTLY
        health["supported_chart_types"] = list(self.chart_generators.keys())
        health["available_themes"] = list(self.themes.keys())
        health["default_output_dir"] = self.default_output_dir
        
        # Test basic chart generation
        try:
            test_data = [{"x": "A", "y": 1}, {"x": "B", "y": 2}]
            test_request = ChartRequest(
                data=test_data,
                chart_type="bar",
                x_field="x",
                y_field="y"
            )
            test_result = await self._create_text_chart(["A", "B"], [1, 2], test_request, "bar")
            health["chart_generation"] = "healthy"
        except Exception as e:
            health["chart_generation"] = f"error: {str(e)}"
            health["healthy"] = False
        
        return health
    
