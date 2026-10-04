from wanxi_geo.router import HybridRouter


def names(plan):
    return [step.name for step in plan.agents]


class StubLLM:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = 0
        self.system_prompt = None
        self.user_prompt = None

    def chat_json(self, system_prompt, user_prompt):
        self.calls += 1
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        if self.error is not None:
            raise self.error
        return self.response


def test_llm_is_primary_router_for_website_understanding():
    llm = StubLLM(
        {
            "intent": "website_understanding",
            "agents": ["website_analyst"],
            "reason": "用户仅要求理解官网当前表达的信息。",
        }
    )

    plan = HybridRouter(llm).route("万悉科技官网目前表达了什么？")

    assert llm.calls == 1
    assert names(plan) == ["website_analyst"]
    assert plan.source == "llm"


def test_llm_semantic_router_can_select_multiple_specialists():
    llm = StubLLM(
        {
            "intent": "geo_content_strategy",
            "agents": [
                "geo_diagnostic",
                "question_generator",
                "content_strategy",
            ],
            "reason": "请求同时包含诊断、目标客户问题和内容策略。",
        }
    )

    plan = HybridRouter(llm).route("请分析官网并基于客户需求提出后续内容方向。")

    assert names(plan) == [
        "website_analyst",
        "geo_diagnostic",
        "question_generator",
        "content_strategy",
    ]
    assert plan.agents[-1].depends_on == [
        "website_analyst",
        "geo_diagnostic",
        "question_generator",
    ]
    assert plan.source == "llm"


def test_unknown_llm_agent_is_rejected_and_rules_are_fallback():
    llm = StubLLM(
        {
            "intent": "invalid",
            "agents": ["made_up_agent"],
            "reason": "invalid",
        }
    )

    plan = HybridRouter(llm).route("万悉科技官网目前表达了什么？")

    assert llm.calls == 1
    assert names(plan) == ["website_analyst"]
    assert plan.source == "rules_fallback"


def test_llm_failure_uses_rule_fallback():
    llm = StubLLM(error=RuntimeError("offline"))

    plan = HybridRouter(llm).route("目标客户会怎么问 AI？请给我用户问题列表")

    assert names(plan) == ["website_analyst", "question_generator"]
    assert plan.source == "rules_fallback"
    assert plan.agents[1].depends_on == ["website_analyst"]


def test_no_llm_and_no_rule_match_uses_safe_fallback():
    plan = HybridRouter().route("帮我看看这个")

    assert names(plan) == ["website_analyst"]
    assert plan.source == "safe_fallback"


def test_router_prompt_contains_no_query_to_agent_examples():
    prompt = HybridRouter._router_prompt()

    assert "例如" not in prompt
    assert "example" not in prompt.lower()
    assert "->" not in prompt
    assert "官网表达了什么" not in prompt
    assert "哪些内容适合被 AI 引用" not in prompt


def test_content_strategy_dependency_is_added_by_code():
    llm = StubLLM(
        {
            "intent": "content_strategy",
            "agents": ["content_strategy"],
            "reason": "用户要求内容策略。",
        }
    )

    plan = HybridRouter(llm).route("请给出后续内容方向")

    assert names(plan) == [
        "website_analyst",
        "geo_diagnostic",
        "content_strategy",
    ]
    assert plan.agents[-1].depends_on == [
        "website_analyst",
        "geo_diagnostic",
    ]
