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

    ok, verify = verify_bundle(bundle_dir)
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    anomalies = sorted(_load_jsonl(bundle_dir / "anomalies.jsonl"), key=lambda a: (a["severity"], a["id"]))
    signals = _load_jsonl(bundle_dir / "signals.jsonl")

    capture_quality = manifest.get("capture_stats", {})
    decoded = len([s for s in signals if s.get("source") == "DBC"])
    coverage = {
        "decoded_signals": decoded,
        "total_signals": len(signals),
        "top_unknown_ids": capture_quality.get("top_unknown_ids", []),
    }

    (report_dir / "anomaly_queue.json").write_text(json.dumps(anomalies, indent=2, sort_keys=True), encoding="utf-8")
    (report_dir / "capture_quality.json").write_text(json.dumps(capture_quality, indent=2, sort_keys=True), encoding="utf-8")
    (report_dir / "decode_coverage.json").write_text(json.dumps(coverage, indent=2, sort_keys=True), encoding="utf-8")

    readiness = {}
    rp = bundle_dir / "readiness.json"
    if rp.exists():
        readiness = json.loads(rp.read_text(encoding="utf-8"))
        (report_dir / "readiness.json").write_text(json.dumps(readiness, indent=2, sort_keys=True), encoding="utf-8")


    health = {
        "integrity_status": "PASS" if ok else "FAIL",
        "policy_mode": manifest.get("policy_snapshot", {}).get("risk_class"),
        "arming_status": manifest.get("policy_snapshot", {}).get("armed"),
        "versions": manifest.get("software", {}),
        "anomaly_count": len(anomalies),
        "rlink_readiness": readiness.get("overall_ok") if readiness else None,
    }
    (report_dir / "health_report.json").write_text(json.dumps(health, indent=2, sort_keys=True), encoding="utf-8")

    md = [
        "# TUNERSX Health Report",
        f"- Integrity Banner: **{'PASS' if ok else 'FAIL'}**",
        f"- Policy Mode: **{health['policy_mode']}**",
        f"- Arming Active: **{health['arming_status']}**",
        f"- Versions: {health['versions']}",
        "",
        "## Anomaly Queue",
    ]
    for a in anomalies:
        md.append(f"- {a['id']} [{a['severity']}] {a['channels']} evidence={a['evidence_pointers']}")
    if readiness:
        md.append("\n## RLink Readiness")
        md.append(f"- Overall OK: {readiness.get('overall_ok')}")
    md.append("\n## Signals (units/source/confidence)")
    for s in signals[:30]:
        md.append(f"- {s['timestamp']} {s['channel']}={s['value']} {s.get('unit','')} source={s.get('source')} conf={s.get('confidence')} evidence={s.get('evidence_pointer')}")
    (report_dir / "health_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    html = f"""<!doctype html><html><body>
<div style='padding:8px;background:{'#d1fae5' if ok else '#fecaca'}'><b>Integrity: {'PASS' if ok else 'FAIL'}</b> | Policy: {health['policy_mode']} | Armed: {health['arming_status']}</div>
<h1>TUNERSX Dashboard</h1>
<p>Schema: {health['versions'].get('bundle_schema_version')} DBC: {health['versions'].get('dbc_version')} Registry: {health['versions'].get('registry_version')} Vehicle Profile: {health['versions'].get('vehicle_profile_version')}</p>
<p>Anomalies: {len(anomalies)}</p>
<p>RLink readiness: {readiness.get('overall_ok') if readiness else "n/a"}</p>
</body></html>"""
    (report_dir / "index.html").write_text(html, encoding="utf-8")

    verify_txt = "Offline verification:\n1) run tunersx trace verify bundle\n2) compare SHA256SUMS.txt\n"
    (report_dir / "VERIFY.txt").write_text(verify_txt, encoding="utf-8")

    bundle_files = sorted({p for p in bundle_dir.iterdir() if p.is_file() and p.suffix in {'.json', '.jsonl', '.csv'}})
    sums = []
    from tunersx.audit.integrity import sha256_file
    for p in bundle_files:
        sums.append(f"{sha256_file(p)}  {p.name}")
    (report_dir / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")
    (report_dir / "POLICY_SNAPSHOT.json").write_text(json.dumps(manifest.get("policy_snapshot", {}), indent=2, sort_keys=True), encoding="utf-8")

    zip_path = report_dir / "reviewer_pack.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in bundle_files:
            zf.write(p, arcname=f"bundle/{p.name}")
        for p in sorted(report_dir.iterdir()):
            if p.name == "reviewer_pack.zip":
                continue
            zf.write(p, arcname=f"report/{p.name}")

    return report_dir
