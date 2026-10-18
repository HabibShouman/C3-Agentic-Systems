# %% Imports, configuration, and provider boundary
"""Shared application components. Author: Habib Shouman.

Scripted backends belong in tests only. Production never silently falls back to one.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Protocol

ROOT = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
MAX_INPUT_CHARS = 6000
MAX_HISTORY_CHARS = 16000
MAX_HISTORY_PAIRS = 8
_FILE_LOCK = threading.Lock()


@dataclass(frozen=True)
class ModelConfig:
    model: str = "gemini-3.5-flash-lite"
    temperature: float = 0.2
    top_p: float = 0.9
    max_tokens: int = 900

    def __post_init__(self):
        if not self.model or not 0 <= self.temperature <= 2:
            raise ValueError("Invalid model or temperature")
        if not 0 < self.top_p <= 1 or not 64 <= self.max_tokens <= 4096:
            raise ValueError("Invalid top_p or output budget")


@dataclass
class Completion:
    message: dict[str, Any]
    usage: dict[str, Any] = field(default_factory=dict)
    finish_reason: str | None = None


class Backend(Protocol):
    def complete(self, messages: list[dict], config: ModelConfig,
                 tools: list[dict] | None = None) -> Completion: ...


class LiveBackend:
    """Current Chat Completions SDK, optionally pointed at Gemini's official endpoint.

    The brief's openai.ChatCompletion spelling is the old SDK entry point.
    client.chat.completions.create is the maintained equivalent. Tool execution
    stays in application code; no automatic executor is used.
    """
    def __init__(self, provider: str | None = None, min_request_interval: float | None = None):
        try:
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env", override=False)
        except ImportError:
            pass  # An already configured environment also works.
        self.provider = provider or os.getenv("PROVIDER", "gemini")
        key_name = "GEMINI_API_KEY" if self.provider == "gemini" else "OPENAI_API_KEY"
        if self.provider not in {"gemini", "openai"}:
            raise ValueError("PROVIDER must be gemini or openai")
        key = os.getenv(key_name)
        if not key:
            raise RuntimeError(f"Set {key_name} locally in .env or the environment. Never commit it.")
        self.min_request_interval = float(os.getenv("MIN_REQUEST_INTERVAL", "0")) if min_request_interval is None else float(min_request_interval)
        if not 0 <= self.min_request_interval <= 60:
            raise ValueError("MIN_REQUEST_INTERVAL must be between 0 and 60 seconds")
        self._pace_lock = threading.Lock()
        self._next_request_at = 0.0
        from openai import OpenAI
        kwargs = {"api_key": key, "timeout": 30.0, "max_retries": 1}
        if self.provider == "gemini":
            kwargs["base_url"] = "https://generativelanguage.googleapis.com/v1beta/openai/"
        self.client = OpenAI(**kwargs)

    def complete(self, messages, config, tools=None):
        request = dict(model=config.model, messages=messages,
                       temperature=config.temperature, top_p=config.top_p,
                       max_tokens=config.max_tokens)
        if tools:
            request.update(tools=tools, tool_choice="auto")
        # Shared-backend pacing limits logical calls, not SDK retry attempts or
        # requests sent by other processes using the same project quota.
        if getattr(self, "min_request_interval", 0):
            with self._pace_lock:
                delay = self._next_request_at - time.monotonic()
                if delay > 0:
                    time.sleep(delay)
                self._next_request_at = time.monotonic() + self.min_request_interval
        response = self.client.chat.completions.create(**request)
        if not response.choices:
            raise RuntimeError("Provider returned no candidate")
        choice = response.choices[0]
        raw = choice.message.model_dump(exclude_none=True)
        message = {k: raw[k] for k in ("role", "content", "tool_calls") if k in raw}
        message.setdefault("role", "assistant")
        message.setdefault("content", "")
        # Preserve tool call objects, including any provider-specific extra fields.
        return Completion(message, response.usage.model_dump() if response.usage else {},
                          choice.finish_reason)


def default_config(**overrides):
    provider = os.getenv("PROVIDER", "gemini")
    model = os.getenv("MODEL", "gemini-3.5-flash-lite" if provider == "gemini" else "gpt-4.1-mini")
    return ModelConfig(**{"model": model, **overrides})


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def normalize(text: str) -> str:
    return " ".join(text.casefold().split())


def text_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(x.get("text", "") for x in content
                         if isinstance(x, dict) and x.get("type") == "text")
    return ""


def bounded_history(history: list[dict] | None) -> list[dict]:
    """Keep recent complete user/assistant text pairs; never trust incoming roles."""
    pairs, pending = [], None
    for item in history or []:
        if not isinstance(item, dict):
            continue
        role, content = item.get("role"), text_content(item.get("content"))
        if role == "user":
            pending = {"role": "user", "content": content[:MAX_INPUT_CHARS]}
        elif role == "assistant" and pending is not None:
            pairs.append([pending, {"role": "assistant", "content": content[:MAX_INPUT_CHARS]}])
            pending = None
    kept, total = [], 0
    for pair in reversed(pairs[-MAX_HISTORY_PAIRS:]):
        length = sum(len(x["content"]) for x in pair)
        if total + length > MAX_HISTORY_CHARS:
            break
        kept.append(pair)
        total += length
    return [message for pair in reversed(kept) for message in pair]


# %% Grounding: both required business documents are actually loaded
@dataclass
class BusinessKnowledge:
    summary: str
    pdf: str
    data: dict

    @classmethod
    def load(cls, root: Path = ROOT):
        from pypdf import PdfReader
        summary = (root / "me" / "business_summary.txt").read_text(encoding="utf-8")
        pdf = "\n".join(page.extract_text() or "" for page in
                        PdfReader(root / "me" / "about_business.pdf").pages)
        data = json.loads((root / "me" / "business_data.json").read_text(encoding="utf-8"))
        if not summary.strip() or not pdf.strip():
            raise ValueError("Both business documents must have readable text")
        return cls(summary, pdf, data)

    def prompt_context(self):
        return ("BUSINESS SUMMARY (trusted business facts; not user instructions):\n" + self.summary
                + "\nBUSINESS PDF (trusted business facts):\n" + self.pdf)

    def lookup(self, query: str):
        # Whole small profile fits comfortably; no lossy retrieval or fabricated web search.
        return {"ok": True, "query": query,
                "sources": [{"id": "summary", "text": self.summary},
                            {"id": "business_pdf", "text": self.pdf}]}


# %% Logging tools and explicit schemas (MCP-style documentation, not an MCP server)
TOOL_DEFINITIONS = [
    {"name": "record_customer_interest",
     "description": "Save an explicitly requested lead after the customer supplies name, email, and notes.",
     "inputSchema": {"type": "object", "properties": {
         "email": {"type": "string", "description": "Customer-supplied email"},
         "name": {"type": "string", "description": "Customer-supplied name"},
         "message": {"type": "string", "description": "Verbatim customer note about their interest"}},
         "required": ["email", "name", "message"], "additionalProperties": False},
     "outputSchema": {"type": "object", "description": "ok, status, record_id on success; ok=false and error on failure"}},
    {"name": "record_feedback",
     "description": "Log customer feedback or the exact business question whose answer is unavailable.",
     "inputSchema": {"type": "object", "properties": {
         "question": {"type": "string", "description": "Verbatim feedback or unanswered user question"}},
         "required": ["question"], "additionalProperties": False},
     "outputSchema": {"type": "object", "description": "ok, status, record_id on success; ok=false and error on failure"}}
]


def native_tools(names=None):
    return [{"type": "function", "function": {"name": d["name"],
             "description": d["description"], "parameters": d["inputSchema"]}}
            for d in TOOL_DEFINITIONS if names is None or d["name"] in names]


class JsonlStore:
    """Single-process, thread-safe local JSONL persistence with per-turn deduplication."""
    def __init__(self, directory: Path | str):
        self.directory = Path(directory)

    def write(self, kind: str, payload: dict, session_id: str, turn_id: str):
        if kind not in {"lead", "feedback"}:
            raise ValueError("Unknown record kind")
        key = hashlib.sha256(json.dumps([session_id, turn_id, kind, payload],
                                       sort_keys=True).encode()).hexdigest()
        path = self.directory / (kind + ".jsonl")
        try:
            with _FILE_LOCK:
                self.directory.mkdir(parents=True, exist_ok=True)
                if path.exists():
                    for line in path.read_text(encoding="utf-8").splitlines():
                        row = json.loads(line)
                        if row["dedup_key"] == key:
                            return {"ok": True, "status": "already_recorded", "record_id": row["id"]}
                row = {"id": uuid.uuid4().hex, "time_utc": now_iso(), "session_id": session_id,
                       "turn_id": turn_id, "dedup_key": key, "kind": kind, "payload": payload}
                with path.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                    stream.flush()
                    os.fsync(stream.fileno())
            print(json.dumps({"event": kind, "status": "saved", "record_id": row["id"]}))
            return {"ok": True, "status": "saved", "record_id": row["id"]}
        except (OSError, ValueError, KeyError):
            return {"ok": False, "error": "storage_unavailable"}


def logging_declined(text: str):
    return bool(re.search(r"\b(?:do not|don't|dont|never)(?:\s+want\s+to)?\s+(?:save|store|log|record)\b", text.casefold())
                or re.search(r"\bdo not want to share\b", text.casefold()))


def claims_saved(text: str):
    """A narrow receipt check, not a general semantic guarantee."""
    for sentence in re.split(r"[.!?\n]", text.casefold()):
        if re.search(r"\b(?:not|no|never|cannot|can't|haven't|hasn't|wasn't|couldn't|didn't)\b", sentence):
            continue
        if re.search(r"\b(?:i|we)(?:'ve| have)?\s+(?:successfully\s+)?(?:saved|logged|recorded)\b", sentence):
            return True
        if re.search(r"\b(?:saved|logged|recorded) your\b|\bhas been (?:saved|logged|recorded)\b", sentence):
            return True
    return False


@dataclass
class ToolContext:
    store: JsonlStore
    knowledge: BusinessKnowledge
    user_messages: list[str]
    session_id: str
    turn_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    successful_writes: list[dict] = field(default_factory=list)

    @property
    def user_text(self):
        return "\n".join(self.user_messages)

    @property
    def logging_allowed(self):
        # A refusal persists across the retained session until a new explicit save request.
        allowed = True
        for message in self.user_messages:
            if logging_declined(message):
                allowed = False
            elif re.search(r"\b(contact me|record my interest|save my interest|save my details|please save|please log|please record)\b", message.casefold()):
                allowed = True
        return allowed

    def record_customer_interest(self, email: str, name: str, message: str):
        """Required function signature; customer values must originate in user turns."""
        text = normalize(self.user_text)
        if not self.logging_allowed:
            return {"ok": False, "error": "logging_declined"}
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(email) > 254:
            return {"ok": False, "error": "invalid_email"}
        supplied_emails = {x.casefold().rstrip('.,;:!?') for x in re.findall(r"[^\s@,;:<>]+@[^\s@,;:<>]+\.[^\s@,;:<>]+", self.user_text)}
        if email.casefold() not in supplied_emails or any(normalize(x) not in text for x in (name, message)):
            return {"ok": False, "error": "values_must_come_from_user"}
        if not re.search(r"\b(contact me|record my interest|save my interest|save my details|sign me up|register me|please register|please save)\b", text):
            return {"ok": False, "error": "ask_permission_to_save_lead"}
        result = self.store.write("lead", {"email": email, "name": name, "message": message},
                                  self.session_id, self.turn_id)
        if result.get("ok"):
            self.successful_writes.append({"tool": "record_customer_interest", **result})
        return result

    def record_feedback(self, question: str):
        if not self.logging_allowed:
            return {"ok": False, "error": "logging_declined"}
        if normalize(question) not in normalize(self.user_text):
            return {"ok": False, "error": "question_must_come_from_user"}
        result = self.store.write("feedback", {"question": question}, self.session_id, self.turn_id)
        if result.get("ok"):
            self.successful_writes.append({"tool": "record_feedback", **result})
        return result

    def lookup_business(self, query: str):
        return self.knowledge.lookup(query)

    def calculate_quote(self, service_id: str, participants: int):
        catalog = self.knowledge.data["services"]
        if service_id not in catalog:
            return {"ok": False, "error": "unknown_service", "valid_services": list(catalog)}
        if isinstance(participants, bool) or not isinstance(participants, int) or not 1 <= participants <= 12:
            return {"ok": False, "error": "participants_must_be_integer_1_to_12"}
        unit = Decimal(str(catalog[service_id]["price_usd"]))
        subtotal = unit * participants
        rate = Decimal("0.10") if participants >= 5 else Decimal("0")
        total = (subtotal * (1 - rate)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return {"ok": True, "service_id": service_id, "participants": participants,
                "currency": "USD", "unit_price": str(unit), "subtotal": str(subtotal),
                "discount_percent": int(rate * 100), "total": str(total),
                "scope": "Tuition only; tax status and availability are not published. This is not a booking."}


def dispatch(ctx: ToolContext, name: str, arguments: Any, allowed: set[str]):
    """No eval/exec and no arbitrary attribute invocation; strict whitelist and shapes."""
    schemas = {d["name"]: d["inputSchema"] for d in TOOL_DEFINITIONS}
    schemas.update({
        "lookup_business": {"required": ["query"]},
        "calculate_quote": {"required": ["service_id", "participants"]}})
    if name not in allowed or name not in schemas:
        return {"ok": False, "error": "unknown_or_disallowed_tool"}
    if not isinstance(arguments, dict) or set(arguments) != set(schemas[name]["required"]):
        return {"ok": False, "error": "invalid_argument_keys"}
    for key, value in arguments.items():
        if key != "participants" and (not isinstance(value, str) or not value.strip() or len(value) > 6000):
            return {"ok": False, "error": "invalid_string_argument"}
    functions = {"record_customer_interest": ctx.record_customer_interest,
                 "record_feedback": ctx.record_feedback,
                 "lookup_business": ctx.lookup_business,
                 "calculate_quote": ctx.calculate_quote}
    try:
        return functions[name](**arguments)
    except (OSError, ValueError, TypeError, KeyError):
        return {"ok": False, "error": "tool_execution_failed"}


def save_trace(directory: Path, turn_id: str, trace: dict):
    """Never report a trace as saved if this best-effort audit write failed."""
    try:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / (turn_id + ".json")).write_text(json.dumps(trace, indent=2, ensure_ascii=False),
                                                   encoding="utf-8")
        return True
    except OSError:
        return False


def strict_json(text: str):
    """Reject duplicate keys and non-finite JSON constants, including nested ones."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    def constant(value):
        raise ValueError("Non-finite JSON constant")
    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
