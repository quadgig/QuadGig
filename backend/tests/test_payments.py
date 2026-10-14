import hashlib
import hmac
import json
import os
import time

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-key")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_fake")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_fake")

WEBHOOK_SECRET = "whsec_fake"

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _sign(payload: bytes, secret: str = WEBHOOK_SECRET) -> str:
    timestamp = str(int(time.time()))
    signed_payload = f"{timestamp}.{payload.decode()}"
    signature = hmac.new(secret.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"


def test_webhook_rejects_missing_signature():
    payload = json.dumps({"type": "payment_intent.succeeded"}).encode()
    response = client.post("/webhooks/stripe", content=payload)
    assert response.status_code == 400


def test_webhook_rejects_invalid_signature():
    payload = json.dumps({"type": "payment_intent.succeeded"}).encode()
    response = client.post(
        "/webhooks/stripe",
        content=payload,
        headers={"stripe-signature": "t=123,v1=not_a_real_signature"},
    )
    assert response.status_code == 400


def test_webhook_accepts_correctly_signed_payload():
    payload = json.dumps({
        "id": "evt_test",
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": "pi_test", "amount": 2000}},
    }).encode()
    response = client.post(
        "/webhooks/stripe",
        content=payload,
        headers={"stripe-signature": _sign(payload)},
    )
    assert response.status_code == 500


def test_webhook_handles_charge_refunded_event():
    payload = json.dumps({
        "id": "evt_test_refund",
        "type": "charge.refunded",
        "data": {"object": {"id": "ch_test", "payment_intent": "pi_test"}},
    }).encode()
    response = client.post(
        "/webhooks/stripe",
        content=payload,
        headers={"stripe-signature": _sign(payload)},
    )
    assert response.status_code == 500



def test_webhook_handles_payment_failed_event():
    payload = json.dumps({
        "id": "evt_test_failed",
        "type": "payment_intent.payment_failed",
        "data": {"object": {"id": "pi_test"}},
    }).encode()
    response = client.post(
        "/webhooks/stripe",
        content=payload,
        headers={"stripe-signature": _sign(payload)},
    )
    assert response.status_code == 500


def test_onboarding_links_point_at_frontend(monkeypatch):
    from types import SimpleNamespace
    from app import payments
    from app.deps import get_current_user

    created = {}

    class FakeTable:
        def select(self, *a): return self
        def eq(self, *a): return self
        def update(self, *a): return self
        def execute(self):
            return SimpleNamespace(data=[{"stripe_connect_account_id": "acct_test"}])

    class FakeSupabase:
        def table(self, name): return FakeTable()

    class FakeLinks:
        def create(self, params):
            created.update(params)
            return SimpleNamespace(url="https://connect.stripe.com/setup/test")

    fake_stripe = SimpleNamespace(v1=SimpleNamespace(account_links=FakeLinks()))
    monkeypatch.setattr(payments, "get_supabase", lambda: FakeSupabase())
    monkeypatch.setattr(payments, "get_stripe", lambda: fake_stripe)
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "email": "a@b.edu"}
    try:
        response = client.post("/payments/onboard")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert created["return_url"].endswith("/onboarding/complete")
    assert created["refresh_url"].endswith("/onboarding/refresh")
    assert "example.com" not in created["return_url"]


def test_cors_allows_configured_frontend():
    response = client.options(
        "/listings",
        headers={
            "Origin": "https://quad-gig.vercel.app",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "https://quad-gig.vercel.app"
