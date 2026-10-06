from pathlib import Path

from wanxi_geo.crawler import WebsiteCrawler
from wanxi_geo.models import SiteDocument


def test_parse_html_extracts_main_content_and_links():
    html = """
    <html><head><title>Demo</title></head><body>
      <nav>menu</nav>
      <main>
        <h1>GEO Demo</h1>
        <p>这是用于 GEO 分析的正文内容。</p>
        <a href="/about">About</a>
      </main>
      <footer>footer</footer>
    </body></html>
    """
    doc = WebsiteCrawler().parse_html("https://example.com/", html)
    assert doc.title == "Demo"
    assert "GEO Demo" in doc.headings
    assert "正文内容" in doc.text
    assert "menu" not in doc.text
    assert "https://example.com/about" in doc.links


def test_normalize_url_removes_tracking_query_parameters():
    url = (
        "https://example.com/blog/?utm_source=test&foo=bar&gclid=123#section"
    )
    assert WebsiteCrawler._normalize_url(url) == "https://example.com/blog?foo=bar"


def test_cache_is_invalidated_when_max_pages_changes(tmp_path, monkeypatch):
    crawler = WebsiteCrawler()
    calls: list[int] = []

    def fake_crawl(start_url: str, *, max_pages: int):
        calls.append(max_pages)
        return [
            SiteDocument(
                url=f"https://example.com/{max_pages}",
                title="Demo",
                text="x" * 150,
            )
        ]

    monkeypatch.setattr(crawler, "crawl", fake_crawl)
    cache_path = Path(tmp_path) / "site_docs.json"

    crawler.load_or_crawl(
        "https://example.com/",
        max_pages=12,
        cache_path=cache_path,
    )
    crawler.load_or_crawl(
        "https://example.com/",
        max_pages=12,
        cache_path=cache_path,
    )
    crawler.load_or_crawl(
        "https://example.com/",
        max_pages=17,
        cache_path=cache_path,
    )

    assert calls == [12, 17]


def test_crawl_skips_duplicate_page_content():
    repeated_body = "重复正文 " * 40
    home_body = "首页正文 " * 40

    pages = {
        "https://example.com/": f"""
            <html><head><title>Same Title</title></head><body><main>
              <p>{home_body}</p>
              <a href="/a">A</a>
              <a href="/b">B</a>
            </main></body></html>
        """,
        "https://example.com/a": f"""
            <html><head><title>Same Title</title></head><body><main>
              <p>{repeated_body}</p>
            </main></body></html>
        """,
        "https://example.com/b": f"""
            <html><head><title>Same Title</title></head><body><main>
              <p>{repeated_body}</p>
            </main></body></html>
        """,
    }

    class FakeResponse:
        def __init__(self, url: str, text: str):
            self.url = url
            self.text = text
            self.headers = {"content-type": "text/html"}

        def raise_for_status(self):
            return None

    class FakeSession:
        def get(self, url: str, timeout: int):
            return FakeResponse(url, pages[url])

    crawler = WebsiteCrawler()
    crawler.session = FakeSession()

    docs = crawler.crawl("https://example.com/", max_pages=3)

    assert [doc.url for doc in docs] == [
        "https://example.com/",
        "https://example.com/a",
    ]
