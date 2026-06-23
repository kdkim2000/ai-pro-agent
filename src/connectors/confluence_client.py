# src/connectors/confluence_client.py
"""Confluence REST API connector (T1-2_GUIDE.md Section 4.2)"""
from __future__ import annotations
from typing import Optional
import httpx, os
from .base import BaseConfluenceConnector, ConnectorResult, ConfluencePage


class ConfluenceConnector(BaseConfluenceConnector):
    """Confluence REST API v2 connector"""

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None, timeout: int = 30):
        self.base_url = (base_url or os.getenv("CONFLUENCE_URL", "")).rstrip("/")
        self.token = token or os.getenv("CONFLUENCE_TOKEN", "")
        self.timeout = timeout
        self._headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json", "Accept": "application/json"}

    def _get(self, path: str, params: dict = None) -> dict:
        url = f"{self.base_url}/rest/api{path}"
        with httpx.Client(timeout=self.timeout, verify=False) as client:
            resp = client.get(url, headers=self._headers, params=params or {})
            resp.raise_for_status()
            return resp.json()

    def _post(self, path: str, json: dict) -> dict:
        url = f"{self.base_url}/rest/api{path}"
        with httpx.Client(timeout=self.timeout, verify=False) as client:
            resp = client.post(url, headers=self._headers, json=json)
            resp.raise_for_status()
            return resp.json()

    def health_check(self) -> ConnectorResult:
        try:
            self._get("/space", params={"limit": 1})
            return ConnectorResult(success=True, data="connected", source=self.base_url)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def search_pages(self, query: str, space_key: Optional[str] = None, top_k: int = 5) -> ConnectorResult:
        try:
            cql = f'text ~ "{query}" AND type = "page"'
            if space_key:
                cql += f' AND space = "{space_key}"'
            data = self._get("/content/search", params={"cql": cql, "limit": top_k, "expand": "body.storage"})
            pages = []
            for item in data.get("results", []):
                body = item.get("body", {}).get("storage", {}).get("value", "")
                pages.append(ConfluencePage(
                    page_id=item["id"], title=item["title"], content=body,
                    space_key=item.get("space", {}).get("key", ""),
                    url=f"{self.base_url}{item['_links'].get('webui', '')}",
                    last_modified=item.get("version", {}).get("when", ""),
                    labels=[l["name"] for l in item.get("metadata", {}).get("labels", {}).get("results", [])],
                ))
            return ConnectorResult(success=True, data=pages)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def get_page(self, page_id: str) -> ConnectorResult:
        try:
            data = self._get(f"/content/{page_id}", params={"expand": "body.storage,version,space"})
            page = ConfluencePage(
                page_id=data["id"], title=data["title"], content=data["body"]["storage"]["value"],
                space_key=data["space"]["key"], url=f"{self.base_url}{data['_links']['webui']}",
                last_modified=data["version"]["when"],
            )
            return ConnectorResult(success=True, data=page, source=page.url)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def get_template(self, template_name: str) -> ConnectorResult:
        try:
            result = self.search_pages(f"title:{template_name}", top_k=1)
            if result.success and result.data:
                return ConnectorResult(success=True, data=result.data[0].content)
            return ConnectorResult(success=False, error=f"Template '{template_name}' not found")
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def create_page(self, space_key: str, title: str, content: str, parent_id: Optional[str] = None) -> ConnectorResult:
        try:
            payload = {"type": "page", "title": title, "space": {"key": space_key}, "body": {"storage": {"value": content, "representation": "storage"}}}
            if parent_id:
                payload["ancestors"] = [{"id": parent_id}]
            data = self._post("/content", json=payload)
            return ConnectorResult(success=True, data={"page_id": data["id"], "url": f"{self.base_url}{data['_links']['webui']}"})
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))
