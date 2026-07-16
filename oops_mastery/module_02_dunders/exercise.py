"""
Module 2 Exercise: Vector + Stopwatch
=====================================
Goal
----
Build an immutable-feeling `Vector` with full dunder support, then a `Stopwatch`
context manager that is also callable. This exercises repr/eq/hash, operators,
container dunders, __call__, and __enter__/__exit__.

Complete the TODOs, then run:  python3 exercise.py
"""


# ---------------------------------------------------------------------------
# TODO 1 — Vector identity
# ---------------------------------------------------------------------------
# Create class `Vector` taking any number of components: Vector(1, 2, 3).
# Store them in a tuple `self._components`.
#   * __repr__  -> "Vector(1, 2, 3)"
#   * __eq__    -> equal iff components equal; return NotImplemented for
#                  non-Vectors
#   * __hash__  -> consistent with __eq__


# ---------------------------------------------------------------------------
# TODO 2 — Vector as a container
# ---------------------------------------------------------------------------
#   * __len__      -> number of components
#   * __getitem__  -> support both v[0] and slicing v[1:] (slice returns a
#                     new Vector; int returns the number)


# ---------------------------------------------------------------------------
# TODO 3 — Vector arithmetic
# ---------------------------------------------------------------------------
#   * __add__  -> element-wise; raise ValueError("dimension mismatch") for
#                 different lengths; NotImplemented for non-Vectors
#   * __mul__ and __rmul__ -> scalar multiplication (int/float only)
#   * __abs__  -> Euclidean magnitude (math.sqrt of sum of squares)


# ---------------------------------------------------------------------------
# TODO 4 — Stopwatch: context manager + callable
# ---------------------------------------------------------------------------
# Class `Stopwatch`:
#   * usable as `with Stopwatch() as sw:` — measures wall time into sw.elapsed
#     (use time.perf_counter; __exit__ must NOT suppress exceptions)
#   * an instance is also CALLABLE: sw(func, *args) runs func(*args) inside
#     the stopwatch and returns func's result (elapsed updated as a side effect)
#   * keeps a `history` list of all measured durations (append in __exit__)


# ---------------------------------------------------------------------------
# Self-Verification — do not modify below this line
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import math

    v = Vector(1, 2, 3)
    assert repr(v) == "Vector(1, 2, 3)"
    assert v == Vector(1, 2, 3) and v != Vector(1, 2)
    assert v != "not a vector"
    assert hash(v) == hash(Vector(1, 2, 3))
    assert len({v, Vector(1, 2, 3)}) == 1, "equal vectors must dedupe in a set"

    assert len(v) == 3 and v[0] == 1 and v[-1] == 3
    sliced = v[1:]
    assert isinstance(sliced, Vector) and sliced == Vector(2, 3)
    assert list(v) == [1, 2, 3], "iteration should work via __getitem__"

    assert v + Vector(10, 20, 30) == Vector(11, 22, 33)
    try:
        v + Vector(1, 2)
        raise SystemExit("FAIL: dimension mismatch must raise ValueError")
    except ValueError:
        pass
    assert v * 2 == Vector(2, 4, 6) and 2 * v == Vector(2, 4, 6)
    assert abs(Vector(3, 4)) == 5.0

    sw = Stopwatch()
    with sw:
        sum(range(50_000))
    assert sw.elapsed > 0
    assert len(sw.history) == 1

    result = sw(sorted, [3, 1, 2])
    assert result == [1, 2, 3]
    assert len(sw.history) == 2

    try:
        with sw:
            raise KeyError("boom")
        raise SystemExit("FAIL: Stopwatch must not suppress exceptions")
    except KeyError:
        pass

    print("All exercise checks passed ✔")

# ---------------------------------------------------------------------------
# Stretch Goals
# ---------------------------------------------------------------------------
# 1. Add __sub__ and __neg__ to Vector.
# 2. Make Vector support `v1 @ v2` (dot product) via __matmul__.
# 3. Give Stopwatch a `mean` property over its history.

# Cleanup: nothing to clean up — pure in-memory Python.
