"""Service layer (Module 9: everything injected; Module 10: orchestration only).

The service sequences the use case; the domain calculates and guards; the
provider charges; the repo persists; the emitter broadcasts. No HTTP, no
concrete storage, no concrete providers appear here.
"""
from typing import Callable, Protocol

from pluginpay.domain import (FraudSuspected, Payment, TransientProviderError)
from pluginpay.events import EventEmitter
from pluginpay.fraud import FraudChecker
from pluginpay.middleware import audited, retry
from pluginpay.providers import PaymentProvider
from pluginpay.repos import PaymentRepo


class IdGenerator(Protocol):
    def next_id(self) -> str: ...


class SequentialIds:
    def __init__(self, prefix: str = "pay"):
        self._prefix, self._n = prefix, 0

    def next_id(self) -> str:
        self._n += 1
        return f"{self._prefix}-{self._n:04d}"


class PaymentService:
    def __init__(self,
                 repo: PaymentRepo,
                 provider_factory: Callable[[str], PaymentProvider],
                 fraud: FraudChecker,
                 events: EventEmitter,
                 ids: IdGenerator):
        self._repo = repo
        self._providers = provider_factory
        self._fraud = fraud
        self._events = events
        self._ids = ids
        self._audit: list[str] = []          # written by @audited

    @property
    def audit_trail(self) -> tuple[str, ...]:
        return tuple(self._audit)

    @audited
    @retry(times=3, exceptions=(TransientProviderError,))
    def charge(self, customer: str, amount_cents: int, currency: str,
               provider_name: str) -> Payment:
        provider = self._providers(provider_name)      # factory: ValueError if unknown
        payment = Payment.create(self._ids.next_id(), customer,
                                 amount_cents, currency, provider_name)
        if self._fraud.is_suspicious(payment.amount):
            payment.mark_failed()
            raise FraudSuspected(
                f"payment {payment.payment_id!r} flagged as suspicious")

        try:
            reference = provider.charge(payment.amount)
        except TransientProviderError:
            raise                                       # let @retry re-attempt
        except Exception:
            payment.mark_failed()
            self._repo.add(payment)
            self._events.emit("payment.failed", payment.payment_id)
            raise

        payment.mark_captured()
        self._repo.add(payment)
        self._events.emit("payment.captured",
                          {"id": payment.payment_id, "ref": reference})
        return payment

    @audited
    def refund(self, payment_id: str) -> Payment:
        payment = self._repo.get(payment_id)
        provider = self._providers(payment.provider_name)
        provider.refund(payment.amount, f"{payment.provider_name}-ref-"
                                        f"{payment.amount.amount}")
        payment.mark_refunded()                # domain guards the transition
        self._events.emit("payment.refunded", payment.payment_id)
        return payment

    def get_payment(self, payment_id: str) -> Payment:
        return self._repo.get(payment_id)

    def captured_total_cents(self, currency: str = "USD") -> int:
        return sum(p.amount.amount for p in self._repo.list_all()
                   if p.status in ("captured", "refunded")
                   and p.amount.currency == currency)
