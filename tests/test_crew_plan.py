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


def _required_section_block(description: str) -> str:
    return description.split("REQUIRED_SECTION_ORDER:\n", 1)[1].split(
        "\n\nFORBIDDEN_WORK:", 1
    )[0]


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


def test_single_agent_synth_contract_omits_unselected_sections():
    description = CrewAIRuntime._synth_task_description(
        "万悉科技官网目前表达了什么？",
        ["website_analyst"],
    )
    sections = _required_section_block(description)

    assert "官网现状 / 关键发现" in sections
    assert "GEO 诊断" not in sections
    assert "目标客户问题" not in sections
    assert "内容优化建议与优先级" not in sections

    assert "Do not perform GEO diagnosis" in description
    assert "Do not generate customer questions" in description
    assert "Do not create content recommendations" in description


def test_question_generation_contract_only_adds_question_section():
    description = CrewAIRuntime._synth_task_description(
        "生成目标客户问题",
        ["website_analyst", "question_generator"],
    )
    sections = _required_section_block(description)

    assert "官网现状 / 关键发现" in sections
    assert "目标客户问题" in sections
    assert "GEO 诊断" not in sections
    assert "内容优化建议与优先级" not in sections

    assert "Show at most 8 representative customer questions." in description
    assert "Do not perform GEO diagnosis" in description
    assert "Do not create content recommendations" in description


def test_full_workflow_synth_contract_contains_all_specialist_sections():
    selected = [
        "website_analyst",
        "geo_diagnostic",
        "question_generator",
        "content_strategy",
    ]
    description = CrewAIRuntime._synth_task_description(
        "完整分析",
        selected,
    )
    sections = _required_section_block(description)

    assert "官网现状 / 关键发现" in sections
    assert "GEO 诊断" in sections
    assert "目标客户问题" in sections
    assert "内容优化建议与优先级" in sections
    assert "FORBIDDEN_WORK:\n- None." in description


def test_synth_expected_output_is_stage_aware():
    output = CrewAIRuntime._synth_expected_output(["website_analyst"])

    assert "官网现状 / 关键发现" in output
    assert "GEO 诊断" not in output
    assert "目标客户问题" not in output
    assert "内容优化建议与优先级" not in output
