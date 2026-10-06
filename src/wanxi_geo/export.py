from __future__ import annotations

from html import escape
from io import BytesIO
import json
import re
from typing import Iterable

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from .models import RunResult, SiteDocument
from .presentation import (
    AGENT_PURPOSES,
    agent_label,
    execution_plan_lines,
    source_label,
    summarize_agent_result,
)


def build_sample_markdown(result: RunResult, documents: Iterable[SiteDocument]) -> str:
    lines: list[str] = [
        "# WANXI Project 2 · Sample Output",
        "",
        f"- Input: {result.question}",
        f"- Framework: {result.framework}",
        f"- Crew process: {result.crew_process}",
        f"- Routing source: {result.routing.source}",
        "",
        "## Routing Decision",
        "",
        f"- Intent: `{result.routing.intent}`",
        f"- Reason: {result.routing.reason}",
        "",
        "## Called Agents & Execution Plan",
        "",
    ]

    for line in execution_plan_lines(result.routing):
        lines.append(f"- {line}")

    lines.extend(["", "## Intermediate Agent Results", ""])

    for step in result.routing.agents:
        payload = result.agent_results.get(step.name, {})
        lines.extend(
            [
                f"### {agent_label(step.name)}",
                "",
                AGENT_PURPOSES.get(step.name, ""),
                "",
            ]
        )
        highlights = summarize_agent_result(step.name, payload)
        if highlights:
            lines.extend(f"- {item}" for item in highlights)
        else:
            lines.append("- Agent completed; inspect structured output below.")

        lines.extend(
            [
                "",
                "<details>",
                "<summary>Structured result</summary>",
                "",
                "```json",
                json.dumps(payload, ensure_ascii=False, indent=2),
                "```",
                "",
                "</details>",
                "",
            ]
        )

    lines.extend(
        [
            "## Final Report",
            "",
            result.final_answer.strip(),
            "",
            "## Website Sources",
            "",
        ]
    )

    seen: set[str] = set()
    for doc in documents:
        if doc.url in seen:
            continue
        seen.add(doc.url)
        lines.append(f"- [{source_label(doc.url, doc.title, doc.headings)}]({doc.url})")

    lines.append("")
    return "\n".join(lines)


def build_sample_pdf(result: RunResult, documents: Iterable[SiteDocument]) -> bytes:
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="WANXI Project 2 Sample Output",
        author="WANXI Multi-Agent GEO Studio",
    )

    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "CJKBody",
        parent=styles["BodyText"],
        fontName="STSong-Light",
        fontSize=9.5,
        leading=15,
        spaceAfter=5,
    )
    small = ParagraphStyle(
        "CJKSmall",
        parent=body,
        fontSize=8.3,
        leading=12,
        textColor="#555555",
    )
    h1 = ParagraphStyle(
        "CJKH1",
        parent=styles["Heading1"],
        fontName="STSong-Light",
        fontSize=18,
        leading=24,
        spaceAfter=10,
        alignment=TA_CENTER,
    )
    h2 = ParagraphStyle(
        "CJKH2",
        parent=styles["Heading2"],
        fontName="STSong-Light",
        fontSize=13,
        leading=18,
        spaceBefore=10,
        spaceAfter=6,
    )
    h3 = ParagraphStyle(
        "CJKH3",
        parent=styles["Heading3"],
        fontName="STSong-Light",
        fontSize=11,
        leading=16,
        spaceBefore=7,
        spaceAfter=4,
    )

    story = [
        Paragraph("WANXI Project 2 - Sample Output", h1),
        Paragraph(f"<b>Input:</b> {escape(result.question)}", body),
        Paragraph(
            f"<b>Framework:</b> {escape(result.framework)} &nbsp;&nbsp; "
            f"<b>Process:</b> {escape(result.crew_process)}",
            small,
        ),
        Paragraph(
            f"<b>Routing source:</b> {escape(result.routing.source)}",
            small,
        ),
        Spacer(1, 6),
        Paragraph("Routing Decision", h2),
        Paragraph(f"<b>Intent:</b> {escape(result.routing.intent)}", body),
        Paragraph(f"<b>Reason:</b> {escape(result.routing.reason)}", body),
        Paragraph("Called Agents & Execution Plan", h2),
    ]

    for line in execution_plan_lines(result.routing):
        story.append(Paragraph("• " + escape(line), body))

    story.append(Paragraph("Intermediate Agent Results", h2))
    for step in result.routing.agents:
        payload = result.agent_results.get(step.name, {})
        story.append(Paragraph(escape(agent_label(step.name)), h3))
        purpose = AGENT_PURPOSES.get(step.name)
        if purpose:
            story.append(Paragraph(escape(purpose), small))

        highlights = summarize_agent_result(step.name, payload)
        if highlights:
            for item in highlights:
                story.append(Paragraph("• " + escape(item), body))
        else:
            story.append(Paragraph("Agent completed; no compact summary field available.", body))

    story.append(Paragraph("Final Report", h2))
    story.extend(_markdown_to_flowables(result.final_answer, body, h2, h3))

    story.append(Paragraph("Website Sources", h2))
    seen: set[str] = set()
    for doc_item in documents:
        if doc_item.url in seen:
            continue
        seen.add(doc_item.url)
        label = source_label(doc_item.url, doc_item.title, doc_item.headings)
        story.append(
            Paragraph(
                f"• {escape(label)}<br/><font size='7'>{escape(doc_item.url)}</font>",
                body,
            )
        )

    doc.build(story)
    return buffer.getvalue()


def _markdown_to_flowables(
    markdown: str,
    body: ParagraphStyle,
    h2: ParagraphStyle,
    h3: ParagraphStyle,
) -> list:
    flowables: list = []
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            flowables.append(Spacer(1, 3))
            continue

        if line.startswith("### "):
            flowables.append(Paragraph(escape(line[4:]), h3))
            continue
        if line.startswith("## "):
            flowables.append(Paragraph(escape(line[3:]), h2))
            continue
        if line.startswith("# "):
            flowables.append(Paragraph(escape(line[2:]), h2))
            continue

        bullet = re.match(r"^[-*]\s+(.*)$", line)
        if bullet:
            flowables.append(Paragraph("• " + _inline_markdown(bullet.group(1)), body))
            continue

        numbered = re.match(r"^(\d+)\.\s+(.*)$", line)
        if numbered:
            flowables.append(
                Paragraph(
                    f"{numbered.group(1)}. " + _inline_markdown(numbered.group(2)),
                    body,
                )
            )
            continue

        flowables.append(Paragraph(_inline_markdown(line), body))
    return flowables


def _inline_markdown(text: str) -> str:
    escaped = escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"`(.+?)`", r"<font name='Courier'>\1</font>", escaped)
    return escaped
