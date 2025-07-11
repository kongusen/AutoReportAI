from typing import Any, Dict
from app.services.statistics_service import StatisticsService
from app.services.visualization_service import VisualizationService
from app.services.data_retrieval_service import DataRetrievalService
from sqlalchemy.orm import Session

class ToolDispatcherService:
    """
    A service to dispatch tasks to the appropriate tool based on the task type.
    This acts as a router for the AI orchestrator.
    """

    def __init__(self, db: Session):
        self.db = db
        # In a real app, these could be injected, but for simplicity, we instantiate them here.
        self.statistics_service = StatisticsService()
        self.visualization_service = VisualizationService()
        self.data_retrieval_service = DataRetrievalService()

    def dispatch(self, task_type: str, params: Dict[str, Any]) -> Any:
        """
        Dispatches a task to the correct service.

        :param task_type: The type of task (e.g., 'count', 'query', 'draw').
        :param params: A dictionary of parameters for the task, determined by the AI.
        :return: The result from the executed tool.
        """
        # 1. Get Data (Common for most tools)
        # The AI needs to provide the data_source_id in the params.
        data_source_id = params.get("data_source_id")
        if not data_source_id:
            raise ValueError("`data_source_id` must be provided by the AI.")
        
        raw_data = self.data_retrieval_service.get_data(db=self.db, data_source_id=data_source_id)

        # 2. Route to the appropriate tool
        if task_type == "count":
            # AI must provide 'column_name' for this task
            column = params.get("column_name")
            if not column:
                raise ValueError("`column_name` must be provided for 'count' task.")
            return self.statistics_service.calculate_sum(data=raw_data, column_name=column)
        
        elif task_type == "query":
            # This is a placeholder for more complex queries like 'month-over-month'
            # A real implementation would involve more complex logic, potentially
            # fetching data for two different periods.
            # For now, let's simulate it by calculating change between two hardcoded values.
            val1 = params.get("value1", 100)
            val2 = params.get("value2", 120)
            return self.statistics_service.calculate_percentage_change(val2, val1)

        elif task_type == "draw":
            # AI must provide 'x_column', 'y_column', and 'title'
            x_col = params.get("x_column")
            y_col = params.get("y_column")
            title = params.get("title")
            if not all([x_col, y_col, title]):
                raise ValueError("`x_column`, `y_column`, and `title` are required for 'draw' task.")
            return self.visualization_service.generate_bar_chart(
                data=raw_data, x_column=x_col, y_column=y_col, title=title
            )

        else:
            raise ValueError(f"Unknown task type: {task_type}") 