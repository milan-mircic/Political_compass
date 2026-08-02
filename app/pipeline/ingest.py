from itertools import islice
from urllib.parse import urlparse

import requests

from app.config import settings
from app.db import get_cursor

NEWSDATA_URL = "https://newsdata.io/api/1/latest"
DOMAINS_PER_REQUEST = 5
MAX_PAGES_PER_BATCH = 3


def _chunk(items: list[str], size: int) -> list[list[str]]:
    it = iter(items)
    while chunk := list(islice(it, size)):
        yield chunk


def _source_map() -> dict[str, int]:
    with get_cursor() as cur:
        cur.execute("SELECT id, domain FROM sources")
        return {row["domain"]: row["id"] for row in cur.fetchall()}


def _domain_of(url: str) -> str:
    netloc = urlparse(url).netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else netloc


def _fetch_batch(domains: list[str]) -> list[dict]:
    articles = []
    domains = list(domains)
    params = {
        "apikey": settings.newsdata_api_key,
        "domainurl": ",".join(domains),
        "category": "politics",
        "language": "en",
    }
    for _ in range(MAX_PAGES_PER_BATCH):
        response = requests.get(NEWSDATA_URL, params=params, timeout=30)
        if response.status_code == 422:
            # A domain NewsData doesn't recognize poisons the whole batch --
            # drop it and retry with the rest rather than losing the batch.
            invalid = {
                err.get("invalid_domain")
                for err in (response.json().get("results") or [])
                if err.get("invalid_domain")
            }
            domains = [d for d in domains if d not in invalid]
            if not domains:
                return articles
            params["domainurl"] = ",".join(domains)
            continue
        response.raise_for_status()
        payload = response.json()
        articles.extend(payload.get("results") or [])
        next_page = payload.get("nextPage")
        if not next_page:
            break
        params["page"] = next_page
    return articles


def ingest() -> None:
    source_map = _source_map()
    rows = []

    for domains in _chunk(list(source_map), DOMAINS_PER_REQUEST):
        try:
            articles = _fetch_batch(domains)
        except requests.RequestException:
            continue

        for article in articles:
            link = article.get("link")
            title = article.get("title")
            if not link or not title:
                continue
            source_id = source_map.get(_domain_of(link))
            if source_id is None:
                continue
            rows.append((
                source_id,
                link,
                title,
                article.get("pubDate"),
                article.get("description"),
            ))

    if not rows:
        return

    with get_cursor() as cur:
        cur.executemany(
            """
            INSERT OR IGNORE INTO articles (source_id, url, title, published_at, snippet)
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )


if __name__ == "__main__":
    ingest()
