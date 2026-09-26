from scanners import jev_decision


def test_evaluate_candidate_parses_structured_response(monkeypatch):
    payload = {
        "model": "jev-1.13.0",
        "answers": {
            "setup": {
                "choice": "SETUP",
                "probabilities": {"ENTRY": 0.2, "SETUP": 0.7, "WATCH": 0.1, "AVOID": 0.0},
                "confidence": 0.8,
            },
            "quality": {"score": 3.0},
            "needs_review": {"noul": 0.65},
        },
        "usage": {"input_tokens": 500},
    }

    captured = {}

    def fake_request(request_payload, api_key):
        captured["payload"] = request_payload
        captured["api_key"] = api_key
        return payload

    monkeypatch.setattr(jev_decision, "_request", fake_request)

    result = jev_decision.evaluate_candidate(
        {
            "ticker": "NVDA",
            "master_score": 78.5,
            "status": "ENTRY",
            "rr": 2.1,
            "signals": {"trend_momentum": "BUY DIP"},
        },
        api_key="test-key",
    )

    assert result["jev_setup"] == "SETUP"
    assert result["jev_confidence"] == 0.8
    assert result["jev_quality"] == 3.0
    assert result["jev_review_probability"] == 0.65
    assert captured["api_key"] == "test-key"
    assert captured["payload"]["model"] == jev_decision.JEV_MODEL
    assert captured["payload"]["questions"]["setup"]["type"] == "choice"
    assert "NVDA" == captured["payload"]["state"]["ticker"]


def test_evaluate_candidates_fails_open(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("temporary failure")

    monkeypatch.setattr(jev_decision, "evaluate_candidate", fail)

    rows = [{"ticker": "AAPL", "master_score": 80}]
    result = jev_decision.evaluate_candidates(rows, api_key="test-key")

    assert result[0]["ticker"] == "AAPL"
    assert "temporary failure" in result[0]["jev_error"]
