# 提交说明

## Project 2：WANXI Multi-Agent GEO Studio

### 推荐评审入口

优先提供 **Live Web Demo**，让评审直接在浏览器测试 Router、Agent 调度、中间结果和最终报告；GitHub 用于检查代码和架构；录屏视频作为网络异常时的备用材料。

```text
1. Live Web Demo: https://<your-app-name>.streamlit.app
2. GitHub: https://github.com/chromiii/WANXI-multiagent
3. Demo Video: optional backup
```

部署步骤见 `DEPLOY.md`.

GitHub Repository:

```text
https://github.com/chromiii/WANXI-multiagent
```

项目基于万悉科技官网构建一个可本地运行的 CrewAI Multi-Agent GEO 系统，支持根据自然语言请求动态选择不同 Specialist Agents，并展示 Router 决策、Agent 调用链、中间结果与最终报告。

## 核心实现

系统主链：

```text
User Query
    ↓
LLM Intent Router
    ↓
Agent whitelist validation
    ↓
Deterministic Dependency Resolver
    ↓
CrewAI Agents / Tasks / Task.context
    ↓
Stage-aware Final Prompt Builder
    ↓
Final Synthesizer
```

四个业务 Agent：

- `website_analyst`：官网事实抽取、品牌/产品/客户画像与证据整理
- `geo_diagnostic`：GEO citation-readiness 诊断
- `question_generator`：目标客户 AI 提问生成
- `content_strategy`：基于诊断与问题生成 P0/P1/P2 内容路线

另有 `final_synthesizer` 作为整合层，不计入 specialist 数量。

## 设计重点

### 1. LLM-first Router

正常路径由 LLM 做语义意图识别，返回结构化 `intent / agents / reason`。

关键词规则只用于模型不可用或输出非法时的 fallback，不参与正常意图识别。

Router Prompt 不包含 query → Agent 的示例映射，避免通过 few-shot 示例硬编码路由结果。

### 2. Dependency Resolver

Agent 之间的工程依赖由代码确定，而不是让模型猜：

- 下游分析自动依赖 `website_analyst`
- `geo_diagnostic`、`question_generator` 使用官网画像
- `content_strategy` 使用官网分析、GEO 诊断，以及本次被选择时的客户问题结果

### 3. CrewAI 真正执行协作

系统动态创建 CrewAI `Agent` / `Task` / `Crew`，通过 `Task.context` 显式传递上游结果，而不是简单把多个 Prompt 顺序调用。

### 4. Stage-aware Final Synthesis

Final Synthesizer 不拥有无限推理权限。

代码根据本次实际执行的 Agents 动态生成：

- 允许出现的报告章节
- 禁止执行的 specialist 工作
- 章节顺序
- 输出数量上限

因此单 Agent、双 Agent 与完整 Multi-Agent 请求会得到不同的最终报告结构，未调用的专业 Agent 不会被 Synthesizer 越权替代。

### 5. Evidence Grounding

官网事实要求保留 `source_url` 和 evidence。

系统明确区分：

- 官网事实
- GEO 诊断解释
- 未来内容建议

缺少证据的信息保留为 missing information，不自动补全。

## 已验证的三类场景

### Website understanding

```text
万悉科技官网目前表达了什么？
```

执行：

```text
website_analyst
→ final_synthesizer
```

### Customer question generation

```text
请基于万悉官网内容，生成一组目标客户可能向 AI 提出的问题。
```

执行：

```text
website_analyst
→ question_generator
→ final_synthesizer
```

### Full GEO workflow

```text
请分析万悉科技官网目前哪些内容适合被 AI 引用，
哪些内容还需要优化，
并基于目标客户问题提出内容策略。
```

执行：

```text
website_analyst
├─ geo_diagnostic
├─ question_generator
└─ content_strategy
      ↓
final_synthesizer
```

## 本地运行

Python 3.11 / 3.12。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
python -m pytest -q
python -m streamlit run app.py
```

模型支持 OpenAI-compatible endpoint。可以使用本地 Ollama，也可以在本地 `.env` 配置 DeepSeek。

真实 API Key 不应提交到 GitHub。

## 当前工程边界

这是笔试规模 Demo，不声称为完整生产系统。目前主要取舍包括：

- 官网检索采用 lexical ranking，而非 embedding / hybrid retrieval
- Crew 使用 sequential process，优先保证可解释性
- JavaScript 重度页面尚未增加 Playwright fallback
- 暂无长期 memory / checkpoint
- 暂无真实线上 citation monitoring
- GEO rubric 属于内容可引用性诊断，不等价于真实平台曝光结果

## 面试一句话

> 我把语义判断、工程依赖和最终展示拆成三个不同层级：LLM Router 决定用户需要哪些专业能力，代码 Dependency Resolver 保证合法执行图，CrewAI 执行实际协作；最终再由 Stage-aware Prompt Builder 限制 Synthesizer 只能整合本次真实执行过的 Agent 输出。
