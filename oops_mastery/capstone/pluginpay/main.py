"""Composition root (Module 9) + end-to-end demo.

Run from the capstone directory:
    python3 -m pluginpay.main

This is the ONE place concrete classes meet: repo, providers, fraud scorer,
emitter, ids — all chosen here, injected everywhere else.
"""
from pluginpay.api import Response, build_api
from pluginpay.events import EventEmitter
from pluginpay.fraud import FraudAdapter, LegacyFraudScorer
from pluginpay.providers import (PaymentProvider, available_providers,
                                 get_provider)
from pluginpay.providers.wallet import WalletProvider
from pluginpay.repos import InMemoryPaymentRepo
from pluginpay.service import PaymentService, SequentialIds


def build_app() -> tuple:
    events = EventEmitter()
    service = PaymentService(
        repo=InMemoryPaymentRepo(),
        provider_factory=get_provider,
        fraud=FraudAdapter(LegacyFraudScorer(), threshold=80),
        events=events,
        ids=SequentialIds(),
    )
    return build_api(service), service, events


def show(label: str, resp: Response):
    print(f"   {label:42} -> {resp.status} {resp.body}")


def main():
    print("=" * 74)
    print("PluginPay — end-to-end demo")
    print("=" * 74)

    api, service, events = build_app()

    print(f"registered provider plugins: {available_providers()}")
    assert available_providers() == ["card", "wallet"]

    # observers: a webhook collector and a deliberately broken one
    webhooks: list[dict] = []
    events.subscribe("payment.captured", webhooks.append)
    events.subscribe("payment.captured", lambda p: 1 / 0)   # must not break flow

    # --- 1. happy path: card charge -------------------------------------
    r = api.handle("POST", "/payments", {
        "customer": "ada", "amount_cents": 129_99, "provider": "card"})
    show("POST /payments card $129.99", r)
    assert r.status == 201 and r.body["status"] == "captured"
    pay_id = r.body["id"]
    assert webhooks and webhooks[0]["id"] == pay_id        # observer fired

    # --- 2. flaky wallet: @retry absorbs two transient failures ----------
    WalletProvider.make_flaky(2)
    r = api.handle("POST", "/payments", {
        "customer": "bob", "amount_cents": 15_00, "provider": "wallet"})
    show("POST /payments wallet (flaky x2)", r)
    assert r.status == 201, "retry middleware should have absorbed the hiccups"

    # --- 3. fraud path -> 402 at the boundary ------------------------------
    r = api.handle("POST", "/payments", {
        "customer": "mallory", "amount_cents": 900_00, "provider": "card"})
    show("POST /payments $900.00 (suspicious)", r)
    assert r.status == 402

    # --- 4. provider rule -> 502 -------------------------------------------
    r = api.handle("POST", "/payments", {
        "customer": "carol", "amount_cents": 700_00, "provider": "wallet"})
    r2 = api.handle("POST", "/payments", {
        "customer": "carol", "amount_cents": 700_00, "provider": "card"})
    show("POST /payments card $700.00 (over cap)", r2)
    assert r.status == 201 and r2.status == 502            # wallet ok, card capped

    # --- 5. domain invariants -> 400 -----------------------------------------
    r = api.handle("POST", "/payments", {
        "customer": "", "amount_cents": 10_00, "provider": "card"})
    show("POST /payments empty customer", r)
    assert r.status == 400                                  # descriptor fired

    r = api.handle("POST", "/payments", {
        "customer": "dan", "amount_cents": 10_00, "provider": "carrier-pigeon"})
    show("POST /payments unknown provider", r)
    assert r.status == 400                                  # factory rejected

    # --- 6. lookup + refund flow -----------------------------------------------
    r = api.handle("GET", "/payments", {"id": pay_id})
    show(f"GET  /payments {pay_id}", r)
    assert r.status == 200

    r = api.handle("POST", "/refunds", {"id": pay_id})
    show(f"POST /refunds {pay_id}", r)
    assert r.status == 200 and r.body["status"] == "refunded"

    r = api.handle("POST", "/refunds", {"id": pay_id})      # double refund
    show(f"POST /refunds {pay_id} (again)", r)
    assert r.status == 400                                  # state machine said no

    r = api.handle("GET", "/payments", {"id": "pay-9999"})
    show("GET  /payments pay-9999", r)
    assert r.status == 404

    # --- 7. runtime extensibility: a new plugin, zero core edits -----------------
    class GiftCardProvider(PaymentProvider):
        provider_name = "giftcard"

        def charge(self, amount):
            return f"gift-ref-{amount.amount}"

        def refund(self, amount, reference):
            pass

    r = api.handle("POST", "/payments", {
        "customer": "erin", "amount_cents": 25_00, "provider": "giftcard"})
    show("POST /payments via giftcard plugin", r)
    assert r.status == 201
    assert "giftcard" in available_providers()

    # a broken plugin cannot even be defined:
    try:
        class BrokenProvider(PaymentProvider):
            provider_name = "broken"
            def charge(self, amount):                        # refund missing
                return "?"
        raise SystemExit("FAIL: metaclass enforcement did not fire")
    except TypeError as e:
        print(f"   defining BrokenProvider -> TypeError: {e}")

    # --- 8. the books balance ------------------------------------------------------
    total = service.captured_total_cents()
    print(f"captured total: {total} cents")
    assert total == 129_99 + 15_00 + 700_00 + 25_00

    print(f"audit trail ({len(service.audit_trail)} entries): "
          f"{service.audit_trail[:3]} ...")
    assert "charge: ok" in service.audit_trail
    assert "charge: FraudSuspected" in service.audit_trail
    assert "refund: DomainError" in service.audit_trail

    print()
    print("All capstone assertions passed ✔")


if __name__ == "__main__":
    main()
