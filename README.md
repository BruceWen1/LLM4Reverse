# 🔍 LLM4Reverse

<p align="right">
  English | <a href="README_zh.md">中文</a>
</p>

**LLM4Reverse** is a professional-grade reverse engineering toolkit that combines static code analysis and dynamic network traffic analysis with Large Language Model (LLM) reasoning to automatically discover and document API endpoints from frontend JavaScript/TypeScript codebases.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Status](https://img.shields.io/badge/status-alpha-orange)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [CLI Reference](#cli-reference)
- [Output Format](#output-format)
- [Technical Details](#technical-details)
- [Development Guide](#development-guide)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Ethics & Legal](#ethics--legal)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

LLM4Reverse provides two complementary workflows for reverse engineering frontend applications:

1. **Static Audit (`audit`)**: Analyzes local JavaScript/TypeScript source code to extract API endpoint candidates using regex patterns, then enriches findings with LLM-powered reasoning to infer missing metadata (headers, parameters, authentication).

2. **Dynamic Reverse (`reverse`)**: Captures runtime network traffic (HAR format) from a live web page using Playwright, then uses an LLM agent to analyze the traffic and extract structured API endpoint information.

Both workflows generate comprehensive reports in JSON and Markdown formats, along with complete LLM reasoning traces for transparency and debugging.

### Use Cases

- **Security Research**: Discover undocumented API endpoints for security assessment
- **API Documentation**: Automatically generate API documentation from frontend code
- **Integration Testing**: Identify all API endpoints used by a frontend application
- **Code Analysis**: Understand external dependencies and API contracts in legacy codebases

---

## ✨ Features

### Static Audit Features

- **Multi-pattern Regex Extraction**: Detects endpoints via multiple heuristics:
  - `fetch()` and `axios` HTTP calls
  - WebSocket connections (`new WebSocket()`)
  - GraphQL operation hints
  - Raw HTTP/HTTPS URLs
  - Relative API paths (`/api/...`)
- **Symbol Index**: Builds a cross-file symbol index (constants, functions, classes) to resolve variable references
- **LLM Enrichment**: Uses ReAct agent with custom tools to infer:
  - Missing URL base paths
  - Required headers and authentication tokens
  - Request body schemas and query parameters
  - Confidence scores for each finding
- **Deduplication**: Automatically removes duplicate findings based on type, method, URL, file, and line number

### Dynamic Reverse Features

- **HAR Capture**: Records complete network traffic using Playwright's HAR recording capability
- **Intelligent Waiting**: Supports configurable wait times after network idle for single-page applications
- **LLM Analysis**: ReAct agent analyzes HAR entries to extract:
  - API endpoint URLs and HTTP methods
  - Request/response headers
  - Query parameters and request bodies
  - Authentication mechanisms
- **Headless/Headed Modes**: Run browser in headless mode for automation or with UI for debugging

### General Features

- **Comprehensive Reporting**: Generates both JSON (machine-readable) and Markdown (human-readable) reports
- **LLM Trace Logging**: Complete trace of all LLM interactions for transparency and debugging
- **OpenAI-Compatible API**: Works with any OpenAI-compatible API endpoint (OpenAI, Qwen, local models, etc.)
- **CLI-First Design**: Simple, intuitive command-line interface with clear subcommands
- **Extensible Architecture**: Modular design allows easy extension and customization

---

## 🏗️ Architecture

### Project Structure

```
LLM4Reverse/
├── llm4reverse/                    # Main package
│   ├── __init__.py                 # Package initialization and version
│   ├── cli.py                      # CLI entrypoint and argument parsing
│   ├── config.py                   # Configuration management
│   │
│   ├── llm/                        # LLM integration module
│   │   ├── __init__.py
│   │   └── client.py               # OpenAI-compatible client wrapper
│   │
│   ├── audit/                      # Static audit module
│   │   ├── __init__.py
│   │   ├── pipeline.py             # Main audit orchestration
│   │   ├── scanner.py              # File system scanner
│   │   ├── report.py               # Report generation
│   │   │
│   │   ├── extractors/             # Endpoint extraction
│   │   │   ├── __init__.py
│   │   │   └── regex_extractor.py  # Regex-based endpoint detection
│   │   │
│   │   ├── resolvers/              # Symbol resolution
│   │   │   ├── __init__.py
│   │   │   └── symbol_index.py     # Cross-file symbol index
│   │   │
│   │   ├── agents/                 # LLM agents
│   │   │   ├── __init__.py
│   │   │   └── endpoint_agent.py   # ReAct agent for endpoint enrichment
│   │   │
│   │   └── tools/                  # Agent tools
│   │       ├── __init__.py
│   │       ├── symbol_lookup.py    # Symbol lookup tool
│   │       └── code_search.py      # Code search tool
│   │
│   └── reverse/                    # Dynamic reverse module
│       ├── __init__.py
│       ├── pipeline.py             # Main reverse orchestration
│       ├── report.py                # Report generation
│       │
│       ├── collectors/             # Data collection
│       │   ├── __init__.py
│       │   └── browser.py          # Playwright browser session manager
│       │
│       ├── analyzers/              # Code analysis (future use)
│       │   ├── __init__.py
│       │   ├── js_beautify.py
│       │   └── js_ast.py
│       │
│       └── agents/                 # LLM agents
│           ├── __init__.py
│           └── har_agent.py       # ReAct agent for HAR analysis
│
├── scripts/                        # Utility scripts
│   └── install_playwright.sh      # Playwright browser installation
│
├── requirements.txt                 # Python dependencies
├── pyproject.toml                   # Project metadata and build config
├── README.md                       # This file (English)
├── README_zh.md                    # Chinese documentation
└── LICENSE                         # MIT License
```

### Workflow Diagrams

#### Static Audit Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. File Scanning                                             │
│    - Recursively scan directory tree                        │
│    - Filter by file extensions (.js, .ts, .jsx, .tsx)      │
│    - Exclude directories (node_modules, dist, build, .git)    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Regex Extraction                                          │
│    - Apply multiple regex patterns to each file              │
│    - Extract: fetch(), axios, WebSocket, GraphQL hints      │
│    - Generate Finding objects (type, method, url, file, line)│
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Deduplication                                             │
│    - Remove duplicates based on (type, method, url, file,   │
│      line) tuple                                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Symbol Index Building                                     │
│    - Parse all source files for symbol definitions           │
│    - Index: const/let/var, functions, classes                │
│    - Build lookup table: identifier → SymbolRef[]           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. LLM Enrichment (ReAct Agent)                             │
│    For each finding:                                         │
│    - Agent receives: file path, line number, code snippet    │
│    - Tools available:                                        │
│      * SymbolLookupTool: resolve variable references         │
│      * CodeSearchTool: search codebase for related code      │
│    - Agent infers: headers, params, body schema, auth       │
│    - Updates Finding with enriched metadata                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Report Generation                                         │
│    - static_findings.json: Complete findings in JSON         │
│    - static_report.md: Human-readable Markdown report        │
│    - audit_trace.json: Full LLM interaction trace           │
└─────────────────────────────────────────────────────────────┘
```

#### Dynamic Reverse Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Browser Launch (Playwright)                               │
│    - Launch Chromium browser (headless or headed)            │
│    - Enable HAR recording                                    │
│    - Navigate to target URL                                  │
│    - Wait for networkidle (or domcontentloaded fallback)     │
│    - Additional timeout for SPA loading                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. HAR File Generation                                       │
│    - Playwright automatically saves HAR file                 │
│    - Contains all network requests/responses                │
│    - Includes headers, bodies, timing information           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. HAR Parsing                                               │
│    - Load HAR file as JSON                                   │
│    - Extract entries from log.entries                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. LLM Analysis (ReAct Agent)                               │
│    - Agent receives: full HAR dictionary                     │
│    - Tool available:                                         │
│      * HarSearchTool: search HAR entries by URL/header      │
│    - Agent analyzes traffic and extracts:                    │
│      * API endpoint URLs and methods                         │
│      * Request/response headers                              │
│      * Query parameters and request bodies                   │
│      * Authentication mechanisms                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Report Generation                                         │
│    - reverse_report.json: Extracted endpoints in JSON        │
│    - reverse_report.md: Human-readable Markdown report       │
│    - reverse_trace.json: Full LLM interaction trace         │
│    - traffic.har: Original HAR file (preserved)              │
└─────────────────────────────────────────────────────────────┘
```

### Component Interactions

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

## 📦 Installation

### Prerequisites

- **Python 3.10 or higher** (tested with 3.10, 3.11, 3.12)
- **pip** (Python package manager)
- **Git** (for cloning the repository)
- **OpenAI-compatible API access** (API key required)

### Step-by-Step Installation

1. **Clone the repository**:
```bash
git clone https://github.com/BruceWen1/LLM4Reverse.git
cd LLM4Reverse
```

2. **Install the package** (recommended: use a virtual environment):
   ```bash
   # Create virtual environment (optional but recommended)
   python -m venv venv
   
   # Activate virtual environment
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   
   # Install package in editable mode
   pip install -e .
   ```

3. **Install Playwright browsers** (required for dynamic reverse):
   ```bash
   playwright install chromium
   ```
   
   Or use the provided script (Linux/macOS):
   ```bash
   bash scripts/install_playwright.sh
   ```

4. **Verify installation**:
   ```bash
   llm4reverse --version
   ```

### Dependencies

The following packages are automatically installed:

- `python-dotenv>=1.0.1` - Environment variable management
- `openai>=1.35.0` - OpenAI API client
- `jsbeautifier>=1.15.1` - JavaScript code formatting
- `beautifulsoup4>=4.12.2` - HTML parsing (for future features)
- `playwright>=1.45.0` - Browser automation and HAR capture
- `langchain>=0.2.7` - LLM framework and agent orchestration
- `langchain-core>=0.2.7` - Core LangChain components
- `langchain-community>=0.2.7` - Community LangChain integrations
- `langchain-openai>=0.1.0` - OpenAI integration for LangChain

---

## ⚙️ Configuration

### Environment Variables

LLM4Reverse uses environment variables for configuration. You can set them in your shell or create a `.env` file in the project root.

#### Required Variables

- **`API_KEY`** (required): Your API key for the OpenAI-compatible service
  ```bash
  export API_KEY="your-api-key"
  ```

#### Optional Variables

- **`BASE_URL`** (optional): Custom API endpoint URL (for non-OpenAI services)
  ```bash
  export BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
  ```

- **`MODEL`** (optional): Default model name to use
  ```bash
  export MODEL="gpt-4o"
  ```

- **`TEMPERATURE`** (optional): Sampling temperature for LLM (default: 0.0)
  ```bash
  export TEMPERATURE="0.0"
  ```

### Creating a `.env` File

Create a `.env` file in the project root:

```bash
# .env
API_KEY=your-api-key
BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL=qwen3-max
TEMPERATURE=0.0
```

The `python-dotenv` package automatically loads this file when the package is imported.

### Supported LLM Providers

LLM4Reverse works with any OpenAI-compatible API endpoint, including:

- **OpenAI**: `https://api.openai.com/v1` (default)
- **Azure OpenAI Service**: `https://YOUR_RESOURCE_NAME.openai.azure.com/v1`
- **Google Gemini**: `https://generativelanguage.googleapis.com/v1beta`
- **Anthropic Claude**: `https://api.anthropic.com/v1`
- **Qwen (Alibaba Cloud)**: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- **Local models**:
  - **Ollama**: `http://127.0.0.1:11434/v1`
  - **LM Studio**: `http://127.0.0.1:1234/v1`
  - **vLLM**: `http://127.0.0.1:8000/v1`
  - **LocalAI**: `http://127.0.0.1:8080/v1`
  - **llama.cpp server**: `http://127.0.0.1:8080/v1`
- **Other providers**: Any service that implements the OpenAI API format

### Configuration Priority

1. Environment variables (highest priority)
2. `.env` file
3. Default values (lowest priority)

---

## 🚀 Quick Start

### Example 1: Static Audit

Analyze a local JavaScript/TypeScript codebase:

```bash
llm4reverse audit --path ./my-frontend-app
```

This will:
1. Scan all `.js`, `.ts`, `.jsx`, `.tsx` files in `./my-frontend-app`
2. Extract API endpoint candidates using regex
3. Build a symbol index
4. Enrich findings with LLM reasoning
5. Generate reports in the target directory

**Output files**:
- `./my-frontend-app/static_findings.json` - Complete findings in JSON
- `./my-frontend-app/static_report.md` - Human-readable report
- `./my-frontend-app/audit_trace.json` - LLM interaction trace

### Example 2: Dynamic Reverse

Capture and analyze network traffic from a live website:

```bash
llm4reverse reverse --url https://example.com
```

This will:
1. Launch a headless browser
2. Navigate to `https://example.com`
3. Record all network traffic as HAR
4. Analyze traffic with LLM
5. Generate reports in `./reverse_out/`

**Output files**:
- `./reverse_out/traffic.har` - Original HAR file
- `./reverse_out/reverse_report.json` - Extracted endpoints in JSON
- `./reverse_out/reverse_report.md` - Human-readable report
- `./reverse_out/reverse_trace.json` - LLM interaction trace

### Example 3: Custom Options

```bash
# Static audit with custom file filters
llm4reverse audit \
  --path ./src \
  --include .js,.ts \
  --exclude node_modules,dist,tests

# Dynamic reverse with visible browser and longer timeout
llm4reverse reverse \
  --url https://example.com \
  --output ./my_results \
  --no-headless \
  --timeout 60

# Enable verbose logging
llm4reverse --verbose reverse --url https://example.com
```

---

## 🧰 CLI Reference

### Global Options

```
llm4reverse [OPTIONS] COMMAND [ARGS]

Options:
  -v, --verbose    Enable debug logging
  --version        Show version and exit
```

### `reverse` Subcommand

Dynamic reverse engineering workflow.

```
llm4reverse reverse --url URL [OPTIONS]

Required Arguments:
  --url URL        Target webpage URL to reverse engineer

Options:
  --output, --outdir DIR    Output directory (default: ./reverse_out)
  --no-headless            Run browser in UI mode (default: headless)
  --timeout SECONDS        Extra wait time after networkidle (default: 30)
  -v, --verbose            Enable debug logging
```

**Examples**:
```bash
# Basic usage
llm4reverse reverse --url https://example.com

# Custom output directory
llm4reverse reverse --url https://example.com --output ./results

# Visible browser for debugging
llm4reverse reverse --url https://example.com --no-headless

# Longer timeout for slow-loading SPAs
llm4reverse reverse --url https://example.com --timeout 60
```

### `audit` Subcommand

Static code audit workflow.

```
llm4reverse audit --path PATH [OPTIONS]

Required Arguments:
  --path PATH      Path to local code directory

Options:
  --include EXT,EXT,...    Comma-separated file extensions to include
                           (default: .js,.ts,.jsx,.tsx)
  --exclude DIR,DIR,...   Comma-separated directory names to exclude
                           (default: node_modules,dist,build,.git)
  -v, --verbose            Enable debug logging
```

**Examples**:
```bash
# Basic usage
llm4reverse audit --path ./src

# Custom file types
llm4reverse audit --path ./src --include .js,.ts

# Custom exclusions
llm4reverse audit --path ./src --exclude node_modules,dist,tests,.git
```

### Exit Codes

- `0`: Success
- `1`: Error (check logs for details)

---

## 📄 Output Format

### Static Audit Output

#### `static_findings.json`

Complete findings in JSON format:

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

Human-readable Markdown report with sections for each finding:

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

Complete trace of LLM interactions:

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

### Dynamic Reverse Output

#### `reverse_report.json`

Extracted endpoints from HAR analysis:

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

Human-readable Markdown report:

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

Standard HAR (HTTP Archive) format file containing all network traffic. Can be opened in:
- Chrome DevTools (Network tab → Import HAR)
- HAR Analyzer tools
- Any HAR-compatible tool

#### `reverse_trace.json`

Complete trace of LLM interactions during HAR analysis.

---

## 🔧 Technical Details

### Regex Extraction Patterns

The static audit uses multiple regex patterns to detect endpoints:

1. **HTTP Request Patterns**:
   - `fetch('...')` or `fetch("...")`
   - `axios.get/post/put/delete/patch('...')`

2. **Raw URL Patterns**:
   - `https?://[a-zA-Z0-9_\-./:?=&%#]+`
   - `/api/[a-zA-Z0-9_\-./:?=&%#]+`

3. **WebSocket Patterns**:
   - `new WebSocket('...')` or `new WebSocket("...")`

4. **GraphQL Hints**:
   - `/graphql` in URL
   - `operationName` in code

### Symbol Index

The symbol index uses regex to extract:

- **Constants/Variables**: `const`, `let`, `var` declarations
- **Functions**: `function` and `async function` declarations
- **Classes**: `class` declarations

Pattern:
```regex
(?:export\s+)?(?:const|let|var)\s+(?P<const>[A-Za-z_][\w$]*)\s*=
(?:export\s+)?(?:async\s+)?function\s+(?P<func>[A-Za-z_][\w$]*)\s*\(
(?:export\s+)?class\s+(?P<class>[A-Za-z_][\w$]*)
```

### LLM Agent Architecture

Both workflows use **ReAct (Reasoning + Acting)** agents:

1. **Agent receives**: Context (code snippet, file path, HAR entries, etc.)
2. **Agent has access to tools**:
   - Static audit: `SymbolLookupTool`, `CodeSearchTool`
   - Dynamic reverse: `HarSearchTool`
3. **Agent reasons**: Uses LLM to think step-by-step
4. **Agent acts**: Calls tools to gather additional information
5. **Agent responds**: Returns structured JSON with endpoint details

### Browser Session Management

The dynamic reverse workflow uses Playwright's context manager pattern:

```python
with BrowserSession(har_path="traffic.har", headless=True) as page:
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(timeout * 1000)
```

HAR is automatically saved when the context closes.

### Error Handling

- **File reading errors**: Logged and skipped, processing continues
- **LLM API errors**: Logged with full traceback, original finding preserved
- **Browser navigation errors**: Falls back to `domcontentloaded` if `networkidle` times out
- **JSON parsing errors**: Raw text stored in findings, processing continues

### Performance Considerations

- **Symbol index**: Built once per audit, cached in memory
- **LLM calls**: Sequential (one finding at a time) to avoid rate limits
- **File scanning**: Uses `pathlib.rglob()` for efficient directory traversal
- **HAR file size**: Can be large (10-100MB+), ensure sufficient disk space

---

## 🛠️ Development Guide

### Project Structure Guidelines

- **Type hints**: All functions should have type annotations
- **Docstrings**: Use concise docstrings following Google/NumPy style
- **Modularity**: Keep functions small and composable
- **Error handling**: Use try-except with proper logging

### Adding New Extractors

To add a new regex pattern for endpoint extraction:

1. Edit `llm4reverse/audit/extractors/regex_extractor.py`
2. Add pattern to `_HTTP_PATTERNS`, `_WS_PATTERNS`, or create new pattern list
3. Update `extract_endpoints()` function to use new pattern
4. Test with sample code

### Adding New Agent Tools

To add a new tool for the LLM agent:

1. Create tool function in `llm4reverse/audit/tools/` or `llm4reverse/reverse/agents/`
2. Use `langchain_core.tools.Tool` to wrap the function
3. Add tool to tools list in agent initialization
4. Update agent prompt to describe the new tool

### Testing

Run the test suite:

```bash
# Run tests using pytest or your preferred testing framework
pytest
```

### Code Style

- Follow PEP 8
- Use `black` for formatting (if configured)
- Maximum line length: 100 characters (flexible)

### Version Management

- Update `__version__` in `llm4reverse/__init__.py`
- Update `version` in `pyproject.toml`
- Document breaking changes in CHANGELOG.md

---

## 🐛 Troubleshooting

### Common Issues

#### 1. "Missing API_KEY" Error

**Problem**: `RuntimeError: Missing API_KEY`

**Solution**: 
- Set `API_KEY` environment variable
- Or create `.env` file with `API_KEY=your-api-key`

#### 2. Playwright Browser Not Found

**Problem**: `playwright._impl._api_types.Error: Executable doesn't exist`

**Solution**:
```bash
playwright install chromium
```

#### 3. LLM API Timeout

**Problem**: Requests timeout or fail

**Solution**:
- Check network connectivity
- Verify `BASE_URL` is correct
- Increase timeout in `llm/client.py` (default: 60s)
- Check API key validity

#### 4. No Endpoints Found

**Problem**: Static audit finds no endpoints

**Solution**:
- Check file extensions match `--include` patterns
- Verify code contains fetch/axios/WebSocket calls
- Check excluded directories don't contain target files
- Enable verbose logging: `llm4reverse -v audit --path ...`

#### 5. HAR File Empty or Missing

**Problem**: `traffic.har` is empty or not generated

**Solution**:
- Increase `--timeout` value
- Try `--no-headless` to see browser behavior
- Check target URL is accessible
- Verify Playwright browser is installed

#### 6. JSON Parsing Errors in Reports

**Problem**: LLM returns non-JSON output

**Solution**:
- This is handled automatically (raw text stored)
- Check `*_trace.json` for LLM reasoning
- May indicate LLM model incompatibility
- Try different model or adjust temperature

### Debug Mode

Enable verbose logging:

```bash
llm4reverse -v audit --path ./src
llm4reverse -v reverse --url https://example.com
```

This shows:
- File scanning progress
- Regex extraction results
- Symbol index building
- LLM API calls
- Error details with tracebacks

### Getting Help

1. Check this README
2. Review `*_trace.json` files for LLM reasoning
3. Enable verbose logging (`-v` flag)
4. Open an issue on GitHub with:
   - Error message
   - Command used
   - Relevant log output
   - Environment details (OS, Python version, etc.)

---

## ❓ FAQ

### Q: Can I use this with local LLM models?

**A**: Yes! Set `BASE_URL` to your local OpenAI-compatible API endpoint (e.g., `http://localhost:11434/v1`).

### Q: How accurate are the extracted endpoints?

**A**: Accuracy depends on:
- Code quality and patterns
- LLM model capabilities
- Network traffic completeness (for dynamic reverse)

Always validate findings manually before use in production.

### Q: Does this work with minified JavaScript?

**A**: Partially. Regex patterns can detect URLs and basic patterns, but symbol resolution and code analysis work better with readable code. Consider using a JavaScript beautifier first.

### Q: Can I customize the regex patterns?

**A**: Yes, edit `llm4reverse/audit/extractors/regex_extractor.py` and modify the pattern lists.

### Q: How do I exclude specific files (not just directories)?

**A**: Currently, only directory exclusion is supported. File-level filtering can be added by modifying `scanner.py`.

### Q: What's the difference between static audit and dynamic reverse?

**A**:
- **Static audit**: Analyzes source code without running it. Finds endpoints defined in code.
- **Dynamic reverse**: Captures actual network traffic. Finds endpoints that are actually called at runtime.

Both approaches are complementary and can reveal different endpoints.

### Q: Can I use this for API documentation generation?

**A**: Yes! The generated reports can serve as a starting point for API documentation, though manual review and enhancement is recommended.

### Q: Is this tool safe to use on production systems?

**A**: The tool itself is safe, but:
- Only use on systems you own or have explicit permission to test
- Be aware of rate limits and API costs
- Review generated reports before sharing

### Q: How do I contribute?

**A**: See the [Contributing](#contributing) section below.

---

## 🔐 Ethics & Legal

### Important Disclaimer

**LLM4Reverse is a tool for security research, API documentation, and legitimate reverse engineering purposes only.**

### Usage Guidelines

- ✅ **DO**: Use on codebases you own or have explicit permission to analyze
- ✅ **DO**: Use for security research with proper authorization
- ✅ **DO**: Use for understanding your own applications
- ❌ **DON'T**: Use on systems without permission
- ❌ **DON'T**: Use for malicious purposes
- ❌ **DON'T**: Violate terms of service or laws

### Legal Responsibility

Users are solely responsible for ensuring their use of LLM4Reverse complies with:
- Applicable laws and regulations
- Terms of service of target systems
- Ethical guidelines for security research

The authors and contributors of LLM4Reverse assume no liability for misuse of this tool.

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

### How to Contribute

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes**: Follow the development guidelines
4. **Test your changes**: Run tests and ensure they pass
5. **Update documentation**: Keep README and docstrings in sync
6. **Commit your changes**: Use clear, descriptive commit messages
7. **Push to your fork**: `git push origin feature/your-feature-name`
8. **Open a Pull Request**: Provide a clear description of changes

### Contribution Guidelines

- **Code style**: Follow PEP 8, use type hints, write docstrings
- **Testing**: Add tests for new features
- **Documentation**: Update README for user-facing changes
- **Compatibility**: Maintain Python 3.10+ compatibility
- **Ethics**: Ensure contributions align with ethical use guidelines

### Areas for Contribution

- Additional regex patterns for endpoint detection
- Support for more programming languages
- Improved LLM prompts for better accuracy
- Performance optimizations
- Additional report formats (HTML, PDF, etc.)
- Better error messages and user experience
- Documentation improvements

### Reporting Issues

When reporting issues, please include:
- Description of the problem
- Steps to reproduce
- Expected vs. actual behavior
- Environment details (OS, Python version, etc.)
- Relevant log output (with sensitive data redacted)

---

## 📝 License

This project is licensed under the **MIT License**.

See [LICENSE](LICENSE) file for details.

Copyright © 2025 [@BruceWen1](https://github.com/BruceWen1)

---

## 🙏 Acknowledgments

- **LangChain**: For the excellent LLM framework and agent orchestration
- **Playwright**: For robust browser automation and HAR capture
- **OpenAI**: For the API format that enabled compatibility with many providers
- **Community**: For feedback, contributions, and support

---

## 🗺️ Roadmap

Future improvements planned:

- [ ] Enhanced AST-based code analysis (beyond regex)
- [ ] Interactive mode for reviewing findings
- [ ] Integration with API testing tools
- [ ] Support for GraphQL schema extraction
- [ ] Web UI for report visualization
- [ ] Batch processing for multiple targets
- [ ] Export to OpenAPI/Swagger format
- [ ] Performance optimizations (parallel LLM calls, caching)
- [ ] Better handling of minified/obfuscated code
