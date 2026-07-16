"""Card provider plugin. Registration is the class statement itself."""
from pluginpay.domain.errors import ProviderError
from pluginpay.domain.money import Money
from pluginpay.providers import PaymentProvider


class CardProvider(PaymentProvider):
    provider_name = "card"
    LIMIT = Money(500_00)                    # $500 per-transaction cap

    def charge(self, amount: Money) -> str:
        if self.LIMIT < amount:
            raise ProviderError(f"card declines charges over {self.LIMIT}")
        return f"card-ref-{amount.amount}"

    def refund(self, amount: Money, reference: str) -> None:
        if not reference.startswith("card-ref-"):
            raise ProviderError("unknown card reference")
