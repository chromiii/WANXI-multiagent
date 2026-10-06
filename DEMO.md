# Project 2 Demo 录屏脚本

这份脚本用于万悉科技 AI 高级工程师笔试 Project 2。建议成片控制在 **5–8 分钟**。目标不是逐行讲代码，而是让评审清楚看到四件事：

1. 项目可以本地安装与运行；
2. 系统有明确的 Multi-Agent 框架与职责边界；
3. Agent 不是固定串行调用，而是根据用户请求动态路由并真实传递上下游结果；
4. 最终能输出一个有证据、有诊断、有客户问题、有优先级策略的 GEO 业务结果。

录屏时不要展示 `.env` 或任何真实 API Key。

---

## 0. 录屏前准备

建议先完成一次本地验证：

```powershell
cd C:\Users\29546\Documents\作业\WANXI-multiagent
.\.venv\Scripts\Activate.ps1
git pull origin main
python -m pytest -q
python -m streamlit run app.py
```

建议录屏时使用已抓取好的官网缓存，避免网络波动。只有在介绍 crawler 时说明系统支持“强制刷新官网缓存”即可，不需要现场重新抓全站。

---

# 1. 开场：项目目标与框架（约 45–60 秒）

先打开项目 README 或 Streamlit 首页。

口播：

> 这是我针对万悉科技 Project 2 实现的 WANXI Multi-Agent GEO Studio。项目使用 Python 和 CrewAI 构建，Streamlit 提供本地 Demo 界面，DeepSeek 通过 OpenAI-compatible API 作为当前 LLM 后端。网站数据通过 requests 和 BeautifulSoup 抓取，经过 URL 规范化、正文去重和本地缓存后，再交给不同 Specialist Agents 分析。

然后展示主架构：

```text
User Query
    ↓
LLM Intent Router
    ↓
Agent Whitelist Validation
    ↓
Deterministic Dependency Resolver
    ↓
CrewAI Agents / Tasks / Task.context
    ↓
Stage-aware Final Prompt Builder
    ↓
Final Synthesizer
```

口播：

> 这里我把“语义判断”和“工程依赖”拆开。LLM Router 只负责理解用户需要哪些专业能力；依赖关系不让模型猜，而由代码确定。CrewAI 负责实际 Agent、Task 和 Task.context 的执行。最后再由 Stage-aware Final Prompt Builder 限制最终报告只能包含本次真实执行过的专业阶段。

---

# 2. 安装与启动（约 45–60 秒）

切到 README 的安装部分或 PowerShell。

说明环境：

```text
Python 3.11 / 3.12
CrewAI
Streamlit
Pydantic
requests + BeautifulSoup
DeepSeek / Ollama (OpenAI-compatible)
```

展示安装命令：

```powershell
git clone https://github.com/chromiii/WANXI-multiagent.git
cd WANXI-multiagent

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

Copy-Item .env.example .env
```

解释模型配置，但不要打开真实 `.env`：

> 项目默认支持 OpenAI-compatible endpoint。可以完全本地连接 Ollama，也可以像本次 Demo 一样配置 DeepSeek。API Key 只保存在本地 .env，不进入 GitHub，也不从 Streamlit 页面输入，避免录屏泄露。

再展示测试与启动：

```powershell
python -m pytest -q
python -m streamlit run app.py
```

口播：

> 启动后 Streamlit 页面会显示当前框架、模型、官网地址和最大抓取页面数。

---

# 3. 功能说明（约 60–90 秒）

在 Streamlit 首页讲五块功能。

## 3.1 Website Crawler

侧边栏指出目标官网和 Website Pages。

口播：

> 系统会从首页开始发现同域链接，并继续抓取 About、Blog、News、GEO Center、白皮书和行业报告等页面。Crawler 会做 URL 规范化、tracking 参数清理和正文内容指纹去重，因此 Website Pages 表示实际保留的唯一正文页面数，而不是请求次数。

切到“网站来源”：

> 每个来源都可以直接点击。显示名称优先使用页面 H1/H2；如果没有合适标题，再回退到 URL path，中文 URL 也会解码为可读形式。

## 3.2 LLM Intent Router

切到“执行概览”。

口播：

> Router 使用 LLM 做语义任务识别，输出 intent、需要的 agents 和 reason。Prompt 里没有 query-to-agent 的示例映射，所以正常路径不是关键词 hardcoding。模型输出之后还会经过 Agent 白名单校验。

## 3.3 Dependency Resolver

指向 Execution Plan。

口播：

> 依赖由代码补齐。例如 question_generator 必须基于 website_analyst 的官网画像；content_strategy 需要使用网站分析、GEO 诊断，以及本次如果被选择的客户问题结果。

## 3.4 Specialist Agents

四个业务 Agent：

- `website_analyst`：官网事实、品牌、产品、客户、核心表达、missing information
- `geo_diagnostic`：citation readiness、strengths、gaps、rubric
- `question_generator`：persona、customer stage、自然语言问题、content needed
- `content_strategy`：把上游 gaps + questions 转成 P0/P1/P2 内容路线

口播：

> 每个 Agent 都有独立 role、goal、prompt 和结构化输出，不只是同一个 Prompt 换几个名字。

## 3.5 Stage-aware Final Synthesis

切到“最终报告”。

口播：

> 最终层不会自动重做全部工作。代码会根据本次真正执行过的 Agents 动态组装最终 Prompt。未调用 GEO Diagnostic，就不会出现 GEO 诊断；未调用 Content Strategy，就不会自行生成 P0/P1/P2 路线。这是为了避免 Final Synthesizer 发生角色越权。

---

# 4. Demo Case 1：证明不是固定调用所有 Agent（约 45 秒）

输入：

```text
万悉科技官网目前表达了什么？
```

展示：

```text
Routing Source: llm
Selected Specialists: 1

website_analyst
→ final_synthesizer
```

口播：

> 这个问题只要求理解官网当前表达，所以 Router 只选择 Website Analyst。这里可以证明系统不会为了“看起来像 Multi-Agent”而每次强制执行全部 Agent。

在 Agent 结果里指出：

- 品牌定位
- 产品能力
- 目标客户
- missing information
- source_url / evidence

再切到最终报告：

> 最终报告只出现官网现状、引用来源和边界，不会生成 GEO 诊断、客户问题或内容策略。

---

# 5. Demo Case 2：证明上下游协作（约 45–60 秒）

输入：

```text
请基于万悉官网内容，生成一组目标客户可能向 AI 提出的问题。
```

展示 Execution Plan：

```text
website_analyst
    ↓
question_generator
    ↓
final_synthesizer
```

口播：

> Router 判断需要 Question Generator，代码自动补上 Website Analyst 作为事实基础。Question Generator 通过 CrewAI Task.context 使用上游官网画像，而不是重新猜公司信息。

展示：

- persona
- stage
- query
- intent
- content_needed

最终报告只应包含官网现状 + 客户问题，不出现 GEO 诊断和内容策略。

---

# 6. Demo Case 3：完整 Multi-Agent 主演示（约 2–3 分钟）

输入：

```text
请分析万悉科技官网目前哪些内容适合被 AI 引用，
哪些内容还需要优化，
并基于目标客户问题提出内容策略。
```

## 6.1 Router 与执行图

展示：

```text
website_analyst
├─ geo_diagnostic
├─ question_generator
└─ content_strategy
```

解释：

> Website Analyst 提供官网事实基线；GEO Diagnostic 和 Question Generator 都使用这份画像；Content Strategy 再消费官网分析、GEO gaps 和客户问题，形成真正的协作链。

## 6.2 Website Analyst

快速展示：

- brand positioning
- products and capabilities
- target customers
- missing information
- source URL / evidence

口播：

> 公司事实必须保留来源和 evidence；未披露的信息保持 missing，而不是让模型自动补齐。

## 6.3 GEO Diagnostic

展示：

- strengths
- gaps
- citation readiness rubric

口播：

> 这一层评估内容是否容易被生成式系统理解、抽取和回答，不等于承诺一定获得排名或引用。

## 6.4 Question Generator

展示代表问题，例如：

- 为什么 Google 排名不错，但 ChatGPT 搜不到品牌？
- 制造企业做 GEO 应该从哪里开始？
- GEO 和 SEO 有什么区别？
- GEO 怎么衡量 ROI？

口播：

> 问题不是固定模板，而是基于官网目标客户和信息缺口生成，并按 problem awareness、education、solution discovery、vendor comparison、implementation 和 measurement 等阶段组织。

## 6.5 Content Strategy

展示 P0 / P1 / P2：

```text
P0
- 量化 Case Study
- 服务流程 / 计费 Product Page
- 联系与 GEO 诊断 FAQ

P1
- AI 可见性缺失解释
- 制造企业 GEO 启动指南
- AI Citation 指标框架

P2
- 行业报告公开摘要
- 公司基础信息结构化补充
```

口播：

> 这些选题不是凭空生成，而是把上游 GEO gaps 和客户问题映射成优先级，同时列出 evidence_needed，明确哪些数据必须由企业内部补证。

## 6.6 Final Report

切到最终报告：

> 因为这次四个 specialist 都真实执行了，所以 Stage-aware Final Prompt Builder 才允许最终报告完整包含官网现状、GEO 诊断、客户问题和内容路线。

最后切一下“Raw Debug”：

> 默认页面为了 Demo 可读性展示业务摘要，但完整 Routing JSON、CrewAI Task Trace 和 Agent structured outputs 都保留在 Raw Debug，便于审查。

---

# 7. 工程取舍与边界（约 30–45 秒）

口播：

> 这是三天笔试规模的工程 Demo，所以我优先保证可运行、可解释和职责边界清晰。目前网站检索使用 lexical ranking，不是生产级 embedding/hybrid retrieval；Crew 使用 sequential process，方便展示依赖关系；没有实现线上 citation monitoring、长期 memory 和 JavaScript 页面 Playwright fallback。如果生产化，可以把这些部分分别升级为 hybrid retrieval、并行或 Flow orchestration、checkpoint/memory 和线上监控。

---

# 8. 结尾一句话（约 15 秒）

建议最后直接这样说：

> 这个项目的核心不是 Agent 数量，而是把语义路由、确定性依赖、Agent 专业职责、结构化中间结果和最终整合真正拆开。LLM 决定“用户需要什么能力”，代码保证“任务应该怎么依赖”，CrewAI 执行协作，最终层只整合真实发生过的 specialist 工作。

---

# 录屏检查清单

录之前确认：

- [ ] `git pull origin main`
- [ ] `python -m pytest -q` 通过
- [ ] Streamlit 已重启，页面顶部为新版 UI
- [ ] 不展示 `.env` 和 API Key
- [ ] Website Pages 与网站来源正常
- [ ] 来源名称可读且可点击
- [ ] Case 1 只选 website_analyst
- [ ] Case 2 选 website_analyst + question_generator
- [ ] Case 3 四个 specialist 都执行
- [ ] 最终报告没有未调用 Agent 的越权内容
- [ ] Raw Debug 可展开完整 JSON / Trace
- [ ] 录屏前关闭无关窗口、通知与私人信息
