"""Fraud checking (Module 8: adapter).

LegacyFraudScorer stands in for a third-party SDK we cannot change. The
adapter translates its cents/score world into the FraudChecker shape the
service expects — the legacy API never leaks upward.
"""
from typing import Protocol

from pluginpay.domain.money import Money


class LegacyFraudScorer:
    """'Vendor code': camelCase, cents, 0-100 risk score."""

    def riskScoreForCents(self, amountCents: int) -> int:      # noqa: N802,N803
        # Toy heuristic: big round amounts look suspicious.
        if amountCents >= 900_00 and amountCents % 100_00 == 0:
            return 95
        return min(amountCents // 100_00 * 7, 90)


class FraudChecker(Protocol):
    def is_suspicious(self, amount: Money) -> bool: ...


class FraudAdapter:
    def __init__(self, scorer: LegacyFraudScorer, threshold: int = 80):
        self._scorer = scorer
        self._threshold = threshold

    def is_suspicious(self, amount: Money) -> bool:
        return self._scorer.riskScoreForCents(amount.amount) >= self._threshold
