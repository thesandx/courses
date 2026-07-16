"""
Module 3 Solution — A Descriptor Toolkit
========================================
Run: python3 solution.py
"""


class Typed:
    """Data descriptor: enforces isinstance on every write."""

    def __init__(self, expected_type: type):
        self.expected_type = expected_type

    def __set_name__(self, owner, name):
        self._name = name

    def __get__(self, obj, objtype=None):
        if obj is None:                       # Employee.name -> the descriptor
            return self
        return obj.__dict__[self._name]

    def __set__(self, obj, value):
        if not isinstance(value, self.expected_type):
            raise TypeError(
                f"{self._name} must be {self.expected_type.__name__}")
        # Per-instance storage. Safe even though the key matches our own
        # name: data descriptors are checked BEFORE the instance dict.
        obj.__dict__[self._name] = value


class Bounded:
    """Data descriptor: numeric range validation, inclusive bounds."""

    def __init__(self, minimum, maximum):
        self.minimum, self.maximum = minimum, maximum

    def __set_name__(self, owner, name):
        self._name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__[self._name]

    def __set__(self, obj, value):
        if not (self.minimum <= value <= self.maximum):
            raise ValueError(
                f"{self._name} must be between {self.minimum} and {self.maximum}")
        obj.__dict__[self._name] = value


class LazyProperty:
    """NON-data descriptor (only __get__): compute once, cache forever.

    On first access, we plant the result in obj.__dict__ under our own
    name. Because non-data descriptors LOSE to the instance dict, every
    subsequent access hits the cache and never reaches __get__ again.
    """

    def __init__(self, func):
        self.func = func
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        value = self.func(obj)                # compute...
        obj.__dict__[self.__name__] = value   # ...cache: shadows us from now on
        return value


class Employee:
    name = Typed(str)
    age = Bounded(18, 99)
    salary = Typed(float)

    tax_calls = 0                             # proof-of-single-execution counter

    def __init__(self, name: str, age: int, salary: float):
        self.name = name
        self.age = age
        self.salary = salary

    @LazyProperty
    def tax_bracket(self) -> str:
        Employee.tax_calls += 1               # visible side effect for the test
        return "high" if self.salary > 100_000 else "standard"


# --- Stretch 1: composition via inheritance --------------------------------
class TypedBounded(Typed):
    def __init__(self, expected_type, minimum, maximum):
        super().__init__(expected_type)
        self.minimum, self.maximum = minimum, maximum

    def __set__(self, obj, value):
        if isinstance(value, self.expected_type) and not (
                self.minimum <= value <= self.maximum):
            raise ValueError(
                f"{self._name} must be between {self.minimum} and {self.maximum}")
        super().__set__(obj, value)           # type check + store


# --- Stretch 2: write-once field --------------------------------------------
class Frozen:
    def __set_name__(self, owner, name):
        self._name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__[self._name]

    def __set__(self, obj, value):
        if self._name in obj.__dict__:
            raise AttributeError(f"{self._name} is frozen (already set)")
        obj.__dict__[self._name] = value


if __name__ == "__main__":
    e = Employee("ada", 36, 120_000.0)
    assert (e.name, e.age, e.salary) == ("ada", 36, 120_000.0)

    try:
        e.name = 42
        raise SystemExit("FAIL")
    except TypeError as err:
        assert "name must be str" in str(err)

    try:
        e.age = 12
        raise SystemExit("FAIL")
    except ValueError as err:
        assert "between 18 and 99" in str(err)

    e2 = Employee("bob", 44, 50_000.0)
    assert e.name == "ada" and e2.name == "bob"
    assert isinstance(Employee.name, Typed)

    assert Employee.tax_calls == 0
    assert e.tax_bracket == "high"
    assert Employee.tax_calls == 1
    assert e.tax_bracket == "high"
    assert Employee.tax_calls == 1
    assert "tax_bracket" in e.__dict__
    assert e2.tax_bracket == "standard"
    assert Employee.tax_calls == 2

    # stretch checks
    class Dial:
        level = TypedBounded(int, 0, 10)

        def __init__(self, level):
            self.level = level

    d = Dial(7)
    assert d.level == 7
    try:
        d.level = 11
        raise SystemExit("FAIL")
    except ValueError:
        pass
    try:
        d.level = "loud"
        raise SystemExit("FAIL")
    except TypeError:
        pass

    class Cert:
        serial = Frozen()

    cert = Cert()
    cert.serial = "abc-123"
    try:
        cert.serial = "xyz-999"
        raise SystemExit("FAIL")
    except AttributeError:
        pass

    print("All solution checks passed ✔")
