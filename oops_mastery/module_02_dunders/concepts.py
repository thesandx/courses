"""
Module 2: Dunder Methods — Concepts in Action
=============================================
Run: python3 concepts.py
"""
import time
from functools import total_ordering

# ============================================================================
# 1 & 2. repr/str + the eq/hash contract
# ============================================================================
print("=" * 70)
print("1-2. The identity trio")
print("=" * 70)


class Money:
    def __init__(self, amount: float, currency: str):
        self.amount, self.currency = amount, currency

    def __repr__(self):
        # Developer-facing: unambiguous, ideally eval()-able.
        return f"Money({self.amount!r}, {self.currency!r})"

    def __str__(self):
        # User-facing: pretty.
        return f"{self.amount:.2f} {self.currency}"

    def __eq__(self, other):
        if not isinstance(other, Money):
            return NotImplemented        # value, not exception — see README
        return (self.amount, self.currency) == (other.amount, other.currency)

    def __hash__(self):
        # Same fields as __eq__, packed in a tuple -> upholds the contract.
        return hash((self.amount, self.currency))


m1, m2 = Money(9.99, "USD"), Money(9.99, "USD")
print(f"repr: {m1!r}   str: {m1}")
print(f"m1 == m2: {m1 == m2},  hash equal: {hash(m1) == hash(m2)}")
assert m1 == m2 and hash(m1) == hash(m2)
assert m1 != "9.99"                      # NotImplemented -> Python falls back

prices = {m1: "premium"}                 # usable as dict key thanks to __hash__
assert prices[m2] == "premium"           # equal object finds the same slot
print(f"dict lookup via equal key works: prices[m2] = {prices[m2]!r}")


# Defining __eq__ WITHOUT __hash__ silently disables hashing:
class EqOnly:
    def __eq__(self, other):
        return True


try:
    hash(EqOnly())
except TypeError as e:
    print(f"__eq__ without __hash__: TypeError: {e}")

# ============================================================================
# 3. Operator overloading, reflected ops, total_ordering
# ============================================================================
print()
print("=" * 70)
print("3. Operators and reflected methods")
print("=" * 70)


@total_ordering                          # derives <=, >, >= from __lt__ + __eq__
class Vector2:
    def __init__(self, x: float, y: float):
        self.x, self.y = x, y

    def __repr__(self):
        return f"Vector2({self.x}, {self.y})"

    def __add__(self, other):
        if not isinstance(other, Vector2):
            return NotImplemented
        return Vector2(self.x + other.x, self.y + other.y)   # NEW object

    def __mul__(self, scalar):           # vector * 3
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        return Vector2(self.x * scalar, self.y * scalar)

    __rmul__ = __mul__                   # 3 * vector — int defers to us

    def __eq__(self, other):
        if not isinstance(other, Vector2):
            return NotImplemented
        return (self.x, self.y) == (other.x, other.y)

    def __lt__(self, other):             # compare by magnitude
        return self.x ** 2 + self.y ** 2 < other.x ** 2 + other.y ** 2


v = Vector2(1, 2) + Vector2(3, 4)
print(f"Vector2(1,2) + Vector2(3,4) = {v}")
assert v == Vector2(4, 6)

print(f"3 * Vector2(1,2) = {3 * Vector2(1, 2)}   <-- __rmul__ in action")
assert 3 * Vector2(1, 2) == Vector2(3, 6)

print(f"Vector2(1,1) <= Vector2(3,4): {Vector2(1, 1) <= Vector2(3, 4)}"
      "   <-- derived by total_ordering")
assert Vector2(1, 1) <= Vector2(3, 4)

# ============================================================================
# 4. Container dunders
# ============================================================================
print()
print("=" * 70)
print("4. __len__ / __getitem__ give you loops, `in`, slices")
print("=" * 70)


class Playlist:
    def __init__(self, songs):
        self._songs = list(songs)

    def __len__(self):
        return len(self._songs)

    def __getitem__(self, index):        # handles ints AND slices
        return self._songs[index]


pl = Playlist(["Intro", "Verse", "Chorus", "Outro"])
print(f"len(pl) = {len(pl)}")
print(f"pl[1] = {pl[1]},  pl[-1] = {pl[-1]},  pl[1:3] = {pl[1:3]}")
print(f"'Chorus' in pl: {'Chorus' in pl}      <-- via __getitem__ fallback")
print(f"iteration: {[s for s in pl]}          <-- no __iter__ defined!")
assert len(pl) == 4 and "Chorus" in pl and list(pl)[0] == "Intro"

empty = Playlist([])
print(f"bool(empty playlist) = {bool(empty)}  <-- falsy via __len__ == 0")
assert not empty

# ============================================================================
# 5. __call__ and context managers
# ============================================================================
print()
print("=" * 70)
print("5. Callables and context managers")
print("=" * 70)


class RunningAverage:
    """An instance that behaves like a function but keeps state."""

    def __init__(self):
        self._total, self._count = 0.0, 0

    def __call__(self, value: float) -> float:
        self._total += value
        self._count += 1
        return self._total / self._count


avg = RunningAverage()
print(f"avg(10)={avg(10)}, avg(20)={avg(20)}, avg(30)={avg(30)}")
assert avg(40) == 25.0
print(f"callable(avg) = {callable(avg)}")


class Timer:
    def __enter__(self):
        self.start = time.perf_counter()
        return self                      # bound to the `as` target

    def __exit__(self, exc_type, exc, tb):
        self.elapsed = time.perf_counter() - self.start
        return False                     # falsy: never swallow exceptions


with Timer() as t:
    sum(range(100_000))
print(f"Timer measured {t.elapsed * 1000:.2f} ms")
assert t.elapsed > 0


class Suppress:
    """Like contextlib.suppress: returning True from __exit__ eats the error."""

    def __init__(self, *exc_types):
        self.exc_types = exc_types

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return exc_type is not None and issubclass(exc_type, self.exc_types)


with Suppress(ZeroDivisionError):
    1 / 0
print("1/0 inside Suppress(ZeroDivisionError): exception swallowed ✔")

# ============================================================================
# 6. __new__ vs __init__
# ============================================================================
print()
print("=" * 70)
print("6. __new__ creates, __init__ initializes")
print("=" * 70)


class Celsius(float):
    """Subclassing an immutable: the value MUST be set in __new__ —
    by __init__ time, a float's value is frozen."""

    def __new__(cls, degrees):
        if degrees < -273.15:
            raise ValueError("below absolute zero")
        return super().__new__(cls, degrees)

    def as_fahrenheit(self) -> float:
        return self * 9 / 5 + 32


c = Celsius(100)
print(f"Celsius(100) = {c}, as_fahrenheit() = {c.as_fahrenheit()}")
assert c == 100.0 and c.as_fahrenheit() == 212.0


class Interned:
    """__new__ as a cache: one instance per distinct name."""

    _cache: dict[str, "Interned"] = {}

    def __new__(cls, name: str):
        if name not in cls._cache:
            cls._cache[name] = super().__new__(cls)
        return cls._cache[name]

    def __init__(self, name: str):
        self.name = name                 # runs on every call — keep it idempotent


x, y = Interned("db"), Interned("db")
print(f"Interned('db') is Interned('db'): {x is y}")
assert x is y

print()
print("All Module 2 assertions passed ✔")
