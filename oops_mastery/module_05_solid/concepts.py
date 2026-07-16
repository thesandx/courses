"""
Module 5: SOLID in Python — Concepts in Action
==============================================
Run: python3 concepts.py

Each section shows the violation, then the Pythonic refactor, side by side.
"""
from dataclasses import dataclass
from typing import Protocol

# ============================================================================
# 1. S — Single Responsibility
# ============================================================================
print("=" * 70)
print("S — Single Responsibility")
print("=" * 70)


# ✗ One class, three reasons to change: math, formatting, persistence.
class ReportGod:
    def __init__(self, sales):
        self.sales = sales

    def run(self):
        total = sum(self.sales)                       # compute
        text = f"TOTAL: {total}"                      # format
        print("   (pretend this writes a file)")      # persist
        return text


# ✓ Split along the "and"s. Each piece is independently testable.
def compute_total(sales: list[float]) -> float:       # pure logic: a function!
    return sum(sales)


class TextFormatter:
    def format(self, total: float) -> str:
        return f"TOTAL: {total}"


class MemorySink:
    def __init__(self):
        self.written = []

    def write(self, text: str) -> None:
        self.written.append(text)


total = compute_total([10.0, 20.0])
sink = MemorySink()
sink.write(TextFormatter().format(total))
print(f"pipeline result: {sink.written[0]!r}  (math tested without any I/O)")
assert sink.written == ["TOTAL: 30.0"]

# ============================================================================
# 2. O — Open/Closed
# ============================================================================
print()
print("=" * 70)
print("O — Open/Closed")
print("=" * 70)


# ✗ Every new payment method edits this function (and its tests):
def checkout_closed(method: str, amount: float) -> str:
    if method == "card":
        return f"card charged {amount}"
    elif method == "paypal":
        return f"paypal charged {amount}"
    raise ValueError(method)


# ✓ A registry: new methods REGISTER themselves; checkout never changes.
class PaymentMethod(Protocol):
    def charge(self, amount: float) -> str: ...


PAYMENT_REGISTRY: dict[str, PaymentMethod] = {}


def register(name: str):
    def deco(cls):
        PAYMENT_REGISTRY[name] = cls()
        return cls
    return deco


@register("card")
class Card:
    def charge(self, amount):
        return f"card charged {amount}"


@register("paypal")
class PayPal:
    def charge(self, amount):
        return f"paypal charged {amount}"


def checkout(method: str, amount: float) -> str:      # closed for modification
    return PAYMENT_REGISTRY[method].charge(amount)


# Extension = pure addition. No existing line was touched:
@register("crypto")
class Crypto:
    def charge(self, amount):
        return f"crypto charged {amount}"


print(f"checkout('crypto', 5) = {checkout('crypto', 5)!r}   <-- added, not edited")
assert checkout("crypto", 5) == "crypto charged 5"
assert sorted(PAYMENT_REGISTRY) == ["card", "crypto", "paypal"]

# ============================================================================
# 3. L — Liskov Substitution
# ============================================================================
print()
print("=" * 70)
print("L — Liskov Substitution")
print("=" * 70)


# ✗ The classic trap: Square IS-A Rectangle mathematically, but not behaviorally.
class Rectangle:
    def __init__(self, w, h):
        self._w, self._h = w, h

    @property
    def width(self):
        return self._w

    @width.setter
    def width(self, v):
        self._w = v

    @property
    def height(self):
        return self._h

    @height.setter
    def height(self, v):
        self._h = v

    @property
    def area(self):
        return self._w * self._h


class Square(Rectangle):
    def __init__(self, side):
        super().__init__(side, side)

    @Rectangle.width.setter
    def width(self, v):
        self._w = self._h = v            # keeps square-ness, breaks the contract

    @Rectangle.height.setter
    def height(self, v):
        self._w = self._h = v


def stretch(rect: Rectangle) -> float:
    """Callers of Rectangle rely on: setting width doesn't touch height."""
    rect.width, rect.height = 4, 5
    return rect.area


ok = stretch(Rectangle(1, 1))
broken = stretch(Square(1))
print(f"stretch(Rectangle) = {ok} (expected 20);  stretch(Square) = {broken}")
assert ok == 20 and broken == 25          # Square violated the caller's contract!
print("   -> Square silently broke code written for Rectangle: LSP violation")

# ✓ Fix: immutable values — no setters, no invariant to break.
@dataclass(frozen=True)
class FrozenRect:
    width: float
    height: float

    @property
    def area(self):
        return self.width * self.height

    def resized(self, w, h) -> "FrozenRect":
        return FrozenRect(w, h)           # returns a NEW rectangle


sq = FrozenRect(3, 3)                     # a square is just a rect with w == h
assert sq.resized(4, 5).area == 20
print("   frozen refactor: resized() returns a new value — substitutable ✔")

# ============================================================================
# 4. I — Interface Segregation
# ============================================================================
print()
print("=" * 70)
print("I — Interface Segregation")
print("=" * 70)


# ✗ Fat interface: OldPrinter must stub scan() -> manufactured LSP violation.
# ✓ Small protocols; devices implement what they actually do:
class Printer(Protocol):
    def print_doc(self, doc: str) -> str: ...


class Scanner(Protocol):
    def scan(self) -> str: ...


class OldPrinter:                          # implements ONLY Printer
    def print_doc(self, doc):
        return f"printed {doc}"


class OfficeBeast:                         # implements both — implicitly
    def print_doc(self, doc):
        return f"printed {doc}"

    def scan(self):
        return "scanned page"


def print_all(printer: Printer, docs: list[str]) -> list[str]:
    return [printer.print_doc(d) for d in docs]


print(f"OldPrinter works where a Printer is needed: {print_all(OldPrinter(), ['a'])}")
print(f"OfficeBeast scans too: {OfficeBeast().scan()!r}")
assert print_all(OldPrinter(), ["a"]) == ["printed a"]

# ============================================================================
# 5. D — Dependency Inversion
# ============================================================================
print()
print("=" * 70)
print("D — Dependency Inversion")
print("=" * 70)


class Notifier(Protocol):                  # the abstraction both sides depend on
    def send(self, user: str, message: str) -> None: ...


class OrderService:
    """High-level policy. Imports NO concrete notifier — it's injected."""

    def __init__(self, notifier: Notifier):
        self._notifier = notifier

    def place_order(self, user: str, item: str) -> str:
        order_id = f"ord-{abs(hash((user, item))) % 1000:03d}"
        self._notifier.send(user, f"order {order_id} confirmed: {item}")
        return order_id


class FakeNotifier:                        # low-level detail #1 (for tests)
    def __init__(self):
        self.messages = []

    def send(self, user, message):
        self.messages.append((user, message))


class LoudNotifier:                        # low-level detail #2 (for demo)
    def send(self, user, message):
        print(f"   📣 to {user}: {message}")


# The composition root: the ONE place concretions are chosen.
fake = FakeNotifier()
service = OrderService(fake)               # test wiring
oid = service.place_order("ada", "keyboard")
assert fake.messages and oid in fake.messages[0][1]
print(f"tested with a fake: {fake.messages[0]}")

OrderService(LoudNotifier()).place_order("bob", "mouse")   # prod-ish wiring
print("   same service, different detail — zero edits to OrderService ✔")

print()
print("All Module 5 assertions passed ✔")
