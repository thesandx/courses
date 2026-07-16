"""
Module 7 Exercise: A Decorator Toolbox
======================================
Goal
----
Build four decorators covering the full spectrum: a closure decorator, a
parameterized one, a stateful class-based one that works on methods, and a
class decorator.

Complete the TODOs, then run:  python3 exercise.py
"""
import functools
import types


# ---------------------------------------------------------------------------
# TODO 1 — @memoize (closure decorator)
# ---------------------------------------------------------------------------
# Cache results by positional args (assume hashable, no kwargs needed).
#   * use functools.wraps
#   * expose the cache dict as wrapper.cache so tests can inspect it


# ---------------------------------------------------------------------------
# TODO 2 — @retry(times, exceptions) (parameterized decorator)
# ---------------------------------------------------------------------------
#   * retries up to `times` total attempts on the given exception types
#   * re-raises the last exception if all attempts fail
#   * other exception types propagate immediately (no retry)
#   * expose wrapper.attempts — total attempts across all calls


# ---------------------------------------------------------------------------
# TODO 3 — CallLimit(n) (class-based decorator, method-safe)
# ---------------------------------------------------------------------------
# Allows at most n calls; the (n+1)-th raises RuntimeError("call limit
# reached").
#   * store remaining count as instance state
#   * implement __get__ (types.MethodType) so it works on methods too
#   * functools.update_wrapper in __init__


# ---------------------------------------------------------------------------
# TODO 4 — @auto_str (class decorator)
# ---------------------------------------------------------------------------
# Adds a __str__ producing "ClassName(attr1=value1, attr2=value2)" from
# vars(self), in insertion order. Returns the same class.


# ---------------------------------------------------------------------------
# Self-Verification — do not modify below this line
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # TODO 1
    calls = {"n": 0}

    @memoize
    def slow_square(x):
        calls["n"] += 1
        return x * x

    assert slow_square(4) == 16 and slow_square(4) == 16
    assert calls["n"] == 1, "second call must hit the cache"
    assert slow_square.cache == {(4,): 16}
    assert slow_square.__name__ == "slow_square", "use functools.wraps"

    # TODO 2
    state = {"fails_left": 2}

    @retry(times=3, exceptions=(ConnectionError,))
    def flaky():
        if state["fails_left"] > 0:
            state["fails_left"] -= 1
            raise ConnectionError
        return "ok"

    assert flaky() == "ok"
    assert flaky.attempts == 3

    @retry(times=2, exceptions=(ConnectionError,))
    def always_down():
        raise ConnectionError("still down")

    try:
        always_down()
        raise SystemExit("FAIL: must re-raise after exhausting retries")
    except ConnectionError:
        pass

    @retry(times=5, exceptions=(ConnectionError,))
    def wrong_error():
        raise KeyError("not retryable")

    try:
        wrong_error()
        raise SystemExit("FAIL: unlisted exceptions must not be retried")
    except KeyError:
        pass
    assert wrong_error.attempts == 1

    # TODO 3
    @CallLimit(2)
    def limited():
        return "ran"

    assert limited() == "ran" and limited() == "ran"
    try:
        limited()
        raise SystemExit("FAIL: third call must raise")
    except RuntimeError as e:
        assert "call limit reached" in str(e)

    class Api:
        @CallLimit(1)
        def request(self, path):
            return f"GET {path}"

    api = Api()
    assert api.request("/users") == "GET /users", "must work on methods (__get__)"
    try:
        api.request("/again")
        raise SystemExit("FAIL: method limit must fire")
    except RuntimeError:
        pass

    # TODO 4
    @auto_str
    class Point:
        def __init__(self, x, y):
            self.x, self.y = x, y

    assert str(Point(1, 2)) == "Point(x=1, y=2)", str(Point(1, 2))

    print("All exercise checks passed ✔")

# ---------------------------------------------------------------------------
# Stretch Goals
# ---------------------------------------------------------------------------
# 1. Make @memoize handle kwargs (hint: frozenset(kwargs.items())).
# 2. Add exponential backoff to @retry (delay, backoff params; time.sleep).
# 3. Make CallLimit's counter PER-INSTANCE for methods instead of shared
#    (hint: store counts in a WeakKeyDictionary keyed by obj in __get__).

# Cleanup: nothing to clean up — pure in-memory Python.
