"""
Module 8 Solution — Patterns in a Mini Order System
===================================================
Run: python3 solution.py
"""
from typing import Callable


# --- TODO 1: Strategy + Factory ----------------------------------------------
DISCOUNTS: dict[str, Callable[[float], float]] = {}


def discount(name: str):
    def deco(strategy):
        DISCOUNTS[name] = strategy
        return strategy
    return deco


@discount("none")
def no_discount(subtotal: float) -> float:
    return subtotal


@discount("ten_off")
def ten_off(subtotal: float) -> float:
    return max(0, subtotal - 10)


class SeasonalDiscount:
    """Class strategy: carries configuration, still just a callable."""

    def __init__(self, percent: float):
        self.percent = percent

    def __call__(self, subtotal: float) -> float:
        return subtotal * (1 - self.percent / 100)


DISCOUNTS["seasonal"] = SeasonalDiscount(25)


def get_discount(name: str) -> Callable[[float], float]:
    try:
        return DISCOUNTS[name]
    except KeyError:
        raise ValueError(f"unknown discount {name!r}") from None


# --- TODO 2: Observer -----------------------------------------------------------
class NotificationCenter:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}

    def subscribe(self, event: str, handler: Callable) -> Callable[[], None]:
        self._handlers.setdefault(event, []).append(handler)

        def unsubscribe():
            self._handlers[event].remove(handler)
        return unsubscribe

    def emit(self, event: str, payload) -> list[Exception]:
        errors: list[Exception] = []
        # Copy: a handler that unsubscribes during emit must not corrupt
        # the iteration.
        for handler in list(self._handlers.get(event, [])):
            try:
                handler(payload)
            except Exception as e:
                errors.append(e)                 # isolate; keep notifying
        return errors

    # Stretch 2: fire once, then remove itself.
    def once(self, event: str, handler: Callable) -> None:
        def one_shot(payload):
            off()
            handler(payload)
        off = self.subscribe(event, one_shot)


# --- TODO 3: Adapter --------------------------------------------------------------
class LegacyTaxService:
    def computeTaxCents(self, amount_cents: int, region_code: str) -> int:
        rates = {"EU": 20, "US": 8}
        return amount_cents * rates.get(region_code, 0) // 100


class TaxAdapter:
    """Object adapter: converts our dollars/keyword world into the legacy
    cents/camelCase world, and hides that world from callers."""

    def __init__(self, legacy: LegacyTaxService):
        self._legacy = legacy

    def tax_for(self, amount: float, region: str) -> float:
        cents = self._legacy.computeTaxCents(round(amount * 100), region)
        return cents / 100


# --- TODO 4: Builder ----------------------------------------------------------------
class OrderBuilder:
    def __init__(self, notifications: NotificationCenter | None = None):
        self._items: list[tuple[str, float, int]] = []
        self._discount = "none"
        self._region = "US"
        self._notifications = notifications      # Stretch 1

    def item(self, name: str, price: float, qty: int) -> "OrderBuilder":
        self._items.append((name, price, qty))
        return self

    def discount(self, name: str) -> "OrderBuilder":
        self._discount = name
        return self

    def region(self, code: str) -> "OrderBuilder":
        self._region = code
        return self

    def build(self) -> dict:
        if not self._items:
            raise ValueError("order has no items")
        subtotal = sum(price * qty for _, price, qty in self._items)
        discounted = get_discount(self._discount)(subtotal)
        tax = TaxAdapter(LegacyTaxService()).tax_for(discounted, self._region)
        order = {
            "items": list(self._items),
            "subtotal": round(subtotal, 2),
            "discounted": round(discounted, 2),
            "tax": round(tax, 2),
            "total": round(discounted + tax, 2),
        }
        if self._notifications is not None:      # Stretch 1
            self._notifications.emit("order.built", order)
        return order


if __name__ == "__main__":
    assert get_discount("none")(50.0) == 50.0
    assert get_discount("ten_off")(50.0) == 40.0
    assert get_discount("ten_off")(4.0) == 0
    assert get_discount("seasonal")(100.0) == 75.0
    try:
        get_discount("mystery")
        raise SystemExit("FAIL")
    except ValueError:
        pass

    nc = NotificationCenter()
    inbox = []
    off = nc.subscribe("order.placed", inbox.append)
    nc.subscribe("order.placed", lambda p: (_ for _ in ()).throw(RuntimeError()))
    errs = nc.emit("order.placed", "ord-1")
    assert inbox == ["ord-1"] and len(errs) == 1
    off()
    nc.emit("order.placed", "ord-2")
    assert inbox == ["ord-1"]
    assert nc.emit("ghost.event", None) == []

    tax = TaxAdapter(LegacyTaxService())
    assert tax.tax_for(100.0, "EU") == 20.0
    assert tax.tax_for(100.0, "US") == 8.0
    assert tax.tax_for(100.0, "XX") == 0.0

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
        raise SystemExit("FAIL")
    except ValueError:
        pass

    # Stretch 1: builder emits through an injected center
    events = []
    nc2 = NotificationCenter()
    nc2.subscribe("order.built", events.append)
    OrderBuilder(nc2).item("gum", 2.0, 1).build()
    assert len(events) == 1 and events[0]["subtotal"] == 2.0

    # Stretch 2: once()
    seen = []
    nc2.once("ping", seen.append)
    nc2.emit("ping", 1)
    nc2.emit("ping", 2)
    assert seen == [1]

    print("All solution checks passed ✔")
