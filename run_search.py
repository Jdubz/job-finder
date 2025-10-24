#!/usr/bin/env python3
"""
DEPRECATED: Use run_job_search_unified.py instead.

This file now wraps the unified script for backward compatibility.
"""

import subprocess
import sys

print("⚠️  run_search.py is deprecated. Please use run_job_search_unified.py")
print("   Forwarding to unified script with --mode=quick --max-jobs=30...\n")

# Forward to unified script with quick mode and max-jobs=30
result = subprocess.run(
    [sys.executable, "run_job_search_unified.py", "--mode=quick", "--max-jobs=30"],
    cwd=sys.path[0] if sys.path else ".",
)

sys.exit(result.returncode)
