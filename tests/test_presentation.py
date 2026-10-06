from wanxi_geo.models import RoutingPlan, RoutingStep
from wanxi_geo.presentation import (
    execution_plan_lines,
    source_label,
    summarize_agent_result,
)


def test_execution_plan_is_human_readable():
    plan = RoutingPlan(
        intent="geo_strategy",
        source="llm",
        reason="semantic route",
        agents=[
            RoutingStep(name="website_analyst"),
            RoutingStep(name="geo_diagnostic", depends_on=["website_analyst"]),
            RoutingStep(name="content_strategy", depends_on=["website_analyst", "geo_diagnostic"]),
        ],
    )

    lines = execution_plan_lines(plan)

    assert "Website Analyst" in lines[0]
    assert "起点任务" in lines[0]
    assert "依赖" in lines[1]
    assert "GEO Diagnostic" in lines[2]
    assert "Final Synthesizer" in lines[-1]


def test_website_summary_prioritizes_business_findings():
    result = {
        "brand_positioning": [{"claim": "品牌定位 A"}, {"claim": "品牌定位 B"}],
        "products_and_capabilities": [{"claim": "能力 A"}, {"claim": "能力 B"}],
        "target_customers": [{"claim": "中国出海企业"}],
        "missing_information": ["缺定价", "缺案例", "缺 SLA", "缺融资"],
    }

    summary = summarize_agent_result("website_analyst", result)

    assert "品牌定位：品牌定位 A" in summary
    assert "产品能力：能力 A" in summary
    assert "目标客户：中国出海企业" in summary
    assert any("缺定价" in item for item in summary)


def test_geo_summary_surfaces_readiness():
    result = {
        "strengths": [{"finding": "实体清晰"}],
        "gaps": [{"finding": "缺量化案例"}],
        "rubric": {"citation_readiness": "partial"},
    }

    summary = summarize_agent_result("geo_diagnostic", result)

    assert "优势：实体清晰" in summary
    assert "缺口：缺量化案例" in summary
    assert "Citation readiness：partial" in summary


def test_strategy_summary_keeps_priority_and_topic():
    result = {
        "recommendations": [
            {
                "priority": "P0",
                "content_type": "Case Study",
                "topic": "量化案例",
            }
        ]
    }

    assert summarize_agent_result("content_strategy", result) == [
        "P0 · Case Study：量化案例"
    ]



def test_source_label_distinguishes_same_title_pages():
    assert (
        source_label("https://example.com/about", "Same Title")
        == "Same Title · /about"
    )
    assert (
        source_label("https://example.com/", "Same Title")
        == "Same Title · 首页"
    )
