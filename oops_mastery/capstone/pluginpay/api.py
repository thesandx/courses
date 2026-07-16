"""API layer (Module 10): routing, DTOs, and the ONLY place status codes
and exception translation exist."""
from dataclasses import dataclass
from typing import Callable

from pluginpay.domain import (DomainError, FraudSuspected, NotFound, Payment,
                              ProviderError)
from pluginpay.service import PaymentService


@dataclass
class Response:
    status: int
    body: dict


class Router:
    def __init__(self):
        self._routes: dict[tuple[str, str], Callable] = {}

    def route(self, method: str, path: str):
        def deco(handler):                     # Module 7: registration decorator
            self._routes[(method, path)] = handler
            return handler
        return deco

    def handle(self, method: str, path: str,
               body: dict | None = None) -> Response:
        handler = self._routes.get((method, path))
        if handler is None:
            return Response(404, {"error": f"no route {method} {path}"})
        try:
            return handler(body or {})
        except NotFound as e:
            return Response(404, {"error": str(e)})
        except FraudSuspected as e:
            return Response(402, {"error": str(e)})
        except ProviderError as e:
            return Response(502, {"error": str(e)})
        except (ValueError, DomainError) as e:
            return Response(400, {"error": str(e)})


def payment_to_dto(payment: Payment) -> dict:
    """Wire format lives here — entities never grow to_json methods."""
    return {
        "id": payment.payment_id,
        "customer": payment.customer,
        "amount": str(payment.amount),
        "provider": payment.provider_name,
        "status": payment.status,
    }


def build_api(service: PaymentService) -> Router:
    router = Router()

    @router.route("POST", "/payments")
    def create_payment(body: dict) -> Response:
        payment = service.charge(
            customer=body["customer"],
            amount_cents=body["amount_cents"],
            currency=body.get("currency", "USD"),
            provider_name=body["provider"],
        )
        return Response(201, payment_to_dto(payment))

    @router.route("GET", "/payments")
    def get_payment(body: dict) -> Response:
        return Response(200, payment_to_dto(service.get_payment(body["id"])))

    @router.route("POST", "/refunds")
    def refund(body: dict) -> Response:
        return Response(200, payment_to_dto(service.refund(body["id"])))

    return router
