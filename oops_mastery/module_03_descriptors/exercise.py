"""
Module 3 Exercise: A Descriptor Toolkit
=======================================
Goal
----
Build three production-grade descriptors — `Typed`, `Bounded`, and
`LazyProperty` — and use them in an `Employee` class. This locks in
__set_name__, per-instance storage, data vs non-data behavior, and the
descriptor-as-cache trick.

Complete the TODOs, then run:  python3 exercise.py
"""


# ---------------------------------------------------------------------------
# TODO 1 — Typed(expected_type): a data descriptor enforcing isinstance
# ---------------------------------------------------------------------------
#   * __init__ stores expected_type
#   * __set_name__ records the attribute name
#   * __set__ raises TypeError(f"{name} must be {expected_type.__name__}")
#     for wrong types; stores valid values in obj.__dict__[name]
#   * __get__ returns the stored value; return the descriptor itself when
#     accessed on the class (obj is None)


# ---------------------------------------------------------------------------
# TODO 2 — Bounded(minimum, maximum): numeric range validation
# ---------------------------------------------------------------------------
#   * __set__ raises ValueError(f"{name} must be between {minimum} and
#     {maximum}") when out of range (inclusive bounds)
#   * same storage strategy as Typed


# ---------------------------------------------------------------------------
# TODO 3 — LazyProperty: a NON-data descriptor that caches
# ---------------------------------------------------------------------------
# A decorator-style descriptor: wraps a method, computes on first access,
# then caches the result in the instance dict UNDER THE SAME NAME.
# Because it defines only __get__ (non-data), the cached instance-dict entry
# shadows the descriptor on every later access — the method runs only ONCE.
#
#   class Report:
#       @LazyProperty
#       def stats(self):        # expensive; runs once
#           ...
#
#   * __init__(self, func) stores func and copies func.__name__
#   * __get__ computes func(obj), plants it in obj.__dict__, returns it


# ---------------------------------------------------------------------------
# TODO 4 — Use all three in Employee
# ---------------------------------------------------------------------------
# class Employee:
#     name   = Typed(str)
#     age    = Bounded(18, 99)
#     salary = Typed(float)
#
#     __init__(self, name, age, salary) assigns all three.
#
#     @LazyProperty
#     def tax_bracket(self):  -> "high" if salary > 100_000 else "standard"
#         Also increment the CLASS-level counter Employee.tax_calls by 1
#         inside the method so the test can prove single execution.
# Give Employee a class attribute `tax_calls = 0`.


# ---------------------------------------------------------------------------
# Self-Verification — do not modify below this line
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    e = Employee("ada", 36, 120_000.0)
    assert (e.name, e.age, e.salary) == ("ada", 36, 120_000.0)

    try:
        e.name = 42
        raise SystemExit("FAIL: Typed must reject wrong types")
    except TypeError as err:
        assert "name must be str" in str(err), str(err)

    try:
        e.age = 12
        raise SystemExit("FAIL: Bounded must reject out-of-range")
    except ValueError as err:
        assert "between 18 and 99" in str(err), str(err)

    # two instances must not share stored values
    e2 = Employee("bob", 44, 50_000.0)
    assert e.name == "ada" and e2.name == "bob"

    # class access returns the descriptor object itself
    assert isinstance(Employee.name, Typed)

    # LazyProperty: computed once, then served from the instance dict
    assert Employee.tax_calls == 0
    assert e.tax_bracket == "high"
    assert Employee.tax_calls == 1
    assert e.tax_bracket == "high"        # cached — no second call
    assert Employee.tax_calls == 1, "lazy property ran more than once!"
    assert "tax_bracket" in e.__dict__    # the cache lives on the instance

    assert e2.tax_bracket == "standard"   # separate instance, separate cache
    assert Employee.tax_calls == 2

    print("All exercise checks passed ✔")

# ---------------------------------------------------------------------------
# Stretch Goals
# ---------------------------------------------------------------------------
# 1. Compose them: `TypedBounded(int, 0, 10)` via inheritance or a
#    `validators=[...]` parameter.
# 2. Add a `Frozen` descriptor: settable exactly once, then AttributeError.
# 3. Reimplement LazyProperty using functools.cached_property's approach:
#    look at its source (it's pure Python) and compare.

# Cleanup: nothing to clean up — pure in-memory Python.
