"""usage-telemetry - a Hermes plugin that writes one JSON line per event to <profile>/logs/usage/usage-YYYY-MM-DD.jsonl

  llm_call   every call to the main model (post_api_request): tokens in / out / reasoning / cache, cost, timings
  aux_call   every auxiliary model call (titles, compression, vision ...) - tokens the user never sees
  api_error  a failed model call
  tool_call  every tool call, MCP tools included: duration, status, argument and result sizes
  turn_end   one finished turn (one request to the API): completed / failed / interrupted and why
  process    once per gateway process and profile: the host and software the records came from

Records hold sizes, ids and timings only - never prompts, answers, tool arguments or results - so the files
can be shared for research. The field names are the same as in the usage logs of the MCP servers
(schema harness-usage/1), so the collector app can join them into one data set.

Env (optional): HERMES_USAGE_DIR - write somewhere else than <profile>/logs/usage.
"""
from __future__ import annotations

import json
import logging
import os
import platform
import socket
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SCHEMA = "harness-usage/1"
_LOCK = threading.Lock()
_PENDING: dict[str, dict] = {}       # api_request_id -> what pre_api_request knew about the request
_MAX_PENDING = 512
_STARTED: set[str] = set()           # homes that already have their "process" record
USAGE_FIELDS = ("input_tokens", "output_tokens", "reasoning_tokens", "cache_read_tokens", "cache_write_tokens")


def _home() -> Path:
    from hermes_constants import get_hermes_home
    return Path(get_hermes_home())


def _profile(home: Path) -> str:
    return home.name if home.parent.name == "profiles" else "default"


def _usage_dir(home: Path) -> Path:
    override = os.getenv("HERMES_USAGE_DIR", "").strip()
    return Path(override) if override else home / "logs" / "usage"


def _num(v: Any) -> float | None:
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


def _round(v: Any, digits: int = 3) -> float | None:
    n = _num(v)
    return None if n is None else round(n, digits)


def _chars(v: Any) -> int:
    if v is None:
        return 0
    if isinstance(v, str):
        return len(v)
    try:
        return len(json.dumps(v, ensure_ascii=False, default=str))
    except (TypeError, ValueError):
        return len(str(v))


def _meminfo_total_mb() -> int | None:
    try:
        with open("/proc/meminfo", encoding="ascii") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) // 1024
    except OSError:
        return None
    return None


def _hermes_version() -> str | None:
    try:
        from hermes_cli.version_info import get_version_info   # what GET /health reports
        return get_version_info().base_version
    except Exception:
        return None


def _write(record: dict) -> None:
    try:
        home = _home()
        out = _usage_dir(home)
        now = time.time()
        base = {"schema": SCHEMA, "ts": round(now, 3), "component": "hermes", "profile": _profile(home),
                "host": socket.gethostname()}
        lines = []
        key = str(home)
        if key not in _STARTED:
            lines.append({**base, "kind": "process", "detail": {
                "hermes_version": _hermes_version(), "python": platform.python_version(),
                "platform": platform.platform(), "machine": platform.machine(),
                "cpu_count": os.cpu_count(), "mem_total_mb": _meminfo_total_mb(), "pid": os.getpid()}})
        lines.append({**base, **record})
        path = out / f"usage-{datetime.fromtimestamp(now).strftime('%Y-%m-%d')}.jsonl"
        with _LOCK:
            out.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                for line in lines:
                    f.write(json.dumps(line, ensure_ascii=False, default=str) + "\n")
            _STARTED.add(key)
    except Exception as e:   # telemetry must never break a turn
        logger.debug("usage-telemetry: write failed: %s", e)


def _usage_fields(usage: Any) -> dict:
    u = usage if isinstance(usage, dict) else {}
    out = {k: int(u.get(k) or 0) for k in USAGE_FIELDS}
    out["prompt_tokens"] = int(u.get("prompt_tokens") or (out["input_tokens"] + out["cache_read_tokens"]
                                                          + out["cache_write_tokens"]))
    out["total_tokens"] = int(u.get("total_tokens") or (out["prompt_tokens"] + out["output_tokens"]))
    return out if u else {k: None for k in (*USAGE_FIELDS, "prompt_tokens", "total_tokens")}


def _cost_usd(model: Any, usage: Any, provider: Any, base_url: Any) -> tuple[float | None, str | None]:
    """Hermes' own price estimate (the same one behind estimated_cost_usd of a session)."""
    if not isinstance(usage, dict) or not model:
        return None, None
    try:
        from agent.usage_pricing import CanonicalUsage, estimate_usage_cost
        cu = CanonicalUsage(**{k: int(usage.get(k) or 0) for k in USAGE_FIELDS})
        res = estimate_usage_cost(str(model), cu, provider=provider, base_url=base_url)
        amount = getattr(res, "amount_usd", None)
        if amount is not None:
            return float(amount), getattr(res, "status", None)
        return _upper_bound(model, cu, provider, base_url)
    except Exception:
        return None, None


def _upper_bound(model: Any, cu: Any, provider: Any, base_url: Any) -> tuple[float | None, str | None]:
    """When the route publishes no cache price, Hermes gives no estimate at all: price cached tokens like
    fresh input instead - never below the real cost (status "upper_bound")."""
    from agent.usage_pricing import get_pricing_entry
    e = get_pricing_entry(str(model), provider=provider, base_url=base_url)
    if e is None or e.input_cost_per_million is None or e.output_cost_per_million is None:
        return None, "unknown"
    inp = float(e.input_cost_per_million)
    read = float(e.cache_read_cost_per_million) if e.cache_read_cost_per_million is not None else inp
    write = float(e.cache_write_cost_per_million) if e.cache_write_cost_per_million is not None else inp
    cost = (cu.input_tokens * inp + cu.cache_read_tokens * read + cu.cache_write_tokens * write
            + cu.output_tokens * float(e.output_cost_per_million)) / 1_000_000 + float(e.request_cost or 0)
    return cost, "upper_bound"


def _host_of(url: Any) -> str | None:
    if not url:
        return None
    s = str(url).split("://", 1)[-1]
    return s.split("/", 1)[0] or None


def _ids(kw: dict) -> dict:
    return {"session_id": kw.get("session_id") or None, "turn_id": kw.get("turn_id") or None,
            "request_id": kw.get("api_request_id") or None, "task_id": kw.get("task_id") or None,
            "platform": kw.get("platform") or None}


def _call_record(kind: str, kw: dict) -> dict:
    """Fields shared by llm_call and aux_call."""
    started, ended = _num(kw.get("started_at")), _num(kw.get("ended_at"))
    duration = _num(kw.get("api_duration"))
    if duration is None and started is not None and ended is not None:
        duration = ended - started
    first = _num(kw.get("first_chunk_at"))
    usage = kw.get("usage")
    tokens = _usage_fields(usage)
    cost, cost_status = _cost_usd(kw.get("model"), usage, kw.get("provider"), kw.get("base_url"))
    gen_seconds = (ended - first) if (ended is not None and first is not None and ended > first) else duration
    out_tok = tokens.get("output_tokens")
    served_by = (kw.get("response") or {}).get("upstream_provider") if isinstance(kw.get("response"), dict) else None
    return {"kind": kind, **_ids(kw),
            "model": kw.get("response_model") or kw.get("model"), "provider": kw.get("provider"),
            "upstream_provider": served_by,
            "endpoint_host": _host_of(kw.get("base_url")), "api_mode": kw.get("api_mode"),
            "started_at": _round(started), "ended_at": _round(ended), "duration_s": _round(duration),
            "ttfb_s": _round(first - started) if first is not None and started is not None else None,
            **tokens,
            "output_tps": round(out_tok / gen_seconds, 2) if out_tok and gen_seconds else None,
            "cost_usd": round(cost, 6) if cost is not None else None, "cost_status": cost_status,
            "tokens_estimated": False if isinstance(usage, dict) and usage else None,
            "status": "ok" if not kw.get("error") else "error",
            "finish_reason": kw.get("finish_reason")}


# ------------------------------------------------------------------ hooks
def on_pre_api_request(**kw: Any) -> None:
    rid = kw.get("api_request_id")
    if not rid:
        return
    with _LOCK:
        if len(_PENDING) >= _MAX_PENDING:
            _PENDING.pop(next(iter(_PENDING)))
        _PENDING[str(rid)] = {"approx_input_tokens": kw.get("approx_input_tokens"),
                              "request_chars": kw.get("request_char_count"), "tool_count": kw.get("tool_count"),
                              "message_count": kw.get("message_count"), "max_tokens": kw.get("max_tokens"),
                              "retry_count": kw.get("retry_count")}


def on_post_api_request(**kw: Any) -> None:
    rec = _call_record("llm_call", kw)
    with _LOCK:
        pre = _PENDING.pop(str(kw.get("api_request_id")), {}) if kw.get("api_request_id") else {}
    rec["detail"] = {**pre, "api_call_count": kw.get("api_call_count"),
                     "message_count": kw.get("message_count", pre.get("message_count")),
                     "context_length": kw.get("context_length"),
                     "answer_chars": kw.get("assistant_content_chars"),
                     "tool_calls_requested": kw.get("assistant_tool_call_count")}
    _write(rec)


def on_api_request_error(**kw: Any) -> None:
    with _LOCK:
        pre = _PENDING.pop(str(kw.get("api_request_id")), {}) if kw.get("api_request_id") else {}
    err = kw.get("error")
    _write({"kind": "api_error", **_ids(kw), "model": kw.get("model"), "provider": kw.get("provider"),
            "endpoint_host": _host_of(kw.get("base_url")), "status": "error",
            "started_at": _round(kw.get("started_at")), "duration_s": _round(kw.get("api_duration")),
            "error": kw.get("error_type") or (type(err).__name__ if err is not None else None),
            "detail": {**pre, "status_code": kw.get("status_code"), "retry_count": kw.get("retry_count"),
                       "message": str(kw.get("error_message") or err or "")[:300] or None}})


def on_post_auxiliary_call(**kw: Any) -> None:
    rec = _call_record("aux_call", kw)
    rec["tool"] = kw.get("aux_task")
    if kw.get("error") or kw.get("error_type"):
        rec["status"], rec["error"] = "error", kw.get("error_type") or "error"
    rec["detail"] = {"retry_count": kw.get("retry_count"), "streaming": kw.get("streaming"),
                     "answer_chars": kw.get("assistant_content_chars")}
    _write(rec)


def on_post_tool_call(**kw: Any) -> None:
    ms = _num(kw.get("duration_ms"))
    ended = time.time()
    status = kw.get("status") or ("error" if kw.get("error_type") else "ok")
    _write({"kind": "tool_call", **_ids(kw), "tool": kw.get("tool_name"),
            "tool_call_id": kw.get("tool_call_id") or None,
            "started_at": _round(ended - ms / 1000) if ms is not None else None, "ended_at": _round(ended),
            "duration_s": _round(ms / 1000) if ms is not None else None,
            "status": status, "error": kw.get("error_type") or None,
            "detail": {"args_chars": _chars(kw.get("args")), "result_chars": _chars(kw.get("result")),
                       "arg_names": sorted(kw["args"]) if isinstance(kw.get("args"), dict) else None}})


def on_session_end(**kw: Any) -> None:
    status = ("interrupted" if kw.get("interrupted") else "error" if kw.get("failed")
              else "ok" if kw.get("completed") else "incomplete")
    _write({"kind": "turn_end", **_ids(kw), "model": kw.get("model"), "status": status,
            "finish_reason": kw.get("turn_exit_reason")})


def register(ctx) -> None:
    for name, fn in (("pre_api_request", on_pre_api_request), ("post_api_request", on_post_api_request),
                     ("api_request_error", on_api_request_error),
                     ("post_auxiliary_call", on_post_auxiliary_call),
                     ("post_tool_call", on_post_tool_call), ("on_session_end", on_session_end)):
        ctx.register_hook(name, fn)
