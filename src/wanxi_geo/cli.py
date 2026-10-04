from __future__ import annotations

import argparse
import json

from .config import get_settings
from .crawler import WebsiteCrawler
from .orchestrator import AgentOrchestrator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WANXI local CrewAI GEO multi-agent demo")
    parser.add_argument("question", help="Question for the GEO multi-agent system")
    parser.add_argument("--url", default=None, help="Target website URL")
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--refresh", action="store_true", help="Ignore website cache")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = get_settings()
    target_url = args.url or settings.target_url
    max_pages = args.max_pages or settings.max_pages

    crawler = WebsiteCrawler(timeout=settings.request_timeout)
    documents = crawler.load_or_crawl(
        target_url,
        max_pages=max_pages,
        cache_path=settings.cache_path,
        refresh=args.refresh,
    )

    result = AgentOrchestrator(settings).run(args.question, documents)

    print("\n=== Framework ===")
    print(f"{result.framework} / {result.crew_process}")
    print("\n=== Routing ===")
    print(json.dumps(result.routing.model_dump(), ensure_ascii=False, indent=2))
    print("\n=== Agent Traces ===")
    print(json.dumps([t.model_dump() for t in result.agent_traces], ensure_ascii=False, indent=2))
    print("\n=== Final Answer ===")
    print(result.final_answer)


if __name__ == "__main__":
    main()
