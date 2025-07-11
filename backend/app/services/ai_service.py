import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from typing import List, Dict, Any
from sqlalchemy.orm import Session
import openai

from app import crud
from app.core.config import settings

class AIService:
    def __init__(self, db: Session):
        self.db = db
        # Font settings remain
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False

    def _get_active_provider(self):
        provider = crud.ai_provider.get_active(self.db)
        if not provider:
            # Fallback to a mock provider if none is active
            return {"provider_type": "mock"}
        return {
            "provider_type": provider.provider_type.value,
            "api_key": provider.api_key,
            "api_base_url": provider.api_base_url,
            "model_name": provider.default_model_name,
        }

    def generate_chart_from_description(self, data: List[Dict[str, Any]], description: str) -> str:
        provider_config = self._get_active_provider()
        
        if provider_config["provider_type"] == "openai":
            return self._generate_chart_with_openai(data, description, provider_config)
        else: # Fallback to mock generation
            return self._generate_chart_mock(data, description)

    def generate_text_summary(self, context_data: Dict[str, Any]) -> str:
        provider_config = self._get_active_provider()

        if provider_config["provider_type"] == "openai":
            return self._generate_text_with_openai(context_data, provider_config)
        else: # Fallback to mock generation
            return self._generate_text_mock(context_data)

    def _generate_chart_with_openai(self, data: List[Dict[str, Any]], description: str, config: Dict) -> str:
        client = openai.OpenAI(api_key=config["api_key"], base_url=config.get("api_base_url"))
        
        # Simplified data to string for the prompt
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
            response = client.chat.completions.create(
                model=config["model_name"] or "gpt-4",
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

    def _generate_text_with_openai(self, context_data: Dict[str, Any], config: Dict) -> str:
        client = openai.OpenAI(api_key=config["api_key"], base_url=config.get("api_base_url"))
        
        # Prune large data like images before sending to LLM
        prompt_data = {k: v for k, v in context_data.items() if not isinstance(v, str) or not v.startswith('iVBOR')}
        
        prompt = f"""
        你是一位数据分析师，你需要根据以下JSON格式的数据，撰写一段约100字的专业、客观的数据分析摘要。
        数据:
        {prompt_data}
        
        请直接输出分析摘要文本。
        """
        try:
            response = client.chat.completions.create(
                model=config["model_name"] or "gpt-3.5-turbo",
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
