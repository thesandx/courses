"""
Module 9: Dependency Injection — Concepts in Action
===================================================
Run: python3 concepts.py
"""
import typing
from dataclasses import dataclass
from typing import Callable, Protocol

# ============================================================================
# 1. The refactor: hardcoded -> injected
# ============================================================================
print("=" * 70)
print("1. Constructor injection")
print("=" * 70)


@dataclass
class User:
    user_id: str
    email: str


class UserRepo(Protocol):
    def add(self, user: User) -> None: ...
    def get(self, user_id: str) -> User | None: ...


class Mailer(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...


class SignupService:
    """Depends on SHAPES. Constructs nothing. Valid from birth."""

    def __init__(self, repo: UserRepo, mailer: Mailer):
        self._repo = repo
        self._mailer = mailer

    def signup(self, user_id: str, email: str) -> User:
        if self._repo.get(user_id) is not None:
            raise ValueError(f"user {user_id!r} already exists")
        user = User(user_id, email)
        self._repo.add(user)
        self._mailer.send(email, "Welcome!", f"Hello {user_id}")
        return user


# Two conforming implementations — no inheritance, just matching shape:
class InMemoryUserRepo:
    def __init__(self):
        self._users: dict[str, User] = {}

    def add(self, user: User) -> None:
        self._users[user.user_id] = user

    def get(self, user_id: str) -> User | None:
        return self._users.get(user_id)


class FakeMailer:
    def __init__(self):
        self.outbox: list[tuple[str, str]] = []

    def send(self, to: str, subject: str, body: str) -> None:
        self.outbox.append((to, subject))


repo, mailer = InMemoryUserRepo(), FakeMailer()
svc = SignupService(repo, mailer)
svc.signup("ada", "ada@example.com")
print(f"repo has ada: {repo.get('ada')}")
print(f"outbox: {mailer.outbox}")
assert repo.get("ada").email == "ada@example.com"
assert mailer.outbox == [("ada@example.com", "Welcome!")]

# ============================================================================
# 2. The composition root: one place chooses concretions
# ============================================================================
print()
print("=" * 70)
print("2. Composition root")
print("=" * 70)


class LoudMailer:                                # "production" detail
    def send(self, to, subject, body):
        print(f"   📧 -> {to}: {subject}")


def build_app(env: str) -> SignupService:
    """The ONLY place where concrete classes meet the service."""
    if env == "test":
        return SignupService(InMemoryUserRepo(), FakeMailer())
    return SignupService(InMemoryUserRepo(), LoudMailer())


test_app = build_app("test")
prod_app = build_app("prod")
prod_app.signup("bob", "bob@example.com")
print("   same service class, two wirings — zero edits to SignupService ✔")
assert isinstance(test_app._mailer, FakeMailer)
assert isinstance(prod_app._mailer, LoudMailer)

# ============================================================================
# 3. Testing with fakes: behavior, not choreography
# ============================================================================
print()
print("=" * 70)
print("3. Fakes make tests declarative")
print("=" * 70)


def test_signup_sends_welcome():
    mailer = FakeMailer()
    svc = SignupService(InMemoryUserRepo(), mailer)
    svc.signup("carol", "carol@example.com")
    assert mailer.outbox == [("carol@example.com", "Welcome!")]


def test_duplicate_signup_rejected():
    svc = SignupService(InMemoryUserRepo(), FakeMailer())
    svc.signup("dave", "d@example.com")
    try:
        svc.signup("dave", "d@example.com")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


test_signup_sends_welcome()
test_duplicate_signup_rejected()
print("   two tests ran with zero patching, zero mock objects ✔")

# ============================================================================
# 4. Factory injection: when a dependency is needed per-call
# ============================================================================
print()
print("=" * 70)
print("4. Injecting a factory instead of an instance")
print("=" * 70)


class Connection:
    _counter = 0

    def __init__(self):
        Connection._counter += 1
        self.conn_id = Connection._counter

    def execute(self, sql):
        return f"conn#{self.conn_id}: {sql}"


class ReportJob:
    """Needs a FRESH connection per run — so inject the recipe, not the meal."""

    def __init__(self, connect: Callable[[], Connection]):
        self._connect = connect

    def run(self):
        conn = self._connect()
        return conn.execute("SELECT 1")


job = ReportJob(Connection)                       # a class IS a factory callable
print(f"   run 1: {job.run()}")
print(f"   run 2: {job.run()}   <-- new connection each run")
assert job.run().startswith("conn#3")

# ============================================================================
# 5. A minimal DI container
# ============================================================================
print()
print("=" * 70)
print("5. A 30-line container: type-hint driven auto-wiring")
print("=" * 70)


class Container:
    def __init__(self):
        self._providers: dict[type, Callable[[], object]] = {}
        self._singletons: dict[type, object] = {}
        self._singleton_keys: set[type] = set()

    def register(self, key: type, provider: type | Callable[[], object],
                 *, singleton: bool = False):
        self._providers[key] = provider
        if singleton:
            self._singleton_keys.add(key)

    def resolve(self, key: type):
        if key in self._singletons:
            return self._singletons[key]
        provider = self._providers.get(key, key)   # unregistered concrete: build it
        instance = (self._build(provider) if isinstance(provider, type)
                    else provider())
        if key in self._singleton_keys:
            self._singletons[key] = instance
        return instance

    def _build(self, cls: type):
        """Read __init__ type hints; recursively resolve each parameter."""
        hints = typing.get_type_hints(cls.__init__) if cls.__init__ is not object.__init__ else {}
        hints.pop("return", None)
        deps = {name: self.resolve(dep) for name, dep in hints.items()}
        return cls(**deps)


c = Container()
c.register(UserRepo, InMemoryUserRepo, singleton=True)   # shared repo
c.register(Mailer, FakeMailer)                            # fresh per resolve

service = c.resolve(SignupService)      # container read the constructor hints,
service.signup("erin", "e@example.com")  # built repo + mailer, injected both
print(f"   container-built service works: {service._repo.get('erin')}")

service2 = c.resolve(SignupService)
print(f"   repo shared (singleton): {service._repo is service2._repo}")
print(f"   mailer fresh (transient): {service._mailer is not service2._mailer}")
assert service._repo is service2._repo
assert service._mailer is not service2._mailer

print()
print("All Module 9 assertions passed ✔")
