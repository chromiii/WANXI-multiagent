from wanxi_geo.crawler import WebsiteCrawler


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
