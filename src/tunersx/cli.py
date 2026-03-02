from __future__ import annotations

import argparse
import json
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
from tunersx.policy.enforcer import PolicySnapshot
from tunersx.transports.demo import generate_demo_frames

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


def cmd_trace_verify(args: argparse.Namespace) -> int:
    ok, payload = verify_bundle(Path(args.bundle_dir))
    print(json.dumps(payload, indent=2, sort_keys=True))
    print("OK" if ok else "FAIL")
    return 0 if ok else 1


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
    _package_bundle(
        bundle,
        cfg,
        manifest.get("software", {}).get("dbc_version", "builtin-demo-1.1"),
        policy,
        manifest.get("capture_stats", {}),
        manifest.get("transport_config", {}),
    )
    print(f"dashboard generated: {report}")
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
    start.set_defaults(func=cmd_session_start)
    stop = ss.add_parser("stop")
    stop.set_defaults(func=cmd_session_stop)

    trace = sub.add_parser("trace")
    tsub = trace.add_subparsers(dest="trace_cmd", required=True)
    verify = tsub.add_parser("verify")
    verify.add_argument("bundle_dir")
    verify.set_defaults(func=cmd_trace_verify)

    dec = sub.add_parser("decode")
    dec.add_argument("bundle_dir")
    dec.add_argument("--dbc")
    dec.set_defaults(func=cmd_decode)

    dash = sub.add_parser("dashboard")
    dsub = dash.add_subparsers(dest="dash_cmd", required=True)
    build = dsub.add_parser("build")
    build.add_argument("bundle_dir")
    build.set_defaults(func=cmd_dashboard_build)

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

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
