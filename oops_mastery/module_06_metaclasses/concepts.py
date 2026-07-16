"""
Module 6: Metaclasses — Concepts in Action
==========================================
Run: python3 concepts.py
"""

# ============================================================================
# 1. Classes are instances of type; `class` is sugar for a call
# ============================================================================
print("=" * 70)
print("1. type() builds classes")
print("=" * 70)


class Dog:
    sound = "woof"


print(f"type(Dog)  = {type(Dog).__name__}")
print(f"type(type) = {type(type).__name__}   <-- the fixed point")
assert type(Dog) is type and type(type) is type

# The same class, built by calling type directly:
Cat = type("Cat", (), {
    "sound": "meow",
    "speak": lambda self: f"{type(self).__name__} says {self.sound}",
})
print(f"dynamic class: {Cat().speak()}")
assert Cat().speak() == "Cat says meow"
assert Cat.__name__ == "Cat" and isinstance(Cat, type)

# ============================================================================
# 2. Watching the pipeline fire
# ============================================================================
print()
print("=" * 70)
print("2. The class-creation pipeline, observably")
print("=" * 70)

pipeline_log = []


class TracingMeta(type):
    @classmethod
    def __prepare__(mcls, name, bases, **kw):
        pipeline_log.append(f"__prepare__ for {name}")
        return {}                            # the namespace the body fills

    def __new__(mcls, name, bases, ns, **kw):
        pipeline_log.append(f"__new__ for {name} with members "
                            f"{sorted(k for k in ns if not k.startswith('__'))}")
        return super().__new__(mcls, name, bases, ns)

    def __init__(cls, name, bases, ns, **kw):
        pipeline_log.append(f"__init__ for {name}")
        super().__init__(name, bases, ns)

    def __call__(cls, *args, **kwargs):
        pipeline_log.append(f"__call__ -> instantiating {cls.__name__}")
        return super().__call__(*args, **kwargs)


print("defining class Service(metaclass=TracingMeta)...")


class Service(metaclass=TracingMeta):
    def ping(self):
        return "pong"


print("instantiating Service()...")
svc = Service()

for entry in pipeline_log:
    print(f"   {entry}")
# Definition ran prepare/new/init; instantiation ran ONLY __call__:
assert pipeline_log == [
    "__prepare__ for Service",
    "__new__ for Service with members ['ping']",
    "__init__ for Service",
    "__call__ -> instantiating Service",
]
assert svc.ping() == "pong"

# ============================================================================
# 3a. Singleton via Meta.__call__
# ============================================================================
print()
print("=" * 70)
print("3a. Singleton: intercept instantiation itself")
print("=" * 70)


class SingletonMeta(type):
    _instances: dict[type, object] = {}

    def __call__(cls, *args, **kwargs):
        # Dog() is type(Dog).__call__(Dog) — so this hook IS instantiation.
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class Config(metaclass=SingletonMeta):
    def __init__(self):
        self.settings = {}


c1, c2 = Config(), Config()
c1.settings["env"] = "prod"
print(f"Config() is Config(): {c1 is c2};  c2 sees c1's write: {c2.settings}")
assert c1 is c2 and c2.settings == {"env": "prod"}

# ============================================================================
# 3b. Registry + enforcement at DEFINITION time
# ============================================================================
print()
print("=" * 70)
print("3b. Registry + interface enforcement")
print("=" * 70)


class CommandMeta(type):
    registry: dict[str, type] = {}

    def __new__(mcls, name, bases, ns):
        cls = super().__new__(mcls, name, bases, ns)
        if bases:                                # skip the abstract root
            if not callable(ns.get("execute")):
                raise TypeError(f"{name} must define execute()")
            mcls.registry[name.removesuffix("Command").lower()] = cls
        return cls


class Command(metaclass=CommandMeta):
    pass


class DeployCommand(Command):
    def execute(self):
        return "deploying..."


class RollbackCommand(Command):
    def execute(self):
        return "rolling back..."


print(f"registry: {sorted(CommandMeta.registry)}")
assert sorted(CommandMeta.registry) == ["deploy", "rollback"]
assert CommandMeta.registry["deploy"]().execute() == "deploying..."

# Enforcement fires at class DEFINITION — not at first call:
try:
    class BrokenCommand(Command):
        pass                                     # no execute()
except TypeError as e:
    print(f"defining BrokenCommand -> TypeError: {e}")

# ============================================================================
# 4. The lighter alternative: __init_subclass__
# ============================================================================
print()
print("=" * 70)
print("4. __init_subclass__: the 90% solution")
print("=" * 70)


class Exporter:
    """Plain base class — no metaclass — with the same registry power."""

    registry: dict[str, type] = {}

    def __init_subclass__(cls, /, key: str | None = None, **kwargs):
        super().__init_subclass__(**kwargs)
        Exporter.registry[key or cls.__name__.lower()] = cls


class CsvExporter(Exporter, key="csv"):          # kwargs come from the class stmt!
    def export(self, rows):
        return "\n".join(",".join(map(str, r)) for r in rows)


class JsonExporter(Exporter):                    # default key
    def export(self, rows):
        return str([list(r) for r in rows])


print(f"Exporter.registry: {sorted(Exporter.registry)}")
assert sorted(Exporter.registry) == ["csv", "jsonexporter"]
assert Exporter.registry["csv"]().export([(1, 2)]) == "1,2"

# And no metaclass conflicts — Exporter subclasses mix with anything:
class Hybrid(CsvExporter, dict):
    pass

print("Hybrid(CsvExporter, dict) defined fine — no metaclass conflict ✔")

# Contrast: mixing two custom metaclasses explodes.
class OtherMeta(type):
    pass


class Other(metaclass=OtherMeta):
    pass


try:
    class Clash(Config, Other):                  # SingletonMeta vs OtherMeta
        pass
except TypeError as e:
    print(f"metaclass conflict demo -> TypeError: metaclass conflict ✔")

print()
print("All Module 6 assertions passed ✔")
