# -*- coding: utf-8 -*-
"""
AST extraction via Node + esprima.

- No bundled esprima to keep package light.
- Users can `npm i -g esprima` or install locally.
- We embed a small Node script as a string and run it with the user's Node.

Behavior:
- If Node is missing => {"error": "..."}.
- If esprima missing or parse error => surfaced in error string.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from typing import Any, Dict, Optional


_NODE_SCRIPT = r"""
const fs = require("fs");
let esprima;
try {
  esprima = require("esprima");
} catch (e) {
  console.error("Esprima is required. Install with: npm install esprima");
  process.exit(2);
}

function walk(node, visit) {
  if (!node || typeof node !== "object") return;
  visit(node);
  for (const k of Object.keys(node)) {
    const c = node[k];
    if (Array.isArray(c)) for (const x of c) walk(x, visit);
    else walk(c, visit);
  }
}

function extract(ast) {
  const ids = new Set();
  const lits = new Set();
  const fetchUrls = new Set();
  const xhrUrls = new Set();

  walk(ast, (n) => {
    if (n.type === "Identifier") ids.add(n.name);
    if (n.type === "Literal" && typeof n.value === "string") lits.add(n.value);

    if (n.type === "CallExpression" &&
        n.callee && n.callee.type === "Identifier" && n.callee.name === "fetch" &&
        n.arguments && n.arguments[0] &&
        n.arguments[0].type === "Literal" && typeof n.arguments[0].value === "string") {
      fetchUrls.add(n.arguments[0].value);
    }

    if (n.type === "CallExpression" &&
        n.callee && n.callee.type === "MemberExpression" &&
        n.callee.property && n.callee.property.type === "Identifier" &&
        n.callee.property.name === "open" &&
        n.arguments && n.arguments.length >= 2) {
      const methodArg = n.arguments[0];
      const urlArg = n.arguments[1];
      if (methodArg.type === "Literal" && urlArg.type === "Literal") {
        xhrUrls.add(String(urlArg.value));
      }
    }
  });

  return {
    identifiers: Array.from(ids),
    stringLiterals: Array.from(lits),
    fetchUrls: Array.from(fetchUrls),
    xhrUrls: Array.from(xhrUrls),
  };
}

function main() {
  const file = process.argv[2];
  if (!file) {
    console.error("Usage: node <script> input.js");
    process.exit(1);
  }
  const code = fs.readFileSync(file, "utf8");
  let ast;
  try {
    ast = esprima.parseScript(code, { tolerant: true, loc: false, range: false });
  } catch (e) {
    console.error("Parse error: " + String(e));
    process.exit(3);
  }
  const result = extract(ast);
  process.stdout.write(JSON.stringify(result));
}

main();
"""


def _node_bin() -> Optional[str]:
    """Return path to node executable if present in PATH."""
    return shutil.which("node")


def try_extract_ast(code: str) -> Dict[str, Any]:
    """Extract JS AST info using Node + esprima.

    Args:
        code: Raw JavaScript source.

    Returns:
        Dict[str, Any]: AST summary or {"error": "..."}.
    """
    node = _node_bin()
    if not node:
        return {"error": "Node.js not found in PATH."}

    with tempfile.NamedTemporaryFile("w+", suffix=".js", delete=False, encoding="utf-8") as src_f:
        src_f.write(code)
        src_f.flush()
        src_path = src_f.name

    with tempfile.NamedTemporaryFile("w+", suffix=".js", delete=False, encoding="utf-8") as tool_f:
        tool_f.write(_NODE_SCRIPT)
        tool_f.flush()
        tool_path = tool_f.name

    try:
        out = subprocess.check_output([node, tool_path, src_path], stderr=subprocess.STDOUT, text=True)
        return json.loads(out)
    except subprocess.CalledProcessError as e:
        return {"error": f"Node execution failed: {e.output.strip()}"}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}
