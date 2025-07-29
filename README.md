<p align="right">
  English | <a href="README_zh.md">中文</a>
</p>
# 🔍 LLM4Reverse

**LLM4Reverse** is an expert‑oriented toolkit that automates **front‑end reverse engineering** with the help of Modern LLMs and lightweight agents.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
 ![Python](https://img.shields.io/badge/python-3.10%2B-blue)
 ![Status](https://img.shields.io/badge/status-alpha-orange)

------

## ✨ Features

- **Headless capture** — Collect network requests, console logs and a trimmed DOM snapshot via Playwright.
- **JS beautification & hints** — Prettify minified code and surface token‑like strings, API paths, *fetch*/XHR URLs.
- **Optional AST extraction** — Use Node + esprima to list identifiers, literals and hidden endpoints.
- **LLM reasoning** — Feed evidence to an OpenAI‑compatible model and receive a concise Markdown report.
- **CLI first** — One command does all; install extras only when you need them.

------

## 🧱 Architecture & Project Layout

**Runtime dataflow**

```text
CLI (llm4reverse)
      │
      ├── BrowserTool (Playwright)
      │      └─ Collect: requests(method/url/status/postDataSnippet), console logs, domSnippet
      │
      ├── JSBeautifyTool (jsbeautifier + regex hints)
      │      └─ Output: beautified code, token-like strings, "/api/..." paths, fetch/xhr URLs
      │
      ├── JS AST (optional; Node + esprima)
      │      └─ Output: identifiers, stringLiterals, fetchUrls, xhrUrls
      │
      └── ReverseAgent (optional LLM)
             └─ Input: evidence JSON  →  Output: reverse_report.md
```

**Repository layout**

```text
LLM4Reverse/
├─ llm4reverse/
│  ├─ cli.py               # CLI entrypoints and argument parsing
│  ├─ agent.py             # ReverseAgent: prompt + reasoning
│  ├─ llm_client.py        # Minimal OpenAI-compatible client
│  ├─ report.py            # Artifact writers (json/md)
│  └─ tools/
│     ├─ browser.py        # Playwright capture wrapper
│     ├─ js_beautify.py    # jsbeautifier + regex hints
│     ├─ static_audit.py   # directory‑level static audit (fetch/xhr/axios/$.ajax + const propagation)
│     └─ js_ast.py         # Node + esprima runner (embedded script)
├─ scripts/
│  └─ install_playwright.sh
├─ README.md
├─ pyproject.toml
├─ requirements.txt
└─ LICENSE
```

**Design principles**

- Expert‑first: minimal magic; each module is small, explicit and well‑documented.
- Optional dependencies: Playwright/Node only when needed; graceful degradation with clear errors.
- Reproducible outputs: JSON+MD artifacts with stable field names for downstream tooling.
- Safe by default: DOM is trimmed; request bodies are truncated; LLM usage is opt‑in.

------

## ⚙️ Requirements

- Python 3.10+
- *Optional* — Node 18+ (for `--ast`)
- *Optional* — Playwright browsers (Chromium) ➜ `llm4reverse playwright-install`
- *Optional* — OpenAI‑compatible API (`OPENAI_API_KEY`)

------

## 📦 Installation

```bash
# clone & install editable (recommended for hacking)
git clone https://github.com/BruceWen1/LLM4Reverse.git
cd LLM4Reverse
pip install -e .

# install Playwright browsers (if you plan to capture pages)
llm4reverse playwright-install
```

Set environment variables in **.env** or via shell:

```text
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=      # optional, for Azure-OpenAI or self‑hosted endpoint
OPENAI_MODEL=gpt-4o
```

*To enable AST*:  `npm install -g esprima`  *(or local project install)*

------

## 🚀 Quickstart

```bash
# evidence only (no LLM)
llm4reverse reverse --url https://example.com --no-llm

# add a JS file for beautify / scan
llm4reverse reverse --url https://example.com \
                   --jsfile ./app.min.js --no-llm

# trigger a click after page load
llm4reverse reverse --url https://example.com --click "#login" --no-llm

# include AST (requires Node + esprima)
llm4reverse reverse --url https://example.com \
                   --jsfile ./app.min.js --ast --no-llm

# full pipeline with LLM summary
env OPENAI_API_KEY=sk-... \
llm4reverse reverse --url https://example.com \
                   --jsfile ./app.min.js --ast
```

Output (default **./artifacts**):

```
reverse_report.md    # LLM summary (when not --no-llm)
static_findings.json # endpoint candidates (from static-audit)
static_report.md     # LLM summary for static audit (with --with-llm)
capture.json         # requests / console / domSnippet
js_beautify.json     # prettified JS + regex hints (when --jsfile)
js_ast.json          # AST summary (when --ast)
```

------

## 🧰 CLI Reference

```text
llm4reverse playwright-install
    Install Playwright browsers (Chromium).

llm4reverse reverse --url URL [options]
    --click CSS      click once after load
    --wait-ms INT    wait after load/click  (default 2500)
    --jsfile FILE    local JS for beautify / scan
    --ast            enable Node + esprima AST
    --no-browser     skip Playwright capture
    --show-browser   run non‑headless browser
    --outdir DIR     output directory  (default ./artifacts)
    --model NAME     override OPENAI_MODEL
    --base-url URL   override OPENAI_BASE_URL
    --no-llm         evidence only, no LLM reasoning

llm4reverse static-audit --path PATH [options]
    --include GLOB   repeatable; default includes js/mjs/ts/jsx/tsx
    --exclude GLOB   repeatable; exclude matching files
    --max-files N    cap number of scanned files (default 1000)
    --with-llm       summarize findings with LLM → static_report.md
    --outdir DIR     output directory (default ./artifacts)
    --model NAME     override OPENAI_MODEL (with --with-llm)
    --base-url URL   override OPENAI_BASE_URL (with --with-llm)
```

Exit codes: 0 = success, 2 = jsfile not found, other = error.

------

## 📁 Project Structure (Detailed)

**Module responsibilities**

- `llm4reverse/cli.py` — CLI surface; wires arguments → workflow; handles Playwright install; writes artifacts.
- `llm4reverse/agent.py` — Loads a fixed system prompt, sends evidence to the LLM, returns Markdown.
- `llm4reverse/llm_client.py` — Thin OpenAI‑compatible client; honors `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`.
- `llm4reverse/report.py` — Consolidated writers for `capture.json`, `js_beautify.json`, `js_ast.json`, `reverse_report.md`.
- `llm4reverse/tools/browser.py` — Playwright capture; best‑effort response status correlation; DOM prettify + trim.
- `llm4reverse/tools/js_beautify.py` — Beautify JS; extract conservative regex hints (token/auth/jwt, `/api/...`, fetch/xhr).
- `llm4reverse/tools/js_ast.py` — Runs a tiny Node script that requires `esprima`; returns identifiers/literals/URLs.

**Coding conventions**

- Google‑style docstrings, type hints, explicit error messages.
- Keep functions small; no hidden retries; propagate structured errors in JSON.

------

## 🔧 Configuration

Environment variables (via shell or `.env`):

```text
OPENAI_API_KEY   # required to enable LLM reasoning
OPENAI_BASE_URL  # optional; custom OpenAI‑compatible endpoint
OPENAI_MODEL     # optional; default: gpt-4o
```

Runtime flags of interest:

- `--no-llm`  : disable LLM; only artifacts are produced.
- `--no-browser` / `--show-browser` : skip capture or run interactive Chrome.
- `--wait-ms` : increase if the page triggers late XHR; decrease for faster runs.
- `--ast`     : requires Node 18+ and `npm i -g esprima` (or local install).

Playwright install (once per machine/user):

```bash
llm4reverse playwright-install
```

AST prerequisites:

```bash
# global
npm install -g esprima
# or local in any working dir
npm init -y && npm i esprima
```

------

## 🧪 Usage Recipes

**Evidence‑only sweep (quick triage)**

```bash
llm4reverse reverse --url https://target.site --no-llm
```

**Static‑only JS review**

```bash
llm4reverse reverse --url https://dummy --no-browser --jsfile ./app.min.js --no-llm
```

**AST‑assisted string/URL discovery**

```bash
llm4reverse reverse --url https://dummy --no-browser --jsfile ./app.min.js --ast --no-llm
```

**Trigger one interaction then collect**

```bash
llm4reverse reverse --url https://target.site --click "#login" --no-llm
```

**Full run with LLM summary**

```bash
export OPENAI_API_KEY=sk-...
llm4reverse reverse --url https://target.site --jsfile ./app.min.js --ast
```

Tips

- Combine `--click` with a larger `--wait-ms` if the page defers XHR after UI actions.
- For SPA with route changes, run multiple passes with different `--click` selectors.
- Consider saving raw JS separately to keep `artifacts/` small.

------

## 📤 Output Files (format & notes)

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

- Sections: `Targets`, `Findings (APIs, Params, Headers, Tokens)`, `Risks / Weak points`, `Suggested next steps`.
- Keep in VCS for audit trails; redact secrets if any were captured.

------

## 🧩 Module Reference

- `BrowserTool.capture(url, click_selector, wait_after_ms, include_dom)` → dict with `requests`, `console`, `domSnippet`.
- `JSBeautifyTool.run(code)` → dict with `beautified` and `patterns`.
- `try_extract_ast(code)` → dict with `identifiers`, `stringLiterals`, `fetchUrls`, `xhrUrls` or `{error}`.
- `ReverseAgent.reason(evidence)` → Markdown summary string.
- `save_artifacts(outdir, ...)` → writes JSON/MD to disk.

------

## 🧱 Development Guide

- Style: type hints + Google‑style docstrings; small, composable functions.
- Extending patterns: add conservative regex to `js_beautify.py` and document false‑positive risk.
- Custom prompts: tweak the embedded prompt in `agent.py` for your domain (e.g., auth signatures, anti‑bot flows).
- New tools: add under `llm4reverse/tools/` and wire in `cli.py`; prefer explicit flags over implicit behavior.
- Reproducibility: keep artifact schemas stable; version bump if you change fields.

------

## ⚠️ Notes & Limitations

- No de‑obfuscation beyond beautify + hints; complex packers require custom logic.
- Status matching is best‑effort; heavily async apps may interleave responses.
- LLM summaries do not replace manual verification; always validate with real requests.

------

## ❓ FAQ (selected)

**Playwright missing?**  Install Python package and browsers:

```bash
pip install -r requirements.txt
llm4reverse playwright-install
```

**Node/esprima missing?**  Install Node 18+ and:

```bash
npm install -g esprima
# or: npm init -y && npm i esprima
```

**No API key?**  Use `--no-llm` to skip reasoning and inspect artifacts only.

**Large artifacts?**  Reduce `--wait-ms`, skip DOM (`include_dom=False` in custom code), or post‑process JSON.

------

## 🔐 Ethics & Legal

Use this toolkit **only** on assets you own or have explicit permission to test.
 Violating terms, policies or laws is **your** responsibility.

------

## 🗺️ Roadmap

- String / constant propagation de‑obfuscator
- Chrome DevTools Protocol coverage & source‑map support
- Guided click‑path explorer
- Risk scoring + PoC scaffolding
- Simple Web UI playground

------

## 📝 License

MIT License © 2025 [@BruceWen1](https://github.com/BruceWen1)

------

## 🤝 Contributing

Pull requests and issues are welcome.
 Please follow Google‑style docstrings, keep README sections in sync, and respect the ethical disclaimer.