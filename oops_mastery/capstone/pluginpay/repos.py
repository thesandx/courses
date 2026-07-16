"""Persistence layer (Module 4: protocol seam; Module 8: repository pattern).

The service depends on the PaymentRepo shape only; this in-memory version is
both the dev implementation and the test fake — same contract either way.
"""
from typing import Protocol

from pluginpay.domain import DuplicatePayment, NotFound, Payment


class PaymentRepo(Protocol):
    def add(self, payment: Payment) -> None: ...
    def get(self, payment_id: str) -> Payment: ...
    def list_all(self) -> list[Payment]: ...


class InMemoryPaymentRepo:
    def __init__(self):
        self._payments: dict[str, Payment] = {}

    def add(self, payment: Payment) -> None:
        if payment.payment_id in self._payments:
            raise DuplicatePayment(
                f"payment {payment.payment_id!r} already exists")
        self._payments[payment.payment_id] = payment

    def get(self, payment_id: str) -> Payment:
        try:
            return self._payments[payment_id]
        except KeyError:
            raise NotFound(f"payment {payment_id!r} not found") from None

    def list_all(self) -> list[Payment]:
        return list(self._payments.values())
