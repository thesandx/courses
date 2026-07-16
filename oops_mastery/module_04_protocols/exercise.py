"""
Module 4 Exercise: Contracts Three Ways
=======================================
Goal
----
Implement the same "pluggable notification" idea three ways — an ABC with a
template method, a structural Protocol, and a proper iterable container —
so the trade-offs from the README become muscle memory.

Complete the TODOs, then run:  python3 exercise.py
"""
from abc import ABC, abstractmethod
from collections import abc as cabc
from typing import Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# TODO 1 — Notifier ABC with a template method
# ---------------------------------------------------------------------------
# class Notifier(ABC):
#   * abstract method format(self, message: str) -> str
#   * abstract method deliver(self, payload: str) -> None
#   * CONCRETE method notify(self, message): calls deliver(format(message))
#
# Then implement:
#   * ConsoleNotifier: format -> f"[console] {message}",
#     deliver appends the payload to a class-level list `sent`
#   * SilentNotifier: format -> message unchanged, deliver does nothing
#     (pass) — but must still be instantiable (implements both abstracts)


# ---------------------------------------------------------------------------
# TODO 2 — a structural Protocol for third-party senders
# ---------------------------------------------------------------------------
# @runtime_checkable
# class Sender(Protocol):
#     def send(self, message: str) -> bool: ...
#
# Write function broadcast(senders, message) -> int
#   * calls .send(message) on each object and returns how many returned True
#   * annotate the parameter as list[Sender]
#
# Then write a class SmsGateway (NO inheritance from anything) with
# send(self, message) -> bool returning True, appending message to self.outbox.


# ---------------------------------------------------------------------------
# TODO 3 — EventLog: a real Sequence
# ---------------------------------------------------------------------------
# class EventLog(cabc.Sequence):
#   * __init__(self, events=()) stores a list
#   * implement ONLY __getitem__ and __len__
#   * add method append(event) that appends
# The Sequence ABC must supply `in`, iteration, .index, .count for free.


# ---------------------------------------------------------------------------
# TODO 4 — Replayable: iterable, not iterator
# ---------------------------------------------------------------------------
# class Replayable:
#   * __init__(self, *items)
#   * __iter__ must return a FRESH iterator every call (hint: generator or
#     iter(tuple)) so the object can be looped over repeatedly.


# ---------------------------------------------------------------------------
# Self-Verification — do not modify below this line
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # TODO 1 checks
    try:
        Notifier()
        raise SystemExit("FAIL: Notifier must be abstract")
    except TypeError:
        pass

    ConsoleNotifier.sent = []
    cn = ConsoleNotifier()
    cn.notify("deploy finished")
    assert ConsoleNotifier.sent == ["[console] deploy finished"], ConsoleNotifier.sent
    SilentNotifier().notify("into the void")     # must not raise

    # TODO 2 checks
    gw = SmsGateway()
    assert isinstance(gw, Sender), "SmsGateway must conform structurally"

    class FlakySender:                            # duck-typed, returns False
        def send(self, message):
            return False

    assert broadcast([gw, FlakySender(), SmsGateway()], "hi") == 2
    assert gw.outbox == ["hi"]
    assert not isinstance("nope", Sender)

    # TODO 3 checks
    logbook = EventLog(["boot", "login"])
    logbook.append("logout")
    assert len(logbook) == 3
    assert "login" in logbook                     # free from Sequence
    assert logbook.index("logout") == 2           # free
    assert list(logbook) == ["boot", "login", "logout"]
    assert isinstance(logbook, cabc.Sequence)

    # TODO 4 checks
    r = Replayable("a", "b")
    assert list(r) == ["a", "b"]
    assert list(r) == ["a", "b"], "second iteration must work — fresh iterator!"
    i1, i2 = iter(r), iter(r)
    assert i1 is not i2, "each __iter__ call must return a new iterator"

    print("All exercise checks passed ✔")

# ---------------------------------------------------------------------------
# Stretch Goals
# ---------------------------------------------------------------------------
# 1. Register a class as a virtual subclass of Notifier with
#    Notifier.register and observe isinstance passing without verification.
# 2. Give EventLog an O(1) __contains__ backed by a set, overriding the O(n)
#    mixin.
# 3. Run mypy over this file and see the Protocol checked statically.

# Cleanup: nothing to clean up — pure in-memory Python.
