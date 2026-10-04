from __future__ import annotations

import streamlit as st

from wanxi_geo.config import get_settings
from wanxi_geo.crawler import WebsiteCrawler
from wanxi_geo.orchestrator import AgentOrchestrator


st.set_page_config(page_title="WANXI GEO Agent Studio", page_icon="🧭", layout="wide")

settings = get_settings()
st.title("WANXI GEO Agent Studio")
st.caption("Project 2 · CrewAI · LLM-first Hybrid Router · GEO website analysis · local deploy")

with st.sidebar:
    st.subheader("运行配置")
    target_url = st.text_input("目标官网", value=settings.target_url)
    max_pages = st.number_input(
        "最多抓取页面", min_value=1, max_value=30, value=settings.max_pages
    )
    refresh = st.checkbox("强制刷新官网缓存", value=False)
    st.divider()
    st.write("**Framework:** CrewAI")
    st.write(f"**LLM Provider:** {settings.llm_provider}")
    st.write(f"**Model:** {settings.llm_model}")
    st.caption("模型配置请在 .env 中修改；页面不接收 API Key，避免录屏时泄露。")

examples = [
    "万悉科技官网目前表达了什么？",
    "请基于万悉官网内容，生成一组目标客户可能向 AI 提出的问题。",
    "请分析万悉科技官网目前哪些内容适合被 AI 引用，哪些内容还需要优化，并基于目标客户问题提出内容策略。",
]

if "question" not in st.session_state:
    st.session_state.question = examples[2]
if "history" not in st.session_state:
    st.session_state.history = []

selected = st.selectbox("Demo Case", examples, index=2)
if st.button("载入示例问题"):
    st.session_state.question = selected

question = st.text_area(
    "输入问题",
    key="question",
    height=120,
    placeholder="例如：请分析官网哪些内容适合被 AI 引用，并给出 GEO 优化建议。",
)

if st.button("开始分析", type="primary", use_container_width=True):
    if not question.strip():
        st.warning("请先输入问题。")
        st.stop()

    try:
        with st.status("正在准备网站知识并执行 CrewAI…", expanded=True) as status:
            st.write("1/3 读取官网或本地缓存")
            crawler = WebsiteCrawler(timeout=settings.request_timeout)
            documents = crawler.load_or_crawl(
                target_url,
                max_pages=int(max_pages),
                cache_path=settings.cache_path,
                refresh=refresh,
            )
            st.write(f"已加载 {len(documents)} 个页面。")

            st.write("2/3 LLM Intent Router 语义规划 + 代码依赖解析")
            orchestrator = AgentOrchestrator(settings)

            st.write("3/3 CrewAI 创建 Agent / Task / Crew 并执行")
            result = orchestrator.run(question.strip(), documents)
            status.update(label="分析完成", state="complete")

        st.session_state.history.append(
            {"question": question.strip(), "result": result.model_dump()}
        )

        st.success(f"{result.framework} · Process: {result.crew_process}")
        tab1, tab2, tab3, tab4 = st.tabs(
            ["Router / Crew Trace", "中间结果", "最终报告", "网站来源"]
        )

        with tab1:
            st.subheader("Routing Decision")
            st.json(result.routing.model_dump())
            st.subheader("CrewAI Agent / Task Trace")
            for trace in result.agent_traces:
                icon = "✅" if trace.status == "completed" else "❌"
                with st.expander(f"{icon} {trace.agent}", expanded=True):
                    if trace.error:
                        st.error(trace.error)
                    else:
                        st.json(trace.result)

        with tab2:
            st.json(result.agent_results)

        with tab3:
            st.markdown(result.final_answer)

        with tab4:
            for doc in documents:
                st.markdown(f"- [{doc.title or doc.url}]({doc.url})")

    except Exception as exc:
        st.error(str(exc))
        st.info(
            "如果使用 Ollama，请确认 Ollama 已启动且已拉取 .env 中配置的模型；"
            "如果使用 DeepSeek，请检查 LLM_BASE_URL / LLM_MODEL / LLM_API_KEY。"
        )

if st.session_state.history:
    with st.expander("本次会话历史", expanded=False):
        for i, item in enumerate(reversed(st.session_state.history[-5:]), start=1):
            st.markdown(f"**{i}. {item['question']}**")
            routing = item["result"]["routing"]
            st.code(
                "Router -> "
                + " -> ".join(step["name"] for step in routing["agents"])
                + " -> final_synthesizer"
            )
