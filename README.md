---
title: CircuitBridge Learning C3
emoji: 🔌
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: "6.30.0"
app_file: app.py
pinned: false
python_version: "3.11"
---

# C3 - Agent-Powered Business Assistant

**Author: Habib Shouman | EECE 503P/798S: Agentic Systems**

CircuitBridge Learning is a fictional electronics and AI workshop business. Mira answers documented questions, collects authorized leads, and logs feedback or unanswered questions. The submitted code uses Gemini through its official OpenAI-compatible endpoint by default, with an OpenAI option.

**Status:** Complete code, business assets, an executed notebook, genuine Gemini checks, and the actual demonstration video are published at [HabibShouman/C3-Agentic-Systems](https://github.com/HabibShouman/C3-Agentic-Systems). All 79 files in the first full publication were verified by their Git blob hashes. The Hugging Face hosting bonus is blocked by account eligibility; no instructor submission has been made.

## Start locally

Extract the whole ZIP and open a terminal inside `business_bot`. Use Python 3.11 or newer.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` with your file manager or editor. Set `GEMINI_API_KEY` locally; keep `PROVIDER=gemini` and the configured Gemini model, or select a model available to your account. For OpenAI, set `PROVIDER=openai`, `OPENAI_API_KEY`, and an appropriate `MODEL`. Model access, quotas, free-tier eligibility, and parameter support depend on the provider/account. No paid subscription or API credit is assumed to exist.

```bash
python run_verification.py
python live_check.py
python app.py
```

The first command makes no API calls. The second uses real API quota and writes genuine tool-call traces. The app listens on localhost port 7860 by default. Never expose your `.env` file in a screenshot, recording, repository, or ZIP.

## Notebook and Colab

`business_agent.ipynb` contains the complete implementation cells, requirements, demonstrations, coverage table, and verification summary. It also works with the accompanying modules. The saved execution uses local Python, not Colab.

For Colab, upload the entire ZIP, extract it, change directory to `business_bot`, install `requirements-dev.txt`, and open/run the notebook. Colab Secrets can supply the key without embedding it in notebook source:

```python
import os
from google.colab import userdata
os.environ['GEMINI_API_KEY'] = userdata.get('GEMINI_API_KEY')
```

Set `RUN_LIVE=True` only when you intend to use the configured API. Set `LAUNCH_UI=True` to launch the Gradio UI. The notebook defaults leave both disabled. Recorded-result cells display the included genuine evidence without making new calls. If Colab needs a share URL, explicitly call `build_demo().launch(share=True)` there; that is a temporary demo link, not a Hugging Face deployment.

## Files

| File | Purpose |
|---|---|
| `me/about_business.pdf` | One-page fictional profile with catalog and operating policies |
| `me/business_summary.txt`, `me/summary.txt` | Identical short summaries, covering both names used in the brief |
| `business_agent.ipynb` | Main submission notebook; exact filename requested by C3 |
| `agent.py`, `common.py`, `app.py` | Reusable implementation and Gradio entry point |
| `SOLUTION.md`, `COVERAGE.md` | Answers in task order and requirement evidence |
| `DEFENSE_GUIDE.md` | Short explanation of the difficult concepts |
| `live_check.py`, `tests/`, `run_verification.py` | Live checks and independent application tests |
| `evidence/` | Actual local test and notebook-execution records |
| `.env.example`, `.gitignore` | Credential template and exclusions; no real `.env` is submitted |

## Required video and repository

`demo/C3_demonstration.webm` is the actual silent automated browser recording, re-encoded compactly without sequence edits or substituted replies. `DEMO_SCRIPT.md` explains the sequence, and `evidence/video_transcode_verification.json` records original/derivative hashes and timing. The code, notebook, business PDF, and video are published in [the course repository](https://github.com/HabibShouman/C3-Agentic-Systems). Publication evidence is in `evidence/repository.json`; all demonstrated contact details are fictional.

## Hugging Face bonus: actual deployment result

The supplied write token authenticated successfully. Creation of `HabibShouman/c3-agentic-systems` was rejected with HTTP 402 on both CPU Basic and ZeroGPU. CPU Basic requires PRO; the ZeroGPU response also rejected this account's current eligibility. No Space was created, no live URL is claimed, and the hosting bonus is not counted as complete. `evidence/huggingface_attempts.json` preserves these outcomes without credentials.

`tools/deploy_space.py` implements the complete deployment process using the official Hub API. It uploads an explicit runtime-file whitelist, sets `GEMINI_API_KEY` as a secret, configures `SERVER_NAME=0.0.0.0`, and records actual upload/runtime status. Once the account is eligible:

```bash
python -m pip install -r requirements-deploy.txt
hf auth login
python tools/deploy_space.py --wait-seconds 300
```

For an account eligible for the documented free ZeroGPU tier, select `--hardware zero-a10g`; that deployment uses Python 3.12. The default CPU Basic deployment uses Python 3.11. The helper supports no hourly paid hardware and purchases no subscription. A running build must still be checked with genuine browser/model/tool interactions before claiming the bonus. Default Space files are ephemeral; the local JSONL files are not a durable production database.

## Sources and assistance

The supplied C3 brief is the primary specification. `SOURCES.md` identifies the official API documentation consulted. No separate lecture notes, starter code, numeric C3 grading rubric, or AI-assistance policy were supplied. `AI_ASSISTANCE.md` records the assistance used. The business is intentionally fictional, as the assignment permits.


Request pacing is inspectable: MIN_REQUEST_INTERVAL controls a single app backend, and the experiment runner's --min-request-interval defaults to six seconds. Project-wide quota errors remain possible. Model access was verified for the submitted Gemini run; other accounts or later model versions may differ.
