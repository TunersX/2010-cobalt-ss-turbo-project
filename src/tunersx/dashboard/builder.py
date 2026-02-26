from __future__ import annotations

import json
import zipfile
from pathlib import Path

from tunersx.audit.integrity import verify_bundle


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_dashboard(bundle_dir: Path) -> Path:
    report_dir = bundle_dir / "report"
    report_dir.mkdir(exist_ok=True)

    ok, errors = verify_bundle(bundle_dir)
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    anomalies = _load_jsonl(bundle_dir / "anomalies.jsonl")
    signals = _load_jsonl(bundle_dir / "signals.jsonl")[:20]

    (report_dir / "anomaly_queue.json").write_text(json.dumps(anomalies, indent=2), encoding="utf-8")

    lines = [
        "# TUNERSX Health Report",
        "",
        f"- Integrity: {'PASS' if ok else 'FAIL'}",
        f"- Policy Mode: {manifest.get('policy_mode')}",
        f"- Schema Version: {manifest.get('schema_version')}",
        f"- Registry Version: {manifest.get('registry_version')}",
        f"- DBC Version: {manifest.get('dbc_version')}",
        "",
        "## Anomalies",
    ]
    if anomalies:
        for a in anomalies:
            lines.append(
                f"- [{a['severity']}] {a['channel']}: {a['description']} (evidence: {a['evidence']})"
            )
    else:
        lines.append("- No anomalies detected")

    lines.extend(["", "## Signal Preview (with units/source/confidence)"])
    for s in signals:
        lines.append(
            f"- {s['timestamp']} {s['channel']}={s['value']} {s['unit']} source={s['source']} confidence={s['confidence']} evidence=signals.jsonl:{s['frame_index']+1}"
        )

    if errors:
        lines.extend(["", "## Integrity Errors"] + [f"- {e}" for e in errors])

    (report_dir / "health_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    html = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>TUNERSX Report</title></head>
<body>
<h1>TUNERSX Summary</h1>
<p>Integrity: <strong>{'PASS' if ok else 'FAIL'}</strong></p>
<p>Policy mode: <strong>{manifest.get('policy_mode')}</strong></p>
<p>Schema {manifest.get('schema_version')} | Registry {manifest.get('registry_version')} | DBC {manifest.get('dbc_version')}</p>
<p>Anomaly count: {len(anomalies)}</p>
</body></html>"""
    (report_dir / "index.html").write_text(html, encoding="utf-8")

    summary = report_dir / "summary.txt"
    summary.write_text("TUNERSX reviewer pack\n", encoding="utf-8")

    zip_path = report_dir / "reviewer_pack.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in ["manifest.json", "frames.jsonl", "signals.jsonl", "anomalies.jsonl", "audit.jsonl", "hashes.json"]:
            zf.write(bundle_dir / name, arcname=name)
        for name in ["health_report.md", "anomaly_queue.json", "index.html", "summary.txt"]:
            zf.write(report_dir / name, arcname=f"report/{name}")

    return report_dir
