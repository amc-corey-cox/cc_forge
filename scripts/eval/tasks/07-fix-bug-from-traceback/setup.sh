#!/bin/bash
set -e

git init -q
git config user.email "eval@forge.local"
git config user.name "Eval Setup"

cat > config.py <<'PY'
def get_settings():
    return {
        "output_format": "csv",
        "delimiter": None,
        "include_header": True,
    }
PY

cat > formatter.py <<'PY'
def format_rows(headers, rows, delimiter):
    lines = []
    if headers:
        lines.append(delimiter.join(headers))
    for row in rows:
        lines.append(delimiter.join(str(v) for v in row))
    return "\n".join(lines)
PY

cat > app.py <<'PY'
from config import get_settings
from formatter import format_rows

def generate_report(data):
    settings = get_settings()
    headers = list(data[0].keys())
    rows = [list(d.values()) for d in data]
    return format_rows(
        headers if settings["include_header"] else None,
        rows,
        settings["delimiter"],
    )
PY

cat > check.py <<'PY'
from app import generate_report

data = [
    {"name": "Alice", "score": 95},
    {"name": "Bob", "score": 87},
]
result = generate_report(data)
expected = "name,score\nAlice,95\nBob,87"
assert result == expected, f"Expected:\n{expected}\n\nGot:\n{result}"
print("OK")
PY

git add .
git commit -qm "init"
