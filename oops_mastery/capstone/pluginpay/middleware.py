"""Cross-cutting concerns as decorators (Module 7).

Applied to service methods: retry wraps transient provider hiccups; audited
records every call into the service's injected audit trail.
"""
import functools


def retry(times: int, exceptions: tuple[type, ...]):
    """Parameterized decorator: up to `times` attempts on the given errors."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    if attempt == times:
                        raise
        return wrapper
    return decorator


def audited(func):
    """Method decorator: logs name + outcome to self._audit (the service
    injects the list, so tests can read it — Module 9)."""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            result = func(self, *args, **kwargs)
            self._audit.append(f"{func.__name__}: ok")
            return result
        except Exception as exc:
            self._audit.append(f"{func.__name__}: {type(exc).__name__}")
            raise
    return wrapper
