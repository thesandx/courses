"""
Module 8 Exercise: Patterns in a Mini Order System
==================================================
Goal
----
Assemble a small order-processing toolkit from four patterns: a factory of
discount strategies, an observer-based notification center, an adapter for a
legacy tax service, and a fluent order builder.

Complete the TODOs, then run:  python3 exercise.py
"""
from typing import Callable, Protocol


# ---------------------------------------------------------------------------
# TODO 1 — Strategy + Factory: discounts
# ---------------------------------------------------------------------------
# * DISCOUNTS: dict[str, Callable[[float], float]] — registry
# * decorator discount(name) that registers a callable under `name`
# * register three strategies:
#     "none"      -> unchanged
#     "ten_off"   -> subtotal - 10, floored at 0
#     "seasonal"  -> a CLASS SeasonalDiscount with __init__(percent) and
#                    __call__(subtotal); register an instance:
#                    SeasonalDiscount(25) under "seasonal" (25% off)
# * factory get_discount(name) -> the callable; ValueError for unknown names


# ---------------------------------------------------------------------------
# TODO 2 — Observer: NotificationCenter
# ---------------------------------------------------------------------------
# class NotificationCenter:
#   * subscribe(event, handler) -> returns an unsubscribe callable
#   * emit(event, payload) -> list of exceptions raised by handlers
#     (handlers that raise must NOT stop the rest; collect the exceptions)
#   * emitting an event nobody subscribed to returns []


# ---------------------------------------------------------------------------
# TODO 3 — Adapter: LegacyTaxService
# ---------------------------------------------------------------------------
# Provided legacy class (do not modify):
class LegacyTaxService:
    def computeTaxCents(self, amount_cents: int, region_code: str) -> int:
        rates = {"EU": 20, "US": 8}
        return amount_cents * rates.get(region_code, 0) // 100


# Our code expects:  tax_for(amount: float, region: str) -> float (in dollars)
# Write TaxAdapter wrapping a LegacyTaxService instance and exposing
# tax_for(amount, region). Convert dollars<->cents (round to int cents on the
# way in, back to float dollars on the way out).


# ---------------------------------------------------------------------------
# TODO 4 — Builder: OrderBuilder
# ---------------------------------------------------------------------------
# Fluent builder producing a plain dict:
#   OrderBuilder().item("book", 12.5, 2).item("pen", 1.0, 1)
#                 .discount("ten_off").region("EU").build()
# -> {"items": [...], "subtotal": 26.0, "discounted": 16.0,
#     "tax": <tax on discounted>, "total": discounted + tax}
# Rules:
#   * item(name, price, qty) appends and returns self
#   * discount(name) / region(code) store and return self
#   * build() raises ValueError("order has no items") when empty
#   * discount defaults to "none"; region defaults to "US"
#   * build() uses get_discount(...) and a TaxAdapter(LegacyTaxService())
#   * round money to 2 decimals in the result


# ---------------------------------------------------------------------------
# Self-Verification — do not modify below this line
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # TODO 1
    assert get_discount("none")(50.0) == 50.0
    assert get_discount("ten_off")(50.0) == 40.0
    assert get_discount("ten_off")(4.0) == 0
    assert get_discount("seasonal")(100.0) == 75.0
    try:
        get_discount("mystery")
        raise SystemExit("FAIL: unknown discount must raise ValueError")
    except ValueError:
        pass

    # TODO 2
    nc = NotificationCenter()
    inbox = []
    off = nc.subscribe("order.placed", inbox.append)
    nc.subscribe("order.placed", lambda p: (_ for _ in ()).throw(RuntimeError()))
    errs = nc.emit("order.placed", "ord-1")
    assert inbox == ["ord-1"] and len(errs) == 1
    off()
    nc.emit("order.placed", "ord-2")
    assert inbox == ["ord-1"], "unsubscribed handler must not fire"
    assert nc.emit("ghost.event", None) == []

    # TODO 3
    tax = TaxAdapter(LegacyTaxService())
    assert tax.tax_for(100.0, "EU") == 20.0
    assert tax.tax_for(100.0, "US") == 8.0
    assert tax.tax_for(100.0, "XX") == 0.0

    # TODO 4
    order = (OrderBuilder()
             .item("book", 12.5, 2)
             .item("pen", 1.0, 1)
             .discount("ten_off")
             .region("EU")
             .build())
    assert order["subtotal"] == 26.0
    assert order["discounted"] == 16.0
    assert order["tax"] == 3.2
    assert order["total"] == 19.2

    default_order = OrderBuilder().item("gum", 2.0, 1).build()
    assert default_order["total"] == round(2.0 + 2.0 * 0.08, 2)

    try:
        OrderBuilder().build()
        raise SystemExit("FAIL: empty order must raise")
    except ValueError:
        pass

    print("All exercise checks passed ✔")

# ---------------------------------------------------------------------------
# Stretch Goals
# ---------------------------------------------------------------------------
# 1. Make OrderBuilder emit "order.built" through a NotificationCenter
#    injected into its constructor (observer + builder composed).
# 2. Add a once(event, handler) to NotificationCenter (auto-unsubscribes
#    after the first firing).
# 3. Replace the DISCOUNTS registry with entry points discovered from a
#    dict-of-modules to simulate plugin loading.

# Cleanup: nothing to clean up — pure in-memory Python.
