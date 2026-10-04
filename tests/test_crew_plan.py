from wanxi_geo.crew_plan import build_task_specs
from wanxi_geo.crewai_runtime import CrewAIRuntime
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


def test_synthesizer_receives_authoritative_agent_roster():
    description = CrewAIRuntime._synth_task_description(
        "请分析官网并提出内容策略",
        [
            "website_analyst",
            "geo_diagnostic",
            "question_generator",
            "content_strategy",
        ],
    )

    assert "SELECTED_SPECIALIST_COUNT: 4" in description
    assert (
        "SELECTED_SPECIALIST_AGENTS: website_analyst, geo_diagnostic, "
        "question_generator, content_strategy"
    ) in description
    assert "INTEGRATION_AGENT: final_synthesizer" in description
    assert "Do not count final_synthesizer as a selected specialist" in description
