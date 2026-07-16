"""
Module 5 Solution — Refactoring the God Class
=============================================
Run: python3 solution.py
"""
from typing import Protocol


# --- the original, kept as the behavioral baseline ---------------------------
class OrderManager:
    def __init__(self):
        self.sent_emails = []

    def process(self, items, discount_kind):
        subtotal = sum(price * qty for _, price, qty in items)
        if discount_kind == "none":
            total = subtotal
        elif discount_kind == "percent10":
            total = subtotal * 0.9
        elif discount_kind == "flat5":
            total = max(0, subtotal - 5)
        else:
            raise ValueError(discount_kind)
        receipt = f"RECEIPT: {len(items)} line(s), total ${total:.2f}"
        self.sent_emails.append(f"to=customer :: {receipt}")
        return total, receipt


# --- TODO 1 (SRP): pricing is pure logic — it wants to be a function ---------
def compute_subtotal(items: list[tuple[str, float, int]]) -> float:
    return sum(price * qty for _, price, qty in items)


# --- TODO 2 (OCP): discount registry ------------------------------------------
class Discount(Protocol):
    def apply(self, subtotal: float) -> float: ...


DISCOUNTS: dict[str, Discount] = {}


def register_discount(name: str):
    """New discounts self-register; nobody edits an if/elif ladder again."""
    def deco(cls):
        DISCOUNTS[name] = cls()
        return cls
    return deco


@register_discount("none")
class NoDiscount:
    def apply(self, subtotal: float) -> float:
        return subtotal


@register_discount("percent10")
class TenPercent:
    def apply(self, subtotal: float) -> float:
        return subtotal * 0.9


@register_discount("flat5")
class FlatFive:
    def apply(self, subtotal: float) -> float:
        return max(0, subtotal - 5)


# --- TODO 3 (SRP): formatting stands alone -------------------------------------
class ReceiptFormatter:
    def format(self, line_count: int, total: float) -> str:
        return f"RECEIPT: {line_count} line(s), total ${total:.2f}"


# --- TODO 4 (DIP + ISP): a narrow, injectable mailer ----------------------------
class Mailer(Protocol):
    def send(self, to: str, body: str) -> None: ...


class MemoryMailer:
    def __init__(self):
        self.sent: list[str] = []

    def send(self, to: str, body: str) -> None:
        self.sent.append(f"to={to} :: {body}")


# --- TODO 5: the thin coordinator ------------------------------------------------
class OrderService:
    """High-level policy only: sequence the steps. Every concern is a
    collaborator injected through the constructor — the DIP seam."""

    def __init__(self, discounts: dict[str, Discount],
                 formatter: ReceiptFormatter, mailer: Mailer):
        self._discounts = discounts
        self._formatter = formatter
        self._mailer = mailer

    def process(self, items, discount_kind: str) -> tuple[float, str]:
        try:
            discount = self._discounts[discount_kind]
        except KeyError:
            raise ValueError(discount_kind) from None
        total = discount.apply(compute_subtotal(items))
        # Stretch 1 (LSP guard): the Discount contract promises a
        # non-negative total; enforce the postcondition at the boundary.
        if total < 0:
            raise ValueError(f"discount {discount_kind!r} produced a negative total")
        receipt = self._formatter.format(len(items), total)
        self._mailer.send("customer", receipt)
        return total, receipt

    # Stretch 2: stackable discounts
    def process_stacked(self, items, discount_kinds: list[str]) -> tuple[float, str]:
        total = compute_subtotal(items)
        for kind in discount_kinds:
            total = self._discounts[kind].apply(total)
        receipt = self._formatter.format(len(items), total)
        self._mailer.send("customer", receipt)
        return total, receipt


if __name__ == "__main__":
    items = [("book", 12.50, 2), ("pen", 1.25, 4)]      # subtotal 30.00

    legacy_total, legacy_receipt = OrderManager().process(items, "percent10")

    mailer = MemoryMailer()
    service = OrderService(DISCOUNTS, ReceiptFormatter(), mailer)

    total, receipt = service.process(items, "percent10")
    assert (total, receipt) == (legacy_total, legacy_receipt)
    assert mailer.sent == [f"to=customer :: {receipt}"]

    assert service.process(items, "none")[0] == 30.00
    assert service.process(items, "flat5")[0] == 25.00

    try:
        service.process(items, "mystery")
        raise SystemExit("FAIL")
    except ValueError:
        pass

    # OCP: extend without edits
    class HalfOff:
        def apply(self, subtotal):
            return subtotal / 2

    DISCOUNTS["half"] = HalfOff()
    assert service.process(items, "half")[0] == 15.00

    # DIP: swap the mailer freely
    class NullMailer:
        def send(self, to, body):
            pass

    OrderService(DISCOUNTS, ReceiptFormatter(), NullMailer()).process(items, "none")

    # Stretch 1: a contract-breaking discount is caught at the boundary
    class EvilDiscount:
        def apply(self, subtotal):
            return subtotal - 1_000_000   # breaks the non-negative postcondition

    DISCOUNTS["evil"] = EvilDiscount()
    try:
        service.process(items, "evil")
        raise SystemExit("FAIL: LSP guard missing")
    except ValueError:
        pass

    # Stretch 2: stacking
    stacked_total, _ = service.process_stacked(items, ["percent10", "flat5"])
    assert stacked_total == 30.00 * 0.9 - 5

    print("All solution checks passed ✔")
