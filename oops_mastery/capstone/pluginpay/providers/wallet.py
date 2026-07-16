"""Wallet provider plugin — deliberately flaky, so the service layer's
@retry middleware (Module 7) has something real to do."""
from pluginpay.domain.errors import TransientProviderError
from pluginpay.domain.money import Money
from pluginpay.providers import PaymentProvider


class WalletProvider(PaymentProvider):
    provider_name = "wallet"

    # Class-level on purpose: the flakiness budget spans instances, because
    # get_provider() builds a fresh strategy per charge (Module 1 pitfall,
    # used deliberately here).
    _hiccups_remaining = 0

    @classmethod
    def make_flaky(cls, times: int):
        cls._hiccups_remaining = times

    def charge(self, amount: Money) -> str:
        if WalletProvider._hiccups_remaining > 0:
            WalletProvider._hiccups_remaining -= 1
            raise TransientProviderError("wallet backend timeout")
        return f"wallet-ref-{amount.amount}"

    def refund(self, amount: Money, reference: str) -> None:
        pass
