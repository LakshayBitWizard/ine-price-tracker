import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from django.conf import settings


class StoreClientError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class StoreProduct:
    id: int
    slug: str
    name: str
    brand: str
    category: str
    sku: str
    description: str
    raw: dict[str, Any]

    @property
    def url(self) -> str:
        return urljoin(settings.STORE_BASE_URL, f"/product/{self.id}")


def fetch_store_json(
    path: str,
    *,
    timeout_seconds: int = 15,
    max_attempts: int = 3,
) -> dict[str, Any]:
    url = urljoin(settings.STORE_BASE_URL, path)
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            request = Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": settings.STORE_USER_AGENT,
                },
            )
            with urlopen(request, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)
        except HTTPError as exc:
            last_error = exc
            if exc.code < 500 and exc.code != 429:
                raise StoreClientError(
                    f"Store returned HTTP {exc.code} for {path}", exc.code
                ) from exc
        except (TimeoutError, URLError, json.JSONDecodeError) as exc:
            last_error = exc

        if attempt < max_attempts:
            time.sleep(0.35 * attempt)

    raise StoreClientError(f"Could not fetch store path {path}: {last_error}")


def parse_store_product(payload: dict[str, Any]) -> StoreProduct:
    return StoreProduct(
        id=int(payload["id"]),
        slug=str(payload.get("slug") or ""),
        name=str(payload["name"]),
        brand=str(payload.get("brand") or ""),
        category=str(payload.get("category") or ""),
        sku=str(payload.get("sku") or ""),
        description=str(payload.get("description") or ""),
        raw=payload,
    )


def fetch_catalog_page(page: int = 1, page_size: int = 100) -> dict[str, Any]:
    query = urlencode({"page": page, "pageSize": page_size})
    return fetch_store_json(f"/api/catalog?{query}")


def fetch_store_product(store_product_id: int | str) -> StoreProduct:
    payload = fetch_store_json(f"/api/product/{store_product_id}")
    return parse_store_product(payload)


def search_store_products(query: str, *, limit: int = 30) -> list[StoreProduct]:
    normalized = " ".join(query.lower().split())
    if len(normalized) < 2:
        return []

    # Split query into individual words so each word is matched independently.
    # "larkspur smart plug air" matches any product containing all four words
    # anywhere in its name, brand, category, sku, or description.
    query_words = normalized.split()

    # The INE store deliberately randomizes catalog pages — each request returns
    # a different subset of ~60 products per page.  A single pass through all
    # pages often misses products.  We make multiple passes and deduplicate by
    # product ID to maximise coverage.
    seen_ids: set[int] = set()
    matches: list[StoreProduct] = []
    max_passes = 2
    page_size = 100

    for _pass in range(max_passes):
        page = 1
        while True:
            payload = fetch_catalog_page(page=page, page_size=page_size)
            for item in payload.get("items", []):
                item_id = int(item.get("id", 0))
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)
                haystack = " ".join(
                    str(item.get(key, ""))
                    for key in ("name", "brand", "category", "sku", "description")
                ).lower()
                if all(word in haystack for word in query_words):
                    matches.append(parse_store_product(item))
                    if len(matches) >= limit:
                        return matches

            pages = int(payload.get("pages") or page)
            if page >= pages:
                break
            page += 1

        # If we already found results, no need for another pass.
        if matches:
            return matches

    return matches


