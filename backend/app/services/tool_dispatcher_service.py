from typing import Any, Dict

import pandas as pd
from sqlalchemy.orm import Session

from app import crud
from app.services.ai_service import AIService
from app.services.data_retrieval_service import DataRetrievalService
from app.services.visualization_service import VisualizationService


class ToolDispatcherService:
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIService(db)
        self.data_retrieval_service = DataRetrievalService()
        self.visualization_service = VisualizationService()

    def dispatch(
        self, data_source_id: int, placeholder_type: str, placeholder_description: str
    ) -> Any:
        # 1. 获取原始数据
        data_source = crud.data_source.get(self.db, id=data_source_id)
        if not data_source:
            raise ValueError(f"Data source with id {data_source_id} not found.")
        df = self.data_retrieval_service.get_data(data_source)

        # 2. 调用AI服务解释描述，生成结构化参数
        ai_params = self.ai_service.interpret_description_for_tool(
            task_type=placeholder_type,
            description=placeholder_description,
            df_columns=df.columns.tolist(),
        )

        # 3. 根据AI返回的参数处理数据
        processed_df = self._apply_filters(df, ai_params)

        # 4. 根据占位符类型执行最终操作
        if placeholder_type == "text":
            # 对于文本，我们可以进行描述性统计或返回特定指标
            metric = (
                ai_params.get("metrics", [])[0]
                if ai_params.get("metrics")
                else processed_df.columns[0]
            )
            if not processed_df.empty:
                # 这里可以根据需要进行更复杂的文本生成
                return processed_df[metric].iloc[0]
            return "No data found for the given criteria."

        elif placeholder_type == "chart":
            # 对于图表，调用可视化服务
            if processed_df.empty:
                raise ValueError("Cannot generate chart from empty data.")

            # 从AI参数中获取绘图所需信息
            chart_type = ai_params.get("chart_type", "bar")
            metrics = ai_params.get("metrics")
            dimensions = ai_params.get("dimensions")

            if not metrics or not dimensions:
                raise ValueError(
                    "Metrics and dimensions are required for chart generation."
                )

            # 简单处理，取第一个维度和指标
            x_column = dimensions[0]
            y_column = metrics[0]

            title = f"{y_column} by {x_column}"  # 可以让AI也生成标题

            return self.visualization_service.create_chart_image(
                df=processed_df,
                chart_type=chart_type,
                x_column=x_column,
                y_column=y_column,
                title=title,
            )

        elif placeholder_type == "table":
            # 对于表格，返回处理后的DataFrame的JSON表示
            return processed_df.to_dict(orient="records")

        else:
            raise ValueError(f"Unsupported placeholder type: {placeholder_type}")

    def _apply_filters(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """根据参数筛选DataFrame"""
        filtered_df = df.copy()

        # 应用日期范围筛选
        date_range = params.get("date_range")
        if date_range and len(date_range) == 2:
            # 假设DataFrame中有一个datetime类型的列，这里需要确定是哪一列
            # 我们可以在AI prompt中要求它也识别出日期列的名称
            date_column = next(
                (col for col in filtered_df.columns if "date" in col.lower()), None
            )
            if date_column:
                filtered_df[date_column] = pd.to_datetime(filtered_df[date_column])
                start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(
                    date_range[1]
                )
                filtered_df = filtered_df[
                    (filtered_df[date_column] >= start_date)
                    & (filtered_df[date_column] <= end_date)
                ]

        # 应用多列内容筛选
        filters = params.get("filters", {})
        for column, value in filters.items():
            if column in filtered_df.columns:
                if isinstance(value, list):
                    filtered_df = filtered_df[filtered_df[column].isin(value)]
                else:
                    filtered_df = filtered_df[filtered_df[column] == value]

        return filtered_df
