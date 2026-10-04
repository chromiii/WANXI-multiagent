from wanxi_geo.crew_plan import build_task_specs
from wanxi_geo.router import HybridRouter


def test_router_plan_maps_to_crewai_task_dependencies():
    plan = HybridRouter().route(
        "请分析哪些内容适合被 AI 引用，并基于目标客户问题提出内容优化建议"
    )
    specs = build_task_specs(plan)

    assert [spec.name for spec in specs] == [
        "website_analyst",
        "geo_diagnostic",
        "question_generator",
        "content_strategy",
    ]
    assert specs[0].depends_on == ()
    assert specs[1].depends_on == ("website_analyst",)
    assert specs[2].depends_on == ("website_analyst",)
    assert specs[3].depends_on == (
        "website_analyst",
        "geo_diagnostic",
        "question_generator",
    )


def test_single_agent_plan_stays_small_before_synthesizer():
    plan = HybridRouter().route("万悉科技官网目前表达了什么？")
    specs = build_task_specs(plan)
    assert [spec.name for spec in specs] == ["website_analyst"]
