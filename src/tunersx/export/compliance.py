from __future__ import annotations

import json
import shutil
from pathlib import Path

from tunersx.audit.integrity import verify_bundle


def export_compliance(bundle: Path, out: Path, include_bundle: bool = False) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    ok, report = verify_bundle(bundle)
    (out / 'verification_report.json').write_text(json.dumps(report, indent=2, sort_keys=True), encoding='utf-8')
    manifest = json.loads((bundle / 'manifest.json').read_text(encoding='utf-8'))
    (out / 'policy_snapshot.json').write_text(json.dumps(manifest.get('policy_snapshot', {}), indent=2, sort_keys=True), encoding='utf-8')
    (out / 'registry_versions.json').write_text(json.dumps(manifest.get('software', {}), indent=2, sort_keys=True), encoding='utf-8')
    (out / 'environment.json').write_text(json.dumps({"tool": "tunersx", "verify_ok": ok}, indent=2, sort_keys=True), encoding='utf-8')
    (out / 'run_summary.md').write_text(f"# Compliance Export\n\n- Verify: {'OK' if ok else 'FAIL'}\n", encoding='utf-8')
    if include_bundle:
        dst = out / 'bundle'
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(bundle, dst)
    return out
