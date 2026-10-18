"""Deploy the C3 app using official Hub APIs; never upload local credentials.

Author: Habib Shouman. Install requirements-deploy.txt, authenticate with `hf auth
login` or HF_TOKEN, and run `python tools/deploy_space.py`. CPU Basic is the default;
the documented free ZeroGPU tier can be selected for an eligible account.
No subscription purchase or paid hardware upgrade is performed.
"""
import argparse
import hashlib
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/HabibShouman/C3-Agentic-Systems"
RUNTIME_FILES = ["app.py", "agent.py", "common.py", "requirements.txt", ".gitattributes",
                 "me/about_business.pdf", "me/business_data.json",
                 "me/business_summary.txt", "me/summary.txt"]
SPACE_README = """---
title: CircuitBridge Learning C3
emoji: 🔌
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: "6.30.0"
app_file: app.py
python_version: "3.11"
---
# CircuitBridge Learning | Mira

Author: Habib Shouman. C3, EECE 503P/798S: Agentic Systems.

This is a fictional workshop business. The assistant answers from the supplied
PDF and summary, collects authorized expressions of interest, and records
feedback or unanswered questions using model-selected native tools. It uses
Gemini through Google's OpenAI-compatible endpoint and includes one bounded
reflection pass. It cannot book a workshop or send messages to staff.

Code, executed notebook, actual video, tests, and limitations:
https://github.com/HabibShouman/C3-Agentic-Systems

Feedback and authorized leads are written to the Space's local filesystem.
Say 'do not log' to decline application logging. The model provider still
receives the conversation. These files are ephemeral and are not a durable
production database. This is a teaching demonstration, not a real business.
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-id", help="Defaults to authenticated-user/c3-agentic-systems")
    parser.add_argument("--update-existing", action="store_true",
                        help="Explicitly update an existing course Space with this identifier")
    parser.add_argument("--hardware", choices=["cpu-basic", "zero-a10g"], default="cpu-basic",
                        help="No hourly paid hardware is supported by this script")
    parser.add_argument("--wait-seconds", type=int, default=0,
                        help="Optional bounded runtime polling; 0 returns after upload")
    args = parser.parse_args()
    if not 0 <= args.wait_seconds <= 600:
        parser.error("--wait-seconds must be between 0 and 600")

    from dotenv import dotenv_values
    from huggingface_hub import HfApi, get_token
    from huggingface_hub.errors import HfHubHTTPError

    if not get_token():
        raise RuntimeError("Authenticate using hf auth login or the HF_TOKEN environment variable.")
    api = HfApi()
    account = api.whoami()["name"]
    repo_id = args.repo_id or account + "/c3-agentic-systems"
    if repo_id.split("/", 1)[0] != account:
        raise ValueError("Use a Space in the authenticated user's own namespace.")
    settings = dotenv_values(ROOT / ".env")
    key = os.getenv("GEMINI_API_KEY") or settings.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("Set GEMINI_API_KEY in the environment or local .env file.")
    model = os.getenv("MODEL") or settings.get("MODEL") or "gemini-3.5-flash-lite"
    variables = {"PROVIDER": "gemini", "MODEL": model, "SERVER_NAME": "0.0.0.0",
                 "PORT": "7860", "MIN_REQUEST_INTERVAL": "6",
                 "GRADIO_ANALYTICS_ENABLED": "False"}
    exists = False
    try:
        api.space_info(repo_id)
        exists = True
    except HfHubHTTPError as error:
        if error.response.status_code != 404:
            raise
    if exists and not args.update_existing:
        raise RuntimeError("Space already exists. Inspect it, then use --update-existing if appropriate.")
    if not exists:
        api.create_repo(repo_id, repo_type="space", space_sdk="gradio", private=False,
                        space_hardware=args.hardware,
                        space_secrets=[{"key": "GEMINI_API_KEY", "value": key}],
                        space_variables=[{"key": name, "value": value} for name, value in variables.items()])
    else:
        api.add_space_secret(repo_id, key="GEMINI_API_KEY", value=key)
        for name, value in variables.items():
            api.add_space_variable(repo_id, key=name, value=value)

    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in RUNTIME_FILES}
    with tempfile.TemporaryDirectory(prefix="c3_space_") as temporary:
        stage = Path(temporary)
        for name in RUNTIME_FILES:
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / name).read_bytes())
        readme = SPACE_README
        if args.hardware == "zero-a10g":
            readme = readme.replace('python_version: "3.11"', 'python_version: "3.12"')
            readme += "\nHosting tier: ZeroGPU. This application makes remote Gemini API calls; it does not allocate a GPU or claim local model inference.\n"
        (stage / "README.md").write_text(readme, encoding="utf-8")
        marker = {"author": "Habib Shouman", "source_repository": REPOSITORY,
                  "runtime_sha256": hashes}
        (stage / "deployment_source.json").write_text(json.dumps(marker, indent=2), encoding="utf-8")
        # The stage is built from an explicit whitelist; .env and API keys never enter it.
        assert not any(key.encode() in path.read_bytes() for path in stage.rglob("*") if path.is_file())
        commit = api.upload_folder(repo_id=repo_id, repo_type="space", folder_path=stage,
                                   commit_message="Deploy C3 CircuitBridge Learning assistant")
    deadline = time.monotonic() + args.wait_seconds
    while True:
        runtime = api.get_space_runtime(repo_id)
        stage_name = getattr(runtime.stage, "value", runtime.stage)
        print(json.dumps({"space": repo_id, "stage": stage_name}), flush=True)
        if stage_name in {"RUNNING", "BUILD_ERROR", "RUNTIME_ERROR", "CONFIG_ERROR"} or time.monotonic() >= deadline:
            break
        time.sleep(min(5, max(0, deadline - time.monotonic())))
    evidence = {"author": "Habib Shouman", "executed_utc": datetime.now(timezone.utc).isoformat(),
                "space_id": repo_id, "space_url": "https://huggingface.co/spaces/" + repo_id,
                "commit_sha": commit.oid, "runtime_stage": stage_name,
                "requested_hardware": args.hardware, "paid_hardware_requested": False,
                "secret_names": sorted(api.get_space_secrets(repo_id)),
                "runtime_sha256": hashes, "live_browser_verified": False,
                "bonus_verified": False,
                "note": "Upload/runtime status alone does not establish live model or tool behavior."}
    (ROOT / "evidence/huggingface.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps({"space_url": evidence["space_url"], "runtime_stage": stage_name,
                      "live_browser_verified": False}), flush=True)


if __name__ == "__main__":
    main()
