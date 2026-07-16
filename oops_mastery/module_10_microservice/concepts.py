"""
Module 10: Microservice Architecture — Concepts in Action
=========================================================
Run: python3 concepts.py

A complete four-layer "orders" service in one file. In a real repo each
section would be its own package (domain/, repos/, services/, api/) — the
capstone does exactly that. Read top-to-bottom: the import rule (inward only)
holds section by section.
"""
from dataclasses import dataclass, field
from typing import Callable, Protocol

# ============================================================================
# LAYER 1 — DOMAIN: entities, value objects, domain errors (imports: stdlib)
# ============================================================================


class DomainError(Exception):
    """Root of the domain exception hierarchy."""


class NotFound(DomainError):
    pass


class DuplicateId(DomainError):
    pass


@dataclass(frozen=True)
class Money:
    """Value object: immutable, equality by value, invariant inside."""

    amount: int                     # integer cents — never float for money
    currency: str = "USD"

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("amount cannot be negative")

    def __add__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        if other.currency != self.currency:
            raise ValueError("currency mismatch")
        return Money(self.amount + other.amount, self.currency)

    def __str__(self):
        return f"{self.amount / 100:.2f} {self.currency}"


@dataclass(frozen=True)
class OrderLine:
    sku: str
    unit_price: Money
    quantity: int

    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")

    @property
    def line_total(self) -> Money:
        return Money(self.unit_price.amount * self.quantity,
                     self.unit_price.currency)


class Order:
    """Entity: identity (order_id), state transitions, invariants."""

    def __init__(self, order_id: str, customer: str):
        self.order_id = order_id
        self.customer = customer
        self._lines: list[OrderLine] = []
        self.status = "open"

    @classmethod
    def create(cls, order_id, customer,
               lines: list[tuple[str, int, int]]) -> "Order":
        """Factory (Module 1): builds a valid order or raises."""
        order = cls(order_id, customer)
        for sku, price_cents, qty in lines:
            order.add_line(sku, price_cents, qty)
        return order

    def add_line(self, sku: str, price_cents: int, qty: int):
        if self.status != "open":
            raise DomainError(f"cannot modify a {self.status} order")
        self._lines.append(OrderLine(sku, Money(price_cents), qty))

    @property
    def total(self) -> Money:
        """The DOMAIN does the math — not the service layer."""
        total = Money(0)
        for line in self._lines:
            total = total + line.line_total
        return total

    @property
    def lines(self) -> tuple[OrderLine, ...]:
        return tuple(self._lines)          # no live internals leak out

    def submit(self):
        if not self._lines:
            raise DomainError("cannot submit an empty order")
        self.status = "submitted"

    def __eq__(self, other):               # entity: equality by IDENTITY
        if not isinstance(other, Order):
            return NotImplemented
        return self.order_id == other.order_id

    def __hash__(self):
        return hash(self.order_id)

    def __repr__(self):
        return (f"Order({self.order_id!r}, customer={self.customer!r}, "
                f"lines={len(self._lines)}, status={self.status!r})")


# ============================================================================
# LAYER 2 — REPOSITORY: persistence behind a Protocol (imports: domain)
# ============================================================================


class OrderRepo(Protocol):
    def add(self, order: Order) -> None: ...
    def get(self, order_id: str) -> Order: ...
    def list_all(self) -> list[Order]: ...


class InMemoryOrderRepo:
    """Prod-shaped fake: same contract as any future SQL implementation."""

    def __init__(self):
        self._orders: dict[str, Order] = {}

    def add(self, order: Order) -> None:
        if order.order_id in self._orders:
            raise DuplicateId(f"order {order.order_id!r} already exists")
        self._orders[order.order_id] = order

    def get(self, order_id: str) -> Order:
        try:
            return self._orders[order_id]
        except KeyError:
            raise NotFound(f"order {order_id!r} not found") from None

    def list_all(self) -> list[Order]:
        return list(self._orders.values())


# ============================================================================
# LAYER 3 — SERVICE: use cases over injected seams (imports: domain, protocols)
# ============================================================================


class IdGenerator(Protocol):
    def next_id(self) -> str: ...


class SequentialIds:
    def __init__(self, prefix="ord"):
        self._prefix, self._n = prefix, 0

    def next_id(self) -> str:
        self._n += 1
        return f"{self._prefix}-{self._n:04d}"


class EventEmitter:
    """Module 8's observer, reused as the service's outbound signal."""

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}

    def subscribe(self, event, handler):
        self._handlers.setdefault(event, []).append(handler)

    def emit(self, event, payload):
        for h in self._handlers.get(event, []):
            h(payload)


class OrderService:
    """Orchestration only. The domain calculated; the repo persisted;
    the emitter notified. Nothing here knows about HTTP or storage."""

    def __init__(self, repo: OrderRepo, ids: IdGenerator, events: EventEmitter):
        self._repo = repo
        self._ids = ids
        self._events = events

    def place_order(self, customer: str,
                    lines: list[tuple[str, int, int]]) -> Order:
        order = Order.create(self._ids.next_id(), customer, lines)
        order.submit()
        self._repo.add(order)
        self._events.emit("order.placed", order.order_id)
        return order

    def get_order(self, order_id: str) -> Order:
        return self._repo.get(order_id)

    def revenue_cents(self) -> int:
        return sum(o.total.amount for o in self._repo.list_all())


# ============================================================================
# LAYER 4 — API: routing, DTOs, status codes (imports: service)
# ============================================================================


@dataclass
class Response:
    status: int
    body: dict


class Router:
    """Maps (method, path) -> handler; owns exception -> status translation.
    This is the ONLY layer that knows what a 404 is."""

    def __init__(self):
        self._routes: dict[tuple[str, str], Callable] = {}

    def route(self, method: str, path: str):
        def deco(handler):                  # Module 7: registration decorator
            self._routes[(method, path)] = handler
            return handler
        return deco

    def handle(self, method: str, path: str, body: dict | None = None) -> Response:
        handler = self._routes.get((method, path))
        if handler is None:
            return Response(404, {"error": f"no route {method} {path}"})
        try:
            return handler(body or {})
        except NotFound as e:
            return Response(404, {"error": str(e)})
        except (ValueError, DomainError) as e:
            return Response(400, {"error": str(e)})


def order_to_dto(order: Order) -> dict:
    """DTO mapping lives HERE — entities never grow wire formats."""
    return {
        "id": order.order_id,
        "customer": order.customer,
        "status": order.status,
        "total": str(order.total),
        "lines": [{"sku": l.sku, "qty": l.quantity} for l in order.lines],
    }


def build_api(service: OrderService) -> Router:
    router = Router()

    @router.route("POST", "/orders")
    def create_order(body: dict) -> Response:
        order = service.place_order(
            customer=body["customer"],
            lines=[(l["sku"], l["price_cents"], l["qty"])
                   for l in body["lines"]],
        )
        return Response(201, order_to_dto(order))

    @router.route("GET", "/orders")
    def get_order(body: dict) -> Response:
        return Response(200, order_to_dto(service.get_order(body["id"])))

    return router


# ============================================================================
# COMPOSITION ROOT — the one place everything is wired (Module 9)
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("Wiring the service and driving it through the API layer")
    print("=" * 70)

    events = EventEmitter()
    audit_log: list[str] = []
    events.subscribe("order.placed", lambda oid: audit_log.append(oid))

    service = OrderService(InMemoryOrderRepo(), SequentialIds(), events)
    api = build_api(service)

    # --- a valid order -------------------------------------------------
    resp = api.handle("POST", "/orders", {
        "customer": "ada",
        "lines": [{"sku": "kbd", "price_cents": 4999, "qty": 2},
                  {"sku": "mouse", "price_cents": 1550, "qty": 1}],
    })
    print(f"POST /orders -> {resp.status} {resp.body}")
    assert resp.status == 201
    assert resp.body["total"] == "115.48 USD"          # domain did the math
    assert audit_log == ["ord-0001"]                    # observer fired

    # --- fetch it back ---------------------------------------------------
    resp = api.handle("GET", "/orders", {"id": "ord-0001"})
    print(f"GET  /orders id=ord-0001 -> {resp.status}, status={resp.body['status']}")
    assert resp.status == 200 and resp.body["status"] == "submitted"

    # --- domain errors become 4xx at the boundary, nowhere else -----------
    resp = api.handle("GET", "/orders", {"id": "ghost"})
    print(f"GET  /orders id=ghost -> {resp.status} {resp.body}")
    assert resp.status == 404

    resp = api.handle("POST", "/orders", {"customer": "bob", "lines": []})
    print(f"POST /orders (empty) -> {resp.status} {resp.body}")
    assert resp.status == 400                           # DomainError mapped

    resp = api.handle("POST", "/orders", {
        "customer": "bob",
        "lines": [{"sku": "x", "price_cents": 100, "qty": -1}],
    })
    print(f"POST /orders (qty=-1) -> {resp.status} {resp.body}")
    assert resp.status == 400                           # value-object invariant

    resp = api.handle("DELETE", "/orders")
    assert resp.status == 404                           # unknown route

    # --- the service layer is independently testable ----------------------
    assert service.revenue_cents() == 11548
    print(f"revenue: {service.revenue_cents()} cents")

    # --- swap the repo, touch nothing else (the DIP payoff) ----------------
    class CountingRepo(InMemoryOrderRepo):
        adds = 0

        def add(self, order):
            CountingRepo.adds += 1
            super().add(order)

    alt = OrderService(CountingRepo(), SequentialIds("alt"), EventEmitter())
    alt.place_order("erin", [("cable", 900, 1)])
    assert CountingRepo.adds == 1
    print("swapped repo implementation with zero service edits ✔")

    print()
    print("All Module 10 assertions passed ✔")
