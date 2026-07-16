"""
Module 7: Decorators — Concepts in Action
=========================================
Run: python3 concepts.py
"""
import functools
import time
import types

# ============================================================================
# 1. @ is sugar; decoration happens once, at definition time
# ============================================================================
print("=" * 70)
print("1. Decoration = function application at definition time")
print("=" * 70)

definition_log = []


def announce(func):
    definition_log.append(f"decorating {func.__name__}")   # runs ONCE
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


@announce
def greet():
    return "hi"


def plain():
    return "hi"


plain_decorated = announce(plain)               # identical to the @ form
print(f"log after definitions: {definition_log}")
assert definition_log == ["decorating greet", "decorating plain"]
greet(); greet()                                # calling adds nothing:
assert definition_log == ["decorating greet", "decorating plain"]
print("calling greet() twice added no log entries — decorator body ran once ✔")

# ============================================================================
# 2. functools.wraps preserves identity
# ============================================================================
print()
print("=" * 70)
print("2. Why @functools.wraps matters")
print("=" * 70)


def bad_deco(func):
    def wrapper(*a, **kw):
        return func(*a, **kw)
    return wrapper                              # no wraps!


def good_deco(func):
    @functools.wraps(func)
    def wrapper(*a, **kw):
        return func(*a, **kw)
    return wrapper


@bad_deco
def alpha():
    """Alpha's docs."""


@good_deco
def beta():
    """Beta's docs."""


print(f"bad : __name__={alpha.__name__!r}, __doc__={alpha.__doc__!r}")
print(f"good: __name__={beta.__name__!r}, __doc__={beta.__doc__!r}")
assert alpha.__name__ == "wrapper" and beta.__name__ == "beta"
assert beta.__wrapped__() is None               # wraps also exposes the original

# ============================================================================
# 3. Parameterized decorators (three layers) + with-or-without-args
# ============================================================================
print()
print("=" * 70)
print("3. @retry(times=3) — factory -> decorator -> wrapper")
print("=" * 70)


def retry(times=3, exceptions=(Exception,)):
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


attempts = {"n": 0}


@retry(times=3, exceptions=(ConnectionError,))
def flaky_fetch():
    attempts["n"] += 1
    if attempts["n"] < 3:
        raise ConnectionError("net down")
    return "payload"


print(f"flaky_fetch() -> {flaky_fetch()!r} after {attempts['n']} attempts")
assert attempts["n"] == 3


# The dual-use trick: @log and @log(prefix="!") both work.
def log(func=None, *, prefix=">>"):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            wrapper.lines.append(f"{prefix} {f.__name__}")
            return f(*args, **kwargs)
        wrapper.lines = []
        return wrapper
    if callable(func):                          # used bare: @log
        return decorator(func)
    return decorator                            # used with args: @log(...)


@log
def bare():
    return 1


@log(prefix="!!")
def fancy():
    return 2


bare(); fancy()
print(f"bare.lines={bare.lines}, fancy.lines={fancy.lines}")
assert bare.lines == [">> bare"] and fancy.lines == ["!! fancy"]

# ============================================================================
# 4. Class-based decorators — and the __get__ requirement for methods
# ============================================================================
print()
print("=" * 70)
print("4. Class-based decorators hold state; __get__ makes them method-safe")
print("=" * 70)


class CountCalls:
    def __init__(self, func):
        functools.update_wrapper(self, func)
        self.func = func
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        return self.func(*args, **kwargs)

    def __get__(self, obj, objtype=None):
        # Mimic what plain functions do (Module 3): produce a bound method.
        if obj is None:
            return self
        return types.MethodType(self, obj)


@CountCalls
def ping():
    return "pong"


ping(); ping(); ping()
print(f"ping.calls = {ping.calls}  <-- state readable from outside")
assert ping.calls == 3


class Server:
    @CountCalls
    def handle(self, request):                  # works BECAUSE of __get__
        return f"handled {request}"


s = Server()
print(f"s.handle('req1') = {s.handle('req1')!r}")
assert s.handle("req2") == "handled req2"
assert Server.__dict__["handle"].calls == 2

# ============================================================================
# 5. Decorating classes
# ============================================================================
print()
print("=" * 70)
print("5. Class decorators: transform a class explicitly")
print("=" * 70)


def auto_repr(cls):
    def __repr__(self):
        fields = ", ".join(f"{k}={v!r}" for k, v in vars(self).items())
        return f"{type(self).__name__}({fields})"
    cls.__repr__ = __repr__
    return cls


@auto_repr
class Point:
    def __init__(self, x, y):
        self.x, self.y = x, y


print(f"repr(Point(1, 2)) = {Point(1, 2)!r}")
assert repr(Point(1, 2)) == "Point(x=1, y=2)"

# ============================================================================
# 6. Stacking order
# ============================================================================
print()
print("=" * 70)
print("6. Stacked decorators apply bottom-up")
print("=" * 70)

order = []


def tag(label):
    def decorator(func):
        order.append(f"applied {label}")        # records application order
        @functools.wraps(func)
        def wrapper(*a, **kw):
            return [label] + func(*a, **kw)     # records call order
        return wrapper
    return decorator


@tag("outer")
@tag("inner")
def core():
    return ["core"]


print(f"application order: {order}")
print(f"call order:        {core()}")
assert order == ["applied inner", "applied outer"]   # bottom decorator first
assert core() == ["outer", "inner", "core"]           # top wrapper runs first

# Bonus: the stdlib's decorator jewel — free memoization.
@functools.lru_cache(maxsize=None)
def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)


start = time.perf_counter()
result = fib(80)
elapsed = time.perf_counter() - start
print(f"fib(80) = {result} in {elapsed * 1000:.2f} ms (lru_cache)")
assert result == 23416728348467685

print()
print("All Module 7 assertions passed ✔")
