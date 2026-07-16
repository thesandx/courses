"""Provider plugin system (Module 6: metaclass registry + enforcement;
Module 8: strategy + factory).

Defining a subclass of PaymentProvider IS the plugin API: the metaclass
verifies the interface and registers the class at definition time. Adding a
provider means adding a file — no core edits (Module 5: Open/Closed).
"""
from typing import ClassVar

from pluginpay.domain.money import Money


class ProviderMeta(type):
    registry: dict[str, type] = {}

    def __new__(mcls, name, bases, ns):
        cls = super().__new__(mcls, name, bases, ns)
        if bases:                                    # skip the abstract root
            # Definition-time enforcement: a broken plugin can't even be
            # defined. Each plugin must implement BOTH methods itself — the
            # root's stubs don't count.
            for required in ("charge", "refund"):
                if not callable(ns.get(required)):
                    raise TypeError(f"{name} must define {required}()")
            key = ns.get("provider_name")
            if not key:
                raise TypeError(f"{name} must set provider_name")
            mcls.registry[key] = cls
        return cls


class PaymentProvider(metaclass=ProviderMeta):
    """Abstract root. Subclasses are strategies (Module 8): interchangeable
    charge/refund behaviors behind one shape."""

    provider_name: ClassVar[str] = ""

    def charge(self, amount: Money) -> str:
        """Return a provider reference string, or raise ProviderError."""
        raise NotImplementedError

    def refund(self, amount: Money, reference: str) -> None:
        raise NotImplementedError


def get_provider(name: str) -> PaymentProvider:
    """Factory (Module 8): callers name what they want, never a class."""
    try:
        return ProviderMeta.registry[name]()
    except KeyError:
        raise ValueError(f"unknown provider {name!r}") from None


def available_providers() -> list[str]:
    return sorted(ProviderMeta.registry)


# Importing the built-in plugins triggers their registration.
from pluginpay.providers import card, wallet    # noqa: E402,F401
