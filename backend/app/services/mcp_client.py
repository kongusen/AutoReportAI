import requests
from typing import Optional, Dict, Any

from app.core.config import settings

class FastMCPClient:
    def __init__(self, service_urls: Dict[str, str]):
        self.service_urls = service_urls
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def _get_service_url(self, service_name: str) -> str:
        url = self.service_urls.get(service_name)
        if not url:
            raise ValueError(f"Service '{service_name}' not configured in SERVICE_URLS.")
        return url

    def post(self, service_name: str, endpoint: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Sends a POST request to a configured service.
        `endpoint` should start with a '/' (e.g., '/generate-chart').
        """
        base_url = self._get_service_url(service_name)
        full_url = f"{base_url}{endpoint}"
        
        try:
            response = self.session.post(full_url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"FastMCPClient POST Error to {full_url}: {e}")
            # In a real app, you might want more sophisticated error handling or logging
            return None

    # You can add get, put, delete methods here in the future
    # def get(...)
    # def put(...)

mcp_client = FastMCPClient(settings.SERVICE_URLS) 