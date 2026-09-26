from scanners import gemini_decision


def test_evaluate_candidate_parses_structured_response(monkeypatch):
    payload = {
        "candidates": [{
            "content": {"parts": [{"text": '{"setup":"SETUP","confidence":0.8,"quality":4,"review_probability":0.65,"reason":"Mixed confirmation."}'}]}
        }],
        "usageMetadata": {"promptTokenCount": 500, "candidatesTokenCount": 80},
    }

    captured = {}

    def fake_request(request_payload, api_key):
        captured["payload"] = request_payload
        captured["api_key"] = api_key
        return payload

    monkeypatch.setattr(gemini_decision, "_request", fake_request)

    result = gemini_decision.evaluate_candidate(
        {"ticker": "NVDA", "master_score": 78.5, "status": "ENTRY", "rr": 2.1},
        api_key="test-key",
    )

    assert result["ai_setup"] == "SETUP"
    assert result["ai_confidence"] == 0.8
    assert result["ai_quality"] == 4
    assert result["ai_review_probability"] == 0.65
    assert captured["api_key"] == "test-key"
    assert captured["payload"]["model"] == gemini_decision.GEMINI_MODEL
    assert captured["payload"]["generationConfig"]["responseMimeType"] == "application/json"


def test_evaluate_candidates_fails_open(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("temporary failure")

    monkeypatch.setattr(gemini_decision, "evaluate_candidate", fail)

    rows = [{"ticker": "AAPL", "master_score": 80}]
    result = gemini_decision.evaluate_candidates(rows, api_key="test-key")

    assert result[0]["ticker"] == "AAPL"
    assert "temporary failure" in result[0]["ai_error"]
