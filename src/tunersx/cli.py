from __future__ import annotations

import argparse
import json
import random
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tunersx import __version__
from tunersx.audit.integrity import AuditLogger, build_hashes, verify_bundle, write_manifest
from tunersx.core.config import AppConfig
from tunersx.core.session import clear_session, load_session, save_session
from tunersx.core.types import PipelineState, RiskClass
from tunersx.dashboard.builder import build_dashboard
from tunersx.decode.anomalies import detect_anomalies
from tunersx.decode.dbc_loader import load_dbc_map
from tunersx.decode.pipeline import decode_frames_to_signals, write_unknown_frames_csv
from tunersx.export.compliance import export_compliance
from tunersx.integrity.signing import sign_file, verify_file_signature
from tunersx.policy.capabilities import Capability
from tunersx.policy.enforcer import PolicySnapshot
from tunersx.policy.engine import check_capability
from tunersx.privacy.scrub import scrub_bundle
from tunersx.transports.demo import generate_demo_frames
from tunersx.transports.j2534_readiness import J2534Backend
from tunersx.orchestration.provider import run_active_operations_provider
from tunersx.calib.cap import pack_calibration, verify_calibration, diff_calibrations

REQUIRED_FILES = ["frames.jsonl", "signals.jsonl", "anomalies.jsonl", "audit.jsonl"]


def _ensure_bundle(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_FILES:
        p = path / name
        if not p.exists():
            p.write_text("", encoding="utf-8")


def _audit_decision(audit: AuditLogger, policy: PolicySnapshot, command_id: str, actor: str = "cli") -> tuple[bool, str, str]:
    allowed, rule, reason = policy.evaluate(command_id)
    audit.log("policy", actor, policy.state.value, command_id, "ALLOW" if allowed else "DENY", {"rule_id": rule, "reason": reason})
    return allowed, rule, reason


def _cap_set(values: list[str] | None) -> set[Capability]:
    if not values:
        return {Capability.PASSIVE_CAPTURE, Capability.EXPORT_REPORT}
    return {Capability(v) for v in values}


def _package_bundle(bundle: Path, cfg: AppConfig, dbc_version: str, policy: PolicySnapshot, capture_stats: dict, transport_config: dict) -> None:
    hashes = build_hashes(bundle, REQUIRED_FILES)
    (bundle / "hashes.json").write_text(json.dumps(hashes, indent=2, sort_keys=True), encoding="utf-8")
    write_manifest(
        bundle,
        hashes,
        versions={
            "app_version": __version__,
            "bundle_schema_version": cfg.bundle_schema_version,
            "registry_version": cfg.registry_version,
            "dbc_version": dbc_version,
            "vehicle_profile_version": cfg.vehicle_profile_version,
        },
        policy_snapshot={"risk_class": policy.risk_class.value, "state": policy.state.value, "armed": policy.armed},
        capture_stats=capture_stats,
        transport_config=transport_config,
    )


def cmd_session_start(args: argparse.Namespace) -> int:
    cfg = AppConfig()
    bundle = Path(args.out)
    _ensure_bundle(bundle)
    policy = PolicySnapshot(risk_class=RiskClass.PASSIVE, state=PipelineState.BOOT)
    audit = AuditLogger(bundle / "audit.jsonl")

    caps = _cap_set(args.cap)
    cap_ok, cap_reason = check_capability("session.start", caps)
    if not cap_ok:
        audit.log("policy", "cli", policy.state.value, "session.start", "DENY", {"reason": cap_reason})
        print(cap_reason)
        return 2

    allowed, _, reason = _audit_decision(audit, policy, "session.start")
    if not allowed:
        print(reason)
        return 2

    policy.transition(PipelineState.SELF_TEST)
    policy.transition(PipelineState.IDENTIFY_TARGET)
    policy.target_identified = True
    policy.transition(PipelineState.PASSIVE_CAPTURE)

    if args.transport != "demo":
        audit.log("transport", "cli", policy.state.value, "session.start", "DENY", {"reason": "only demo implemented"})
        return 3
    capture_stats = generate_demo_frames(args.seconds, bundle / "frames.jsonl")

    dbc_map, dbc_version = load_dbc_map(args.dbc)
    decode_stats = decode_frames_to_signals(bundle / "frames.jsonl", bundle / "signals.jsonl", dbc_map, cfg.decode, labels_file=Path(args.labels) if args.labels else None)
    write_unknown_frames_csv(bundle / "unknown_frames.csv", decode_stats["unknown"], args.seconds)
    (bundle / "decode_coverage.json").write_text(json.dumps({k: v for k, v in decode_stats.items() if k != "unknown"}, indent=2, sort_keys=True), encoding="utf-8")

    count, anomalies = detect_anomalies(bundle / "signals.jsonl", bundle / "anomalies.jsonl", cfg.anomaly)
    if args.baseline:
        base = json.loads((Path(args.baseline) / "decode_coverage.json").read_text(encoding="utf-8")) if (Path(args.baseline) / "decode_coverage.json").exists() else {}
        delta = {"decode_coverage_delta": round(decode_stats["decode_coverage_pct"] - float(base.get("decode_coverage_pct", 0)), 3), "anomaly_delta": count}
        (bundle / "delta_report.json").write_text(json.dumps(delta, indent=2, sort_keys=True), encoding="utf-8")

    policy.transition(PipelineState.PACK)
    _package_bundle(bundle, cfg, dbc_version, policy, capture_stats, {"transport": args.transport, "seconds": args.seconds, "buses": ["hs_can"]})
    policy.transition(PipelineState.COMPLETE)
    _package_bundle(bundle, cfg, dbc_version, policy, {**capture_stats, "top_unknown_ids": sorted([k for k, _ in decode_stats["unknown"].items()])[:5], "anomaly_count": len(anomalies)}, {"transport": args.transport, "seconds": args.seconds, "buses": ["hs_can"]})
    save_session(bundle, policy.state, policy.risk_class)
    print(f"session complete: {bundle}")
    return 0


def cmd_session_stop(args: argparse.Namespace) -> int:
    sess = load_session()
    if not sess:
        print("no active session")
        return 0
    bundle = Path(sess["bundle_dir"])
    audit = AuditLogger(bundle / "audit.jsonl")
    policy = PolicySnapshot(risk_class=RiskClass(sess["risk_class"]), state=PipelineState.COMPLETE)
    _audit_decision(audit, policy, "session.stop")
    clear_session()
    print("session stopped")
    return 0


def cmd_trace_pack(args: argparse.Namespace) -> int:
    bundle = Path(args.bundle_dir)
    sig_path = bundle / "signature.json"
    if args.sign_key:
        target = bundle / "manifest.json"
        sig = sign_file(target, Path(args.sign_key))
        sig_path.write_text(json.dumps(sig, indent=2, sort_keys=True), encoding="utf-8")
    print("packed")
    return 0


def cmd_trace_verify(args: argparse.Namespace) -> int:
    bundle = Path(args.bundle_dir)
    ok, payload = verify_bundle(bundle)
    sig_status = "missing"
    if (bundle / "signature.json").exists():
        sig = json.loads((bundle / "signature.json").read_text(encoding="utf-8"))
        sig_ok, sig_status = verify_file_signature(bundle / sig.get("target", "manifest.json"), sig, Path(args.pubkey) if args.pubkey else None)
        if not sig_ok:
            ok = False
    payload["signature_status"] = sig_status
    if args.explain:
        payload["first_failure"] = payload.get("errors", [None])[0] if payload.get("errors") else None
    print(json.dumps(payload, indent=2, sort_keys=True))
    print("OK" if ok else "FAIL")
    return 0 if ok else 1


def cmd_trace_fuzz(args: argparse.Namespace) -> int:
    src = Path(args.bundle)
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out)
    random.seed(args.seed)
    case = args.case
    if case == "delete":
        (out / "signals.jsonl").unlink(missing_ok=True)
    elif case == "hashcorrupt":
        h = json.loads((out / "hashes.json").read_text(encoding="utf-8"))
        k = sorted(h.keys())[0]
        h[k]["sha256"] = "0" * 64
        (out / "hashes.json").write_text(json.dumps(h), encoding="utf-8")
    elif case == "truncate":
        p = out / "frames.jsonl"
        txt = p.read_text(encoding="utf-8")
        p.write_text(txt[: max(1, len(txt) // 2)], encoding="utf-8")
    elif case == "bitflip":
        p = out / "frames.jsonl"
        b = bytearray(p.read_bytes())
        i = random.randrange(len(b))
        b[i] ^= 1
        p.write_bytes(bytes(b))
    elif case == "reorder":
        p = out / "frames.jsonl"
        lines = p.read_text(encoding="utf-8").splitlines()
        lines = list(reversed(lines))
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"fuzzed: {case}")
    return 0


def cmd_trace_scrub(args: argparse.Namespace) -> int:
    scrub_bundle(Path(args.bundle), Path(args.out), args.profile, args.encrypt_private, args.key)
    print("scrubbed")
    return 0



def cmd_rlink_readiness(args: argparse.Namespace) -> int:
    bundle = Path(args.bundle_dir)
    bundle.mkdir(parents=True, exist_ok=True)
    audit = AuditLogger(bundle / "audit.jsonl")
    policy = PolicySnapshot(risk_class=RiskClass.PASSIVE, state=PipelineState.COMPLETE)
    backend = J2534Backend()

    results = {}
    for cmd in ["j2534.enumerate", "j2534.open", "j2534.connect", "j2534.close"]:
        allowed, rule, reason = policy.evaluate(cmd)
        audit.log("policy", "cli", policy.state.value, cmd, "ALLOW" if allowed else "DENY", {"rule_id": rule, "reason": reason})
        if not allowed:
            results[cmd] = {"ok": False, "reason": reason}
            continue
        if cmd == "j2534.enumerate":
            devs = backend.enumerate()
            results[cmd] = {"ok": True, "devices": [d.name for d in devs]}
        elif cmd == "j2534.open":
            results[cmd] = {"ok": backend.open("mock")}
        elif cmd == "j2534.connect":
            results[cmd] = {"ok": backend.connect("CAN", 500000)}
        elif cmd == "j2534.close":
            results[cmd] = {"ok": backend.close()}

    readiness = {
        "report": "RLink Readiness Report",
        "default_mode": "PASSIVE",
        "transport": "j2534",
        "results": results,
        "overall_ok": all(v.get("ok") for v in results.values()),
    }
    (bundle / "readiness.json").write_text(json.dumps(readiness, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(readiness, indent=2, sort_keys=True))
    return 0


def cmd_orchestration_run(args: argparse.Namespace) -> int:
    bundle = Path(args.bundle_dir)
    audit = AuditLogger(bundle / "audit.jsonl")
    policy = PolicySnapshot(risk_class=RiskClass.PASSIVE, state=PipelineState.COMPLETE)
    allowed, rule, reason = policy.evaluate("orchestration.run")
    audit.log("policy", "cli", policy.state.value, "orchestration.run", "ALLOW" if allowed else "DENY", {"rule_id": rule, "reason": reason})
    if not allowed:
        print(reason)
        return 2

    tool_cmd = [args.tool_cmd] + (args.arg or [])
    result = run_active_operations_provider(tool_cmd, bundle / "provider_artifacts", timeout_s=args.timeout)
    (bundle / "active_operations_provider.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def cmd_decode(args: argparse.Namespace) -> int:
    cfg = AppConfig()
    bundle = Path(args.bundle_dir)
    audit = AuditLogger(bundle / "audit.jsonl")
    policy = PolicySnapshot(risk_class=RiskClass.PASSIVE, state=PipelineState.PASSIVE_CAPTURE, target_identified=True)
    allowed, _, reason = _audit_decision(audit, policy, "decode")
    if not allowed:
        print(reason)
        return 2
    dbc_map, dbc_version = load_dbc_map(args.dbc)
    stats = decode_frames_to_signals(bundle / "frames.jsonl", bundle / "signals.jsonl", dbc_map, cfg.decode)
    write_unknown_frames_csv(bundle / "unknown_frames.csv", stats["unknown"], 1)
    (bundle / "decode_coverage.json").write_text(json.dumps({k: v for k, v in stats.items() if k != "unknown"}, indent=2, sort_keys=True), encoding="utf-8")
    detect_anomalies(bundle / "signals.jsonl", bundle / "anomalies.jsonl", cfg.anomaly)
    policy.transition(PipelineState.PACK)
    _package_bundle(bundle, cfg, dbc_version, policy, {}, {"transport": "redecode"})
    print("decode complete")
    return 0


def cmd_dashboard_build(args: argparse.Namespace) -> int:
    bundle = Path(args.bundle_dir)
    audit = AuditLogger(bundle / "audit.jsonl")
    policy = PolicySnapshot(risk_class=RiskClass.PASSIVE, state=PipelineState.PACK)
    allowed, _, reason = _audit_decision(audit, policy, "dashboard.build")
    if not allowed:
        print(reason)
        return 2
    report = build_dashboard(bundle)
    cfg = AppConfig()
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    _package_bundle(bundle, cfg, manifest.get("software", {}).get("dbc_version", "builtin-demo-1.1"), policy, manifest.get("capture_stats", {}), manifest.get("transport_config", {}))
    print(f"dashboard generated: {report}")
    return 0


def cmd_export_compliance(args: argparse.Namespace) -> int:
    b = Path(args.bundle)
    if args.scrub:
        tmp = Path(args.out) / "_scrubbed"
        scrub_bundle(b, tmp, args.scrub)
        b = tmp
    export_compliance(b, Path(args.out), include_bundle=args.include_bundle)
    print("compliance export complete")
    return 0


def cmd_policy_explain(args: argparse.Namespace) -> int:
    print(json.dumps({"default_mode": "PASSIVE", "write_capable_transports": False}, indent=2))
    return 0


def cmd_arm(args: argparse.Namespace) -> int:
    sess = load_session()
    if not sess:
        print("no session")
        return 1
    bundle = Path(sess["bundle_dir"])
    policy = PolicySnapshot(risk_class=RiskClass.PASSIVE, state=PipelineState.COMPLETE)
    audit = AuditLogger(bundle / "audit.jsonl")
    allowed, _, reason = _audit_decision(audit, policy, "arm")
    if not allowed:
        print(reason)
        return 2
    armed_until = (datetime.now(timezone.utc) + timedelta(seconds=args.seconds)).isoformat(timespec="seconds")
    save_session(bundle, PipelineState.COMPLETE, RiskClass.READ_ONLY_DIAG, armed_until=armed_until)
    audit.log("arm", "cli", policy.state.value, "arm", "ALLOW", {"armed_until": armed_until})
    print(f"armed until {armed_until}")
    return 0


def cmd_lockout_reset(args: argparse.Namespace) -> int:
    if args.ack != "RESET_LOCKOUT":
        print("acknowledgement required: RESET_LOCKOUT")
        return 2
    clear_session()
    print("lockout reset")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    report = {"python": "ok", "demo_transport": "ok", "canable": "stub-ready", "j2534": "readiness-only", "pcan": "hook-ready", "kvaser": "hook-ready"}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def cmd_list_transports(args: argparse.Namespace) -> int:
    print("demo\ncanable_passive\nj2534_readiness\npcan_hook\nkvaser_hook")
    return 0


def cmd_schema_print(args: argparse.Namespace) -> int:
    cfg = AppConfig()
    print(json.dumps({"bundle_schema_version": cfg.bundle_schema_version, "registry_version": cfg.registry_version, "policy_version": cfg.policy_version, "vehicle_profile_version": cfg.vehicle_profile_version}, indent=2, sort_keys=True))
    return 0


def cmd_bundle_info(args: argparse.Namespace) -> int:
    b = Path(args.bundle_dir)
    manifest = json.loads((b / "manifest.json").read_text(encoding="utf-8"))
    print(json.dumps({"software": manifest.get("software"), "policy_snapshot": manifest.get("policy_snapshot"), "capture_stats": manifest.get("capture_stats")}, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tunersx")
    parser.add_argument("--version", action="version", version=f"tunersx {__version__}")
    sub = parser.add_subparsers(dest="top", required=True)

    session = sub.add_parser("session")
    ss = session.add_subparsers(dest="session_cmd", required=True)
    start = ss.add_parser("start")
    start.add_argument("--transport", default="demo")
    start.add_argument("--seconds", type=int, default=5)
    start.add_argument("--out", required=True)
    start.add_argument("--dbc")
    start.add_argument("--labels")
    start.add_argument("--baseline")
    start.add_argument("--cap", action="append")
    start.set_defaults(func=cmd_session_start)
    stop = ss.add_parser("stop")
    stop.set_defaults(func=cmd_session_stop)

    trace = sub.add_parser("trace")
    tsub = trace.add_subparsers(dest="trace_cmd", required=True)
    verify = tsub.add_parser("verify")
    verify.add_argument("bundle_dir")
    verify.add_argument("--pubkey")
    verify.add_argument("--explain", action="store_true")
    verify.set_defaults(func=cmd_trace_verify)
    pack = tsub.add_parser("pack")
    pack.add_argument("bundle_dir")
    pack.add_argument("--sign-key")
    pack.set_defaults(func=cmd_trace_pack)
    fuzz = tsub.add_parser("fuzz")
    fuzz.add_argument("--bundle", required=True)
    fuzz.add_argument("--out", required=True)
    fuzz.add_argument("--case", required=True, choices=["bitflip", "truncate", "reorder", "hashcorrupt", "delete"])
    fuzz.add_argument("--seed", type=int, default=1)
    fuzz.set_defaults(func=cmd_trace_fuzz)
    scrub = tsub.add_parser("scrub")
    scrub.add_argument("--bundle", required=True)
    scrub.add_argument("--out", required=True)
    scrub.add_argument("--profile", choices=["public", "shop", "research"], required=True)
    scrub.add_argument("--encrypt-private", action="store_true")
    scrub.add_argument("--key")
    scrub.set_defaults(func=cmd_trace_scrub)

    dec = sub.add_parser("decode")
    dec.add_argument("bundle_dir")
    dec.add_argument("--dbc")
    dec.set_defaults(func=cmd_decode)

    dash = sub.add_parser("dashboard")
    dsub = dash.add_subparsers(dest="dash_cmd", required=True)
    build = dsub.add_parser("build")
    build.add_argument("bundle_dir")
    build.set_defaults(func=cmd_dashboard_build)

    exp = sub.add_parser("export")
    exp_sub = exp.add_subparsers(dest="exp_cmd", required=True)
    compliance = exp_sub.add_parser("compliance")
    compliance.add_argument("--bundle", required=True)
    compliance.add_argument("--out", required=True)
    compliance.add_argument("--scrub", choices=["public", "shop", "research"])
    compliance.add_argument("--include-bundle", action="store_true")
    compliance.set_defaults(func=cmd_export_compliance)

    pol = sub.add_parser("policy")
    pol_sub = pol.add_subparsers(dest="policy_cmd", required=True)
    explain = pol_sub.add_parser("explain")
    explain.set_defaults(func=cmd_policy_explain)

    arm = sub.add_parser("arm")
    arm.add_argument("--seconds", type=int, required=True)
    arm.set_defaults(func=cmd_arm)

    lock = sub.add_parser("lockout-reset")
    lock.add_argument("--ack", required=True)
    lock.set_defaults(func=cmd_lockout_reset)

    doctor = sub.add_parser("doctor")
    doctor.set_defaults(func=cmd_doctor)

    lt = sub.add_parser("list")
    lt_sub = lt.add_subparsers(dest="list_cmd", required=True)
    ltt = lt_sub.add_parser("transports")
    ltt.set_defaults(func=cmd_list_transports)

    schema = sub.add_parser("schema")
    sc_sub = schema.add_subparsers(dest="schema_cmd", required=True)
    pr = sc_sub.add_parser("print")
    pr.set_defaults(func=cmd_schema_print)

    bi = sub.add_parser("bundle")
    bi_sub = bi.add_subparsers(dest="bundle_cmd", required=True)
    inf = bi_sub.add_parser("info")
    inf.add_argument("bundle_dir")
    inf.set_defaults(func=cmd_bundle_info)

    readiness = sub.add_parser("readiness")
    rsub = readiness.add_subparsers(dest="readiness_cmd", required=True)
    rlink = rsub.add_parser("rlink")
    rlink.add_argument("bundle_dir")
    rlink.set_defaults(func=cmd_rlink_readiness)

    orch = sub.add_parser("orchestrate")
    orch_sub = orch.add_subparsers(dest="orch_cmd", required=True)
    run = orch_sub.add_parser("provider")
    run.add_argument("bundle_dir")
    run.add_argument("--tool-cmd", required=True)
    run.add_argument("--arg", action="append")
    run.add_argument("--timeout", type=int, default=30)
    run.set_defaults(func=cmd_orchestration_run)

    calib = sub.add_parser("calib")
    calib_sub = calib.add_subparsers(dest="calib_cmd", required=True)
    cpack = calib_sub.add_parser("pack")
    cpack.add_argument("--input", required=True)
    cpack.add_argument("--out", required=True)
    cpack.add_argument("--vin")
    cpack.add_argument("--module")
    cpack.add_argument("--notes")
    cpack.set_defaults(func=cmd_calib_pack)

    cverify = calib_sub.add_parser("verify")
    cverify.add_argument("cap_dir")
    cverify.set_defaults(func=cmd_calib_verify)

    cdiff = calib_sub.add_parser("diff")
    cdiff.add_argument("cap_a")
    cdiff.add_argument("cap_b")
    cdiff.set_defaults(func=cmd_calib_diff)

    return parser



def cmd_calib_pack(args: argparse.Namespace) -> int:
    meta = {
        "vin": args.vin,
        "module": args.module,
        "notes": args.notes,
    }
    out = pack_calibration(Path(args.input), Path(args.out), meta)
    print(f"CAP packed: {out}")
    return 0


def cmd_calib_verify(args: argparse.Namespace) -> int:
    ok, report = verify_calibration(Path(args.cap_dir))
    print(json.dumps(report, indent=2, sort_keys=True))
    print("OK" if ok else "FAIL")
    return 0 if ok else 1


def cmd_calib_diff(args: argparse.Namespace) -> int:
    report = diff_calibrations(Path(args.cap_a), Path(args.cap_b))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
