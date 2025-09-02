"""
图表生成工具 - 供React Agent调用
使用专业图表库生成真实图片
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from matplotlib import rcParams
import matplotlib.patches as patches

# 设置中文字体支持
import matplotlib.font_manager as fm
import platform

def setup_chinese_fonts():
    """设置中文字体支持 - Docker环境优化"""
    system = platform.system()
    
    # 检测是否在Docker环境中
    is_docker = os.path.exists('/.dockerenv') or os.path.exists('/proc/1/cgroup')
    
    if system == "Darwin":  # macOS
        fonts = [
            'PingFang SC',           # 苹果默认中文字体
            'PingFang TC', 
            'Hiragino Sans GB',      # 日文汉字字体，支持中文
            'STHeiti',               # 华文黑体
            'Songti SC',             # 宋体
            'Arial Unicode MS',      # 通用Unicode字体
        ]
    elif system == "Windows":
        fonts = [
            'Microsoft YaHei',       # 微软雅黑
            'SimHei',               # 黑体
            'SimSun',               # 宋体
            'KaiTi',                # 楷体
            'Arial Unicode MS',
        ]
    elif system == "Linux" or is_docker:
        # Docker环境优先使用已安装的中文字体
        fonts = [
            'Noto Sans CJK SC',      # Google Noto CJK 简体中文 (推荐)
            'Noto Sans CJK TC',      # Google Noto CJK 繁体中文
            'WenQuanYi Micro Hei',   # 文泉驿微米黑 (Docker常用)
            'WenQuanYi Zen Hei',     # 文泉驿正黑
            'Source Han Sans CN',    # 思源黑体简体
            'Source Han Sans SC',    # 思源黑体简体
            'Droid Sans Fallback',   # Android字体备选
            'Liberation Sans',       # 开源Liberation字体
            'DejaVu Sans',          # DejaVu字体
            'Arial Unicode MS',      # 通用Unicode字体 
            'sans-serif'            # 系统默认无衬线字体
        ]
    else:
        fonts = ['Arial Unicode MS', 'DejaVu Sans', 'sans-serif']
    
    # 设置matplotlib字体
    plt.rcParams['font.sans-serif'] = fonts
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
    plt.rcParams['font.size'] = 12              # 设置默认字体大小
    
    # 禁用字体警告（对于正常显示的中文字符，警告不影响功能）
    import warnings
    warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
    
    # 验证字体是否可用
    available_fonts = []
    font_names = [f.name for f in fm.fontManager.ttflist]
    
    # 额外检查字体文件路径（Docker环境）
    font_files = [f.fname for f in fm.fontManager.ttflist if f.fname]
    
    for font in fonts:
        if font in font_names:
            available_fonts.append(font)
            continue
            
        # 检查是否有对应的字体文件
        for font_file in font_files:
            if any(keyword in font_file.lower() for keyword in [
                'noto', 'wenquanyi', 'source', 'han', 'cjk', 'liberation', 'dejavu'
            ]):
                available_fonts.append(font)
                break
    
    # Docker环境特殊处理
    if is_docker and not available_fonts:
        # 强制刷新字体缓存
        try:
            import subprocess
            subprocess.run(['fc-cache', '-fv'], check=True, capture_output=True)
            fm._rebuild()  # 重建matplotlib字体缓存
        except Exception:
            pass
        
        # 再次检查
        font_names = [f.name for f in fm.fontManager.ttflist]
        for font in fonts:
            if font in font_names:
                available_fonts.append(font)
                break
    
    if available_fonts:
        print(f"✅ 中文字体配置成功: {available_fonts[0]}")
        if is_docker:
            print(f"   🐳 Docker环境检测: 使用容器字体")
        return available_fonts[0]
    else:
        font_info = f"系统: {system}"
        if is_docker:
            font_info += " (Docker)"
        print(f"⚠️  警告: 未找到理想的中文字体 ({font_info})")
        print(f"   可用字体数量: {len(font_names)}")
        
        # 显示一些可能有用的字体
        chinese_related = [name for name in font_names if any(
            keyword in name.lower() for keyword in ['cjk', 'han', 'noto', 'wenquanyi', 'source']
        )]
        if chinese_related:
            print(f"   检测到相关字体: {chinese_related[:3]}")
        
        return fonts[0]

# 初始化中文字体
setup_chinese_fonts()

# 全局禁用matplotlib字体警告
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib.font_manager')
warnings.filterwarnings('ignore', message='.*Glyph.*missing from font.*')

class ChartGeneratorTool:
    """专业图表生成工具 - 支持中文显示"""
    
    def __init__(self, output_dir: str = "/Users/shan/work/me/AutoReportAI/storage/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 确保中文字体配置
        self.chinese_font = setup_chinese_fonts()
        
        # 设置专业样式
        sns.set_style("whitegrid")
        sns.set_palette("husl")
        
        # 中文显示配置
        self.font_config = {
            'title': {'fontsize': 16, 'fontweight': 'bold', 'pad': 20},
            'label': {'fontsize': 12, 'fontweight': 'bold'},
            'tick': {'fontsize': 10},
            'annotation': {'fontsize': 10, 'fontweight': 'bold'}
        }
    
    def set_chinese_font_for_axes(self, ax):
        """为matplotlib轴对象设置中文字体支持"""
        # 确保所有文本元素使用中文字体
        for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] +
                    ax.get_xticklabels() + ax.get_yticklabels()):
            item.set_fontfamily('sans-serif')
        
        # 设置图例字体
        legend = ax.get_legend()
        if legend:
            for text in legend.get_texts():
                text.set_fontfamily('sans-serif')
        
    def generate_bar_chart(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """生成柱状图 - 支持中文显示
        
        Args:
            data: {
                "title": "销售业绩分析图表",
                "x_data": ["产品A", "产品B", "产品C"],
                "y_data": [100000, 200000, 150000],
                "x_label": "产品类型",
                "y_label": "销售额（元）",
                "colors": ["#1f77b4", "#ff7f0e", "#2ca02c"] # 可选
            }
        """
        try:
            # 创建图表，设置中文友好的尺寸
            fig, ax = plt.subplots(figsize=(12, 7))
            
            x_data = data.get("x_data", [])
            y_data = data.get("y_data", [])
            colors = data.get("colors", sns.color_palette("husl", len(x_data)))
            
            # 绘制柱状图
            bars = ax.bar(x_data, y_data, color=colors, alpha=0.85, 
                         edgecolor='black', linewidth=0.8)
            
            # 添加数值标签（支持中文数字格式）
            for bar, value in zip(bars, y_data):
                height = bar.get_height()
                # 格式化大数字显示
                if value >= 10000:
                    label = f'{value/10000:.1f}万' if value < 100000000 else f'{value/100000000:.1f}亿'
                else:
                    label = f'{value:,.0f}'
                
                ax.text(bar.get_x() + bar.get_width()/2., height + max(y_data)*0.01,
                       label, ha='center', va='bottom', 
                       **self.font_config['annotation'])
            
            # 设置标题和标签（确保中文显示正常）
            title = data.get("title", "柱状图")
            ax.set_title(title, **self.font_config['title'])
            ax.set_xlabel(data.get("x_label", "类别"), **self.font_config['label'])
            ax.set_ylabel(data.get("y_label", "数值"), **self.font_config['label'])
            
            # 优化X轴标签显示（中文长标签处理）
            max_label_length = max([len(str(label)) for label in x_data]) if x_data else 0
            rotation_angle = 45 if max_label_length > 4 else 0
            
            plt.xticks(rotation=rotation_angle, ha='right' if rotation_angle > 0 else 'center',
                      fontsize=self.font_config['tick']['fontsize'])
            plt.yticks(fontsize=self.font_config['tick']['fontsize'])
            
            # 美化图表
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            # Y轴数值格式化（大数字显示）
            if max(y_data) >= 10000:
                ax.yaxis.set_major_formatter(plt.FuncFormatter(
                    lambda x, p: f'{x/10000:.0f}万' if x >= 10000 else f'{x:.0f}'
                ))
            
            # 确保中文字体显示正常
            self.set_chinese_font_for_axes(ax)
            
            plt.tight_layout()
            
            # 保存图片
            filename = f"bar_chart_{uuid.uuid4().hex[:8]}.png"
            filepath = self.output_dir / filename
            plt.savefig(filepath, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close()
            
            return {
                "success": True,
                "chart_type": "bar_chart",
                "filepath": str(filepath),
                "filename": filename,
                "title": title,
                "data_points": len(x_data),
                "chinese_support": True,
                "font_used": self.chinese_font
            }
            
        except Exception as e:
            plt.close('all')  # 确保清理
            return {
                "success": False,
                "error": str(e),
                "chart_type": "bar_chart"
            }
    
    def generate_line_chart(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """生成折线图 - 支持中文显示
        
        Args:
            data: {
                "title": "销售趋势分析",
                "x_data": ["1月", "2月", "3月", "4月", "5月"],
                "series": [
                    {"name": "收入", "data": [120, 135, 145, 160, 180]},
                    {"name": "支出", "data": [80, 85, 90, 95, 100]}
                ],
                "x_label": "月份",
                "y_label": "金额（万元）"
            }
        """
        try:
            fig, ax = plt.subplots(figsize=(12, 7))
            
            x_data = data.get("x_data", [])
            series_data = data.get("series", [])
            
            # 设置颜色调色板
            colors = sns.color_palette("husl", len(series_data))
            
            for i, series in enumerate(series_data):
                ax.plot(x_data, series["data"], 
                       marker='o', linewidth=3, markersize=7,
                       label=series["name"], alpha=0.9,
                       color=colors[i], markerfacecolor='white',
                       markeredgecolor=colors[i], markeredgewidth=2)
                
                # 添加数值标签
                for j, (x, y) in enumerate(zip(x_data, series["data"])):
                    # 格式化数值显示
                    if y >= 10000:
                        label = f'{y/10000:.1f}万'
                    else:
                        label = f'{y:.1f}'
                    
                    ax.annotate(label, (j, y), 
                              textcoords="offset points", 
                              xytext=(0, 8), ha='center',
                              **self.font_config['annotation'],
                              alpha=0.8)
            
            # 设置标题和标签
            title = data.get("title", "折线图")
            ax.set_title(title, **self.font_config['title'])
            ax.set_xlabel(data.get("x_label", "时间"), **self.font_config['label'])
            ax.set_ylabel(data.get("y_label", "数值"), **self.font_config['label'])
            
            # 优化X轴标签显示
            max_label_length = max([len(str(label)) for label in x_data]) if x_data else 0
            rotation_angle = 30 if max_label_length > 3 else 0
            
            plt.xticks(rotation=rotation_angle, ha='right' if rotation_angle > 0 else 'center',
                      fontsize=self.font_config['tick']['fontsize'])
            plt.yticks(fontsize=self.font_config['tick']['fontsize'])
            
            # 美化图表
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            # 图例设置（支持中文）
            if len(series_data) > 1:
                legend = ax.legend(frameon=True, shadow=True, 
                                 loc='best', fontsize=self.font_config['tick']['fontsize'])
                legend.get_frame().set_facecolor('white')
                legend.get_frame().set_alpha(0.9)
            
            # Y轴数值格式化
            all_values = [val for series in series_data for val in series["data"]]
            if max(all_values) >= 10000:
                ax.yaxis.set_major_formatter(plt.FuncFormatter(
                    lambda x, p: f'{x/10000:.0f}万' if x >= 10000 else f'{x:.0f}'
                ))
            
            # 确保中文字体显示正常
            self.set_chinese_font_for_axes(ax)
            
            plt.tight_layout()
            
            # 保存图片
            filename = f"line_chart_{uuid.uuid4().hex[:8]}.png"
            filepath = self.output_dir / filename
            plt.savefig(filepath, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close()
            
            return {
                "success": True,
                "chart_type": "line_chart",
                "filepath": str(filepath),
                "filename": filename,
                "title": title,
                "series_count": len(series_data),
                "chinese_support": True,
                "font_used": self.chinese_font
            }
            
        except Exception as e:
            plt.close('all')
            return {
                "success": False,
                "error": str(e),
                "chart_type": "line_chart"
            }
    
    def generate_pie_chart(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """生成饼图 - 支持中文显示
        
        Args:
            data: {
                "title": "市场份额分布",
                "labels": ["华北区", "华东区", "华南区", "西部区", "其他"],
                "sizes": [30, 25, 20, 15, 10]
            }
        """
        try:
            fig, ax = plt.subplots(figsize=(11, 9))
            
            labels = data.get("labels", [])
            sizes = data.get("sizes", [])
            colors = data.get("colors", sns.color_palette("Set3", len(labels)))
            
            # 计算百分比
            total = sum(sizes)
            percentages = [s/total*100 for s in sizes]
            
            # 突出显示最大的扇形
            max_index = sizes.index(max(sizes)) if sizes else 0
            explode = [0.1 if i == max_index else 0 for i in range(len(sizes))]
            
            # 绘制饼图
            wedges, texts, autotexts = ax.pie(
                sizes, labels=labels, colors=colors, 
                autopct=lambda pct: f'{pct:.1f}%' if pct > 3 else '',  # 小于3%不显示百分比
                startangle=90, explode=explode, shadow=True,
                textprops={'fontsize': self.font_config['tick']['fontsize'], 
                          'fontweight': 'normal'},
                pctdistance=0.85
            )
            
            # 美化标签文本（支持中文）
            for text in texts:
                text.set_fontsize(self.font_config['label']['fontsize'])
                text.set_fontweight('bold')
            
            # 美化百分比文本
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
                autotext.set_fontsize(self.font_config['annotation']['fontsize'])
            
            # 设置标题
            title = data.get("title", "饼图")
            ax.set_title(title, **self.font_config['title'])
            
            # 添加图例（对于标签过长的情况）
            max_label_length = max([len(str(label)) for label in labels]) if labels else 0
            if max_label_length > 6:  # 标签较长时使用图例
                ax.legend(wedges, [f'{label} ({size})' for label, size in zip(labels, sizes)],
                         title="详细信息", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1),
                         fontsize=self.font_config['tick']['fontsize'])
            
            # 确保饼图是圆形
            ax.axis('equal')
            
            # 确保中文字体显示正常
            self.set_chinese_font_for_axes(ax)
            
            plt.tight_layout()
            
            # 保存图片
            filename = f"pie_chart_{uuid.uuid4().hex[:8]}.png"
            filepath = self.output_dir / filename
            plt.savefig(filepath, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close()
            
            return {
                "success": True,
                "chart_type": "pie_chart",
                "filepath": str(filepath),
                "filename": filename,
                "title": title,
                "categories": len(labels),
                "chinese_support": True,
                "font_used": self.chinese_font
            }
            
        except Exception as e:
            plt.close('all')
            return {
                "success": False,
                "error": str(e),
                "chart_type": "pie_chart"
            }
    
    def generate_area_chart(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """生成面积图"""
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            x_data = data.get("x_data", [])
            series_data = data.get("series", [])
            
            # 创建堆叠面积图
            bottom = np.zeros(len(x_data))
            colors = sns.color_palette("husl", len(series_data))
            
            for i, series in enumerate(series_data):
                ax.fill_between(x_data, bottom, bottom + series["data"],
                               label=series["name"], alpha=0.7, color=colors[i])
                bottom += series["data"]
            
            # 设置标题和标签
            ax.set_title(data.get("title", "面积图"), fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel(data.get("x_label", "时间"), fontsize=12, fontweight='bold')
            ax.set_ylabel(data.get("y_label", "数值"), fontsize=12, fontweight='bold')
            
            # 美化
            ax.grid(True, alpha=0.3)
            ax.legend(frameon=True, shadow=True)
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            # 保存图片
            filename = f"area_chart_{uuid.uuid4().hex[:8]}.png"
            filepath = self.output_dir / filename
            plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
            plt.close()
            
            return {
                "success": True,
                "chart_type": "area_chart",
                "filepath": str(filepath),
                "filename": filename,
                "title": data.get("title", "面积图"),
                "series_count": len(series_data)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "chart_type": "area_chart"
            }
    
    def generate_mixed_dashboard(self, charts_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成混合仪表板（多个图表组合）"""
        try:
            num_charts = len(charts_data)
            if num_charts <= 2:
                fig, axes = plt.subplots(1, num_charts, figsize=(15, 6))
            else:
                rows = (num_charts + 1) // 2
                fig, axes = plt.subplots(rows, 2, figsize=(15, rows * 6))
                axes = axes.flatten() if rows > 1 else [axes] if num_charts == 1 else axes
            
            if num_charts == 1:
                axes = [axes]
            
            chart_results = []
            
            for i, chart_data in enumerate(charts_data):
                ax = axes[i]
                chart_type = chart_data.get("type", "bar")
                
                if chart_type == "bar":
                    self._draw_bar_on_axis(ax, chart_data)
                elif chart_type == "line":
                    self._draw_line_on_axis(ax, chart_data)
                elif chart_type == "pie":
                    self._draw_pie_on_axis(ax, chart_data)
                
                chart_results.append({
                    "type": chart_type,
                    "title": chart_data.get("title", f"图表{i+1}")
                })
            
            # 隐藏多余的子图
            for j in range(num_charts, len(axes)):
                axes[j].set_visible(False)
            
            plt.suptitle("业务分析仪表板", fontsize=18, fontweight='bold', y=0.95)
            plt.tight_layout()
            
            # 保存图片
            filename = f"dashboard_{uuid.uuid4().hex[:8]}.png"
            filepath = self.output_dir / filename
            plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
            plt.close()
            
            return {
                "success": True,
                "chart_type": "dashboard",
                "filepath": str(filepath),
                "filename": filename,
                "charts": chart_results,
                "chart_count": num_charts
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "chart_type": "dashboard"
            }
    
    def _draw_bar_on_axis(self, ax, data):
        """在指定轴上绘制柱状图"""
        x_data = data.get("x_data", [])
        y_data = data.get("y_data", [])
        colors = data.get("colors", sns.color_palette("husl", len(x_data)))
        
        bars = ax.bar(x_data, y_data, color=colors, alpha=0.8)
        ax.set_title(data.get("title", "柱状图"), fontweight='bold')
        ax.set_xlabel(data.get("x_label", "类别"))
        ax.set_ylabel(data.get("y_label", "数值"))
        ax.grid(True, alpha=0.3)
        
        # 添加数值标签
        for bar, value in zip(bars, y_data):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{value}', ha='center', va='bottom', fontsize=8)
    
    def _draw_line_on_axis(self, ax, data):
        """在指定轴上绘制折线图"""
        x_data = data.get("x_data", [])
        series_data = data.get("series", [])
        
        for series in series_data:
            ax.plot(x_data, series["data"], marker='o', label=series["name"])
        
        ax.set_title(data.get("title", "折线图"), fontweight='bold')
        ax.set_xlabel(data.get("x_label", "时间"))
        ax.set_ylabel(data.get("y_label", "数值"))
        ax.grid(True, alpha=0.3)
        if len(series_data) > 1:
            ax.legend()
    
    def _draw_pie_on_axis(self, ax, data):
        """在指定轴上绘制饼图"""
        labels = data.get("labels", [])
        sizes = data.get("sizes", [])
        
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        ax.set_title(data.get("title", "饼图"), fontweight='bold')


# 工具函数 - 供Agent调用
def generate_chart(chart_config: str) -> str:
    """
    生成图表的工具函数
    
    Args:
        chart_config: JSON格式的图表配置
        
    Returns:
        JSON格式的生成结果
    """
    try:
        config = json.loads(chart_config)
        generator = ChartGeneratorTool()
        
        chart_type = config.get("type", "bar")
        
        if chart_type == "bar":
            result = generator.generate_bar_chart(config)
        elif chart_type == "line":
            result = generator.generate_line_chart(config)
        elif chart_type == "pie":
            result = generator.generate_pie_chart(config)
        elif chart_type == "area":
            result = generator.generate_area_chart(config)
        elif chart_type == "dashboard":
            result = generator.generate_mixed_dashboard(config.get("charts", []))
        else:
            result = {
                "success": False,
                "error": f"不支持的图表类型: {chart_type}"
            }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"图表生成失败: {str(e)}"
        }, ensure_ascii=False, indent=2)

# 示例数据生成函数
def generate_sample_data() -> Dict[str, Any]:
    """生成示例数据供测试"""
    return {
        "bar_chart_sample": {
            "type": "bar",
            "title": "月度销售额对比",
            "x_data": ["1月", "2月", "3月", "4月", "5月"],
            "y_data": [120000, 150000, 180000, 160000, 200000],
            "x_label": "月份",
            "y_label": "销售额 (元)",
            "colors": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
        },
        "line_chart_sample": {
            "type": "line",
            "title": "用户增长趋势",
            "x_data": ["1月", "2月", "3月", "4月", "5月"],
            "series": [
                {"name": "新用户", "data": [1000, 1200, 1500, 1800, 2000]},
                {"name": "活跃用户", "data": [8000, 8500, 9200, 9800, 10500]}
            ],
            "x_label": "月份",
            "y_label": "用户数"
        },
        "pie_chart_sample": {
            "type": "pie",
            "title": "产品销售占比",
            "labels": ["产品A", "产品B", "产品C", "产品D", "其他"],
            "sizes": [30, 25, 20, 15, 10]
        }
    }