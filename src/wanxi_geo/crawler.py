from __future__ import annotations

import json
import re
from collections import deque
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

from .models import SiteDocument


ASSET_SUFFIXES = (
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico",
    ".pdf", ".zip", ".rar", ".7z", ".mp4", ".mp3", ".css", ".js",
)


class WebsiteCrawler:
    def __init__(self, timeout: int = 12, user_agent: str | None = None):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent
                or "WANXI-GEO-Demo/0.1 (+local candidate assessment project)"
            }
        )

    def load_or_crawl(
        self,
        start_url: str,
        *,
        max_pages: int,
        cache_path: Path,
        refresh: bool = False,
    ) -> list[SiteDocument]:
        cache_path = Path(cache_path)
        if not refresh and cache_path.exists():
            try:
                payload = json.loads(cache_path.read_text(encoding="utf-8"))
                if payload.get("start_url") == start_url:
                    docs = [SiteDocument.model_validate(x) for x in payload.get("documents", [])]
                    if docs:
                        return docs
            except (json.JSONDecodeError, OSError, ValueError):
                pass

        docs = self.crawl(start_url, max_pages=max_pages)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(
                {
                    "start_url": start_url,
                    "documents": [d.model_dump() for d in docs],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return docs

    def crawl(self, start_url: str, *, max_pages: int = 12) -> list[SiteDocument]:
        start = self._normalize_url(start_url)
        allowed_host = self._canonical_host(urlparse(start).netloc)
        queue: deque[str] = deque([start])
        seen: set[str] = set()
        docs: list[SiteDocument] = []

        while queue and len(docs) < max_pages:
            url = queue.popleft()
            if url in seen:
                continue
            seen.add(url)

            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
            except requests.RequestException:
                continue

            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type.lower():
                continue

            doc = self.parse_html(url, response.text)
            if len(doc.text) < 120:
                continue
            docs.append(doc)

            for link in doc.links:
                parsed = urlparse(link)
                if self._canonical_host(parsed.netloc) != allowed_host:
                    continue
                if parsed.path.lower().endswith(ASSET_SUFFIXES):
                    continue
                if link not in seen:
                    queue.append(link)

        if not docs:
            raise RuntimeError(
                "No readable HTML pages were collected. The site may block requests or require JavaScript rendering."
            )
        return docs

    def parse_html(self, url: str, html: str) -> SiteDocument:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        headings = [
            self._clean_text(h.get_text(" ", strip=True))
            for h in soup.find_all(["h1", "h2", "h3"])
            if h.get_text(" ", strip=True)
        ]

        links: list[str] = []
        for a in soup.find_all("a", href=True):
            href = a.get("href", "").strip()
            if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue
            absolute = self._normalize_url(urljoin(url, href))
            links.append(absolute)

        for node in soup.find_all(["script", "style", "noscript", "svg", "form"]):
            node.decompose()
        for selector in ["nav", "footer"]:
            for node in soup.select(selector):
                node.decompose()

        container = soup.find("main") or soup.find("article") or soup.body or soup
        text = self._clean_text(container.get_text("\n", strip=True))
        links = list(dict.fromkeys(links))
        headings = list(dict.fromkeys(h for h in headings if h))
        return SiteDocument(url=url, title=title, headings=headings, text=text, links=links)

    @staticmethod
    def _clean_text(text: str) -> str:
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
        lines = [line for line in lines if line]
        return "\n".join(lines)

    @staticmethod
    def _canonical_host(host: str) -> str:
        host = host.lower().split(":", 1)[0]
        return host[4:] if host.startswith("www.") else host

    @staticmethod
    def _normalize_url(url: str) -> str:
        url, _fragment = urldefrag(url)
        parsed = urlparse(url)
        scheme = parsed.scheme or "https"
        path = parsed.path or "/"
        if path != "/":
            path = path.rstrip("/")
        return urlunparse((scheme, parsed.netloc, path, "", parsed.query, ""))
