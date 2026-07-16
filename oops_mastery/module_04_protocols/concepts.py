"""
Module 4: Protocols, ABCs & Structural Typing — Concepts in Action
==================================================================
Run: python3 concepts.py
"""
from abc import ABC, abstractmethod
from collections import abc as cabc
from typing import Protocol, runtime_checkable

# ============================================================================
# 1. Duck typing: capability over ancestry
# ============================================================================
print("=" * 70)
print("1. Duck typing")
print("=" * 70)


class FileishLog:
    """Not a file, inherits nothing — but has .write, so print() accepts it."""

    def __init__(self):
        self.lines = []

    def write(self, text):
        if text.strip():
            self.lines.append(text.strip())


log = FileishLog()
print("hello ducks", file=log)          # print only cares about .write
print(f"captured: {log.lines}")
assert log.lines == ["hello ducks"]

# ============================================================================
# 2. collections.abc — structural isinstance + free mixin methods
# ============================================================================
print()
print("=" * 70)
print("2. collections.abc")
print("=" * 70)


class Countdown:                        # no inheritance at all
    def __init__(self, start):
        self.start = start

    def __iter__(self):
        n = self.start
        while n > 0:
            yield n
            n -= 1


# a) structural isinstance via __subclasshook__:
print(f"isinstance(Countdown(3), Iterable) = "
      f"{isinstance(Countdown(3), cabc.Iterable)}   <-- no registration needed")
assert isinstance(Countdown(3), cabc.Iterable)
assert not isinstance(42, cabc.Iterable)

# b) mixin methods: implement 2, inherit 5.
class SortedItems(cabc.Sequence):
    def __init__(self, data):
        self._items = sorted(data)

    def __getitem__(self, index):        # we write this...
        return self._items[index]

    def __len__(self):                   # ...and this
        return len(self._items)


s = SortedItems([5, 1, 3])
print(f"SortedItems([5,1,3]): list={list(s)}, 3 in s: {3 in s}, "
      f"index(3)={s.index(3)}, reversed={list(reversed(s))}")
# __contains__, __iter__, index, count, __reversed__ all came from Sequence:
assert list(s) == [1, 3, 5] and 3 in s and s.index(3) == 1 and s.count(5) == 1

# ============================================================================
# 3. Abstract Base Classes
# ============================================================================
print()
print("=" * 70)
print("3. ABCs: contract + shared implementation")
print("=" * 70)


class Storage(ABC):
    @abstractmethod
    def save(self, key: str, data: bytes) -> None: ...

    @abstractmethod
    def load(self, key: str) -> bytes: ...

    def copy(self, src: str, dst: str) -> None:
        """Concrete 'template method' written against the abstract ones."""
        self.save(dst, self.load(src))


try:
    Storage()                            # abstract methods unimplemented
except TypeError as e:
    print(f"Storage() -> TypeError: {e}")


class HalfDone(Storage):                 # defines save but NOT load
    def save(self, key, data): ...


try:
    HalfDone()                           # still abstract — one method missing
except TypeError as e:
    print(f"HalfDone() -> TypeError (missing load)")


class MemoryStorage(Storage):
    def __init__(self):
        self._blobs: dict[str, bytes] = {}

    def save(self, key, data):
        self._blobs[key] = data

    def load(self, key):
        return self._blobs[key]


mem = MemoryStorage()
mem.save("a", b"payload")
mem.copy("a", "b")                       # inherited concrete method
print(f"after copy: load('b') = {mem.load('b')}")
assert mem.load("b") == b"payload"

# Virtual subclassing: isinstance passes, but NOTHING is verified.
class Sneaky:
    pass


Storage.register(Sneaky)
print(f"registered Sneaky: isinstance -> {isinstance(Sneaky(), Storage)}, "
      f"has save? {hasattr(Sneaky(), 'save')}   <-- trust, not verification")
assert isinstance(Sneaky(), Storage) and not hasattr(Sneaky(), "save")

# ============================================================================
# 4. typing.Protocol — structural typing
# ============================================================================
print()
print("=" * 70)
print("4. Protocols")
print("=" * 70)


@runtime_checkable
class Serializer(Protocol):
    def serialize(self) -> str: ...


class JsonUser:                          # conforms by SHAPE — no inheritance
    def __init__(self, name):
        self.name = name

    def serialize(self) -> str:
        return f'{{"name": "{self.name}"}}'


class CsvRow:                            # also conforms
    def __init__(self, *cells):
        self.cells = cells

    def serialize(self) -> str:
        return ",".join(map(str, self.cells))


def export_all(items: list[Serializer]) -> list[str]:
    """A static checker verifies conformance here — structurally."""
    return [item.serialize() for item in items]


out = export_all([JsonUser("ada"), CsvRow(1, 2, 3)])
print(f"export_all -> {out}")
assert out == ['{"name": "ada"}', "1,2,3"]

print(f"isinstance(JsonUser('x'), Serializer) = "
      f"{isinstance(JsonUser('x'), Serializer)}   <-- runtime_checkable")
assert isinstance(JsonUser("x"), Serializer)
assert not isinstance("plain string", Serializer)


# The limit: runtime check is NAME-presence only, not signature.
class WrongShape:
    def serialize(self, a, b, c):        # bad signature — still "passes"
        return "?"


print(f"WrongShape passes isinstance: {isinstance(WrongShape(), Serializer)}"
      "   <-- names only; signatures are the static checker's job")
assert isinstance(WrongShape(), Serializer)

# ============================================================================
# 5. Iterable vs iterator
# ============================================================================
print()
print("=" * 70)
print("5. The iterator protocol")
print("=" * 70)

cd = Countdown(3)
print(f"first  loop: {list(cd)}")
print(f"second loop: {list(cd)}   <-- fresh generator each __iter__ call")
assert list(cd) == [3, 2, 1] == list(cd)     # reusable: iterable, not iterator


class BadCountdown:
    """Anti-example: the container IS its own iterator -> one-shot."""

    def __init__(self, start):
        self.n = start

    def __iter__(self):
        return self                      # the classic mistake

    def __next__(self):
        if self.n <= 0:
            raise StopIteration
        self.n -= 1
        return self.n + 1


bad = BadCountdown(3)
print(f"BadCountdown first loop:  {list(bad)}")
print(f"BadCountdown second loop: {list(bad)}   <-- exhausted forever")
assert list(bad) == []                   # silently empty: the bug in the wild

# iterators are also iterable (iter(it) is it) — that's why they work in `for`:
it = iter(Countdown(2))
assert iter(it) is it
assert next(it) == 2 and next(it) == 1
try:
    next(it)
except StopIteration:
    print("manual next() until StopIteration ✔")

print()
print("All Module 4 assertions passed ✔")
