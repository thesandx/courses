"""Payment entity (Module 1: factory/properties; Module 3: descriptors).

An entity: identity (payment_id), guarded state transitions, equality by id.
"""
from pluginpay.domain.errors import DomainError
from pluginpay.domain.money import Money


class NonEmptyStr:
    """Reusable validating descriptor (Module 3): write once, use anywhere."""

    def __set_name__(self, owner, name):
        self._name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__[self._name]

    def __set__(self, obj, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{self._name} must be a non-empty string")
        obj.__dict__[self._name] = value


# The legal state machine: transitions not listed here raise.
_TRANSITIONS = {
    "pending": {"captured", "failed"},
    "captured": {"refunded"},
    "failed": set(),
    "refunded": set(),
}


class Payment:
    customer = NonEmptyStr()
    provider_name = NonEmptyStr()

    def __init__(self, payment_id: str, customer: str,
                 amount: Money, provider_name: str):
        self.payment_id = payment_id
        self.customer = customer               # descriptor validates
        self.amount = amount
        self.provider_name = provider_name     # descriptor validates
        self._status = "pending"
        self._history = ["pending"]            # encapsulated audit of states

    @classmethod
    def create(cls, payment_id: str, customer: str,
               amount_cents: int, currency: str, provider_name: str) -> "Payment":
        """Factory (Module 1): the one blessed way to build a valid Payment."""
        return cls(payment_id, customer, Money(amount_cents, currency),
                   provider_name)

    @property
    def status(self) -> str:                   # read-only outside; transitions
        return self._status                    # go through the methods below

    @property
    def history(self) -> tuple[str, ...]:
        return tuple(self._history)            # copy out — no live internals

    def _transition(self, new_status: str):
        if new_status not in _TRANSITIONS[self._status]:
            raise DomainError(
                f"cannot go {self._status} -> {new_status} "
                f"for payment {self.payment_id!r}")
        self._status = new_status
        self._history.append(new_status)

    def mark_captured(self):
        self._transition("captured")

    def mark_failed(self):
        self._transition("failed")

    def mark_refunded(self):
        self._transition("refunded")

    def __eq__(self, other):                   # entity: identity, not state
        if not isinstance(other, Payment):
            return NotImplemented
        return self.payment_id == other.payment_id

    def __hash__(self):
        return hash(self.payment_id)

    def __repr__(self):
        return (f"Payment({self.payment_id!r}, {self.customer!r}, "
                f"{self.amount}, via={self.provider_name!r}, "
                f"status={self._status!r})")
