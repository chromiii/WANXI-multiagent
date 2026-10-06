# Web Demo 部署：Streamlit Community Cloud

本项目已经是 Streamlit 应用，推荐直接部署到 Streamlit Community Cloud 作为评审主入口。

部署后会获得一个固定的：

```text
https://<your-app-name>.streamlit.app
```

评审可以直接在浏览器输入问题、查看 Router、Agent 执行计划、中间结果和最终报告，不需要本地安装。

## 1. 部署前检查

本地执行：

```powershell
git pull origin main
.\.venv\Scripts\Activate.ps1
python -m pytest -q
python -m streamlit run app.py
```

确认：

- Case 1 只调用 `website_analyst`
- Case 2 调用 `website_analyst + question_generator`
- Case 3 完整调用 4 个 specialist
- “网站来源”可以点击
- 不存在 API Key 硬编码

## 2. 创建 Streamlit Community Cloud App

打开 Streamlit Community Cloud，并使用 GitHub 登录。

创建 App 时填写：

```text
Repository: chromiii/WANXI-multiagent
Branch: main
Main file path: app.py
```

在 Advanced settings 中**明确选择**：

```text
Python: 3.12
```

不要选择 3.14。当前 CrewAI 依赖链会通过 ChromaDB / Pydantic v1 触发兼容性错误。

注意：Streamlit Community Cloud 的 Python 版本在 App 创建后不能原地修改。如果已经用错误版本部署，需要删除该 App 后重新部署，并重新选择 Python 3.12。

## 3. 配置 Secrets

不要上传本地 `.env`。

在 Streamlit Cloud 的 Advanced settings / Secrets 中粘贴类似：

```toml
TARGET_URL = "https://www.wanxitech.cn/"
MAX_PAGES = 17
REQUEST_TIMEOUT = 12
CACHE_PATH = ".cache/site_docs.json"

LLM_PROVIDER = "deepseek"
LLM_BASE_URL = "https://api.deepseek.com/v1"
LLM_MODEL = "deepseek-chat"
LLM_API_KEY = "YOUR_DEMO_DEEPSEEK_API_KEY"
LLM_TIMEOUT = 120
LLM_TEMPERATURE = 0.2

CREWAI_VERBOSE = false
```

推荐使用专门用于笔试 Demo 的 API Key，而不是日常主 Key。

## 4. Deploy

点击 Deploy。

部署完成后，先测试：

### Case 1

```text
万悉科技官网目前表达了什么？
```

确认：

```text
Routing Source = llm
Selected Specialists = 1
website_analyst
```

### Case 3

```text
请分析万悉科技官网目前哪些内容适合被 AI 引用，
哪些内容还需要优化，
并基于目标客户问题提出内容策略。
```

确认：

```text
website_analyst
geo_diagnostic
question_generator
content_strategy
```

并检查最终报告、网站来源和 Raw Debug。

## 5. 提交时怎么放

建议最终提交顺序：

```text
1. Live Web Demo
2. GitHub Repository
3. Demo Video（可选 / 备用）
```

例如：

```text
Live Demo:
https://<your-app-name>.streamlit.app

GitHub:
https://github.com/chromiii/WANXI-multiagent
```

网页 Demo 应作为主入口；视频只需要作为网络异常或评审不方便现场运行时的备用材料。

## 6. API 成本与公开访问

如果网页公开，任何访问者都可能触发 LLM 请求并消耗 API 额度。

建议：

- 使用独立 Demo Key；
- 控制 Key 的可用余额或生命周期；
- 提交期结束后关闭 App 或撤销 Demo Key；
- 不要把 Key 写进 GitHub、README、代码或截图。

## 7. 缓存说明

Streamlit Cloud 的运行实例不应被视为永久磁盘。

本项目的 `.cache/site_docs.json` 用于运行实例内减少重复抓取；实例重启后可以重新抓取官网。

如果部署 Demo 以稳定性优先，可以：

- 首次启动后先跑一次 Case；
- 后续评审访问复用当前实例缓存；
- 不必在 Demo 中勾选“强制刷新官网缓存”。

## 8. 故障排查

如果部署失败：

### `pydantic.v1.errors.ConfigError` / traceback 中出现 `python3.14`

这通常表示 App 被部署在 Python 3.14。请删除当前 App 并重新部署，在 Advanced settings 中选择 Python 3.12。

项目的 `pyproject.toml` 已显式限制为 Python 3.12，以便错误版本在安装阶段就被拒绝。

### `ModuleNotFoundError: wanxi_geo`

确认根目录的 `requirements.txt` 包含：

```text
-e .
```

本项目使用 `src/` layout，Cloud 必须先把当前仓库安装成 Python package，`app.py` 才能导入 `wanxi_geo`。

### 依赖安装失败

确认根目录同时存在：

```text
requirements.txt
pyproject.toml
```

### DeepSeek 调用失败

检查 Secrets：

```text
LLM_PROVIDER
LLM_BASE_URL
LLM_MODEL
LLM_API_KEY
```

### 页面能开但运行失败

在 Streamlit App 的 Manage app / Logs 查看服务器日志。

### 官网抓取失败

可再次运行，或检查官网是否临时限制请求。当前 crawler 对不可读页面会跳过，只保留成功解析的正文页面。
