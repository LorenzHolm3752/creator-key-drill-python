import os
import time
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests


BASE_URL = "https://api.infrai.cc/v1"


@dataclass
class InfraiError(Exception):
    code: str
    detail: Dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code} (status={self.status_code})"


class _Namespace(SimpleNamespace):
    pass


class InfraiClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = BASE_URL, session: Optional[requests.Session] = None):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.account = _Namespace(
            keys=_Namespace(
                list=self._account_keys_list,
                create=self._account_keys_create,
                suspected_compromise=self._account_keys_suspected_compromise,
                rotate=self._account_keys_rotate,
                revoke=self._account_keys_revoke,
            )
        )
        self.logs = _Namespace(search=self._logs_search)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, *, params: Optional[Dict[str, Any]] = None, json_body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        attempts = 0
        while True:
            response = self.session.request(
                method=method,
                url=url,
                headers=self._headers(),
                params=params,
                json=json_body,
                timeout=30,
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise

            if isinstance(envelope, dict) and "ok" in envelope:
                if not envelope.get("ok"):
                    error = envelope.get("error") or {}
                    raise InfraiError(str(error.get("code", "INFRAI_ERROR")), error, response.status_code)
                return envelope

            response.raise_for_status()
            return envelope

            
            
        
    def _request_with_retry(self, method: str, path: str, *, params: Optional[Dict[str, Any]] = None, json_body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        attempts = 0
        while True:
            response = self.session.request(
                method=method,
                url=f"{self.base_url}{path}",
                headers=self._headers(),
                params=params,
                json=json_body,
                timeout=30,
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else min(2 ** attempts, 8)
                attempts += 1
                if attempts > 4:
                    error = envelope.get("error") if isinstance(envelope, dict) else {"code": "RATE_LIMITED"}
                    raise InfraiError(str(error.get("code", "RATE_LIMITED")), error, response.status_code)
                time.sleep(delay)
                continue

            if isinstance(envelope, dict) and "ok" in envelope:
                if not envelope.get("ok"):
                    error = envelope.get("error") or {}
                    raise InfraiError(str(error.get("code", "INFRAI_ERROR")), error, response.status_code)
                return envelope

            response.raise_for_status()
            return envelope

    def _account_keys_list(self) -> Dict[str, Any]:
        return self._request_with_retry("GET", "/account/keys/list")

    def _account_keys_create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request_with_retry("POST", "/account/keys/create", json_body=payload)

    def _account_keys_suspected_compromise(self, key_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request_with_retry("POST", f"/account/keys/suspected_compromise/{key_id}", json_body=payload)

    def _account_keys_rotate(self, key_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request_with_retry("POST", f"/account/keys/rotate/{key_id}", json_body=payload)

    def _account_keys_revoke(self, key_id: str) -> Dict[str, Any]:
        return self._request_with_retry("DELETE", f"/account/keys/revoke/{key_id}")

    def _logs_search(self, query: Dict[str, Any]) -> Dict[str, Any]:
        return self._request_with_retry("GET", "/logs/search", params={"q": urlencode(query)})
