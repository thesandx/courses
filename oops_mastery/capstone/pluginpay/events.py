"""Observer (Module 8): decoupled reactions to service events.

Production-grade details: subscribe returns an unsubscribe callable, and one
raising handler cannot silence the others.
"""
from typing import Callable


class EventEmitter:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}

    def subscribe(self, event: str, handler: Callable) -> Callable[[], None]:
        self._handlers.setdefault(event, []).append(handler)

        def unsubscribe():
            self._handlers[event].remove(handler)
        return unsubscribe

    def emit(self, event: str, payload) -> list[Exception]:
        errors: list[Exception] = []
        for handler in list(self._handlers.get(event, [])):
            try:
                handler(payload)
            except Exception as exc:            # isolate faulty observers
                errors.append(exc)
        return errors
