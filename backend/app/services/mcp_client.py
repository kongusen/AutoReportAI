from typing import Any, Dict, Optional

import requests

from app.core.config import settings


class FastMCPClient:
    def __init__(self, service_urls: Dict[str, str]):
        self.service_urls = service_urls
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def _get_service_url(self, service_name: str) -> str:
        # In our new simplified model, all tools are part of the main backend.
        # So the service URL is always the backend's own URL.
        url = self.service_urls.get(service_name)
        if not url:
            raise ValueError(
                f"Service '{service_name}' not configured in SERVICE_URLS."
            )
        return url

    def post(
        self, service_name: str, endpoint: str, payload: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Sends a POST request to a configured service.
        `endpoint` should start with a '/' (e.g., '/tools/resolve-data-placeholder').
        """
        base_url = self._get_service_url(service_name)
        full_url = f"{base_url}{endpoint}"

        try:
            response = self.session.post(full_url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"FastMCPClient POST Error to {full_url}: {e}")
            return None


# The settings object will be updated to include SERVICE_URLS.
# For now, we assume it's there.
mcp_client = FastMCPClient(settings.SERVICE_URLS)
