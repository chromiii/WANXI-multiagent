# Demo 录屏脚本

这份脚本用于万悉科技 AI 高级工程师笔试 Project 2 的录屏演示。目标不是逐行解释代码，而是让评审快速看到：**系统会根据用户意图动态选择 Agent，Agent 之间存在真实依赖，最终报告只整合本次实际执行的阶段。**

## 录屏前准备

Windows PowerShell：

```powershell
cd C:\Users\29546\Documents\作业\WANXI-multiagent
.\.venv\Scripts\Activate.ps1
git pull origin main
python -m pytest -q
python -m streamlit run app.py
```

录屏时不要打开或展示 `.env`，避免泄露 API Key。

建议使用已缓存官网数据，除非需要专门展示抓取过程；这样 Demo 更稳定，也更突出 Multi-Agent 调度本身。

---

## 开场

可以直接这样讲：

> 这是我针对万悉科技 Project 2 实现的 CrewAI Multi-Agent GEO Demo。系统不是把几个 Prompt 顺序执行，而是先用 LLM Intent Router 理解用户请求，只选择最小必要的 specialist agents；代码随后做 Agent 白名单校验和依赖补全，再交给 CrewAI 执行。最终报告由 Stage-aware Final Prompt Builder 根据实际执行阶段动态生成，因此未调用的 Agent 不会被 Final Synthesizer 越权替代。

随后在页面上指出：

- LLM Provider / Model
- 目标官网
- 顶部四个运行指标：Routing Source / Selected Specialists / Website Pages / Crew Process
- “执行概览”里的 Router 决策与 Execution Plan
- “Agent 结果”里的业务摘要
- “最终报告”
- “Raw Debug”中仍可检查完整 JSON / Task Trace

---

## Case 1：单 Agent 路由

输入：

```text
万悉科技官网目前表达了什么？
```

重点展示 `Routing Decision`：

```text
source: llm
agents:
- website_analyst
```

讲解：

> 这个问题只要求理解官网当前表达，因此 LLM Router 只选择 website_analyst。Dependency Resolver 不需要补其他业务 Agent。

切到“Agent 结果”，先看默认业务摘要，再按需展开 `website_analyst` 的完整 JSON，简单指出：

- brand_positioning
- products_and_capabilities
- target_customers
- core_messages
- missing_information
- 每条事实带 source_url / evidence

再打开最终报告，强调：

> 因为本次只执行了 website_analyst，最终报告只包含官网现状、引用来源和边界，不会自行生成 GEO 诊断、客户问题或内容策略。

这个 Case 用来证明：**系统不会为了“看起来像 Multi-Agent”而强制调用所有 Agent。**

---

## Case 2：双 Agent 协作

输入：

```text
请基于万悉官网内容，生成一组目标客户可能向 AI 提出的问题。
```

重点展示：

```text
website_analyst
    ↓
question_generator
```

讲解：

> Router 判断用户需要客户问题生成能力；代码自动补上 website_analyst 作为事实基础。question_generator 通过 CrewAI Task.context 使用上游官网画像，而不是重新猜公司信息。

展开 `question_generator`，指出：

- personas
- questions
- stage
- intent
- content_needed
- coverage_notes

再展示 Final Synthesizer：

> Stage-aware Final Prompt Builder 这次只允许“官网现状 + 目标客户问题”两个专业章节，因此不会出现 GEO 诊断或 P0/P1/P2 内容策略。

这个 Case 用来证明：**上游 Agent 的结果真实进入下游 Task，且最终输出结构会随执行阶段变化。**

---

## Case 3：完整 Multi-Agent 协作

输入：

```text
请分析万悉科技官网目前哪些内容适合被 AI 引用，
哪些内容还需要优化，
并基于目标客户问题提出内容策略。
```

重点展示 Router：

```text
website_analyst
├─ geo_diagnostic
├─ question_generator
└─ content_strategy
```

解释依赖：

> website_analyst 提供官网事实基线；geo_diagnostic 和 question_generator 都依赖官网画像；content_strategy 同时消费官网分析、GEO 诊断和客户问题，因此这里形成了完整的多 Agent 协作链。

依次快速展示：

### website_analyst

重点看事实、证据和缺失信息。

### geo_diagnostic

重点看：

- strengths
- gaps
- rubric
- missing_content

说明：

> GEO 诊断区分官网观察、风险解释和未来建议，不把“可能提高引用”写成确定性结果。

### question_generator

重点看：

- 4 类 persona
- 不同 customer stage
- 目标客户自然语言问题

### content_strategy

重点看：

- P0 / P1 / P2
- target_question
- reason
- outline
- evidence_needed

说明：

> Content Strategy 不是凭空想选题，而是把上游 GEO gaps 和客户问题映射成内容优先级，并明确哪些证据需要企业内部补充。

最后展示 Final Synthesizer：

> 由于这次四个 specialist 都执行了，Stage-aware Final Prompt Builder 才允许完整报告包含官网现状、GEO 诊断、目标客户问题和内容策略四部分。

---

## 架构总结

录屏结尾建议用这段：

> 这个 Demo 的核心不是 Agent 数量，而是职责边界和执行图。LLM Router 负责语义意图识别，Dependency Resolver 负责确定性工程约束，CrewAI 负责 Agent、Task 和 Task.context 的实际执行，Stage-aware Final Prompt Builder 决定最终报告允许出现哪些专业结果。这样既保留 LLM 的语义理解能力，也避免用关键词 hardcoding 代替意图识别，或者让最终 Agent 越权重做所有 specialist 的工作。

然后补充工程边界：

> 这是三天笔试规模的工程 Demo，目前官网检索采用 lexical ranking，Crew 使用 sequential process，尚未做线上 citation monitoring、长期 memory 或生产级 hybrid retrieval；这些会作为生产化扩展方向，而不是在笔试版本中过度设计。
