"""Money value object (Module 2: dunders; Module 1: invariants).

Immutable, equality by value, integer cents. An invalid Money cannot exist:
the invariant lives inside the object, so every layer above trusts it.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Money:
    amount: int                    # integer cents — never floats for money
    currency: str = "USD"

    def __post_init__(self):
        if not isinstance(self.amount, int):
            raise ValueError("amount must be integer cents")
        if self.amount < 0:
            raise ValueError("amount cannot be negative")

    def _check(self, other: "Money"):
        if other.currency != self.currency:
            raise ValueError(
                f"currency mismatch: {self.currency} vs {other.currency}")

    def __add__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        self._check(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        self._check(other)
        return Money(self.amount - other.amount, self.currency)   # may raise: good

    def __lt__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        self._check(other)
        return self.amount < other.amount

    def __le__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        self._check(other)
        return self.amount <= other.amount

    def __str__(self):
        return f"{self.amount / 100:.2f} {self.currency}"
