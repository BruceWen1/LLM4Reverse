<p align="right">
  <a href="README.md">English</a> | 中文
</p>

# 🔍 LLM4Reverse

**LLM4Reverse** 是一个面向专家用户的 **前端逆向工程** 工具箱，结合 **大语言模型（LLM）** 与轻量智能体实现自动化的证据采集、JavaScript 分析与推理报告生成。

![License](https://img.shields.io/badge/license-MIT-blue.svg)
 ![Python](https://img.shields.io/badge/python-3.10%2B-blue)
 ![Status](https://img.shields.io/badge/status-alpha-orange)

------

## ✨ 功能特性

- **无头浏览器采集**（Playwright）：抓取网络请求（方法/URL/状态/请求体片段）、控制台日志与精简 DOM 片段。
- **JS 美化与提示**：对压缩/混淆 JS 进行格式化，并以正则提示 token-like 字符串、`/api/...` 路径、`fetch`/XHR URL。
- **可选 AST 抽取**：通过 Node + esprima 提取标识符、字符串常量与隐藏端点。
- **LLM 推理**：将证据输入 OpenAI 兼容模型，输出简明的 Markdown 逆向报告。
- **CLI 优先**：一条命令完成常用流程；按需安装可选组件。

------

## 🧱 架构与项目结构

**运行时数据流**

```text
CLI (llm4reverse)
      │
      ├── BrowserTool (Playwright)
      │      └─ 采集：requests(method/url/status/postDataSnippet), console, domSnippet
      │
      ├── JSBeautifyTool (jsbeautifier + regex)
      │      └─ 输出：beautified, token-like, "/api/...", fetch/xhr
      │
      ├── JS AST (可选；Node + esprima)
      │      └─ 输出：identifiers, stringLiterals, fetchUrls, xhrUrls
      │
      └── ReverseAgent (可选 LLM)
             └─ 输入：evidence JSON → 输出：reverse_report.md
```

**仓库目录**

```text
LLM4Reverse/
├─ llm4reverse/
│  ├─ cli.py               # CLI 入口与参数解析
│  ├─ agent.py             # ReverseAgent：提示词 + 推理
│  ├─ llm_client.py        # 极简 OpenAI 兼容客户端
│  ├─ report.py            # 产物写入（json/md）
│  └─ tools/
│     ├─ browser.py        # Playwright 抓取封装
│     ├─ js_beautify.py    # jsbeautifier + 正则提示
│     ├─ static_audit.py   # 目录级静态审计（fetch/xhr/axios/$.ajax + 轻量常量传播）
│     └─ js_ast.py         # Node + esprima（内嵌脚本）
├─ scripts/
│  └─ install_playwright.sh
├─ README.md               # 英文版说明
├─ README_zh.md            # 中文版说明
├─ pyproject.toml
├─ requirements.txt
└─ LICENSE
```

**设计原则**

- 专家优先：避免“魔法”，小而清晰、注释充分的模块。
- 可选依赖：Playwright/Node 按需启用；缺失时优雅退化并明确报错。
- 可复现输出：产物以稳定字段的 JSON/MD 为主，便于后续工具消费。
- 默认安全：DOM 截断，请求体只保存片段；LLM 使用为可选项。

------

## ⚙️ 环境要求

- Python 3.10+
- 可选：Node 18+（用于 `--ast`）
- 可选：Playwright 浏览器（Chromium），通过 `llm4reverse playwright-install` 安装
- 可选：OpenAI 兼容 API（`OPENAI_API_KEY`）

------

## 📦 安装

```bash
# 克隆并以可编辑模式安装（推荐二次开发）
git clone https://github.com/BruceWen1/LLM4Reverse.git
cd LLM4Reverse
pip install -e .

# 若计划进行页面采集，安装 Playwright 浏览器
llm4reverse playwright-install
```

在 **.env** 或 shell 中设置环境变量：

```text
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=      # 可选，用于 Azure-OpenAI 或自建兼容端点
OPENAI_MODEL=gpt-4o
```

启用 AST：`npm install -g esprima`（或在项目目录局部安装）。

------

## 🚀 快速开始

```bash
# 仅采集证据（不调用 LLM）
llm4reverse reverse --url https://example.com --no-llm

# 对本地 JS 文件进行美化/扫描\ nllm4reverse reverse --url https://example.com \
                   --jsfile ./app.min.js --no-llm

# 页面加载后触发一次点击
llm4reverse reverse --url https://example.com --click "#login" --no-llm

# 启用 AST（需要 Node + esprima）
llm4reverse reverse --url https://example.com \
                   --jsfile ./app.min.js --ast --no-llm

# 完整流程（含 LLM 摘要）
export OPENAI_API_KEY=sk-...
llm4reverse reverse --url https://example.com \
                   --jsfile ./app.min.js --ast
```

输出（默认 **./artifacts**）：

```
reverse_report.md   # LLM 摘要（未使用 --no-llm 时生成）
static_findings.json # 静态审计接口候选（使用 static-audit 时）
static_report.md     # 静态审计 LLM 摘要（使用 --with-llm 时）
capture.json        # 请求 / 控制台 / DOM 片段
js_beautify.json    # 美化结果 + 正则提示（提供 --jsfile 时）
js_ast.json         # AST 摘要（提供 --ast 时）
```

------

## 🧰 命令行参考

```text
llm4reverse playwright-install
    安装 Playwright 浏览器（Chromium）。

llm4reverse reverse --url URL [options]
    --click CSS      页面加载后点击一次
    --wait-ms INT    加载/点击后的等待毫秒数（默认 2500）
    --jsfile FILE    本地 JS 文件（美化/扫描）
    --ast            启用 Node + esprima AST
    --no-browser     跳过 Playwright 采集
    --show-browser   以非无头模式运行
    --outdir DIR     输出目录（默认 ./artifacts）
    --model NAME     覆盖 OPENAI_MODEL
    --base-url URL   覆盖 OPENAI_BASE_URL
    --no-llm         仅保存证据，不进行 LLM 推理

llm4reverse static-audit --path PATH [options]
    --include GLOB   可重复；默认包含 js/mjs/ts/jsx/tsx
    --exclude GLOB   可重复；排除匹配的文件
    --max-files N    最大扫描文件数（默认 1000）
    --with-llm       将静态结果交给 Agent 生成 static_report.md
    --outdir DIR     输出目录（默认 ./artifacts）
    --model NAME     覆盖 OPENAI_MODEL（与 --with-llm 一起使用）
    --base-url URL   覆盖 OPENAI_BASE_URL（与 --with-llm 一起使用）
```

返回码：0 = 成功；2 = jsfile 不存在；其他 = 错误。

------

## 📁 模块职责（详细）

- `llm4reverse/cli.py`：CLI 入口；参数映射到工作流；Playwright 安装；产物写入。
- `llm4reverse/agent.py`：内置系统提示词；将证据发送给 LLM；返回 Markdown 文本。
- `llm4reverse/llm_client.py`：极简 OpenAI 兼容客户端；遵循 `OPENAI_API_KEY/BASE_URL/MODEL`。
- `llm4reverse/report.py`：统一写入 `capture.json`、`js_beautify.json`、`js_ast.json`、`reverse_report.md`。
- `llm4reverse/tools/browser.py`：Playwright 抓取；尽力关联响应状态；DOM 美化与截断。
- `llm4reverse/tools/js_beautify.py`：JS 美化；保守正则提示（token/auth/jwt、`/api/...`、fetch/xhr）。
- `llm4reverse/tools/js_ast.py`：运行小型 Node 脚本（需要 `esprima`）；返回 identifiers/literals/URLs。

编码规范：Google 风格 docstring、类型注解、明确错误信息；函数保持短小；JSON 中以结构化错误返回。

------

## 🔧 配置与开关

环境变量（shell 或 `.env`）：

```text
OPENAI_API_KEY   # 启用 LLM 推理所必需
OPENAI_BASE_URL  # 可选，自定义 OpenAI 兼容端点
OPENAI_MODEL     # 可选，默认：gpt-4o
```

运行时常用开关：

- `--no-llm`：关闭 LLM 推理，仅保存证据。
- `--no-browser` / `--show-browser`：跳过浏览器抓取或以可视化模式调试。
- `--wait-ms`：若页面操作后延迟发起 XHR，可适当增大。
- `--ast`：需要 Node 18+ 与 `npm i -g esprima`（或局部安装）。

Playwright 安装（建议首次执行）：

```bash
llm4reverse playwright-install
```

AST 依赖准备：

```bash
# 全局安装\ nnpm install -g esprima
# 或在任意目录局部安装
npm init -y && npm i esprima
```

------

## 🧪 常用场景配方

**快速排查（仅证据）**

```bash
llm4reverse reverse --url https://target.site --no-llm
```

**仅做 JS 静态分析**

```bash
llm4reverse reverse --url https://dummy --no-browser --jsfile ./app.min.js --no-llm
```

**借助 AST 定位字符串/URL**

```bash
llm4reverse reverse --url https://dummy --no-browser --jsfile ./app.min.js --ast --no-llm
```

**触发一次交互再采集**

```bash
llm4reverse reverse --url https://target.site --click "#login" --no-llm
```

**完整流程（带 LLM 摘要）**

```bash
export OPENAI_API_KEY=sk-...
llm4reverse reverse --url https://target.site --jsfile ./app.min.js --ast
```

提示：

- 对单页应用（SPA），可结合不同 `--click` 选择器多次运行进行广度探索；
- 适当增大 `--wait-ms` 以等待用户交互后的延迟请求；
- 如需压缩产出体积，可自行二次开发过滤字段或缩短等待时间。

------

## 📤 产物格式示例

```
capture.json
{
  "url": "https://target.site",
  "requests": [{ "method": "GET", "url": "https://api...", "status": 200, "postDataSnippet": "..." }],
  "console": ["[log] ...", "[warn] ..."],
  "domSnippet": "<html>... trimmed ...</html>"
}
js_beautify.json
{
  "beautified": "function a(){...}",
  "patterns": {
    "token_like": ["token=..."],
    "api_paths": ["/api/v1/..."],
    "fetch_calls": ["https://api..."],
    "xhr_open": [["GET", "/api/..."]]
  }
}
js_ast.json
{
  "identifiers": ["sign", "ts", "nonce"],
  "stringLiterals": ["/api/v2/...", "Bearer "],
  "fetchUrls": ["https://api..."],
  "xhrUrls": ["/ajax/..."]
}
reverse_report.md
```

- 建议段落：`Targets`、`Findings (APIs, Params, Headers, Tokens)`、`Risks / Weak points`、`Suggested next steps`。
- 建议纳入版本管理以保留审计轨迹；如包含敏感信息请做脱敏处理。

------

## 🧩 模块接口速查

- `BrowserTool.capture(url, click_selector, wait_after_ms, include_dom)` → 返回 `requests/console/domSnippet`。
- `JSBeautifyTool.run(code)` → 返回 `beautified + patterns`。
- `try_extract_ast(code)` → 返回 `identifiers/stringLiterals/fetchUrls/xhrUrls` 或 `{error}`。
- `ReverseAgent.reason(evidence)` → 返回 Markdown 摘要字符串。
- `save_artifacts(outdir, ...)` → 统一写盘 JSON/MD。

------

## 🧱 开发指南

- 风格：类型注解 + Google 风格 docstring；小函数、可组合、显式错误。
- 扩展正则：在 `js_beautify.py` 新增保守模式并记录潜在误报风险。
- 自定义提示词：按领域在 `agent.py` 内嵌提示中增补（如签名参数、反爬策略）。
- 新工具：放入 `llm4reverse/tools/` 并在 `cli.py` 接入；优先显式参数控制。
- 可复现性：稳定 JSON 字段；如调整字段请同步 README 并 bump 版本。

------

## ⚠️ 注意与局限

- 未包含深入解混淆（字符串传播/控制流等）；复杂 packer 建议自定义逻辑。
- 响应状态关联为尽力处理；强异步场景可能出现错配。
- LLM 摘要不替代人工验证；务必结合真实请求与源码审阅判断。

------

## ❓ 常见问题（FAQ）

Playwright 缺失？

```bash
pip install -r requirements.txt
llm4reverse playwright-install
```

Node/esprima 缺失？

```bash
npm install -g esprima
# 或在任意目录局部安装
npm init -y && npm i esprima
```

没有 API Key？

使用 `--no-llm` 跳过推理，仅检查产出。

产物太大？

适当降低 `--wait-ms`、在自定义代码中关闭 DOM 采集或二次处理 JSON。

------

## 🔐 合规与伦理

仅在授权范围内使用本工具。任何条款、政策或法律的违反行为，由使用者自行承担责任。

------

## 🗺️ Roadmap

- 字符串/常量传播等解混淆策略
- Chrome DevTools Protocol（coverage / source map）
- 引导式点击路径探索
- 风险评分与 PoC 雏形
- 简易 Web UI 演示

------

## 📝 许可证

MIT License © 2025 [@BruceWen1](https://github.com/BruceWen1)

------

## 🤝 贡献

欢迎提交 PR 与 Issue。请遵循 Google 风格注释、保持 README 与行为一致，并严格遵守合规与伦理边界。