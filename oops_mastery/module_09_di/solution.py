"""
Module 9 Solution — An Alerting Pipeline, Injected
==================================================
Run: python3 solution.py
"""
import typing
from typing import Callable, Protocol


# --- TODO 1: the seams --------------------------------------------------------
class Clock(Protocol):
    def now(self) -> str: ...


class AlertSink(Protocol):
    def push(self, formatted: str) -> None: ...


class SeverityPolicy(Protocol):
    def should_alert(self, level: int) -> bool: ...


# --- TODO 2: implementations (conform structurally — no inheritance) -----------
class FixedClock:
    def __init__(self, stamp: str = "2026-01-01T00:00"):
        self.stamp = stamp

    def now(self) -> str:
        return self.stamp


class MemorySink:
    def __init__(self):
        self.items: list[str] = []

    def push(self, formatted: str) -> None:
        self.items.append(formatted)


class ThresholdPolicy:
    def __init__(self, threshold: int = 3):
        self.threshold = threshold

    def should_alert(self, level: int) -> bool:
        return level >= self.threshold


# --- TODO 3: the service — pure policy, zero construction ----------------------
class AlertService:
    def __init__(self, clock: Clock, sink: AlertSink, policy: SeverityPolicy):
        self._clock = clock
        self._sink = sink
        self._policy = policy

    def alert(self, message: str, level: int) -> bool:
        if not self._policy.should_alert(level):
            return False
        self._sink.push(f"[{self._clock.now()}] L{level}: {message}")
        return True


# --- TODO 4: composition root ----------------------------------------------------
def build_service(env: str) -> AlertService:
    if env == "test":
        return AlertService(FixedClock(), MemorySink(), ThresholdPolicy(threshold=0))
    return AlertService(FixedClock("2026-07-09T12:00"), MemorySink(),
                        ThresholdPolicy(3))


# --- TODO 5: the container ----------------------------------------------------------
class Container:
    def __init__(self):
        self._providers: dict[type, Callable[[], object] | type] = {}
        self._singleton_keys: set[type] = set()
        self._singletons: dict[type, object] = {}
        self._building: set[type] = set()          # Stretch 2

    def register(self, key: type, provider, *, singleton: bool = False):
        self._providers[key] = provider
        if singleton:
            self._singleton_keys.add(key)

    def register_instance(self, key: type, obj):   # Stretch 1
        self._providers[key] = lambda: obj
        self._singleton_keys.add(key)

    def resolve(self, key: type):
        if key in self._singletons:
            return self._singletons[key]

        if key in self._providers:
            provider = self._providers[key]
        elif getattr(key, "_is_protocol", False):
            raise KeyError(f"no provider registered for protocol {key.__name__}")
        else:
            provider = key                         # plain concrete class: build it

        if key in self._building:                  # Stretch 2
            raise RuntimeError(f"circular dependency involving {key.__name__}")
        self._building.add(key)
        try:
            instance = (self._build(provider) if isinstance(provider, type)
                        else provider())
        finally:
            self._building.discard(key)

        if key in self._singleton_keys:
            self._singletons[key] = instance
        return instance

    def _build(self, cls: type):
        import inspect
        if cls.__init__ is object.__init__:
            return cls()
        hints = typing.get_type_hints(cls.__init__)
        hints.pop("return", None)
        signature = inspect.signature(cls.__init__)
        deps = {}
        for name, dep_type in hints.items():
            param = signature.parameters.get(name)
            has_default = (param is not None
                           and param.default is not inspect.Parameter.empty)
            # Stretch 3: an unregistered dependency with a default is
            # optional — let the constructor's own default win.
            if dep_type in self._providers or not has_default:
                deps[name] = self.resolve(dep_type)
        return cls(**deps)


if __name__ == "__main__":
    sink = MemorySink()
    service = AlertService(FixedClock("T0"), sink, ThresholdPolicy(3))
    assert service.alert("disk full", 5) is True
    assert service.alert("just noise", 1) is False
    assert sink.items == ["[T0] L5: disk full"]

    test_svc = build_service("test")
    assert test_svc.alert("anything", 0) is True
    prod_svc = build_service("prod")
    assert prod_svc.alert("meh", 2) is False

    c = Container()
    c.register(Clock, lambda: FixedClock("T1"))
    c.register(AlertSink, MemorySink, singleton=True)
    c.register(SeverityPolicy, ThresholdPolicy)

    svc1 = c.resolve(AlertService)
    svc2 = c.resolve(AlertService)
    assert svc1 is not svc2
    assert svc1._sink is svc2._sink
    assert svc1._policy is not svc2._policy

    svc1.alert("cpu on fire", 9)
    assert c.resolve(AlertSink).items == ["[T1] L9: cpu on fire"]

    empty = Container()
    try:
        empty.resolve(AlertSink)
        raise SystemExit("FAIL")
    except KeyError:
        pass

    # Stretch 1: pre-built instance
    c2 = Container()
    the_sink = MemorySink()
    c2.register_instance(AlertSink, the_sink)
    c2.register(Clock, FixedClock)
    c2.register(SeverityPolicy, ThresholdPolicy)
    assert c2.resolve(AlertService)._sink is the_sink

    # Stretch 2: circular dependency detection
    class Chicken:
        def __init__(self, egg: "Egg"):
            self.egg = egg

    class Egg:
        def __init__(self, chicken: Chicken):
            self.chicken = chicken

    c3 = Container()
    try:
        c3.resolve(Chicken)
        raise SystemExit("FAIL: circular dep must be detected")
    except RuntimeError as e:
        assert "circular" in str(e)

    print("All solution checks passed ✔")
