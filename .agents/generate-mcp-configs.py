#!/usr/bin/env python3
"""Regenerate .mcp.json and .cursor/mcp.json from mcp.servers.yaml."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    try:
        from devharness.mcp_gen import generate_mcp_configs
        lines: list[str] = []
        generate_mcp_configs(ROOT, lines)
        for line in lines:
            print(f"  • {line}")
        return 0
    except ImportError:
        pass
    # Fallback: call dvh if installed
    try:
        return subprocess.call(["dvh", "mcp", str(ROOT)])
    except FileNotFoundError:
        print(
            "Neither the devharness package nor the dvh CLI is available.\n"
            "Install with: ./install.sh   (or: uv tool install <devharness-repo>)",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
