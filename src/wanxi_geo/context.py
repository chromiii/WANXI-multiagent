from __future__ import annotations

import re
from collections import Counter

from .models import SiteDocument


_LATIN = re.compile(r"[a-z0-9][a-z0-9_+.-]*", re.I)
_CHINESE = re.compile(r"[\u4e00-\u9fff]+")


def lexical_terms(text: str) -> list[str]:
    text = text.lower()
    terms = _LATIN.findall(text)
    for span in _CHINESE.findall(text):
        if len(span) == 1:
            terms.append(span)
        else:
            terms.extend(span[i : i + 2] for i in range(len(span) - 1))
    return terms


def rank_documents(
    query: str,
    documents: list[SiteDocument],
    *,
    top_k: int = 6,
) -> list[SiteDocument]:
    if len(documents) <= top_k:
        return documents

    q = Counter(lexical_terms(query))
    scored: list[tuple[float, SiteDocument]] = []
    for doc in documents:
        body = Counter(lexical_terms(doc.text[:12000]))
        head = Counter(lexical_terms(doc.title + " " + " ".join(doc.headings)))
        overlap = sum(min(count, body.get(term, 0)) for term, count in q.items())
        head_overlap = sum(min(count, head.get(term, 0)) for term, count in q.items())
        score = overlap + 3.0 * head_overlap
        scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    chosen = [doc for score, doc in scored[:top_k] if score > 0]
    return chosen or documents[:top_k]


def build_site_context(
    query: str,
    documents: list[SiteDocument],
    *,
    top_k: int = 6,
    per_page_chars: int = 5000,
    total_chars: int = 24000,
) -> str:
    selected = rank_documents(query, documents, top_k=top_k)
    blocks: list[str] = []
    used = 0
    for doc in selected:
        text = doc.text[:per_page_chars]
        block = (
            f"URL: {doc.url}\n"
            f"TITLE: {doc.title}\n"
            f"HEADINGS: {' | '.join(doc.headings[:12])}\n"
            f"CONTENT:\n{text}\n"
        )
        if used + len(block) > total_chars:
            remaining = total_chars - used
            if remaining > 500:
                blocks.append(block[:remaining])
            break
        blocks.append(block)
        used += len(block)
    return "\n--- PAGE ---\n".join(blocks)
