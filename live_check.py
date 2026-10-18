"""Real C3 API checks. Run deliberately after configuring .env; consumes API quota."""
import json
import hashlib
from dataclasses import asdict
from pathlib import Path
from datetime import datetime, timezone
from common import ROOT, BusinessKnowledge, JsonlStore, LiveBackend, default_config
from agent import BusinessAgent


def main():
    backend = LiveBackend(min_request_interval=6)
    root = ROOT / "evidence" / ("live_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    root.mkdir(parents=True, exist_ok=False)
    agent = BusinessAgent(backend, BusinessKnowledge.load(), JsonlStore(root / "records"),
                          default_config(), reflection=True, trace_dir=root / "traces")
    cases = [
        ("general", "Which beginner workshops do you offer?", None),
        ("lead", "Please record my interest. My name is Dana Saleh, my email is dana@example.com. Interested in AI Foundations.", "record_customer_interest"),
        ("feedback", "Feedback: Please add evening sessions.", "record_feedback"),
        ("unknown", "Is VAT included in your tuition?", "record_feedback")]
    rows = []
    for label, customer, required_tool in cases:
        result = agent.run(customer, session_id="demo_" + label)
        observed = {x["name"] for x in result["trace"]
                    if x.get("event") == "tool" and x["observation"].get("ok")}
        rows.append({"case": label, "status": result["status"], "answer": result["answer"],
                     "required_tool": required_tool, "observed_tools": sorted(observed),
                     "tool_check": required_tool is None or required_tool in observed,
                     "trace_file": result["turn_id"] + ".json"})
    metadata = {"mode":"LIVE_API", "executed_utc":datetime.now(timezone.utc).isoformat(),
                "provider":backend.provider, "configuration":asdict(agent.config),
                "min_request_interval_seconds":6,
                "source_sha256":{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                                 for name in ("common.py","agent.py","live_check.py")},
                "checks":rows}
    (root / "live_checks.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(rows, indent=2))
    if not all(x["status"] == "ok" and x["tool_check"] for x in rows):
        raise SystemExit("One or more live checks failed; preserve the logs and investigate.")


if __name__ == "__main__":
    main()
