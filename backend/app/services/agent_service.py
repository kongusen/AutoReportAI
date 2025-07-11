from typing import List, Dict, Any
from sqlalchemy.orm import Session
import json

from app import crud, models
from app.services.ai_service import AIService
from app.api.endpoints.tools import router as tools_router

class AgentService:
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIService(db)

    def _get_tools_description(self) -> List[Dict[str, Any]]:
        """
        Dynamically generates a description of available tools for the LLM.
        """
        tools_desc = []
        for route in tools_router.routes:
            if hasattr(route, "endpoint"):
                tools_desc.append({
                    "type": "function",
                    "function": {
                        "name": route.name,
                        "description": route.description or "",
                        "parameters": route.body_schema.schema() if hasattr(route, "body_schema") else {},
                    },
                })
        return tools_desc

    async def run(self, user_prompt: str):
        provider_config = self.ai_service._get_active_provider()
        if provider_config.get("provider_type") != "openai":
            return "Agent requires an active OpenAI provider."

        client = self.ai_service.openai.OpenAI(
            api_key=provider_config["api_key"],
            base_url=provider_config.get("api_base_url"),
        )
        
        system_prompt = "You are a helpful assistant that can call functions to retrieve data and generate reports."
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        tools = self._get_tools_description()

        # First call to the LLM
        response = client.chat.completions.create(
            model=provider_config["model_name"] or "gpt-4-turbo",
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        
        response_message = response.choices[0].message
        
        # In the next steps, we will add logic to handle the tool_calls here.
        # For now, we just return the LLM's raw response.
        
        return response_message

agent_service = AgentService 