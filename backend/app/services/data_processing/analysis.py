import pandas as pd
from sqlalchemy.orm import Session

from app import models
from .retrieval import DataRetrievalService
from ..statistics_service import StatisticsService
from ..visualization_service import VisualizationService


class DataAnalysisService:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.retrieval_service = DataRetrievalService()
        self.statistics_service = StatisticsService()
        self.visualization_service = VisualizationService()

    def analyze(self, data_source_id: int):
        """执行数据源的基础分析"""
        try:
            # 获取数据源配置
            data_source = (
                self.db_session.query(models.DataSource)
                .filter(models.DataSource.id == data_source_id)
                .first()
            )

            if not data_source:
                raise ValueError(f"Data source with id {data_source_id} not found")

            # 获取数据
            df = self.retrieval_service.get_data(data_source)

            if df.empty:
                return {"error": "No data available for analysis"}

            # 执行基础分析
            analysis_result = {
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": df.columns.tolist(),
                "data_types": df.dtypes.to_dict(),
                "summary_stats": self.statistics_service.get_basic_stats(df),
                "missing_values": df.isnull().sum().to_dict(),
                "data_source_id": data_source_id,
                "analysis_timestamp": pd.Timestamp.now().isoformat(),
            }

            return analysis_result

        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}"}

    def get_summary_statistics(self, data_source_id: int):
        """获取数据源的汇总统计信息"""
        try:
            # 获取数据源配置
            data_source = (
                self.db_session.query(models.DataSource)
                .filter(models.DataSource.id == data_source_id)
                .first()
            )

            if not data_source:
                raise ValueError(f"Data source with id {data_source_id} not found")

            # 获取数据
            df = self.retrieval_service.get_data(data_source)

            if df.empty:
                return {"error": "No data available for statistics"}

            # 生成汇总统计
            numeric_columns = df.select_dtypes(include=[pd.np.number]).columns.tolist()
            categorical_columns = df.select_dtypes(include=["object"]).columns.tolist()

            summary = {
                "basic_info": {
                    "total_rows": len(df),
                    "total_columns": len(df.columns),
                    "numeric_columns": len(numeric_columns),
                    "categorical_columns": len(categorical_columns),
                },
                "numeric_summary": {},
                "categorical_summary": {},
                "data_quality": {
                    "missing_values_total": df.isnull().sum().sum(),
                    "duplicate_rows": df.duplicated().sum(),
                    "completeness_rate": (
                        1 - df.isnull().sum().sum() / (len(df) * len(df.columns))
                    )
                    * 100,
                },
            }

            # 数值列统计
            if numeric_columns:
                for col in numeric_columns:
                    summary["numeric_summary"][col] = {
                        "mean": (
                            float(df[col].mean())
                            if not df[col].isnull().all()
                            else None
                        ),
                        "median": (
                            float(df[col].median())
                            if not df[col].isnull().all()
                            else None
                        ),
                        "std": (
                            float(df[col].std()) if not df[col].isnull().all() else None
                        ),
                        "min": (
                            float(df[col].min()) if not df[col].isnull().all() else None
                        ),
                        "max": (
                            float(df[col].max()) if not df[col].isnull().all() else None
                        ),
                        "missing_count": int(df[col].isnull().sum()),
                    }

            # 分类列统计
            if categorical_columns:
                for col in categorical_columns:
                    value_counts = df[col].value_counts().head(10)
                    summary["categorical_summary"][col] = {
                        "unique_values": int(df[col].nunique()),
                        "most_frequent": value_counts.to_dict(),
                        "missing_count": int(df[col].isnull().sum()),
                    }

            return summary

        except Exception as e:
            return {"error": f"Statistics calculation failed: {str(e)}"}

    def create_visualization(self, data_source_id: int, chart_type: str):
        """创建数据可视化"""
        try:
            # 获取数据源配置
            data_source = (
                self.db_session.query(models.DataSource)
                .filter(models.DataSource.id == data_source_id)
                .first()
            )

            if not data_source:
                raise ValueError(f"Data source with id {data_source_id} not found")

            # 获取数据
            df = self.retrieval_service.get_data(data_source)

            if df.empty:
                return {"error": "No data available for visualization"}

            # 根据图表类型生成可视化
            if chart_type == "bar":
                # 对于条形图，尝试找到合适的分类列和数值列
                categorical_cols = df.select_dtypes(include=["object"]).columns.tolist()
                numeric_cols = df.select_dtypes(include=[pd.np.number]).columns.tolist()

                if not categorical_cols or not numeric_cols:
                    return {
                        "error": "Insufficient data for bar chart (need categorical and numeric columns)"
                    }

                x_col = categorical_cols[0]
                y_col = numeric_cols[0]

                return self.visualization_service.generate_bar_chart(
                    data=df.to_dict("records"),
                    x_column=x_col,
                    y_column=y_col,
                    title=f"{y_col} by {x_col}",
                )

            elif chart_type == "line":
                # 对于折线图，尝试找到时间序列数据
                numeric_cols = df.select_dtypes(include=[pd.np.number]).columns.tolist()
                date_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()

                if not numeric_cols:
                    return {"error": "No numeric columns found for line chart"}

                # 如果有日期列，使用第一个；否则使用索引
                x_col = date_cols[0] if date_cols else df.index.name or "index"
                y_col = numeric_cols[0]

                chart_data = (
                    df.to_dict("records")
                    if date_cols
                    else [{x_col: i, y_col: row[y_col]} for i, row in df.iterrows()]
                )

                return {
                    "type": "line",
                    "title": f"{y_col} over {x_col}",
                    "data": chart_data,
                    "x_column": x_col,
                    "y_column": y_col,
                }

            elif chart_type == "pie":
                # 对于饼图，使用分类列的值计数
                categorical_cols = df.select_dtypes(include=["object"]).columns.tolist()

                if not categorical_cols:
                    return {"error": "No categorical columns found for pie chart"}

                col = categorical_cols[0]
                value_counts = df[col].value_counts().head(10)  # 只取前10个值

                return {
                    "type": "pie",
                    "title": f"Distribution of {col}",
                    "data": [
                        {"label": str(k), "value": int(v)}
                        for k, v in value_counts.items()
                    ],
                    "column": col,
                }

            else:
                return {"error": f"Unsupported chart type: {chart_type}"}

        except Exception as e:
            return {"error": f"Visualization failed: {str(e)}"}
