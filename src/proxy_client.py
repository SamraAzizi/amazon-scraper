import os
import requests
from typing import Optional, Dict


class ThordataProxyClient:
    def __init__(self):
        self.username = os.getenv("THORDATA_USERNAME")
        self.password = os.getenv("THORDATA_PASSWORD")
        proxy_server = os.getenv("THORDATA_PROXY_SERVER", "t.pr.thordata.net:9999")
        
        if not self.username or not self.password:
            raise ValueError("THORDATA_USERNAME and THORDATA_PASSWORD must be set")
        
        if ":" in proxy_server:
            self.proxy_host, self.proxy_port = proxy_server.rsplit(":", 1)
        else:
            self.proxy_host = proxy_server
            self.proxy_port = "9999"

    def _build_proxy_auth(self, country: Optional[str] = None, session_id: Optional[str] = None) -> str:
        username_part = self.username
        if username_part.startswith("td-customer-"):
            username_part = username_part.replace("td-customer-", "")
        
        auth_parts = [username_part]
        
        if country:
            auth_parts.append(f"country-{country.lower()}")
        
        if session_id:
            auth_parts.append(f"sessid-{session_id}")
            auth_parts.append("sesstime-30")
        
        auth_string = "-".join(auth_parts)
        return f"td-customer-{auth_string}:{self.password}"

    def _get_proxy_url(self, country: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, str]:
        auth = self._build_proxy_auth(country, session_id)
        proxy_url = f"http://{auth}@{self.proxy_host}:{self.proxy_port}"
        return {
            "http": proxy_url,
            "https": proxy_url
        }