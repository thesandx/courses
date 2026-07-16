"""
Module 6 Solution — A Mini Model Framework
==========================================
Run: python3 solution.py
"""
import json


class Field:
    def __init__(self, ftype: type, default=None, has_default=False):
        self.ftype = ftype
        self.default = default
        # Stretch 1: distinguish "no default" from "default=None"
        self.has_default = has_default or default is not None

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


class ModelMeta(type):
    def __new__(mcls, name, bases, ns):
        if bases and name[0].islower():
            # Definition-time enforcement: the class never even gets created.
            raise TypeError(f"model name {name!r} must start uppercase")

        cls = super().__new__(mcls, name, bases, ns)

        # Parents' fields first, then this class's — subclasses extend.
        fields: dict[str, Field] = {}
        for base in bases:
            fields.update(getattr(base, "_fields", {}))
        fields.update({k: v for k, v in ns.items() if isinstance(v, Field)})
        cls._fields = fields
        return cls

    # Stretch 2: count instantiations per model class.
    def __call__(cls, *args, **kwargs):
        instance = super().__call__(*args, **kwargs)
        cls.instances_created = getattr(cls, "instances_created", 0) + 1
        return instance


class Model(metaclass=ModelMeta):
    def __init__(self, **kwargs):
        for key in kwargs:
            if key not in self._fields:
                raise TypeError(f"unknown field {key!r}")
        for name, field in self._fields.items():
            if name in kwargs:
                setattr(self, name, kwargs[name])    # descriptor validates
            elif field.has_default:                  # Stretch 1
                setattr(self, name, field.default)
            else:
                raise TypeError(f"missing field {name!r}")

    def to_dict(self) -> dict:
        return {name: getattr(self, name) for name in self._fields}

    # Stretch 3: auto __repr__ from _fields.
    def __repr__(self):
        pairs = ", ".join(f"{k}={v!r}" for k, v in self.to_dict().items())
        return f"{type(self).__name__}({pairs})"


class Serializer:
    """Registry via __init_subclass__ — no metaclass needed here."""

    registry: dict[str, type] = {}

    def __init_subclass__(cls, /, fmt: str | None = None, **kwargs):
        super().__init_subclass__(**kwargs)
        if fmt is None:
            raise TypeError("fmt keyword required")
        Serializer.registry[fmt] = cls


class JsonSerializer(Serializer, fmt="json"):
    def dumps(self, model: Model) -> str:
        return json.dumps(model.to_dict(), sort_keys=True)


class KvSerializer(Serializer, fmt="kv"):
    def dumps(self, model: Model) -> str:
        return ";".join(f"{k}={v}" for k, v in sorted(model.to_dict().items()))


if __name__ == "__main__":
    class User(Model):
        name = Field(str)
        age = Field(int)

    u = User(name="ada", age=36)
    assert u.to_dict() == {"name": "ada", "age": 36}
    assert set(User._fields) == {"name", "age"}

    class Admin(User):
        level = Field(int)

    a = Admin(name="root", age=99, level=10)
    assert set(Admin._fields) == {"name", "age", "level"}
    assert a.to_dict()["level"] == 10

    try:
        User(name="bob", age="old")
        raise SystemExit("FAIL")
    except TypeError:
        pass
    try:
        User(name="bob")
        raise SystemExit("FAIL")
    except TypeError as e:
        assert "missing field 'age'" in str(e)
    try:
        User(name="bob", age=1, ghost=True)
        raise SystemExit("FAIL")
    except TypeError as e:
        assert "unknown field 'ghost'" in str(e)

    try:
        class lowercase(Model):           # noqa: N801
            x = Field(int)
        raise SystemExit("FAIL")
    except TypeError as e:
        assert "must start uppercase" in str(e)

    assert sorted(Serializer.registry) == ["json", "kv"]
    assert (Serializer.registry["json"]().dumps(u)
            == json.dumps({"age": 36, "name": "ada"}, sort_keys=True))
    assert Serializer.registry["kv"]().dumps(u) == "age=36;name=ada"

    try:
        class Anon(Serializer):
            pass
        raise SystemExit("FAIL")
    except TypeError:
        pass

    # stretch checks
    class Tagged(Model):
        label = Field(str, default="untagged")

    t = Tagged()
    assert t.label == "untagged"
    assert repr(t) == "Tagged(label='untagged')"
    assert Tagged.instances_created == 1
    Tagged(label="x")
    assert Tagged.instances_created == 2

    print("All solution checks passed ✔")
