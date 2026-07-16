"""
Module 9 Exercise: An Alerting Pipeline, Injected
=================================================
Goal
----
Build a small alerting system where every collaborator arrives through the
constructor, tests use fakes, and finally your own mini-container wires the
whole graph from type hints.

Complete the TODOs, then run:  python3 exercise.py
"""
import typing
from typing import Callable, Protocol


# ---------------------------------------------------------------------------
# TODO 1 — the seams (Protocols)
# ---------------------------------------------------------------------------
# Define three protocols:
#   class Clock(Protocol):        def now(self) -> str: ...
#   class AlertSink(Protocol):    def push(self, formatted: str) -> None: ...
#   class SeverityPolicy(Protocol): def should_alert(self, level: int) -> bool: ...


# ---------------------------------------------------------------------------
# TODO 2 — implementations
# ---------------------------------------------------------------------------
#   * FixedClock: __init__(stamp="2026-01-01T00:00") ; now() returns it
#   * MemorySink: collects pushed strings into self.items
#   * ThresholdPolicy: __init__(threshold: int = 3);
#     should_alert(level) -> level >= threshold


# ---------------------------------------------------------------------------
# TODO 3 — AlertService (constructor injection only!)
# ---------------------------------------------------------------------------
# class AlertService:
#     def __init__(self, clock: Clock, sink: AlertSink, policy: SeverityPolicy)
#     def alert(self, message: str, level: int) -> bool:
#         * if policy says no -> return False, push nothing
#         * else push f"[{clock.now()}] L{level}: {message}" and return True
# The service must not construct ANY collaborator itself.


# ---------------------------------------------------------------------------
# TODO 4 — composition root
# ---------------------------------------------------------------------------
# def build_service(env: str) -> AlertService
#   * "test" -> FixedClock(), MemorySink(), ThresholdPolicy(threshold=0)
#   * anything else -> FixedClock("2026-07-09T12:00"), MemorySink(),
#     ThresholdPolicy(3)


# ---------------------------------------------------------------------------
# TODO 5 — Container
# ---------------------------------------------------------------------------
# class Container with:
#   * register(key: type, provider, *, singleton=False)
#     provider may be a class OR a zero-arg callable
#   * resolve(key) ->
#       - returns the cached instance for singletons
#       - looks up the provider (an unregistered key that is a plain class
#         should just be constructed)
#       - if the provider is a class, build it by reading
#         typing.get_type_hints of its __init__ and recursively resolving
#         each parameter; otherwise call it
#   * raise KeyError for an unregistered Protocol key (hint: Protocols can't
#     be instantiated — treat keys found in neither _providers nor buildable
#     as errors; simplest check: getattr(key, "_is_protocol", False))


# ---------------------------------------------------------------------------
# Self-Verification — do not modify below this line
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # fakes-first test, hand-wired
    sink = MemorySink()
    service = AlertService(FixedClock("T0"), sink, ThresholdPolicy(3))
    assert service.alert("disk full", 5) is True
    assert service.alert("just noise", 1) is False
    assert sink.items == ["[T0] L5: disk full"]

    # composition root
    test_svc = build_service("test")
    assert test_svc.alert("anything", 0) is True     # threshold 0 in test env
    prod_svc = build_service("prod")
    assert prod_svc.alert("meh", 2) is False

    # container wiring
    c = Container()
    c.register(Clock, lambda: FixedClock("T1"))
    c.register(AlertSink, MemorySink, singleton=True)
    c.register(SeverityPolicy, ThresholdPolicy)

    svc1 = c.resolve(AlertService)
    svc2 = c.resolve(AlertService)
    assert svc1 is not svc2, "AlertService not registered singleton"
    assert svc1._sink is svc2._sink, "sink must be a singleton"
    assert svc1._policy is not svc2._policy, "policy must be transient"

    svc1.alert("cpu on fire", 9)
    assert c.resolve(AlertSink).items == ["[T1] L9: cpu on fire"]

    empty = Container()
    try:
        empty.resolve(AlertSink)
        raise SystemExit("FAIL: unregistered protocol must raise KeyError")
    except KeyError:
        pass

    print("All exercise checks passed ✔")

# ---------------------------------------------------------------------------
# Stretch Goals
# ---------------------------------------------------------------------------
# 1. Add register_instance(key, obj) — a pre-built singleton.
# 2. Detect circular dependencies in resolve() and raise a clear error
#    (hint: keep a set of keys currently being built).
# 3. Support Optional dependencies: parameters with defaults are skipped
#    when unregistered instead of failing.

# Cleanup: nothing to clean up — pure in-memory Python.
