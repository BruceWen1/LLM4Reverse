#!/usr/bin/env bash
set -e
python - <<'PY'
import importlib.util, sys
spec = importlib.util.find_spec("playwright")
if spec is None:
    sys.exit("Playwright is not installed. Run: pip install -r requirements.txt or pip install llm4reverse.")
PY
python -m playwright install
echo "Playwright browsers installed."
