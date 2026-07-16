"""
Module 7 Solution — A Decorator Toolbox
=======================================
Run: python3 solution.py
"""
import functools
import time
import types
import weakref


# --- TODO 1: closure decorator with an exposed cache -------------------------
def memoize(func):
    cache = {}

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Stretch 1: fold kwargs into the key (frozenset -> order-insensitive).
        key = args if not kwargs else (args, frozenset(kwargs.items()))
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]

    wrapper.cache = cache                     # inspectable from outside
    return wrapper


# --- TODO 2: parameterized decorator, with Stretch-2 backoff ------------------
def retry(times=3, exceptions=(Exception,), delay=0.0, backoff=2.0):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            wait = delay
            for attempt in range(1, times + 1):
                wrapper.attempts += 1
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    if attempt == times:
                        raise                 # exhausted: surface the real error
                    if wait:
                        time.sleep(wait)
                        wait *= backoff
                # anything NOT in `exceptions` propagates immediately —
                # there is deliberately no bare `except` here.
        wrapper.attempts = 0
        return wrapper
    return decorator


# --- TODO 3: stateful class-based decorator, method-safe ----------------------
class CallLimit:
    """Parameterized: CallLimit(n) is a factory; applying it wraps the
    function in a _Limited instance that carries the state."""

    def __init__(self, n):
        self.n = n

    def __call__(self, func):
        return _Limited(func, self.n)


class _Limited:
    def __init__(self, func, n):
        functools.update_wrapper(self, func)
        self.func = func
        self.n = n
        self.remaining = n                      # budget for plain functions
        # Stretch 3: separate budgets per bound instance for methods.
        self._per_instance = weakref.WeakKeyDictionary()

    def __call__(self, *args, **kwargs):
        if self.remaining <= 0:
            raise RuntimeError("call limit reached")
        self.remaining -= 1
        return self.func(*args, **kwargs)

    def __get__(self, obj, objtype=None):
        # Bound-method support: without this, `self` never reaches func,
        # because only descriptors can produce bound methods (Module 3).
        if obj is None:
            return self
        return types.MethodType(self._call_bound, obj)

    def _call_bound(self, obj, *args, **kwargs):
        left = self._per_instance.setdefault(obj, self.n)
        if left <= 0:
            raise RuntimeError("call limit reached")
        self._per_instance[obj] = left - 1
        return self.func(obj, *args, **kwargs)


# --- TODO 4: class decorator ----------------------------------------------------
def auto_str(cls):
    def __str__(self):
        fields = ", ".join(f"{k}={v!r}" for k, v in vars(self).items())
        return f"{type(self).__name__}({fields})"
    cls.__str__ = __str__
    return cls


if __name__ == "__main__":
    calls = {"n": 0}

    @memoize
    def slow_square(x):
        calls["n"] += 1
        return x * x

    assert slow_square(4) == 16 and slow_square(4) == 16
    assert calls["n"] == 1
    assert slow_square.cache == {(4,): 16}
    assert slow_square.__name__ == "slow_square"

    # stretch 1: kwargs
    @memoize
    def power(base, *, exp=2):
        return base ** exp

    assert power(2, exp=3) == 8 == power(2, exp=3)

    state = {"fails_left": 2}

    @retry(times=3, exceptions=(ConnectionError,))
    def flaky():
        if state["fails_left"] > 0:
            state["fails_left"] -= 1
            raise ConnectionError
        return "ok"

    assert flaky() == "ok" and flaky.attempts == 3

    @retry(times=2, exceptions=(ConnectionError,))
    def always_down():
        raise ConnectionError("still down")

    try:
        always_down()
        raise SystemExit("FAIL")
    except ConnectionError:
        pass

    @retry(times=5, exceptions=(ConnectionError,))
    def wrong_error():
        raise KeyError("not retryable")

    try:
        wrong_error()
        raise SystemExit("FAIL")
    except KeyError:
        pass
    assert wrong_error.attempts == 1

    @CallLimit(2)
    def limited():
        return "ran"

    assert limited() == "ran" and limited() == "ran"
    try:
        limited()
        raise SystemExit("FAIL")
    except RuntimeError as e:
        assert "call limit reached" in str(e)

    class Api:
        @CallLimit(1)
        def request(self, path):
            return f"GET {path}"

    api = Api()
    assert api.request("/users") == "GET /users"
    try:
        api.request("/again")
        raise SystemExit("FAIL")
    except RuntimeError:
        pass

    # stretch 3: a SECOND instance has its own budget
    api2 = Api()
    assert api2.request("/fresh") == "GET /fresh"

    @auto_str
    class Point:
        def __init__(self, x, y):
            self.x, self.y = x, y

    assert str(Point(1, 2)) == "Point(x=1, y=2)"

    print("All solution checks passed ✔")
