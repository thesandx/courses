"""
Module 4 Solution — Contracts Three Ways
========================================
Run: python3 solution.py
"""
from abc import ABC, abstractmethod
from collections import abc as cabc
from typing import Protocol, runtime_checkable


# --- TODO 1: ABC with a template method -------------------------------------
class Notifier(ABC):
    @abstractmethod
    def format(self, message: str) -> str: ...

    @abstractmethod
    def deliver(self, payload: str) -> None: ...

    def notify(self, message: str) -> None:
        # Template method: concrete logic composed from abstract steps.
        self.deliver(self.format(message))


class ConsoleNotifier(Notifier):
    sent: list[str] = []

    def format(self, message: str) -> str:
        return f"[console] {message}"

    def deliver(self, payload: str) -> None:
        ConsoleNotifier.sent.append(payload)


class SilentNotifier(Notifier):
    def format(self, message: str) -> str:
        return message

    def deliver(self, payload: str) -> None:
        pass                                     # implemented, intentionally inert


# --- TODO 2: structural Protocol ---------------------------------------------
@runtime_checkable
class Sender(Protocol):
    def send(self, message: str) -> bool: ...


def broadcast(senders: list[Sender], message: str) -> int:
    """Count successful sends. Conformance is structural — any object
    with a .send method works, no inheritance required."""
    return sum(1 for s in senders if s.send(message))


class SmsGateway:                                # inherits nothing
    def __init__(self):
        self.outbox: list[str] = []

    def send(self, message: str) -> bool:
        self.outbox.append(message)
        return True


# --- TODO 3: a real Sequence ---------------------------------------------------
class EventLog(cabc.Sequence):
    def __init__(self, events=()):
        self._events = list(events)

    def __getitem__(self, index):
        return self._events[index]

    def __len__(self):
        return len(self._events)

    def append(self, event):
        self._events.append(event)
    # `in`, iteration, .index, .count, reversed() all arrive via Sequence.


# --- TODO 4: iterable, not iterator --------------------------------------------
class Replayable:
    def __init__(self, *items):
        self._items = items

    def __iter__(self):
        # Generator function -> a BRAND-NEW iterator per call. Returning
        # `self` here (with a __next__) would make the object one-shot.
        yield from self._items


# --- Stretch 2: O(1) membership, overriding the O(n) mixin ---------------------
class FastEventLog(EventLog):
    def __init__(self, events=()):
        super().__init__(events)
        self._seen = set(self._events)

    def append(self, event):
        super().append(event)
        self._seen.add(event)

    def __contains__(self, event):               # set lookup instead of scan
        return event in self._seen


if __name__ == "__main__":
    try:
        Notifier()
        raise SystemExit("FAIL")
    except TypeError:
        pass

    ConsoleNotifier.sent = []
    ConsoleNotifier().notify("deploy finished")
    assert ConsoleNotifier.sent == ["[console] deploy finished"]
    SilentNotifier().notify("into the void")

    gw = SmsGateway()
    assert isinstance(gw, Sender)

    class FlakySender:
        def send(self, message):
            return False

    assert broadcast([gw, FlakySender(), SmsGateway()], "hi") == 2
    assert gw.outbox == ["hi"]
    assert not isinstance("nope", Sender)

    logbook = EventLog(["boot", "login"])
    logbook.append("logout")
    assert len(logbook) == 3
    assert "login" in logbook
    assert logbook.index("logout") == 2
    assert list(logbook) == ["boot", "login", "logout"]
    assert isinstance(logbook, cabc.Sequence)

    r = Replayable("a", "b")
    assert list(r) == ["a", "b"] == list(r)
    assert iter(r) is not iter(r)

    # Stretch 1: virtual subclass — isinstance without verification.
    class Imposter:
        pass

    Notifier.register(Imposter)
    assert isinstance(Imposter(), Notifier)
    assert not hasattr(Imposter(), "notify")     # trust, not verification

    # Stretch 2
    fast = FastEventLog(["a", "b"])
    fast.append("c")
    assert "c" in fast and "z" not in fast

    print("All solution checks passed ✔")
