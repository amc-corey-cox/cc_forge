#!/bin/bash
# Pass if app.hello has a non-empty __doc__ after the agent run.
set -e

[ -f app.py ] || { echo "app.py missing"; exit 2; }

python3 -c '
import sys
import importlib.util
spec = importlib.util.spec_from_file_location("app", "app.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
doc = getattr(mod.hello, "__doc__", None)
if not doc or not doc.strip():
    sys.exit(1)
'
