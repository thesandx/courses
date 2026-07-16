"""
Module 5 Exercise: Refactor the God Class
=========================================
Goal
----
Below is `OrderManager`, a working but deliberately awful class violating all
five principles. Refactor it into SOLID shape WITHOUT changing observable
behavior — the verification block defines that behavior.

Keep the awful original for reference; build your refactor beneath it.
Run:  python3 exercise.py
"""
from typing import Protocol


# ---------------------------------------------------------------------------
# THE CRIME SCENE (do not edit — reference behavior)
# ---------------------------------------------------------------------------
class OrderManager:
    """Violations: computes totals AND formats receipts AND 'sends' emails (SRP);
    if/elif over discount kinds (OCP); constructs its own mailer inline (DIP);
    one fat class every caller must take whole (ISP)."""

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
        self.sent_emails.append(f"to=customer :: {receipt}")   # inline "mailer"
        return total, receipt


# ---------------------------------------------------------------------------
# YOUR REFACTOR
# ---------------------------------------------------------------------------
# TODO 1 (SRP) — pure pricing function
#   compute_subtotal(items) -> float           items = [(name, price, qty), ...]
#
# TODO 2 (OCP) — a discount REGISTRY instead of if/elif
#   * class Discount(Protocol): def apply(self, subtotal: float) -> float
#   * DISCOUNTS: dict[str, Discount] with "none", "percent10", "flat5"
#     implemented as small classes (or use a @register_discount decorator).
#   * Adding a new discount must require ZERO edits to existing code.
#
# TODO 3 (SRP again) — ReceiptFormatter
#   class ReceiptFormatter with format(line_count: int, total: float) -> str
#   producing exactly:  f"RECEIPT: {line_count} line(s), total ${total:.2f}"
#
# TODO 4 (DIP + ISP) — inject a narrow Mailer protocol
#   * class Mailer(Protocol): def send(self, to: str, body: str) -> None
#   * class MemoryMailer: records into self.sent as f"to={to} :: {body}"
#
# TODO 5 — OrderService: the thin coordinator
#   class OrderService:
#       __init__(self, discounts: dict[str, Discount], formatter, mailer)
#       process(self, items, discount_kind) -> tuple[float, str]
#   Same observable results as OrderManager.process, but every concern
#   lives in an injected collaborator. Raise ValueError for unknown kinds.


# ---------------------------------------------------------------------------
# Self-Verification — do not modify below this line
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    items = [("book", 12.50, 2), ("pen", 1.25, 4)]      # subtotal = 30.00

    # the old god class, as a behavioral baseline
    legacy_total, legacy_receipt = OrderManager().process(items, "percent10")

    mailer = MemoryMailer()
    service = OrderService(DISCOUNTS, ReceiptFormatter(), mailer)

    total, receipt = service.process(items, "percent10")
    assert (total, receipt) == (legacy_total, legacy_receipt), (total, receipt)
    assert mailer.sent == [f"to=customer :: {receipt}"]

    assert service.process(items, "none")[0] == 30.00
    assert service.process(items, "flat5")[0] == 25.00

    try:
        service.process(items, "mystery")
        raise SystemExit("FAIL: unknown discount must raise ValueError")
    except ValueError:
        pass

    # OCP proof: extend WITHOUT touching existing classes
    class HalfOff:
        def apply(self, subtotal):
            return subtotal / 2

    DISCOUNTS["half"] = HalfOff()
    assert service.process(items, "half")[0] == 15.00

    # DIP proof: the service works with any Mailer-shaped object
    class NullMailer:
        def send(self, to, body):
            pass

    OrderService(DISCOUNTS, ReceiptFormatter(), NullMailer()).process(items, "none")

    print("All exercise checks passed ✔")

# ---------------------------------------------------------------------------
# Stretch Goals
# ---------------------------------------------------------------------------
# 1. LSP audit: write a `BulkDiscount(Discount)` whose apply() returns a
#    NEGATIVE total for small orders. Which contract rule does it break?
#    Add a guard where it belongs.
# 2. Make discounts stackable: process(items, ["percent10", "flat5"]).
# 3. Type-check the file with mypy; annotate everything.

# Cleanup: nothing to clean up — pure in-memory Python.
