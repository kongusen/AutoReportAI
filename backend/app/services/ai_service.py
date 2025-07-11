import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from typing import List, Dict, Any
from sqlalchemy.orm import Session
import openai
import json

from app import crud
from app.core.config import settings

class AIService:
    def __init__(self, db: Session):
        self.db = db
        self.client = None
        self.provider_config = self._get_active_provider()
        
        if self.provider_config.get("provider_type") == "openai":
            self.client = openai.OpenAI(
                api_key=self.provider_config["api_key"],
                base_url=self.provider_config.get("api_base_url"),
            )
            
        # Font settings remain
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False

    def interpret_description_for_tool(self, task_type: str, description: str) -> Dict[str, Any]:
        """
        Uses an AI to interpret a natural language description and generate parameters for a tool.
        """
        if not (self.provider_config["provider_type"] == "openai" and self.client):
            # If no real AI is configured, return mock parameters.
            print("AI provider not configured, returning mock parameters.")
            if "投诉" in description:
                return {"data_source_id": 1}
            return {}

        # Define the expected JSON structure for each tool type
        tool_formats = {
            "count": """
            - **'count'**: 统计数量。
              - `data_source_id`: 数据源的数字ID (例如: 1, 2, 3).
              - `column_name`: 要统计的列名。
              - `query_conditions`: (可选) 一个用于过滤数据的条件字典。
            示例: `{"data_source_id": 1, "column_name": "value"}`
            """,
            "query": """
            - **'query'**: 计算百分比变化。
              - `value1`: 第一个值 (例如, 上个月的数量)。
              - `value2`: 第二个值 (例如, 这个月的数量)。
            示例: `{"value1": 100, "value2": 120}`
            """,
            "draw": """
            - **'draw'**: 生成图表。
              - `data_source_id`: 数据源的数字ID.
              - `x_column`: 图表的X轴对应的列名。
              - `y_column`: 图表的Y轴对应的列名。
              - `title`: 图表的标题。
              - `chart_type`: (可选) 'bar', 'pie', 'line'.
            示例: `{"data_source_id": 1, "x_column": "category", "y_column": "value", "title": "各类投诉占比", "chart_type": "bar"}`
            """
        }

        if task_type not in tool_formats:
            raise ValueError(f"Unsupported task_type: {task_type}")

        selected_format = tool_formats[task_type]

        prompt = f"""
        你是一个智能AI助手，你的任务是根据用户的自然语言描述，为特定的工具生成一个JSON格式的参数对象。

        **任务:**
        将以下描述转换为一个JSON对象，用于 `{task_type}` 工具。

        **描述:**
        "{description}"

        **工具和JSON格式:**
        {selected_format}

        **说明:**
        1. 分析描述以提取所有必要的参数。
        2. 如果描述中提到了特定的实体（例如“投诉”、“销售额”），请推断出最合适的 `data_source_id`。假设 "投诉" 数据源的ID是 `1`，"销售" 数据源的ID是 `2`。
        3. 如果某些参数在描述中没有明确提到，请根据常识和上下文进行推断。
        4. 你的回答**必须**只包含一个格式正确的JSON对象，不带任何额外的解释或代码块标记。

        **输出JSON:**
        """

        try:
            response = self.client.chat.completions.create(
                model=self.provider_config.get("model_name") or "gpt-4-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            params = json.loads(content)
            return params
        except json.JSONDecodeError:
            print(f"Failed to parse JSON from AI response: {content}")
            raise ValueError("AI returned invalid JSON.")
        except Exception as e:
            print(f"An unexpected error occurred during AI parameter generation: {e}")
            raise

    def _get_active_provider(self):
        provider = crud.ai_provider.get_active(self.db)
        if not provider:
            # Fallback to a mock provider if none is active
            return {"provider_type": "mock"}
        return {
            "provider_type": provider.provider_type.value,
            "api_key": provider.api_key,
            "api_base_url": str(provider.api_base_url) if provider.api_base_url else None,
            "model_name": provider.default_model_name,
        }

    def generate_chart_from_description(self, data: List[Dict[str, Any]], description: str) -> str:
        if self.provider_config["provider_type"] == "openai" and self.client:
            return self._generate_chart_with_openai(data, description)
        else: # Fallback to mock generation
            return self._generate_chart_mock(data, description)

    def generate_text_summary(self, context_data: Dict[str, Any]) -> str:
        if self.provider_config["provider_type"] == "openai" and self.client:
            return self._generate_text_with_openai(context_data)
        else: # Fallback to mock generation
            return self._generate_text_mock(context_data)

    def _generate_chart_with_openai(self, data: List[Dict[str, Any]], description: str) -> str:
        # client is now self.client
        data_str = pd.DataFrame(data).to_string()

        prompt = f"""
        你是一个数据可视化专家。根据以下数据和描述，生成一个合适的Matplotlib图表。
        你的代码应该：
        1. 导入 matplotlib.pyplot as plt 和 pandas as pd.
        2. 使用以下数据: 
        ```
        {data_str}
        ```
        3. 创建一个符合描述 '{description}' 的图表 (例如 柱状图, 饼图, 折线图).
        4. **不要**调用 `plt.show()`。
        5. 将图表保存到一个 BytesIO buffer 中。
        6. 将 buffer 转换为 base64 编码的字符串并打印出来。
        7. 只输出最终的base64字符串，不要包含任何其他文字或解释。
        
        请生成完整的Python代码。
        """

        try:
            response = self.client.chat.completions.create(
                model=self.provider_config["model_name"] or "gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            code_to_exec = response.choices[0].message.content.strip('` \n')
            
            # This is risky and requires a secure execution environment.
            # For this context, we'll execute it directly.
            # A safer approach would be to use a sandboxed environment like Docker.
            local_namespace = {}
            exec(code_to_exec, globals(), local_namespace)
            
            # Assuming the code prints the base64 string as requested
            # A more robust way is to have the exec'd code return the value.
            return next(iter(local_namespace.values())) # Hacky way to get the output

        except Exception as e:
            print(f"OpenAI chart generation failed: {e}")
            return self._generate_chart_mock(data, description) # Fallback on error

    def _generate_text_with_openai(self, context_data: Dict[str, Any]) -> str:
        # client is now self.client
        prompt_data = {k: v for k, v in context_data.items() if not isinstance(v, str) or not v.startswith('iVBOR')}
        
        prompt = f"""
        你是一位数据分析师，你需要根据以下JSON格式的数据，撰写一段约100字的专业、客观的数据分析摘要。
        数据:
        {prompt_data}
        
        请直接输出分析摘要文本。
        """
        try:
            response = self.client.chat.completions.create(
                model=self.provider_config["model_name"] or "gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI text generation failed: {e}")
            return self._generate_text_mock(context_data) # Fallback on error

    def _generate_chart_mock(self, data: List[Dict[str, Any]], description: str) -> str:
        if not data:
            raise ValueError("Input data cannot be empty.")
        df = pd.DataFrame(data)
        if "柱状图" in description:
            self._create_bar_chart(df, description)
        elif "饼图" in description:
            self._create_pie_chart(df, description)
        elif "折线图" in description:
            self._create_line_chart(df, description)
        else:
            # Default to a bar chart if type is not specified
            self._create_bar_chart(df, description)
            
        # Save plot to a bytes buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close()
        buf.seek(0)
        
        # Encode buffer to base64
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()
        
        return image_base64

    def _generate_text_mock(self, context_data: Dict[str, Any]) -> str:
        project_name = context_data.get("project_name", "该项目")
        total_sales = context_data.get("total_sales_from_regions", 0)
        
        # Example of finding the region with the highest sales
        regional_sales = context_data.get("sales_by_region", [])
        top_region = ""
        max_sales = 0
        if isinstance(regional_sales, list) and regional_sales:
            top_performer = max(regional_sales, key=lambda x: x.get('sales', 0))
            top_region = top_performer.get("region", "")
            max_sales = top_performer.get("sales", 0)

        summary = (
            f"根据数据显示，{project_name}本月表现优异。总销售额达到 {total_sales:,.2f}元。"
            f"其中，{top_region}地区表现最为突出，销售额为 {max_sales:,.2f}元，是主要的增长动力。"
            "建议持续关注该地区的市场动态，并考虑将成功经验推广至其他区域。"
        )
        return summary

    def _create_bar_chart(self, df: pd.DataFrame, title: str):
        if len(df.columns) < 2:
            raise ValueError("Bar chart requires at least two columns (labels and values).")
        x_col, y_col = df.columns[0], df.columns[1]
        df.plot(kind='bar', x=x_col, y=y_col, legend=False)
        plt.title(title)
        plt.ylabel(y_col)
        plt.xticks(rotation=45)
    
    def _create_pie_chart(self, df: pd.DataFrame, title: str):
        if len(df.columns) < 2:
            raise ValueError("Pie chart requires at least two columns (labels and values).")
        labels_col, values_col = df.columns[0], df.columns[1]
        plt.pie(df[values_col], labels=df[labels_col], autopct='%1.1f%%', startangle=90)
        plt.title(title)
        plt.axis('equal') # Equal aspect ratio ensures that pie is drawn as a circle.

    def _create_line_chart(self, df: pd.DataFrame, title: str):
        if len(df.columns) < 2:
            raise ValueError("Line chart requires at least two columns (x and y values).")
        x_col, y_col = df.columns[0], df.columns[1]
        df.plot(kind='line', x=x_col, y=y_col, marker='o', legend=False)
        plt.title(title)
        plt.ylabel(y_col)
        plt.grid(True)
        plt.xticks(rotation=45)

# AIService instance is no longer created here. It will be dependency-injected.
# ai_service = AIService()
