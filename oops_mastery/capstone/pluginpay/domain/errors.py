"""Domain exception hierarchy. The API layer maps these to status codes;
the domain itself has no idea what a 404 is (Module 10)."""


class DomainError(Exception):
    """Root for all domain failures."""


class NotFound(DomainError):
    pass


class DuplicatePayment(DomainError):
    pass


class FraudSuspected(DomainError):
    pass


class ProviderError(DomainError):
    """A provider definitively refused the operation."""


class TransientProviderError(ProviderError):
    """A provider hiccup that is worth retrying (Module 7's @retry)."""
