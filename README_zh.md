# 🔍 LLM4Reverse

<p align="right">
  <a href="README.md">English</a> | 中文
</p>

**LLM4Reverse** 是一个专业级逆向工程工具包，结合静态代码分析和动态网络流量分析，利用大语言模型（LLM）推理能力，自动发现并记录前端 JavaScript/TypeScript 代码库中的 API 端点。

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Status](https://img.shields.io/badge/status-alpha-orange)

---

## 📋 目录

- [概述](#概述)
- [功能特性](#功能特性)
- [架构设计](#架构设计)
- [安装指南](#安装指南)
- [配置说明](#配置说明)
- [快速开始](#快速开始)
- [CLI 参考](#cli-参考)
- [输出格式](#输出格式)
- [技术细节](#技术细节)
- [开发指南](#开发指南)
- [故障排除](#故障排除)
- [常见问题](#常见问题)
- [道德与法律](#道德与法律)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

---

## 🎯 概述

LLM4Reverse 提供两种互补的工作流，用于逆向工程前端应用：

1. **静态审计（`audit`）**：分析本地 JavaScript/TypeScript 源代码，使用正则表达式提取 API 端点候选，然后利用 LLM 推理能力丰富发现结果，推断缺失的元数据（请求头、参数、认证信息）。

2. **动态逆向（`reverse`）**：使用 Playwright 从实时网页捕获运行时网络流量（HAR 格式），然后使用 LLM 代理分析流量并提取结构化的 API 端点信息。

两种工作流都会生成 JSON 和 Markdown 格式的详细报告，以及完整的 LLM 推理轨迹，便于透明度和调试。

### 使用场景

- **安全研究**：发现未文档化的 API 端点用于安全评估
- **API 文档生成**：从前端代码自动生成 API 文档
- **集成测试**：识别前端应用使用的所有 API 端点
- **代码分析**：理解遗留代码库中的外部依赖和 API 契约

---

## ✨ 功能特性

### 静态审计功能

- **多模式正则提取**：通过多种启发式方法检测端点：
  - `fetch()` 和 `axios` HTTP 调用
  - WebSocket 连接（`new WebSocket()`）
  - GraphQL 操作提示
  - 原始 HTTP/HTTPS URL
  - 相对 API 路径（`/api/...`）
- **符号索引**：构建跨文件符号索引（常量、函数、类）以解析变量引用
- **LLM 增强**：使用带自定义工具的 ReAct 代理推断：
  - 缺失的 URL 基础路径
  - 必需的请求头和认证令牌
  - 请求体模式和查询参数
  - 每个发现的置信度分数
- **去重**：基于类型、方法、URL、文件和行号自动删除重复发现

### 动态逆向功能

- **HAR 捕获**：使用 Playwright 的 HAR 录制功能记录完整的网络流量
- **智能等待**：支持在网络空闲后配置等待时间，适用于单页应用
- **LLM 分析**：ReAct 代理分析 HAR 条目以提取：
  - API 端点 URL 和 HTTP 方法
  - 请求/响应头
  - 查询参数和请求体
  - 认证机制
- **无头/有头模式**：可在无头模式下运行浏览器以自动化，或使用 UI 进行调试

### 通用功能

- **全面报告**：生成 JSON（机器可读）和 Markdown（人类可读）报告
- **LLM 轨迹日志**：完整的 LLM 交互轨迹，便于透明度和调试
- **OpenAI 兼容 API**：适用于任何 OpenAI 兼容的 API 端点（OpenAI、Qwen、本地模型等）
- **CLI 优先设计**：简单直观的命令行界面，具有清晰的子命令
- **可扩展架构**：模块化设计，易于扩展和定制

---

## 🏗️ 架构设计

### 项目结构

```
LLM4Reverse/
├── llm4reverse/                    # 主包
│   ├── __init__.py                 # 包初始化和版本
│   ├── cli.py                       # CLI 入口点和参数解析
│   ├── config.py                    # 配置管理
│   │
│   ├── llm/                         # LLM 集成模块
│   │   ├── __init__.py
│   │   └── client.py                # OpenAI 兼容客户端包装器
│   │
│   ├── audit/                       # 静态审计模块
│   │   ├── __init__.py
│   │   ├── pipeline.py              # 主审计编排
│   │   ├── scanner.py               # 文件系统扫描器
│   │   ├── report.py                # 报告生成
│   │   │
│   │   ├── extractors/              # 端点提取
│   │   │   ├── __init__.py
│   │   │   └── regex_extractor.py   # 基于正则的端点检测
│   │   │
│   │   ├── resolvers/               # 符号解析
│   │   │   ├── __init__.py
│   │   │   └── symbol_index.py      # 跨文件符号索引
│   │   │
│   │   ├── agents/                  # LLM 代理
│   │   │   ├── __init__.py
│   │   │   └── endpoint_agent.py    # 端点增强的 ReAct 代理
│   │   │
│   │   └── tools/                    # 代理工具
│   │       ├── __init__.py
│   │       ├── symbol_lookup.py     # 符号查找工具
│   │       └── code_search.py       # 代码搜索工具
│   │
│   └── reverse/                     # 动态逆向模块
│       ├── __init__.py
│       ├── pipeline.py              # 主逆向编排
│       ├── report.py                # 报告生成
│       │
│       ├── collectors/              # 数据收集
│       │   ├── __init__.py
│       │   └── browser.py           # Playwright 浏览器会话管理器
│       │
│       ├── analyzers/               # 代码分析（未来使用）
│       │   ├── __init__.py
│       │   ├── js_beautify.py
│       │   └── js_ast.py
│       │
│       └── agents/                  # LLM 代理
│           ├── __init__.py
│           └── har_agent.py         # HAR 分析的 ReAct 代理
│
├── scripts/                         # 工具脚本
│   └── install_playwright.sh        # Playwright 浏览器安装
│
├── requirements.txt                  # Python 依赖
├── pyproject.toml                    # 项目元数据和构建配置
├── README.md                        # 本文档（英文）
├── README_zh.md                     # 中文文档
└── LICENSE                          # MIT 许可证
```

### 工作流示意图

#### 静态审计工作流

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 文件扫描                                                   │
│    - 递归扫描目录树                                           │
│    - 按文件扩展名过滤（.js, .ts, .jsx, .tsx）                │
│    - 排除目录（node_modules, dist, build, .git）              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. 正则提取                                                   │
│    - 对每个文件应用多个正则模式                               │
│    - 提取：fetch()、axios、WebSocket、GraphQL 提示           │
│    - 生成 Finding 对象（type, method, url, file, line）      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. 去重                                                       │
│    - 基于（type, method, url, file, line）元组删除重复项     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. 符号索引构建                                               │
│    - 解析所有源文件以查找符号定义                             │
│    - 索引：const/let/var、函数、类                            │
│    - 构建查找表：identifier → SymbolRef[]                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. LLM 增强（ReAct 代理）                                    │
│    对每个发现：                                               │
│    - 代理接收：文件路径、行号、代码片段                       │
│    - 可用工具：                                               │
│      * SymbolLookupTool：解析变量引用                         │
│      * CodeSearchTool：在代码库中搜索相关代码                 │
│    - 代理推断：请求头、参数、请求体模式、认证                 │
│    - 使用增强的元数据更新 Finding                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. 报告生成                                                   │
│    - static_findings.json：JSON 格式的完整发现               │
│    - static_report.md：人类可读的 Markdown 报告              │
│    - audit_trace.json：完整的 LLM 交互轨迹                   │
└─────────────────────────────────────────────────────────────┘
```

#### 动态逆向工作流

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 浏览器启动（Playwright）                                   │
│    - 启动 Chromium 浏览器（无头或有头）                      │
│    - 启用 HAR 录制                                            │
│    - 导航到目标 URL                                          │
│    - 等待 networkidle（或 domcontentloaded 回退）            │
│    - SPA 加载的额外超时                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. HAR 文件生成                                               │
│    - Playwright 自动保存 HAR 文件                            │
│    - 包含所有网络请求/响应                                    │
│    - 包括请求头、请求体、时间信息                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. HAR 解析                                                   │
│    - 将 HAR 文件加载为 JSON                                  │
│    - 从 log.entries 提取条目                                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. LLM 分析（ReAct 代理）                                    │
│    - 代理接收：完整的 HAR 字典                                │
│    - 可用工具：                                               │
│      * HarSearchTool：按 URL/请求头搜索 HAR 条目             │
│    - 代理分析流量并提取：                                     │
│      * API 端点 URL 和方法                                   │
│      * 请求/响应头                                            │
│      * 查询参数和请求体                                       │
│      * 认证机制                                               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. 报告生成                                                   │
│    - reverse_report.json：JSON 格式的提取端点                │
│    - reverse_report.md：人类可读的 Markdown 报告             │
│    - reverse_trace.json：完整的 LLM 交互轨迹                 │
│    - traffic.har：原始 HAR 文件（保留）                       │
└─────────────────────────────────────────────────────────────┘
```

### 组件交互

```
┌──────────────┐
│   CLI (cli)  │
└──────┬───────┘
       │
       ├─────────────────┐
       │                 │
       ▼                 ▼
┌─────────────┐   ┌──────────────┐
│ Audit       │   │ Reverse      │
│ Pipeline    │   │ Pipeline     │
└──────┬──────┘   └──────┬───────┘
       │                 │
       ├─────────┐       ├──────────┐
       │         │       │          │
       ▼         ▼       ▼          ▼
┌─────────┐ ┌──────┐ ┌──────┐ ┌─────────┐
│ Scanner │ │Regex │ │Browser│ │ HAR     │
│         │ │Extr. │ │Session│ │ Agent   │
└────┬────┘ └──┬───┘ └───┬───┘ └────┬────┘
     │         │         │          │
     │         │         │          │
     └─────────┴─────────┴──────────┘
                 │
                 ▼
          ┌──────────────┐
          │ LLM Client   │
          │ (OpenAI API) │
          └──────────────┘
```

---

## 📦 安装指南

### 前置要求

- **Python 3.10 或更高版本**（已测试 3.10、3.11、3.12）
- **pip**（Python 包管理器）
- **Git**（用于克隆仓库）
- **OpenAI 兼容 API 访问**（需要 API 密钥）

### 逐步安装

1. **克隆仓库**：
```bash
git clone https://github.com/BruceWen1/LLM4Reverse.git
cd LLM4Reverse
```

2. **安装包**（推荐：使用虚拟环境）：
   ```bash
   # 创建虚拟环境（可选但推荐）
   python -m venv venv
   
   # 激活虚拟环境
   # Windows:
   venv\Scripts\activate
   # Linux/macOS:
   source venv/bin/activate
   
   # 以可编辑模式安装包
   pip install -e .
   ```

3. **安装 Playwright 浏览器**（动态逆向需要）：
   ```bash
   playwright install chromium
   ```
   
   或使用提供的脚本（Linux/macOS）：
   ```bash
   bash scripts/install_playwright.sh
   ```

4. **验证安装**：
   ```bash
   llm4reverse --version
   ```

### 依赖项

以下包会自动安装：

- `python-dotenv>=1.0.1` - 环境变量管理
- `openai>=1.35.0` - OpenAI API 客户端
- `jsbeautifier>=1.15.1` - JavaScript 代码格式化
- `beautifulsoup4>=4.12.2` - HTML 解析（用于未来功能）
- `playwright>=1.45.0` - 浏览器自动化和 HAR 捕获
- `langchain>=0.2.7` - LLM 框架和代理编排
- `langchain-core>=0.2.7` - LangChain 核心组件
- `langchain-community>=0.2.7` - LangChain 社区集成
- `langchain-openai>=0.1.0` - LangChain 的 OpenAI 集成

---

## ⚙️ 配置说明

### 环境变量

LLM4Reverse 使用环境变量进行配置。您可以在 shell 中设置它们，或在项目根目录创建 `.env` 文件。

#### 必需变量

- **`API_KEY`**（必需）：您的 OpenAI 兼容服务的 API 密钥
  ```bash
  export API_KEY="your-api-key"
  ```

#### 可选变量

- **`BASE_URL`**（可选）：自定义 API 端点 URL（用于非 OpenAI 服务）
  ```bash
  export BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
  ```

- **`MODEL`**（可选）：要使用的默认模型名称
  ```bash
  export MODEL="gpt-4o"
  ```

- **`TEMPERATURE`**（可选）：LLM 的采样温度（默认：0.0）
  ```bash
  export TEMPERATURE="0.0"
  ```

### 创建 `.env` 文件

在项目根目录创建 `.env` 文件：

```bash
# .env
API_KEY=your-api-key
BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL=qwen3-max
TEMPERATURE=0.0
```

`python-dotenv` 包在导入包时会自动加载此文件。

### 支持的 LLM 提供商

LLM4Reverse 适用于任何 OpenAI 兼容的 API 端点，包括：

- **OpenAI**：`https://api.openai.com/v1`（默认）
- **Azure OpenAI Service**：`https://YOUR_RESOURCE_NAME.openai.azure.com/v1`
- **Google Gemini**：`https://generativelanguage.googleapis.com/v1beta`
- **Anthropic Claude**：`https://api.anthropic.com/v1`
- **Qwen（阿里云）**：`https://dashscope.aliyuncs.com/compatible-mode/v1`
- **本地模型**：
  - **Ollama**：`http://127.0.0.1:11434/v1`
  - **LM Studio**：`http://127.0.0.1:1234/v1`
  - **vLLM**：`http://127.0.0.1:8000/v1`
  - **LocalAI**：`http://127.0.0.1:8080/v1`
  - **llama.cpp server**：`http://127.0.0.1:8080/v1`
- **其他提供商**：任何实现 OpenAI API 格式的服务

### 配置优先级

1. 环境变量（最高优先级）
2. `.env` 文件
3. 默认值（最低优先级）

---

## 🚀 快速开始

### 示例 1：静态审计

分析本地 JavaScript/TypeScript 代码库：

```bash
llm4reverse audit --path ./my-frontend-app
```

这将：
1. 扫描 `./my-frontend-app` 中的所有 `.js`、`.ts`、`.jsx`、`.tsx` 文件
2. 使用正则表达式提取 API 端点候选
3. 构建符号索引
4. 使用 LLM 推理增强发现结果
5. 在目标目录中生成报告

**输出文件**：
- `./my-frontend-app/static_findings.json` - JSON 格式的完整发现
- `./my-frontend-app/static_report.md` - 人类可读的报告
- `./my-frontend-app/audit_trace.json` - LLM 交互轨迹

### 示例 2：动态逆向

捕获并分析实时网站的网络流量：

```bash
llm4reverse reverse --url https://example.com
```

这将：
1. 启动无头浏览器
2. 导航到 `https://example.com`
3. 将所有网络流量录制为 HAR
4. 使用 LLM 分析流量
5. 在 `./reverse_out/` 中生成报告

**输出文件**：
- `./reverse_out/traffic.har` - 原始 HAR 文件
- `./reverse_out/reverse_report.json` - JSON 格式的提取端点
- `./reverse_out/reverse_report.md` - 人类可读的报告
- `./reverse_out/reverse_trace.json` - LLM 交互轨迹

### 示例 3：自定义选项

```bash
# 使用自定义文件过滤器的静态审计
llm4reverse audit \
  --path ./src \
  --include .js,.ts \
  --exclude node_modules,dist,tests

# 使用可见浏览器和更长超时的动态逆向
llm4reverse reverse \
  --url https://example.com \
  --output ./my_results \
  --no-headless \
  --timeout 60

# 启用详细日志
llm4reverse --verbose reverse --url https://example.com
```

---

## 🧰 CLI 参考

### 全局选项

```
llm4reverse [OPTIONS] COMMAND [ARGS]

选项：
  -v, --verbose    启用调试日志
  --version        显示版本并退出
```

### `reverse` 子命令

动态逆向工程工作流。

```
llm4reverse reverse --url URL [OPTIONS]

必需参数：
  --url URL        要逆向工程的目标网页 URL

选项：
  --output, --outdir DIR    输出目录（默认：./reverse_out）
  --no-headless            以 UI 模式运行浏览器（默认：无头）
  --timeout SECONDS        网络空闲后的额外等待时间（默认：30）
  -v, --verbose            启用调试日志
```

**示例**：
```bash
# 基本用法
llm4reverse reverse --url https://example.com

# 自定义输出目录
llm4reverse reverse --url https://example.com --output ./results

# 可见浏览器用于调试
llm4reverse reverse --url https://example.com --no-headless

# 为加载缓慢的 SPA 设置更长超时
llm4reverse reverse --url https://example.com --timeout 60
```

### `audit` 子命令

静态代码审计工作流。

```
llm4reverse audit --path PATH [OPTIONS]

必需参数：
  --path PATH      本地代码目录路径

选项：
  --include EXT,EXT,...    要包含的逗号分隔文件扩展名
                           （默认：.js,.ts,.jsx,.tsx）
  --exclude DIR,DIR,...   要排除的逗号分隔目录名
                           （默认：node_modules,dist,build,.git）
  -v, --verbose            启用调试日志
```

**示例**：
```bash
# 基本用法
llm4reverse audit --path ./src

# 自定义文件类型
llm4reverse audit --path ./src --include .js,.ts

# 自定义排除项
llm4reverse audit --path ./src --exclude node_modules,dist,tests,.git
```

### 退出代码

- `0`：成功
- `1`：错误（查看日志了解详情）

---

## 📄 输出格式

### 静态审计输出

#### `static_findings.json`

JSON 格式的完整发现：

```json
{
  "findings": [
    {
      "type": "http",
      "method": "POST",
      "url": "/api/users",
      "file": "src/api/client.js",
      "line": 42,
      "snippet": "const response = await fetch('/api/users', { method: 'POST', ... })",
      "confidence": 0.9,
      "headers": {
        "Content-Type": "application/json",
        "Authorization": "Bearer ${token}"
      },
      "params": {},
      "body": {
        "name": "string",
        "email": "string"
      }
    }
  ]
}
```

#### `static_report.md`

人类可读的 Markdown 报告，每个发现都有章节：

```markdown
# Static Audit Report

### HTTP POST /api/users
- **File**: `src/api/client.js:42`
- **Method**: `POST`
- **Confidence**: `0.90`
- **Headers**:
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer ${token}"
}
```
- **Body**:
```json
{
  "name": "string",
  "email": "string"
}
```
- **Code Snippet**:
```js
const response = await fetch('/api/users', { method: 'POST', ... })
```
```

#### `audit_trace.json`

LLM 交互的完整轨迹：

```json
[
  {
    "role": "assistant",
    "content": "Thought: I need to analyze this endpoint..."
  },
  {
    "role": "assistant",
    "content": "Action: SymbolLookupTool\nAction Input: baseURL"
  }
]
```

### 动态逆向输出

#### `reverse_report.json`

从 HAR 分析中提取的端点：

```json
[
  {
    "url": "https://api.example.com/v1/users",
    "method": "GET",
    "headers": {
      "Authorization": "Bearer ...",
      "Content-Type": "application/json"
    },
    "params": {
      "page": "1",
      "limit": "10"
    },
    "body": null,
    "auth": "Bearer token"
  }
]
```

#### `reverse_report.md`

人类可读的 Markdown 报告：

```markdown
# Dynamic Reverse Report

## `GET` https://api.example.com/v1/users

```json
{
  "url": "https://api.example.com/v1/users",
  "method": "GET",
  "headers": {
    "Authorization": "Bearer ...",
    "Content-Type": "application/json"
  },
  "params": {
    "page": "1",
    "limit": "10"
  },
  "body": null,
  "auth": "Bearer token"
}
```
```

#### `traffic.har`

标准 HAR（HTTP 存档）格式文件，包含所有网络流量。可在以下工具中打开：
- Chrome DevTools（网络标签 → 导入 HAR）
- HAR 分析器工具
- 任何 HAR 兼容工具

#### `reverse_trace.json`

HAR 分析期间 LLM 交互的完整轨迹。

---

## 🔧 技术细节

### 正则提取模式

静态审计使用多个正则模式来检测端点：

1. **HTTP 请求模式**：
   - `fetch('...')` 或 `fetch("...")`
   - `axios.get/post/put/delete/patch('...')`

2. **原始 URL 模式**：
   - `https?://[a-zA-Z0-9_\-./:?=&%#]+`
   - `/api/[a-zA-Z0-9_\-./:?=&%#]+`

3. **WebSocket 模式**：
   - `new WebSocket('...')` 或 `new WebSocket("...")`

4. **GraphQL 提示**：
   - URL 中的 `/graphql`
   - 代码中的 `operationName`

### 符号索引

符号索引使用正则表达式提取：

- **常量/变量**：`const`、`let`、`var` 声明
- **函数**：`function` 和 `async function` 声明
- **类**：`class` 声明

模式：
```regex
(?:export\s+)?(?:const|let|var)\s+(?P<const>[A-Za-z_][\w$]*)\s*=
(?:export\s+)?(?:async\s+)?function\s+(?P<func>[A-Za-z_][\w$]*)\s*\(
(?:export\s+)?class\s+(?P<class>[A-Za-z_][\w$]*)
```

### LLM 代理架构

两种工作流都使用 **ReAct（推理 + 行动）** 代理：

1. **代理接收**：上下文（代码片段、文件路径、HAR 条目等）
2. **代理可访问工具**：
   - 静态审计：`SymbolLookupTool`、`CodeSearchTool`
   - 动态逆向：`HarSearchTool`
3. **代理推理**：使用 LLM 逐步思考
4. **代理行动**：调用工具以收集额外信息
5. **代理响应**：返回包含端点详细信息的结构化 JSON

### 浏览器会话管理

动态逆向工作流使用 Playwright 的上下文管理器模式：

```python
with BrowserSession(har_path="traffic.har", headless=True) as page:
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(timeout * 1000)
```

当上下文关闭时，HAR 会自动保存。

### 错误处理

- **文件读取错误**：记录日志并跳过，处理继续
- **LLM API 错误**：记录完整回溯，保留原始发现
- **浏览器导航错误**：如果 `networkidle` 超时，回退到 `domcontentloaded`
- **JSON 解析错误**：原始文本存储在发现中，处理继续

### 性能考虑

- **符号索引**：每次审计构建一次，在内存中缓存
- **LLM 调用**：顺序（一次一个发现）以避免速率限制
- **文件扫描**：使用 `pathlib.rglob()` 进行高效的目录遍历
- **HAR 文件大小**：可能很大（10-100MB+），确保有足够的磁盘空间

---

## 🛠️ 开发指南

### 项目结构指南

- **类型提示**：所有函数都应有类型注解
- **文档字符串**：使用简洁的文档字符串，遵循 Google/NumPy 风格
- **模块化**：保持函数小而可组合
- **错误处理**：使用 try-except 和适当的日志记录

### 添加新提取器

要添加新的正则模式以提取端点：

1. 编辑 `llm4reverse/audit/extractors/regex_extractor.py`
2. 将模式添加到 `_HTTP_PATTERNS`、`_WS_PATTERNS` 或创建新模式列表
3. 更新 `extract_endpoints()` 函数以使用新模式
4. 使用示例代码进行测试

### 添加新代理工具

要为新 LLM 代理添加工具：

1. 在 `llm4reverse/audit/tools/` 或 `llm4reverse/reverse/agents/` 中创建工具函数
2. 使用 `langchain_core.tools.Tool` 包装函数
3. 在代理初始化时将工具添加到工具列表
4. 更新代理提示以描述新工具

### 测试

运行测试套件：

```bash
# 使用 pytest 或您首选的测试框架运行测试
pytest
```

### 代码风格

- 遵循 PEP 8
- 使用 `black` 进行格式化（如果配置）
- 最大行长度：100 个字符（灵活）

### 版本管理

- 更新 `llm4reverse/__init__.py` 中的 `__version__`
- 更新 `pyproject.toml` 中的 `version`
- 在 CHANGELOG.md 中记录破坏性更改

---

## 🐛 故障排除

### 常见问题

#### 1. "Missing API_KEY" 错误

**问题**：`RuntimeError: Missing API_KEY`

**解决方案**：
- 设置 `API_KEY` 环境变量
- 或创建包含 `API_KEY=your-api-key` 的 `.env` 文件

#### 2. Playwright 浏览器未找到

**问题**：`playwright._impl._api_types.Error: Executable doesn't exist`

**解决方案**：
```bash
playwright install chromium
```

#### 3. LLM API 超时

**问题**：请求超时或失败

**解决方案**：
- 检查网络连接
- 验证 `BASE_URL` 是否正确
- 在 `llm/client.py` 中增加超时（默认：60 秒）
- 检查 API 密钥有效性

#### 4. 未找到端点

**问题**：静态审计未找到端点

**解决方案**：
- 检查文件扩展名是否匹配 `--include` 模式
- 验证代码是否包含 fetch/axios/WebSocket 调用
- 检查排除的目录是否不包含目标文件
- 启用详细日志：`llm4reverse -v audit --path ...`

#### 5. HAR 文件为空或缺失

**问题**：`traffic.har` 为空或未生成

**解决方案**：
- 增加 `--timeout` 值
- 尝试 `--no-headless` 查看浏览器行为
- 检查目标 URL 是否可访问
- 验证 Playwright 浏览器是否已安装

#### 6. 报告中的 JSON 解析错误

**问题**：LLM 返回非 JSON 输出

**解决方案**：
- 这是自动处理的（原始文本已存储）
- 检查 `*_trace.json` 了解 LLM 推理
- 可能表示 LLM 模型不兼容
- 尝试不同的模型或调整温度

### 调试模式

启用详细日志：

```bash
llm4reverse -v audit --path ./src
llm4reverse -v reverse --url https://example.com
```

这将显示：
- 文件扫描进度
- 正则提取结果
- 符号索引构建
- LLM API 调用
- 带回溯的错误详情

### 获取帮助

1. 查看本文档
2. 查看 `*_trace.json` 文件了解 LLM 推理
3. 启用详细日志（`-v` 标志）
4. 在 GitHub 上提交问题，包括：
   - 错误消息
   - 使用的命令
   - 相关日志输出
   - 环境详情（操作系统、Python 版本等）

---

## ❓ 常见问题

### Q: 我可以将此工具与本地 LLM 模型一起使用吗？

**A**：可以！将 `BASE_URL` 设置为本地 OpenAI 兼容 API 端点（例如，`http://localhost:11434/v1`）。

### Q: 提取的端点有多准确？

**A**：准确性取决于：
- 代码质量和模式
- LLM 模型能力
- 网络流量完整性（对于动态逆向）

在生产中使用之前，务必手动验证发现。

### Q: 这适用于压缩的 JavaScript 吗？

**A**：部分适用。正则模式可以检测 URL 和基本模式，但符号解析和代码分析在可读代码上效果更好。考虑先使用 JavaScript 美化器。

### Q: 我可以自定义正则模式吗？

**A**：可以，编辑 `llm4reverse/audit/extractors/regex_extractor.py` 并修改模式列表。

### Q: 如何排除特定文件（不仅仅是目录）？

**A**：目前仅支持目录排除。可以通过修改 `scanner.py` 添加文件级过滤。

### Q: 静态审计和动态逆向有什么区别？

**A**：
- **静态审计**：在不运行代码的情况下分析源代码。查找代码中定义的端点。
- **动态逆向**：捕获实际网络流量。查找运行时实际调用的端点。

两种方法是互补的，可以揭示不同的端点。

### Q: 我可以将此工具用于 API 文档生成吗？

**A**：可以！生成的报告可以作为 API 文档的起点，但建议进行手动审查和增强。

### Q: 在生产系统上使用此工具安全吗？

**A**：工具本身是安全的，但：
- 仅在使用您拥有或明确许可测试的系统上使用
- 注意速率限制和 API 成本
- 在分享之前审查生成的报告

### Q: 如何贡献？

**A**：请参阅下面的[贡献指南](#贡献指南)部分。

---

## 🔐 道德与法律

### 重要免责声明

**LLM4Reverse 是仅用于安全研究、API 文档和合法逆向工程目的的工具。**

### 使用指南

- ✅ **应该**：在您拥有或明确许可分析的代码库上使用
- ✅ **应该**：在获得适当授权的情况下用于安全研究
- ✅ **应该**：用于理解您自己的应用程序
- ❌ **不应该**：在未经许可的系统上使用
- ❌ **不应该**：用于恶意目的
- ❌ **不应该**：违反服务条款或法律

### 法律责任

用户全权负责确保他们对 LLM4Reverse 的使用符合：
- 适用的法律法规
- 目标系统的服务条款
- 安全研究的道德准则

LLM4Reverse 的作者和贡献者不对此工具的误用承担任何责任。

---

## 🤝 贡献指南

欢迎贡献！以下是如何提供帮助：

### 如何贡献

1. **Fork 仓库**
2. **创建功能分支**：`git checkout -b feature/your-feature-name`
3. **进行更改**：遵循开发指南
4. **测试更改**：运行测试并确保测试通过
5. **更新文档**：保持 README 和文档字符串同步
6. **提交更改**：使用清晰、描述性的提交消息
7. **推送到您的 fork**：`git push origin feature/your-feature-name`
8. **打开 Pull Request**：提供清晰的更改描述

### 贡献指南

- **代码风格**：遵循 PEP 8，使用类型提示，编写文档字符串
- **测试**：为新功能添加测试
- **文档**：为用户面向的更改更新 README
- **兼容性**：保持 Python 3.10+ 兼容性
- **道德**：确保贡献符合道德使用准则

### 贡献领域

- 端点检测的其他正则模式
- 支持更多编程语言
- 改进 LLM 提示以提高准确性
- 性能优化
- 其他报告格式（HTML、PDF 等）
- 更好的错误消息和用户体验
- 文档改进

### 报告问题

报告问题时，请包括：
- 问题描述
- 重现步骤
- 预期 vs. 实际行为
- 环境详情（操作系统、Python 版本等）
- 相关日志输出（敏感数据已脱敏）

---

## 📝 许可证

本项目采用 **MIT 许可证**。

有关详细信息，请参阅 [LICENSE](LICENSE) 文件。

版权所有 © 2025 [@BruceWen1](https://github.com/BruceWen1)

---

## 🙏 致谢

- **LangChain**：优秀的 LLM 框架和代理编排
- **Playwright**：强大的浏览器自动化和 HAR 捕获
- **OpenAI**：使与许多提供商兼容的 API 格式
- **社区**：反馈、贡献和支持

---

## 🗺️ 路线图

计划中的未来改进：

- [ ] 增强的基于 AST 的代码分析（超越正则）
- [ ] 用于审查发现的交互模式
- [ ] 与 API 测试工具集成
- [ ] 支持 GraphQL 模式提取
- [ ] 报告可视化的 Web UI
- [ ] 多个目标的批处理
- [ ] 导出到 OpenAPI/Swagger 格式
- [ ] 性能优化（并行 LLM 调用、缓存）
- [ ] 更好地处理压缩/混淆代码
