"""
Module 3: Descriptors — Concepts in Action
==========================================
Run: python3 concepts.py
"""
import sys

# ============================================================================
# 1. A minimal descriptor: watch the protocol fire
# ============================================================================
print("=" * 70)
print("1. The descriptor protocol, observably")
print("=" * 70)


class Verbose:
    """Logs every get/set so you can SEE the protocol being invoked."""

    def __set_name__(self, owner, name):
        print(f"   __set_name__: attached to {owner.__name__}.{name}")
        self._name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        print(f"   __get__ for {self._name}")
        return obj.__dict__.get(self._name)

    def __set__(self, obj, value):
        print(f"   __set__ {self._name} = {value!r}")
        obj.__dict__[self._name] = value


print("defining class Config: ...")


class Config:
    host = Verbose()          # descriptor must live on the CLASS


cfg = Config()
cfg.host = "localhost"       # triggers __set__
_ = cfg.host                 # triggers __get__
assert cfg.__dict__ == {"host": "localhost"}

# ============================================================================
# 2. Data vs non-data: who beats the instance dict?
# ============================================================================
print()
print("=" * 70)
print("2. Data descriptors win; non-data descriptors lose")
print("=" * 70)


class NonData:
    def __get__(self, obj, objtype=None):
        return "from NON-DATA descriptor"


class Data:
    def __get__(self, obj, objtype=None):
        return "from DATA descriptor"

    def __set__(self, obj, value):
        raise AttributeError("read-only")


class Demo:
    nd = NonData()
    d = Data()


demo = Demo()
demo.__dict__["nd"] = "from instance dict"    # plant a shadowing entry
demo.__dict__["d"] = "from instance dict"

print(f"demo.nd = {demo.nd!r}   <-- instance dict SHADOWS non-data")
print(f"demo.d  = {demo.d!r}      <-- data descriptor WINS anyway")
assert demo.nd == "from instance dict"
assert demo.d == "from DATA descriptor"

# This is why you can override a method per-instance (functions are non-data)...
class Greeter:
    def greet(self):
        return "hello"


g = Greeter()
g.greet = lambda: "hijacked!"                 # shadows the method
print(f"g.greet() after shadowing: {g.greet()!r}")
assert g.greet() == "hijacked!"

# ...but NOT a property (property is a data descriptor):
class WithProp:
    @property
    def value(self):
        return 42


wp = WithProp()
try:
    wp.value = 99
except AttributeError:
    print("wp.value = 99 -> AttributeError: property's __set__ blocks the write")

# ============================================================================
# 3. Methods ARE descriptors: functions implement __get__
# ============================================================================
print()
print("=" * 70)
print("3. Bound methods are just function.__get__(obj)")
print("=" * 70)

func = Greeter.__dict__["greet"]              # the raw function on the class
bound = func.__get__(g, Greeter)              # what attribute lookup does
print(f"raw:   {func}")
print(f"bound: {bound}")
assert bound() == "hello"
assert Greeter().greet.__self__ is not None   # bound methods remember self

# ============================================================================
# 4. A reusable validated field (the payoff)
# ============================================================================
print()
print("=" * 70)
print("4. One descriptor, many validated fields")
print("=" * 70)


class Positive:
    def __set_name__(self, owner, name):
        self._name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__[self._name]

    def __set__(self, obj, value):
        if not isinstance(value, (int, float)) or value <= 0:
            raise ValueError(f"{self._name} must be a positive number")
        obj.__dict__[self._name] = value      # per-instance storage!


class Product:
    price = Positive()                        # two validated fields,
    stock = Positive()                        # zero property boilerplate

    def __init__(self, price, stock):
        self.price, self.stock = price, stock


p1 = Product(9.99, 100)
p2 = Product(5.00, 3)
print(f"p1: price={p1.price}, stock={p1.stock};  p2: price={p2.price}")
assert (p1.price, p2.price) == (9.99, 5.00)   # values are NOT shared

try:
    p1.price = -1
except ValueError as e:
    print(f"p1.price = -1 -> ValueError: {e}")

# ============================================================================
# 5. __slots__
# ============================================================================
print()
print("=" * 70)
print("5. __slots__: fixed attributes, smaller objects")
print("=" * 70)


class PointDict:
    def __init__(self, x, y):
        self.x, self.y = x, y


class PointSlots:
    __slots__ = ("x", "y")

    def __init__(self, x, y):
        self.x, self.y = x, y


pd, ps = PointDict(1, 2), PointSlots(1, 2)
dict_size = sys.getsizeof(pd) + sys.getsizeof(pd.__dict__)
slot_size = sys.getsizeof(ps)
print(f"with __dict__: {dict_size} bytes;  with __slots__: {slot_size} bytes")
assert slot_size < dict_size
assert not hasattr(ps, "__dict__")

try:
    ps.z = 3
except AttributeError as e:
    print(f"ps.z = 3 -> AttributeError (typo protection): {e}")

# Slots are themselves descriptors, auto-created on the class:
print(f"type(PointSlots.x) = {type(PointSlots.x).__name__}")

# ============================================================================
# 6. __getattr__ (fallback) vs __setattr__ (interception)
# ============================================================================
print()
print("=" * 70)
print("6. Fallback hooks")
print("=" * 70)


class Proxy:
    """Delegates unknown attributes to a wrapped object."""

    def __init__(self, wrapped):
        object.__setattr__(self, "_wrapped", wrapped)   # avoid our own hook
        object.__setattr__(self, "writes", [])

    def __getattr__(self, name):
        # Fires ONLY when normal lookup fails — cheap delegation.
        print(f"   __getattr__ fallback for {name!r}")
        return getattr(self._wrapped, name)

    def __setattr__(self, name, value):
        # Fires on EVERY write. Log it, then delegate.
        self.writes.append(name)
        setattr(self._wrapped, name, value)


class Engine:
    def __init__(self):
        self.rpm = 0

    def start(self):
        return "vroom"


proxy = Proxy(Engine())
print(f"proxy.start() = {proxy.start()!r}")   # not on Proxy -> delegated
proxy.rpm = 3000                               # intercepted + forwarded
assert proxy._wrapped.rpm == 3000
assert proxy.writes == ["rpm"]
print(f"write log: {proxy.writes}")

print()
print("All Module 3 assertions passed ✔")
