from __future__ import annotations

import argparse
import json
from pathlib import Path

from tunersx import __version__
from tunersx.audit.integrity import AuditLogger, build_hashes, verify_bundle, write_manifest
from tunersx.core.config import AppConfig
from tunersx.core.session import clear_session, load_session, save_session
from tunersx.core.types import PipelineState, RiskClass
from tunersx.dashboard.builder import build_dashboard
from tunersx.decode.anomalies import detect_anomalies
from tunersx.decode.dbc_loader import load_dbc_map
from tunersx.decode.pipeline import decode_frames_to_signals
from tunersx.policy.enforcer import PolicySnapshot
from tunersx.transports.demo import generate_demo_frames


REQUIRED_FILES = ["frames.jsonl", "signals.jsonl", "anomalies.jsonl", "audit.jsonl"]


def _ensure_bundle(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_FILES:
        p = path / name
        if not p.exists():
            p.write_text("", encoding="utf-8")


def _package_bundle(bundle: Path, cfg: AppConfig, dbc_version: str, policy_mode: str) -> None:
    file_hashes = build_hashes(bundle, REQUIRED_FILES)
    (bundle / "hashes.json").write_text(json.dumps(file_hashes, indent=2), encoding="utf-8")
    write_manifest(
        bundle,
        file_hashes,
        schema_version=cfg.schema_version,
        registry_version=cfg.registry_version,
        dbc_version=dbc_version,
        policy_mode=policy_mode,
    )


def cmd_session_start(args: argparse.Namespace) -> int:
    cfg = AppConfig()
    bundle = Path(args.out)
    _ensure_bundle(bundle)

    policy = PolicySnapshot(risk_class=RiskClass.PASSIVE)
    audit = AuditLogger(bundle / "audit.jsonl")
    audit.log("action_attempt", {"action": "capture", "risk": policy.risk_class.value})
    allowed, reason = policy.authorize("capture")
    audit.log("action_result", {"action": "capture", "allowed": allowed, "reason": reason})
    if not allowed:
        return 2

    policy.transition(PipelineState.SELF_TEST)
    audit.log("state", {"state": policy.state.value})
    policy.transition(PipelineState.IDENTIFY_TARGET)
    audit.log("state", {"state": policy.state.value})
    policy.transition(PipelineState.PASSIVE_CAPTURE)
    audit.log("state", {"state": policy.state.value, "transport": args.transport})

    if args.transport != "demo":
        audit.log("fault", {"reason": "only demo transport supported in v1.0"})
        return 3

    frame_count = generate_demo_frames(args.seconds, bundle / "frames.jsonl")
    audit.log("capture_complete", {"frame_count": frame_count, "seconds": args.seconds})

    dbc_map, dbc_version = load_dbc_map(args.dbc)
    signal_count = decode_frames_to_signals(bundle / "frames.jsonl", bundle / "signals.jsonl", dbc_map, cfg.decode)
    audit.log("decode_complete", {"signal_count": signal_count, "dbc_version": dbc_version})

    anomaly_count = detect_anomalies(bundle / "signals.jsonl", bundle / "anomalies.jsonl", cfg.anomaly)
    audit.log("anomaly_complete", {"anomaly_count": anomaly_count})

    policy.transition(PipelineState.PACK)
    audit.log("state", {"state": policy.state.value})
    policy.transition(PipelineState.COMPLETE)
    audit.log("state", {"state": policy.state.value})

    _package_bundle(bundle, cfg, dbc_version, policy.risk_class.value)
    save_session(bundle, PipelineState.COMPLETE, policy.risk_class)
    print(f"session complete: {bundle}")
    return 0


def cmd_session_stop(args: argparse.Namespace) -> int:
    sess = load_session()
    if not sess:
        print("no active session")
        return 0
    bundle = Path(sess["bundle_dir"])
    audit = AuditLogger(bundle / "audit.jsonl")
    audit.log("action_attempt", {"action": "session_stop"})
    audit.log("action_result", {"action": "session_stop", "allowed": True, "reason": "allowed"})
    cfg = AppConfig()
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    _package_bundle(bundle, cfg, manifest.get("dbc_version", "builtin-demo-1.0"), manifest.get("policy_mode", "PASSIVE"))
    clear_session()
    print("session stopped")
    return 0


def cmd_trace_verify(args: argparse.Namespace) -> int:
    ok, errors = verify_bundle(Path(args.bundle_dir))
    if ok:
        print("OK")
        return 0
    print("FAIL")
    for e in errors:
        print(f" - {e}")
    return 1


def cmd_decode(args: argparse.Namespace) -> int:
    cfg = AppConfig()
    bundle = Path(args.bundle_dir)
    audit = AuditLogger(bundle / "audit.jsonl")
    policy = PolicySnapshot(risk_class=RiskClass.PASSIVE, state=PipelineState.PASSIVE_CAPTURE)
    audit.log("action_attempt", {"action": "decode"})
    allowed, reason = policy.authorize("decode")
    audit.log("action_result", {"action": "decode", "allowed": allowed, "reason": reason})
    if not allowed:
        return 2

    dbc_map, dbc_version = load_dbc_map(args.dbc)
    signal_count = decode_frames_to_signals(bundle / "frames.jsonl", bundle / "signals.jsonl", dbc_map, cfg.decode)
    anomaly_count = detect_anomalies(bundle / "signals.jsonl", bundle / "anomalies.jsonl", cfg.anomaly)
    audit.log("decode_complete", {"signal_count": signal_count, "anomaly_count": anomaly_count})
    _package_bundle(bundle, cfg, dbc_version, policy.risk_class.value)
    print("decode complete")
    return 0


def cmd_dashboard_build(args: argparse.Namespace) -> int:
    cfg = AppConfig()
    bundle = Path(args.bundle_dir)
    audit = AuditLogger(bundle / "audit.jsonl")
    policy = PolicySnapshot(risk_class=RiskClass.PASSIVE, state=PipelineState.PACK)
    audit.log("action_attempt", {"action": "dashboard"})
    allowed, reason = policy.authorize("dashboard")
    audit.log("action_result", {"action": "dashboard", "allowed": allowed, "reason": reason})
    if not allowed:
        return 2

    report = build_dashboard(bundle)
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    _package_bundle(bundle, cfg, manifest.get("dbc_version", "builtin-demo-1.0"), manifest.get("policy_mode", policy.risk_class.value))
    print(f"dashboard generated: {report}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tunersx")
    parser.add_argument("--version", action="version", version=f"tunersx {__version__}")
    sub = parser.add_subparsers(dest="top", required=True)

    session = sub.add_parser("session")
    session_sub = session.add_subparsers(dest="session_cmd", required=True)
    start = session_sub.add_parser("start")
    start.add_argument("--transport", default="demo")
    start.add_argument("--seconds", type=int, default=5)
    start.add_argument("--out", required=True)
    start.add_argument("--dbc")
    start.set_defaults(func=cmd_session_start)
    stop = session_sub.add_parser("stop")
    stop.set_defaults(func=cmd_session_stop)

    trace = sub.add_parser("trace")
    trace_sub = trace.add_subparsers(dest="trace_cmd", required=True)
    verify = trace_sub.add_parser("verify")
    verify.add_argument("bundle_dir")
    verify.set_defaults(func=cmd_trace_verify)

    dec = sub.add_parser("decode")
    dec.add_argument("bundle_dir")
    dec.add_argument("--dbc")
    dec.set_defaults(func=cmd_decode)

    dash = sub.add_parser("dashboard")
    dash_sub = dash.add_subparsers(dest="dash_cmd", required=True)
    build = dash_sub.add_parser("build")
    build.add_argument("bundle_dir")
    build.set_defaults(func=cmd_dashboard_build)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
