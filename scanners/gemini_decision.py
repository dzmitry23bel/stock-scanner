"""Gemini AI second-opinion layer for the master stock scanner.

Gemini is used as a second opinion. It never changes the deterministic
master-entry rules, trade levels, or hard risk/reward gates.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
SETUP_CHOICES = ("ENTRY", "SETUP", "WATCH", "AVOID")


def _request(payload: dict[str, Any], api_key: str, attempts: int = 3) -> dict[str, Any]:
    model = payload.get("model", GEMINI_MODEL)
    url = GEMINI_ENDPOINT.format(model=model)
    body = json.dumps(payload).encode("utf-8")
    last_error: Exception | None = None

    for attempt in range(attempts):
        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                detail = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"Gemini API HTTP {exc.code}: {detail[:500]}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt == attempts - 1:
                raise RuntimeError(f"Gemini API request failed: {exc}") from exc

        time.sleep(2**attempt)

    raise RuntimeError(f"Gemini API request failed: {last_error}")


def _state_for(row: dict[str, Any]) -> dict[str, Any]:
    """Keep the state compact and limited to scanner-produced evidence."""
    return {
        "ticker": row.get("ticker"),
        "master_score": row.get("master_score"),
        "deterministic_status": row.get("status"),
        "trend_score": row.get("trend_score"),
        "knife_score": row.get("knife_score"),
        "day_score": row.get("day_score"),
        "agreement": row.get("agreement"),
        "risk_reward": row.get("rr"),
        "entry": row.get("entry"),
        "stop": row.get("stop"),
        "tp1": row.get("tp1"),
        "tp2": row.get("tp2"),
        "signals": row.get("signals", {}),
        "analyst_upside_pct": row.get("analyst_upside_pct"),
        "analyst_score": row.get("analyst_score"),
    }


def _extract_json(response: dict[str, Any]) -> dict[str, Any]:
    try:
        text = response["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Gemini returned an invalid structured response") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("Gemini returned a non-object response")
    return parsed


def evaluate_candidate(row: dict[str, Any], api_key: str | None = None) -> dict[str, Any]:
    """Return Gemini's structured second opinion for one master candidate."""
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    state = _state_for(row)
    prompt = f"""
You are a strict second-opinion reviewer for a quantitative stock scanner.

Evaluate ONLY the scanner evidence below. Do not invent news, fundamentals,
catalysts, price data, or facts that are not supplied.

Classify the setup:
- ENTRY: evidence supports an actionable setup and risk/reward is acceptable.
- SETUP: promising setup, but confirmation or risk/reward is incomplete.
- WATCH: interesting evidence, but insufficient for an actionable setup.
- AVOID: materially weak, contradictory, or unattractive risk.

Quality is an integer from 1 to 5.
Confidence is a number from 0 to 1.
Review probability is a number from 0 to 1 indicating how strongly a human
should review the setup before acting.

Return ONLY valid JSON with this exact shape:
{{
  "setup": "ENTRY|SETUP|WATCH|AVOID",
  "confidence": 0.0,
  "quality": 1,
  "review_probability": 0.0,
  "reason": "one concise sentence"
}}

Scanner evidence:
{json.dumps(state, ensure_ascii=False, sort_keys=True)}
""".strip()

    payload = {
        "model": GEMINI_MODEL,
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }

    response = _request(payload, key)
    result = _extract_json(response)

    setup = result.get("setup")
    if setup not in SETUP_CHOICES:
        raise RuntimeError(f"Unexpected Gemini setup: {setup!r}")

    confidence = float(result.get("confidence"))
    quality = int(result.get("quality"))
    review_probability = float(result.get("review_probability"))
    if not 0 <= confidence <= 1 or not 1 <= quality <= 5 or not 0 <= review_probability <= 1:
        raise RuntimeError("Gemini returned out-of-range decision values")

    usage = response.get("usageMetadata", {})
    return {
        "ai_model": GEMINI_MODEL,
        "ai_setup": setup,
        "ai_confidence": confidence,
        "ai_quality": quality,
        "ai_review_probability": review_probability,
        "ai_reason": str(result.get("reason", ""))[:500],
        "ai_input_tokens": usage.get("promptTokenCount"),
        "ai_output_tokens": usage.get("candidatesTokenCount"),
    }


def evaluate_candidates(
    rows: list[dict[str, Any]],
    *,
    api_key: str | None = None,
    max_candidates: int | None = None,
) -> list[dict[str, Any]]:
    """Attach Gemini results while failing open for the scanner itself."""
    selected = rows if max_candidates is None else rows[:max_candidates]
    results: list[dict[str, Any]] = []

    for row in selected:
        enriched = dict(row)
        try:
            enriched.update(evaluate_candidate(row, api_key=api_key))
        except Exception as exc:
            enriched["ai_error"] = str(exc)
        results.append(enriched)

    return results
