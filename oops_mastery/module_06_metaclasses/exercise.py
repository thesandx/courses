"""
Module 6 Exercise: A Mini Model Framework
=========================================
Goal
----
Build a tiny ORM-style framework the way Django/SQLAlchemy do: a metaclass
that collects declared fields, enforces rules at definition time, and a
plugin registry done the modern way with __init_subclass__.

Complete the TODOs, then run:  python3 exercise.py
"""


# ---------------------------------------------------------------------------
# Provided: a simple validating descriptor (Module 3 payoff)
# ---------------------------------------------------------------------------
class Field:
    def __init__(self, ftype: type):
        self.ftype = ftype

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__.get(self.name)

    def __set__(self, obj, value):
        if not isinstance(value, self.ftype):
            raise TypeError(f"{self.name} must be {self.ftype.__name__}")
        obj.__dict__[self.name] = value


# ---------------------------------------------------------------------------
# TODO 1 — ModelMeta
# ---------------------------------------------------------------------------
# A metaclass that, in __new__:
#   * collects every Field declared in the class body into a dict and
#     attaches it as cls._fields = {name: Field, ...}
#     (include Fields inherited from base classes: iterate bases' _fields
#      first, then the new namespace, so subclasses extend parents)
#   * enforces: model class names must be CapWords — raise
#     TypeError(f"model name {name!r} must start uppercase") if
#     name[0].islower() (skip this check for the base Model itself, i.e.
#     when bases is empty)


# ---------------------------------------------------------------------------
# TODO 2 — Model base class
# ---------------------------------------------------------------------------
# class Model(metaclass=ModelMeta):
#   * __init__(self, **kwargs): assign every kwarg via setattr (descriptors
#     validate); raise TypeError(f"unknown field {key!r}") for keys not in
#     cls._fields; raise TypeError(f"missing field {name!r}") for _fields
#     not supplied.
#   * to_dict(self) -> {field_name: value, ...} for all fields


# ---------------------------------------------------------------------------
# TODO 3 — serializer plugins via __init_subclass__ (NO metaclass)
# ---------------------------------------------------------------------------
# class Serializer:
#     registry: dict[str, type] = {}
#     __init_subclass__ registers subclasses under a `fmt` class-keyword:
#         class JsonSerializer(Serializer, fmt="json"): ...
#     If fmt is missing, raise TypeError("fmt keyword required")
#
# Implement:
#   * JsonSerializer (fmt="json"): dumps(model) -> json.dumps(model.to_dict(),
#     sort_keys=True)
#   * KvSerializer (fmt="kv"): dumps(model) -> "k=v;k=v" over sorted fields


# ---------------------------------------------------------------------------
# Self-Verification — do not modify below this line
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json

    class User(Model):
        name = Field(str)
        age = Field(int)

    u = User(name="ada", age=36)
    assert u.to_dict() == {"name": "ada", "age": 36}
    assert set(User._fields) == {"name", "age"}

    class Admin(User):                    # inherits parent's fields
        level = Field(int)

    a = Admin(name="root", age=99, level=10)
    assert set(Admin._fields) == {"name", "age", "level"}
    assert a.to_dict()["level"] == 10

    try:
        User(name="bob", age="old")
        raise SystemExit("FAIL: Field type check must fire")
    except TypeError:
        pass

    try:
        User(name="bob")
        raise SystemExit("FAIL: missing field must raise")
    except TypeError as e:
        assert "missing field 'age'" in str(e), e

    try:
        User(name="bob", age=1, ghost=True)
        raise SystemExit("FAIL: unknown field must raise")
    except TypeError as e:
        assert "unknown field 'ghost'" in str(e), e

    try:
        class lowercase(Model):           # noqa: N801 — deliberately bad name
            x = Field(int)
        raise SystemExit("FAIL: bad class name must be rejected at definition")
    except TypeError as e:
        assert "must start uppercase" in str(e), e

    assert sorted(Serializer.registry) == ["json", "kv"]
    js = Serializer.registry["json"]()
    assert js.dumps(u) == json.dumps({"age": 36, "name": "ada"}, sort_keys=True)
    kv = Serializer.registry["kv"]()
    assert kv.dumps(u) == "age=36;name=ada"

    try:
        class Anon(Serializer):
            pass
        raise SystemExit("FAIL: fmt keyword must be required")
    except TypeError:
        pass

    print("All exercise checks passed ✔")

# ---------------------------------------------------------------------------
# Stretch Goals
# ---------------------------------------------------------------------------
# 1. Add default values: Field(str, default="") — missing kwargs use defaults.
# 2. Give ModelMeta a __call__ that counts instantiations per model class.
# 3. Generate __repr__ automatically in ModelMeta from _fields.

# Cleanup: nothing to clean up — pure in-memory Python.
