from wanxi_geo.context import rank_documents
from wanxi_geo.models import SiteDocument


def test_rank_documents_prefers_matching_page():
    docs = [
        SiteDocument(url="https://x/a", title="公司介绍", text="品牌 团队 公司简介"),
        SiteDocument(url="https://x/b", title="GEO FAQ", text="AI 引用 GEO 优化 生成式引擎"),
        SiteDocument(url="https://x/c", title="招聘", text="岗位 招聘"),
    ]
    ranked = rank_documents("哪些内容适合 AI 引用和 GEO 优化", docs, top_k=2)
    assert ranked[0].url == "https://x/b"
