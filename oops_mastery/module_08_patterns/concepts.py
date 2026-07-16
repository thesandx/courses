"""
Module 8: Design Patterns, Pythonic — Concepts in Action
========================================================
Run: python3 concepts.py
"""
from typing import Callable, Protocol

# ============================================================================
# 1. Singleton — metaclass vs the __new__ trap
# ============================================================================
print("=" * 70)
print("1. Singleton")
print("=" * 70)


class SingletonMeta(type):
    _instances: dict[type, object] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]           # cache hit: __init__ NOT re-run


class AppConfig(metaclass=SingletonMeta):
    def __init__(self):
        self.values = {"env": "dev"}


AppConfig().values["env"] = "prod"
print(f"metaclass singleton keeps state: {AppConfig().values}")
assert AppConfig() is AppConfig()
assert AppConfig().values == {"env": "prod"}     # survived the second "construction"


# The __new__ variant looks equivalent — but silently resets state:
class NewSingleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.values = {"env": "dev"}         # re-runs on EVERY call!


NewSingleton().values["env"] = "prod"
print(f"__new__ singleton after 'second construction': {NewSingleton().values}"
      "   <-- __init__ re-ran and wiped it")
assert NewSingleton().values == {"env": "dev"}   # the trap, demonstrated

# ============================================================================
# 2. Factory — registry + protocol (construction, Open/Closed style)
# ============================================================================
print()
print("=" * 70)
print("2. Factory via registry")
print("=" * 70)


class Exporter(Protocol):
    def export(self, rows: list[tuple]) -> str: ...


_EXPORTERS: dict[str, Callable[[], Exporter]] = {}


def exporter(fmt: str):
    def deco(cls):
        _EXPORTERS[fmt] = cls
        return cls
    return deco


def make_exporter(fmt: str) -> Exporter:
    try:
        return _EXPORTERS[fmt]()
    except KeyError:
        raise ValueError(f"unknown format {fmt!r}") from None


@exporter("csv")
class CsvExporter:
    def export(self, rows):
        return "\n".join(",".join(map(str, r)) for r in rows)


@exporter("md")
class MarkdownExporter:
    def export(self, rows):
        return "\n".join("| " + " | ".join(map(str, r)) + " |" for r in rows)


rows = [(1, "ada"), (2, "bob")]
print(f"csv: {make_exporter('csv').export(rows)!r}")
print(f"md : {make_exporter('md').export(rows)!r}")
assert make_exporter("csv").export(rows) == "1,ada\n2,bob"
try:
    make_exporter("xml")
except ValueError as e:
    print(f"make_exporter('xml') -> ValueError: {e}")

# ============================================================================
# 3. Strategy — functions and callable classes, one registry
# ============================================================================
print()
print("=" * 70)
print("3. Strategy: functions AND classes, interchangeable")
print("=" * 70)


class Order:
    def __init__(self, total, weight):
        self.total, self.weight = total, weight


def flat_shipping(order: Order) -> float:        # a function strategy
    return 5.0


def weight_shipping(order: Order) -> float:
    return round(order.weight * 0.5, 2)


class TieredShipping:                            # a stateful class strategy
    def __init__(self, threshold=100.0):
        self.threshold = threshold

    def __call__(self, order: Order) -> float:   # callable: same shape as the funcs
        return 0.0 if order.total >= self.threshold else 7.5


def checkout(order: Order, shipping: Callable[[Order], float]) -> float:
    return order.total + shipping(order)


order = Order(total=120.0, weight=8.0)
for strategy in (flat_shipping, weight_shipping, TieredShipping()):
    name = getattr(strategy, "__name__", type(strategy).__name__)
    print(f"   {name:18} -> total {checkout(order, strategy)}")
assert checkout(order, flat_shipping) == 125.0
assert checkout(order, weight_shipping) == 124.0
assert checkout(order, TieredShipping()) == 120.0    # free over threshold

# ============================================================================
# 4. Observer — unsubscribe + error isolation
# ============================================================================
print()
print("=" * 70)
print("4. Observer / event emitter")
print("=" * 70)


class EventEmitter:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}

    def subscribe(self, event: str, handler: Callable) -> Callable[[], None]:
        self._handlers.setdefault(event, []).append(handler)

        def unsubscribe():
            self._handlers[event].remove(handler)
        return unsubscribe                       # caller controls its lifetime

    def emit(self, event: str, payload) -> list[Exception]:
        errors = []
        for handler in list(self._handlers.get(event, [])):
            try:
                handler(payload)
            except Exception as e:               # one bad observer can't
                errors.append(e)                 # silence the others
        return errors


emitter = EventEmitter()
seen_by_logger, seen_by_metrics = [], []

off_logger = emitter.subscribe("order.placed", seen_by_logger.append)
emitter.subscribe("order.placed", seen_by_metrics.append)
emitter.subscribe("order.placed", lambda p: 1 / 0)      # a faulty observer

errors = emitter.emit("order.placed", "ord-001")
print(f"logger saw {seen_by_logger}, metrics saw {seen_by_metrics}, "
      f"errors isolated: {len(errors)}")
assert seen_by_logger == ["ord-001"] and seen_by_metrics == ["ord-001"]
assert len(errors) == 1 and isinstance(errors[0], ZeroDivisionError)

off_logger()                                     # unsubscribe the logger
emitter.emit("order.placed", "ord-002")
print(f"after unsubscribe: logger {seen_by_logger}, metrics {seen_by_metrics}")
assert seen_by_logger == ["ord-001"]             # logger stopped
assert seen_by_metrics == ["ord-001", "ord-002"]

# ============================================================================
# 5. Adapter — wrap the legacy thing
# ============================================================================
print()
print("=" * 70)
print("5. Adapter")
print("=" * 70)


class LegacyPrinter:
    """Third-party: we cannot change its interface."""

    def print_text(self, text: str, uppercase: bool = False) -> str:
        return text.upper() if uppercase else text


class Writer(Protocol):                          # the interface OUR code expects
    def write(self, text: str) -> str: ...


class PrinterAdapter:
    """Object adapter: composition, not inheritance — legacy API stays hidden."""

    def __init__(self, legacy: LegacyPrinter, shout: bool = False):
        self._legacy = legacy
        self._shout = shout

    def write(self, text: str) -> str:
        return self._legacy.print_text(text, uppercase=self._shout)


def publish(writer: Writer, message: str) -> str:
    return writer.write(message)


adapted = PrinterAdapter(LegacyPrinter(), shout=True)
print(f"publish via adapter: {publish(adapted, 'hello')!r}")
assert publish(adapted, "hello") == "HELLO"
assert not hasattr(adapted, "print_text")        # legacy interface not leaked

# ============================================================================
# 6. Builder — when kwargs stop scaling
# ============================================================================
print()
print("=" * 70)
print("6. Builder (fluent, validated at build())")
print("=" * 70)


class HttpRequest:
    """The immutable product."""

    def __init__(self, method, url, headers, params, body):
        self.method, self.url = method, url
        self.headers, self.params, self.body = headers, params, body

    def describe(self):
        query = "&".join(f"{k}={v}" for k, v in self.params.items())
        return f"{self.method} {self.url}{'?' + query if query else ''}"


class RequestBuilder:
    def __init__(self):
        self._method, self._url = "GET", None
        self._headers, self._params, self._body = {}, {}, None

    def method(self, m):
        self._method = m.upper()
        return self                              # fluent: every step returns self

    def url(self, u):
        self._url = u
        return self

    def header(self, key, value):
        self._headers[key] = value
        return self

    def param(self, key, value):
        self._params[key] = value
        return self

    def body(self, data):
        self._body = data
        return self

    def build(self) -> HttpRequest:
        if self._url is None:                    # completeness check, at the end
            raise ValueError("url is required")
        if self._method == "GET" and self._body is not None:
            raise ValueError("GET requests cannot have a body")
        return HttpRequest(self._method, self._url,
                           dict(self._headers), dict(self._params), self._body)


req = (RequestBuilder()
       .method("get")
       .url("https://api.example.com/users")
       .param("page", 2)
       .header("Accept", "application/json")
       .build())
print(f"built: {req.describe()}")
assert req.describe() == "GET https://api.example.com/users?page=2"

try:
    RequestBuilder().method("GET").url("x").body("oops").build()
except ValueError as e:
    print(f"invalid combo -> ValueError: {e}")

print()
print("All Module 8 assertions passed ✔")
