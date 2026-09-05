from evaluation.objective_scorers import score


def test_objective_scorers() -> None:
    assert score("exact", " CACHE_READY\n", "CACHE_READY")
    assert score("numeric", "500", 500)
    assert score("integer_set", "503, 422, 429", [422, 429, 503])
    assert score(
        "json_exact",
        '{"healthy": true, "service": "gateway"}',
        {"service": "gateway", "healthy": True},
    )
    assert score("contains_all", "Time to First Token (TTFT)", ["time to first token", "TTFT"])
