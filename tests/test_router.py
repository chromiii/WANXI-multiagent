from wanxi_geo.router import HybridRouter


def names(plan):
    return [step.name for step in plan.agents]


def test_website_question_calls_only_website_analyst():
    plan = HybridRouter().route("万悉科技官网目前表达了什么？")
    assert names(plan) == ["website_analyst"]
    assert plan.source == "rules"


def test_customer_question_generation_adds_website_dependency():
    plan = HybridRouter().route("目标客户会怎么问 AI？请给我用户问题列表")
    assert names(plan) == ["website_analyst", "question_generator"]
    assert plan.agents[1].depends_on == ["website_analyst"]


def test_content_strategy_adds_diagnosis_dependency():
    plan = HybridRouter().route("官网应该写什么 FAQ 和 Blog？给出内容策略")
    assert names(plan) == ["website_analyst", "geo_diagnostic", "content_strategy"]
    assert "geo_diagnostic" in plan.agents[-1].depends_on


def test_compound_question_routes_multiple_agents():
    plan = HybridRouter().route(
        "请分析哪些内容适合被 AI 引用，并基于目标客户问题提出内容优化建议"
    )
    assert names(plan) == [
        "website_analyst",
        "geo_diagnostic",
        "question_generator",
        "content_strategy",
    ]
