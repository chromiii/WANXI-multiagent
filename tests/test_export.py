from wanxi_geo.export import build_sample_markdown, build_sample_pdf
from wanxi_geo.models import AgentTrace, RoutingPlan, RoutingStep, RunResult, SiteDocument


def sample_result() -> RunResult:
    return RunResult(
        question="请分析官网并给出 GEO 建议",
        routing=RoutingPlan(
            intent="geo_analysis",
            source="llm",
            reason="需要官网分析与 GEO 诊断",
            agents=[
                RoutingStep(name="website_analyst"),
                RoutingStep(name="geo_diagnostic", depends_on=["website_analyst"]),
            ],
        ),
        agent_traces=[
            AgentTrace(agent="website_analyst", status="completed", result={}),
            AgentTrace(agent="geo_diagnostic", status="completed", result={}),
        ],
        agent_results={
            "website_analyst": {
                "brand_positioning": [{"claim": "万悉科技聚焦 GEO"}],
                "missing_information": ["缺少定价信息"],
            },
            "geo_diagnostic": {
                "strengths": [{"finding": "品牌定位较清晰"}],
                "gaps": [{"finding": "FAQ 覆盖不足"}],
                "rubric": {"citation_readiness": "partial"},
            },
        },
        final_answer="## 结论\n\n- 官网已有清晰定位。\n- 建议补充 FAQ。",
    )


def sample_docs() -> list[SiteDocument]:
    return [
        SiteDocument(
            url="https://www.wanxitech.cn/",
            title="万悉科技",
            headings=["万悉科技"],
            text="example",
        )
    ]


def test_markdown_export_contains_required_sections():
    text = build_sample_markdown(sample_result(), sample_docs())
    assert "Routing Decision" in text
    assert "Intermediate Agent Results" in text
    assert "Final Report" in text
    assert "Website Sources" in text
    assert "Website Analyst" in text


def test_pdf_export_returns_pdf_bytes():
    data = build_sample_pdf(sample_result(), sample_docs())
    assert data.startswith(b"%PDF")
    assert len(data) > 1000
