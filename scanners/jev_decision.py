"""Jev decision layer for the master stock scanner.

Jev is used as a second-opinion classifier. It never changes the deterministic
master-entry rules; its output is attached to each candidate for review.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

JEV_ENDPOINT = "https://api.typesafe.ai/v1/systemone"
JEV_MODEL = os.getenv("JEV_MODEL", "jev-latest")
JEV_CHOICES = {
    "ENTRY": "Evidence supports an actionable setup with acceptable confirmation and risk/reward.",
    "SETUP": "Promising setup, but confirmation or risk/reward is incomplete.",
    "WATCH": "Interesting evidence, but not enough support for an actionable setup.",
    "AVOID": "Evidence is materially weak, contradictory, or risk is unattractive.",
}


def _request(payload: dict[str, Any], api_key: str, attempts: int = 3) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    last_error: Exception | None = None

    for attempt in range(attempts):
        request = urllib.request.Request(
            JEV_ENDPOINT,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in (429, 529) or attempt == attempts - 1:
                detail = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"Jev API HTTP {exc.code}: {detail[:500]}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt == attempts - 1:
                raise RuntimeError(f"Jev API request failed: {exc}") from exc

        time.sleep(2**attempt)

    raise RuntimeError(f"Jev API request failed: {last_error}")


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


def evaluate_candidate(row: dict[str, Any], api_key: str | None = None) -> dict[str, Any]:
    """Return Jev's structured second opinion for one master candidate."""
    key = api_key or os.getenv("TYPESAFE_API_KEY") or os.getenv("JEV_API_KEY")
    if not key:
        raise RuntimeError("TYPESAFE_API_KEY is not configured")

    payload = {
        "model": JEV_MODEL,
        "state": _state_for(row),
        "questions": {
            "setup": {
                "type": "choice",
                "instructions": (
                    "Classify the setup using only the supplied scanner evidence. "
                    "Do not invent fundamentals, news, price data, or catalysts."
                ),
                "criteria": JEV_CHOICES,
            },
            "quality": {
                "type": "score",
                "instructions": "Score the quality of the supplied trading setup evidence.",
                "criteria": [
                    "Very weak",
                    "Weak",
                    "Mixed",
                    "Good",
                    "Very good",
                ],
            },
            "needs_review": {
                "type": "noul",
                "instructions": (
                    "Does the supplied evidence contain enough uncertainty or "
                    "conflict that a human should review it before acting?"
                ),
            },
        },
    }

    response = _request(payload, key)
    answers = response.get("answers", {})
    setup = answers.get("setup", {})
    quality = answers.get("quality", {})
    review = answers.get("needs_review", {})

    choice = setup.get("choice")
    if choice not in JEV_CHOICES:
        raise RuntimeError(f"Unexpected Jev choice: {choice!r}")

    return {
        "jev_model": response.get("model", JEV_MODEL),
        "jev_setup": choice,
        "jev_probabilities": setup.get("probabilities", {}),
        "jev_confidence": setup.get("confidence"),
        "jev_quality": quality.get("score"),
        "jev_review_probability": review.get("noul"),
        "jev_input_tokens": response.get("usage", {}).get("input_tokens"),
    }


def evaluate_candidates(
    rows: list[dict[str, Any]],
    *,
    api_key: str | None = None,
    max_candidates: int | None = None,
) -> list[dict[str, Any]]:
    """Attach Jev results while failing open for the scanner itself.

    A Jev outage must never prevent the deterministic scanner report from being
    generated. Failed candidates get an explicit error field.
    """
    selected = rows if max_candidates is None else rows[:max_candidates]
    results: list[dict[str, Any]] = []

    for row in selected:
        enriched = dict(row)
        try:
            enriched.update(evaluate_candidate(row, api_key=api_key))
        except Exception as exc:
            enriched["jev_error"] = str(exc)
        results.append(enriched)

    return results
