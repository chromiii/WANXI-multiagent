from __future__ import annotations

from typing import Any
from urllib.parse import unquote, urlparse

from .models import RoutingPlan


AGENT_LABELS: dict[str, str] = {
    "website_analyst": "Website Analyst · 官网分析",
    "geo_diagnostic": "GEO Diagnostic · 引用就绪度诊断",
    "question_generator": "Question Generator · 客户问题生成",
    "content_strategy": "Content Strategy · 内容策略",
    "final_synthesizer": "Final Synthesizer · 最终整合",
}

AGENT_PURPOSES: dict[str, str] = {
    "website_analyst": "从官网证据中提取品牌、产品、目标客户、核心表达与信息缺口。",
    "geo_diagnostic": "评估内容的答案可抽取性、证据密度、语义一致性与引用就绪度。",
    "question_generator": "基于官网画像生成目标客户在 AI 搜索场景中的代表性问题。",
    "content_strategy": "把 GEO 缺口与客户问题转成带优先级的内容路线。",
    "final_synthesizer": "仅整合本次实际执行的 specialist 输出，不替代未调用 Agent。",
}


def agent_label(name: str) -> str:
    return AGENT_LABELS.get(name, name)


def execution_plan_lines(plan: RoutingPlan) -> list[str]:
    lines: list[str] = []
    for index, step in enumerate(plan.agents, start=1):
        if step.depends_on:
            deps = ", ".join(agent_label(dep) for dep in step.depends_on)
            dependency = f"依赖：{deps}"
        else:
            dependency = "起点任务"
        lines.append(f"{index}. {agent_label(step.name)} — {dependency}")
    lines.append(
        f"{len(plan.agents) + 1}. {agent_label('final_synthesizer')} — "
        "整合本次已执行阶段"
    )
    return lines


def summarize_agent_result(name: str, result: dict[str, Any]) -> list[str]:
    if name == "website_analyst":
        return _website_summary(result)
    if name == "geo_diagnostic":
        return _geo_summary(result)
    if name == "question_generator":
        return _question_summary(result)
    if name == "content_strategy":
        return _strategy_summary(result)
    return []


def _dict_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _take_field(items: list[dict[str, Any]], field: str, limit: int) -> list[str]:
    values: list[str] = []
    for item in items:
        value = item.get(field)
        if isinstance(value, str) and value.strip():
            values.append(value.strip())
        if len(values) >= limit:
            break
    return values


def _website_summary(result: dict[str, Any]) -> list[str]:
    highlights: list[str] = []

    for claim in _take_field(_dict_items(result.get("brand_positioning")), "claim", 2):
        highlights.append(f"品牌定位：{claim}")

    for claim in _take_field(
        _dict_items(result.get("products_and_capabilities")), "claim", 2
    ):
        highlights.append(f"产品能力：{claim}")

    customers = _take_field(_dict_items(result.get("target_customers")), "claim", 1)
    if customers:
        highlights.append(f"目标客户：{customers[0]}")

    missing = _strings(result.get("missing_information"))
    if missing:
        highlights.append("主要信息缺口：" + "；".join(missing[:3]))

    return highlights[:6]


def _geo_summary(result: dict[str, Any]) -> list[str]:
    highlights: list[str] = []

    for finding in _take_field(_dict_items(result.get("strengths")), "finding", 3):
        highlights.append(f"优势：{finding}")

    for finding in _take_field(_dict_items(result.get("gaps")), "finding", 3):
        highlights.append(f"缺口：{finding}")

    rubric = result.get("rubric")
    if isinstance(rubric, dict):
        readiness = rubric.get("citation_readiness")
        if isinstance(readiness, str) and readiness.strip():
            highlights.append(f"Citation readiness：{readiness.strip()}")

    return highlights[:7]


def _question_summary(result: dict[str, Any]) -> list[str]:
    highlights: list[str] = []

    personas = _take_field(_dict_items(result.get("personas")), "persona", 3)
    if personas:
        highlights.append("目标角色：" + "；".join(personas))

    for query in _take_field(_dict_items(result.get("questions")), "query", 5):
        highlights.append(f"代表问题：{query}")

    return highlights[:6]


def _strategy_summary(result: dict[str, Any]) -> list[str]:
    highlights: list[str] = []

    for item in _dict_items(result.get("recommendations"))[:6]:
        priority = str(item.get("priority") or "").strip()
        content_type = str(item.get("content_type") or "").strip()
        topic = str(item.get("topic") or "").strip()
        label = " · ".join(part for part in [priority, content_type] if part)
        if topic:
            highlights.append(f"{label}：{topic}" if label else topic)

    return highlights



def source_label(
    url: str,
    title: str = "",
    headings: list[str] | None = None,
) -> str:
    parsed = urlparse(url)
    raw_path = parsed.path or "/"
    decoded_path = unquote(raw_path)
    location = "首页" if decoded_path == "/" else decoded_path

    heading = ""
    for item in headings or []:
        cleaned = " ".join(item.split()).strip()
        if cleaned:
            heading = cleaned
            break

    if heading:
        base = heading[:72] + ("…" if len(heading) > 72 else "")
    elif decoded_path == "/":
        base = "万悉科技官网"
    else:
        base = title.strip() if title and title.strip() else (parsed.netloc or url)

    return f"{base} · {location}"
