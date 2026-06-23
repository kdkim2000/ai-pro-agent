# src/connectors/github_client.py
"""GitHub Enterprise REST API v3 connector (T1-2_GUIDE.md Section 4.1)"""
from __future__ import annotations
from typing import Optional
import httpx, os, base64
from .base import BaseGitHubConnector, ConnectorResult, CodeFile


class GitHubEnterpriseConnector(BaseGitHubConnector):
    """GitHub Enterprise REST API v3 connector"""

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None, timeout: int = 30):
        self.base_url = (base_url or os.getenv("GITHUB_ENTERPRISE_URL", "")).rstrip("/")
        self.token = token or os.getenv("GITHUB_TOKEN", "")
        self.timeout = timeout
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _get(self, path: str, params: dict = None) -> dict:
        url = f"{self.base_url}/api/v3{path}"
        with httpx.Client(timeout=self.timeout, verify=False) as client:
            resp = client.get(url, headers=self._headers, params=params or {})
            resp.raise_for_status()
            return resp.json()

    def _post(self, path: str, json: dict) -> dict:
        url = f"{self.base_url}/api/v3{path}"
        with httpx.Client(timeout=self.timeout, verify=False) as client:
            resp = client.post(url, headers=self._headers, json=json)
            resp.raise_for_status()
            return resp.json()

    def health_check(self) -> ConnectorResult:
        try:
            data = self._get("/meta")
            return ConnectorResult(success=True, data=data.get("version"), source=self.base_url)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def search_code(self, query: str, repo: Optional[str] = None, top_k: int = 5) -> ConnectorResult:
        try:
            q = f"{query} repo:{repo}" if repo else query
            data = self._get("/search/code", params={"q": q, "per_page": top_k})
            files = []
            for item in data.get("items", [])[:top_k]:
                content_data = self._get(f"/repos/{item['repository']['full_name']}/contents/{item['path']}")
                decoded = base64.b64decode(content_data.get("content", "").replace("\n", "")).decode("utf-8", errors="replace")
                files.append(CodeFile(
                    path=item["path"], content=decoded,
                    repo=item["repository"]["full_name"], branch=content_data.get("ref", "main"),
                    sha=content_data.get("sha", ""), url=item["html_url"],
                    language=item.get("language"),
                ))
            return ConnectorResult(success=True, data=files, source=self.base_url)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def get_file(self, repo: str, path: str, ref: str = "main") -> ConnectorResult:
        try:
            data = self._get(f"/repos/{repo}/contents/{path}", params={"ref": ref})
            decoded = base64.b64decode(data.get("content", "").replace("\n", "")).decode("utf-8", errors="replace")
            file = CodeFile(path=path, content=decoded, repo=repo, branch=ref, sha=data.get("sha", ""), url=data.get("html_url", ""))
            return ConnectorResult(success=True, data=file, source=data.get("html_url"))
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def list_repos(self, org: str) -> ConnectorResult:
        try:
            data = self._get(f"/orgs/{org}/repos", params={"per_page": 100, "type": "all"})
            return ConnectorResult(success=True, data=[r["full_name"] for r in data])
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def create_pr_draft(self, repo: str, title: str, body: str, head: str, base: str = "main") -> ConnectorResult:
        try:
            data = self._post(f"/repos/{repo}/pulls", json={"title": title, "body": body, "head": head, "base": base, "draft": True})
            return ConnectorResult(success=True, data={"pr_number": data["number"], "pr_url": data["html_url"]}, source=data["html_url"])
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))
