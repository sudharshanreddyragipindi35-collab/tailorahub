from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_phase10_harness_has_progressive_profiles_and_release_thresholds():
    source = (ROOT / "load-tests" / "phase10.js").read_text(encoding="utf-8")
    for profile in ("smoke", "baseline", "normal", "growth", "release", "high", "spike", "soak"):
        assert f"{profile}:" in source
    for target in ('target: 50', 'target: 100', 'target: 250', 'target: 500', 'target: 1000'):
        assert target in source
    assert 'business_errors: ["rate<0.01"]' in source
    assert '"http_req_duration{operation:read}": ["p(95)<500"]' in source
    assert '"http_req_duration{operation:write}": ["p(95)<1000"]' in source
    assert 'iterations: ["count>0"]' in source


def test_phase10_harness_covers_required_suites_and_fails_closed():
    source = (ROOT / "load-tests" / "phase10.js").read_text(encoding="utf-8")
    for suite in (
        "public-read",
        "customer-read",
        "tailor-read",
        "admin-read",
        "auth",
        "booking",
        "tailor-stage",
        "notifications",
        "media",
        "websocket",
        "payment",
    ):
        assert f'"{suite}"' in source or f'{suite}:' in source
    assert "TAILORAHUB_APPROVED_LOAD_TEST" in source
    assert "TAILORAHUB_APPROVED_SYNTHETIC_WRITES" in source
    assert "TAILORAHUB_APPROVED_SANDBOX_PAYMENTS" in source
    assert "duplicate booking is deduplicated" in source
    assert "websocket receives pong" in source
    assert 'PAYMENT_ACTION || "create"' in source
    assert "PAYMENT_VERIFY_PAYLOAD" in source
    assert 'required("MEDIA_UPLOAD_URL")' in source


def test_phase10_generated_results_are_ignored():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "load-test-results/" in gitignore
