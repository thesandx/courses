"""
Module 2 Solution — Vector + Stopwatch
======================================
Run: python3 solution.py
"""
import math
import time


class Vector:
    def __init__(self, *components: float):
        self._components = tuple(components)   # tuple: safe to hash

    # --- TODO 1: identity ---------------------------------------------------
    def __repr__(self):
        return f"Vector({', '.join(map(repr, self._components))})"

    def __eq__(self, other):
        if not isinstance(other, Vector):
            return NotImplemented
        return self._components == other._components

    def __hash__(self):
        return hash(self._components)

    # --- TODO 2: container --------------------------------------------------
    def __len__(self):
        return len(self._components)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return Vector(*self._components[index])   # slice -> new Vector
        return self._components[index]                 # int   -> scalar

    # --- TODO 3: arithmetic ---------------------------------------------------
    def __add__(self, other):
        if not isinstance(other, Vector):
            return NotImplemented
        if len(self) != len(other):
            raise ValueError("dimension mismatch")
        return Vector(*(a + b for a, b in zip(self, other)))

    def __mul__(self, scalar):
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        return Vector(*(c * scalar for c in self))

    __rmul__ = __mul__                     # scalar * vector delegates to us

    def __abs__(self):
        return math.sqrt(sum(c * c for c in self))

    # --- Stretch 1 & 2 --------------------------------------------------------
    def __neg__(self):
        return self * -1

    def __sub__(self, other):
        if not isinstance(other, Vector):
            return NotImplemented
        return self + (-other)

    def __matmul__(self, other):           # v1 @ v2 -> dot product
        if not isinstance(other, Vector):
            return NotImplemented
        if len(self) != len(other):
            raise ValueError("dimension mismatch")
        return sum(a * b for a, b in zip(self, other))


class Stopwatch:
    def __init__(self):
        self.elapsed = 0.0
        self.history: list[float] = []

    # --- context manager ------------------------------------------------------
    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.elapsed = time.perf_counter() - self._start
        self.history.append(self.elapsed)
        return False                       # never suppress

    # --- callable: time any function call --------------------------------------
    def __call__(self, func, *args, **kwargs):
        with self:                          # reuse our own context manager
            return func(*args, **kwargs)

    # --- Stretch 3 --------------------------------------------------------------
    @property
    def mean(self) -> float:
        return sum(self.history) / len(self.history) if self.history else 0.0


if __name__ == "__main__":
    v = Vector(1, 2, 3)
    assert repr(v) == "Vector(1, 2, 3)"
    assert v == Vector(1, 2, 3) and v != Vector(1, 2)
    assert v != "not a vector"
    assert hash(v) == hash(Vector(1, 2, 3))
    assert len({v, Vector(1, 2, 3)}) == 1

    assert len(v) == 3 and v[0] == 1 and v[-1] == 3
    assert isinstance(v[1:], Vector) and v[1:] == Vector(2, 3)
    assert list(v) == [1, 2, 3]

    assert v + Vector(10, 20, 30) == Vector(11, 22, 33)
    try:
        v + Vector(1, 2)
        raise SystemExit("FAIL")
    except ValueError:
        pass
    assert v * 2 == Vector(2, 4, 6) and 2 * v == Vector(2, 4, 6)
    assert abs(Vector(3, 4)) == 5.0

    # stretch checks
    assert -v == Vector(-1, -2, -3)
    assert v - Vector(1, 1, 1) == Vector(0, 1, 2)
    assert Vector(1, 2) @ Vector(3, 4) == 11

    sw = Stopwatch()
    with sw:
        sum(range(50_000))
    assert sw.elapsed > 0 and len(sw.history) == 1

    assert sw(sorted, [3, 1, 2]) == [1, 2, 3]
    assert len(sw.history) == 2
    assert sw.mean > 0

    try:
        with sw:
            raise KeyError("boom")
        raise SystemExit("FAIL")
    except KeyError:
        pass

    print("All solution checks passed ✔")
