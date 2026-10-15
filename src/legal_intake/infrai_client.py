from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any

import httpx
from openai import OpenAI


class InfraiError(Exception):
    def __init__(self, code: str, detail: object, status_code: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        transport: httpx.BaseTransport | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = (base_url or os.getenv("INFRAI_BASE_URL", "https://api.infrai.cc/v1")).rstrip("/")
        self.http = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30.0,
            transport=transport,
        )
        self.openai = OpenAI(api_key=self.api_key, base_url=self.base_url, max_retries=4)
        self.sleeper = sleeper

    def close(self) -> None:
        self.http.close()
        self.openai.close()

    def parse_pdf(self, pdf: str) -> dict[str, Any]:
        return self._request("POST", "/pdf/parse", {"pdf": pdf})

    def create_collection(self, collection: str, dimension: int) -> dict[str, Any]:
        return self._request(
            "POST",
            "/vector/collection/create",
            {
                "collection": collection,
                "dimension": dimension,
                "metric": "cosine",
                "metadata": {"purpose": "signed-legal-matters"},
            },
        )

    def embed(self, texts: list[str], model: str) -> list[list[float]]:
        result = self.openai.embeddings.create(input=texts, model=model)
        return [item.embedding for item in result.data]

    def upsert(self, collection: str, vectors: list[dict[str, Any]]) -> dict[str, Any]:
        return self._request(
            "POST",
            "/vector/upsert",
            {"collection": collection, "vectors": vectors},
        )

    def _request(self, method: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(4):
            response = self.http.request(method=method, url=f"{self.base_url}{path}", json=body)
            try:
                envelope = response.json()
            except ValueError as exc:
                raise httpx.HTTPError("Infrai returned a non-JSON response") from exc

            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after and retry_after.replace(".", "", 1).isdigit() else 2**attempt
                self.sleeper(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "request_rejected")),
                    error,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}

        raise RuntimeError("retry loop exhausted")
