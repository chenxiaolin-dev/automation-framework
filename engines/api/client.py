"""API 引擎客户端：httpx 封装 + 会话级 Header（鉴权）+ 最近交互环形记录（脱敏）。"""
from __future__ import annotations

import json
import time
from collections import deque
from dataclasses import asdict, dataclass

import httpx
from loguru import logger

from core.logging.redaction import redact


@dataclass
class ApiExchange:
    """一次请求/响应的脱敏快照（最多保留最近 20 条，失败时挂到 Allure）。"""

    method: str
    path: str
    url: str
    status: int
    request_headers: dict
    request_body: object
    response_headers: dict
    response_body: object
    duration_ms: float

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, default=str)


class ApiClient:
    def __init__(self, base_url: str = "", timeout: float = 10.0,
                 headers: dict | None = None, transport: httpx.BaseTransport | None = None,
                 max_history: int = 20):
        self.base_url = (base_url or "").rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout, transport=transport)
        if headers:
            self._client.headers.update(headers)
        self.exchanges: deque[ApiExchange] = deque(maxlen=max_history)

    # ---- 会话级 Header（鉴权 token 等）----
    def set_header(self, key: str, value: str) -> None:
        self._client.headers[key] = value

    # ---- 核心请求 ----
    def request(self, method: str, path: str, *, name: str | None = None,
                params=None, json=None, data=None, headers=None) -> httpx.Response:
        method = method.upper()
        step = name or f"{method} {path}"
        start = time.time()
        try:
            resp = self._client.request(method, path, params=params, json=json,
                                        data=data, headers=headers)
        except Exception as e:
            logger.error(f"[API] {step} 请求异常: {e}")
            raise
        duration_ms = (time.time() - start) * 1000
        self._record(method, path, resp, json=json, data=data, duration_ms=duration_ms)
        logger.info(f"[API] {step} -> {resp.status_code} ({duration_ms:.0f}ms)")
        return resp

    def _record(self, method, path, resp, *, json, data, duration_ms) -> None:
        try:
            body = resp.json()
        except Exception:  # noqa: BLE001 非 JSON 响应
            body = resp.text
        self.exchanges.append(ApiExchange(
            method=method, path=path, url=str(resp.request.url), status=resp.status_code,
            request_headers=redact(dict(resp.request.headers)),
            request_body=redact(json if json is not None else data),
            response_headers=redact(dict(resp.headers)),
            response_body=redact(body) if isinstance(body, (dict, list)) else str(body)[:2000],
            duration_ms=round(duration_ms, 1),
        ))

    def attach_recent_exchanges(self, count: int = 20) -> None:
        """把最近 N 次交互（脱敏）聚合挂载到 Allure。"""
        import allure
        for ex in list(self.exchanges)[-count:]:
            allure.attach(ex.to_json(), name=f"API {ex.method} {ex.path} -> {ex.status}",
                          attachment_type=allure.attachment_type.JSON)

    # ---- 快捷方法 ----
    def get(self, path, **kw):    return self.request("GET", path, **kw)
    def post(self, path, **kw):   return self.request("POST", path, **kw)
    def put(self, path, **kw):    return self.request("PUT", path, **kw)
    def delete(self, path, **kw): return self.request("DELETE", path, **kw)

    def close(self):
        self._client.close()
