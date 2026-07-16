"""
Module 1: The Core Object Model — Concepts in Action
====================================================
Run: python3 concepts.py

Each section maps 1:1 to a section in README.md and prints observable proof.
"""

# ============================================================================
# 1. Classes are objects; instance vs class attributes
# ============================================================================
print("=" * 70)
print("1. Instance vs class attributes")
print("=" * 70)


class Account:
    bank = "MegaBank"                  # class attribute: one copy, on the class

    def __init__(self, owner: str):
        self.owner = owner             # instance attribute: one copy per object


a, b = Account("Ada"), Account("Bob")
print(f"Account is an instance of {type(Account).__name__!r}")     # 'type'
print(f"a.__dict__ = {a.__dict__}")                # only instance attrs
print(f"'bank' in a.__dict__?  {'bank' in a.__dict__}")            # False
print(f"a.bank = {a.bank}  (found on the class via lookup)")

# Assignment SHADOWS the class attribute — it never modifies the class:
a.bank = "TinyBank"
print(f"after a.bank='TinyBank': a.bank={a.bank}, b.bank={b.bank}")
assert Account.bank == "MegaBank"      # class untouched

# The classic mutable-class-attribute bug:
class BuggyCart:
    items = []                         # SHARED by every instance!

    def add(self, item):
        self.items.append(item)        # mutates the class-level list


c1, c2 = BuggyCart(), BuggyCart()
c1.add("apple")
print(f"c2.items after c1.add: {c2.items}   <-- the bug: state leaked")
assert c2.items == ["apple"]


class FixedCart:
    def __init__(self):
        self.items = []                # per-instance, created in __init__

    def add(self, item):
        self.items.append(item)


f1, f2 = FixedCart(), FixedCart()
f1.add("apple")
print(f"FixedCart: f2.items = {f2.items}   <-- isolated, as expected")
assert f2.items == []

# ============================================================================
# 2. Instance / class / static methods
# ============================================================================
print()
print("=" * 70)
print("2. The three method kinds")
print("=" * 70)


class Temperature:
    def __init__(self, degrees: float):
        self.degrees = degrees

    def to_fahrenheit(self) -> float:              # instance method
        return self.degrees * 9 / 5 + 32

    @classmethod
    def from_fahrenheit(cls, f: float) -> "Temperature":
        # `cls` is whatever class the call went through — subclass-friendly.
        return cls((f - 32) * 5 / 9)

    @staticmethod
    def is_valid(degrees: float) -> bool:          # no self, no cls
        return degrees >= -273.15


class LabeledTemperature(Temperature):
    def __repr__(self):
        return f"LabeledTemperature({self.degrees:.1f}°C)"


t = Temperature.from_fahrenheit(212)
print(f"212°F -> {t.degrees:.0f}°C, back -> {t.to_fahrenheit():.0f}°F")
assert round(t.degrees) == 100

# The payoff of @classmethod: the constructor is polymorphic.
lt = LabeledTemperature.from_fahrenheit(32)
print(f"from_fahrenheit via subclass returns: {lt!r} ({type(lt).__name__})")
assert type(lt) is LabeledTemperature

print(f"is_valid(-500) = {Temperature.is_valid(-500)}")
assert not Temperature.is_valid(-500)

# ============================================================================
# 3. Properties
# ============================================================================
print()
print("=" * 70)
print("3. Properties: attributes with behavior")
print("=" * 70)


class Circle:
    def __init__(self, radius: float):
        self.radius = radius           # NOTE: routes through the setter below

    @property
    def radius(self) -> float:
        return self._radius            # backing field: different name!

    @radius.setter
    def radius(self, value: float):
        if value <= 0:
            raise ValueError("radius must be positive")
        self._radius = value

    @property
    def area(self) -> float:           # read-only computed attribute
        return 3.14159 * self._radius ** 2


c = Circle(2)
print(f"Circle(2): radius={c.radius}, area={c.area:.2f}")
c.radius = 3                            # setter validates on every write
print(f"after c.radius=3: area={c.area:.2f}")

try:
    c.radius = -1
except ValueError as e:
    print(f"c.radius = -1 -> ValueError: {e}")

try:
    c.area = 99                         # no setter defined
except AttributeError as e:
    print(f"c.area = 99   -> AttributeError (read-only property)")

# ============================================================================
# 4. Inheritance, MRO, and cooperative super()
# ============================================================================
print()
print("=" * 70)
print("4. MRO and super()")
print("=" * 70)


class A:
    def greet(self):
        return ["A"]


class B(A):
    def greet(self):
        return ["B"] + super().greet()


class C(A):
    def greet(self):
        return ["C"] + super().greet()


class D(B, C):
    def greet(self):
        return ["D"] + super().greet()


print("D.__mro__ =", " -> ".join(k.__name__ for k in D.__mro__))
order = D().greet()
print(f"D().greet() visited: {order}")
# B's super() call reached C — not A — because super() follows the MRO of D.
assert order == ["D", "B", "C", "A"]

# Cooperative __init__ with **kwargs so every class in the chain gets its args:
class Vehicle:
    def __init__(self, *, wheels, **kwargs):
        super().__init__(**kwargs)
        self.wheels = wheels


class Electric:
    def __init__(self, *, battery_kwh, **kwargs):
        super().__init__(**kwargs)
        self.battery_kwh = battery_kwh


class ECar(Vehicle, Electric):
    pass


car = ECar(wheels=4, battery_kwh=75)
print(f"ECar: wheels={car.wheels}, battery={car.battery_kwh} kWh "
      f"(both __init__s ran cooperatively)")
assert (car.wheels, car.battery_kwh) == (4, 75)

# ============================================================================
# 5. Encapsulation conventions and name mangling
# ============================================================================
print()
print("=" * 70)
print("5. Encapsulation: _single vs __double")
print("=" * 70)


class Wallet:
    def __init__(self):
        self._balance = 0              # convention: internal
        self.__ledger = []             # mangled to _Wallet__ledger

    def deposit(self, amount):
        self._balance += amount
        self.__ledger.append(amount)


w = Wallet()
w.deposit(50)
print(f"w.__dict__ keys: {sorted(w.__dict__)}")     # see the mangled name
assert "_Wallet__ledger" in w.__dict__

try:
    w.__ledger
except AttributeError:
    print("w.__ledger  -> AttributeError (mangled away)")

print(f"w._Wallet__ledger = {w._Wallet__ledger}  <-- mangling is not privacy")

# What mangling is actually FOR: subclasses can't accidentally collide.
class AuditedWallet(Wallet):
    def __init__(self):
        super().__init__()
        self.__ledger = "audit-log"    # mangles to _AuditedWallet__ledger


aw = AuditedWallet()
aw.deposit(10)
print(f"AuditedWallet keeps both: {sorted(aw.__dict__)}")
assert aw._Wallet__ledger == [10] and aw._AuditedWallet__ledger == "audit-log"

print()
print("All Module 1 assertions passed ✔")
