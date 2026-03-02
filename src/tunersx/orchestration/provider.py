from __future__ import annotations

import json
import subprocess
from pathlib import Path


def run_active_operations_provider(tool_cmd: list[str], out_dir: Path, timeout_s: int = 30) -> dict:
    """Orchestration-only provider wrapper.

    Runs provider tool command, captures stdout/stderr/rc, and packs artifacts to out_dir.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(tool_cmd, capture_output=True, text=True, timeout=timeout_s)
    (out_dir / "provider_stdout.txt").write_text(proc.stdout, encoding="utf-8")
    (out_dir / "provider_stderr.txt").write_text(proc.stderr, encoding="utf-8")
    meta = {
        "tool_cmd": tool_cmd,
        "returncode": proc.returncode,
        "stdout_file": "provider_stdout.txt",
        "stderr_file": "provider_stderr.txt",
    }
    (out_dir / "provider_result.json").write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")
    return meta
