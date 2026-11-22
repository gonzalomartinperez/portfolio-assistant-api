"""RFC 9457 problem documents for every public HTTP error (contract v1.1, additive).

The v1 members `code`, `message` and `request_id` stay; RFC 9457 members (`type`, `title`, `status`,
`detail`, `instance`) and the extension members `retryable`, `retry_after_s` and `messages` are
added. Codes form a closed vocabulary: anything outside the catalog is reported as a known code, so
no framework or provider text can reach a response body.
"""

from dataclasses import dataclass
from typing import Any, Literal, get_args

from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

PROBLEM_MEDIA_TYPE = "application/problem+json"
TYPE_PREFIX = "urn:portfolio-assistant:error:"

ErrorCode = Literal[
    "invalid_request",
    "malformed_body",
    "invalid_limit",
    "invalid_content_type",
    "invalid_analytics_selection",
    "analytics_credentials_forbidden",
    "request_timeout",
    "session_required",
    "operations_unauthorized",
    "csrf_denied",
    "origin_denied",
    "bootstrap_denied",
    "not_found",
    "analytics_disabled",
    "feedback_overview_disabled",
    "method_not_allowed",
    "run_already_exists",
    "idempotency_conflict",
    "run_in_progress",
    "rate_limited",
    "analytics_rate_limited",
    "conversation_limit",
    "history_limit",
    "busy",
    "knowledge_updating",
    "dependency_unavailable",
    "operations_unconfigured",
    "operations_unavailable",
]


@dataclass(frozen=True, slots=True)
class Problem:
    status: int
    title: str
    en: str
    es: str
    retryable: bool = False
    retry_after_s: int | None = None


# English and neutral Latin American Spanish; never request-specific, never echoes input.
CATALOG: dict[ErrorCode, Problem] = {
    "invalid_request": Problem(
        422,
        "Invalid request",
        "The request is not valid. Check the fields and try again.",
        "La solicitud no es válida. Revisa los campos e inténtalo de nuevo.",
    ),
    "malformed_body": Problem(
        400,
        "Malformed request body",
        "The request body is not valid JSON.",
        "El cuerpo de la solicitud no es un JSON válido.",
    ),
    "invalid_limit": Problem(
        400,
        "Invalid page size",
        "The page size is outside the allowed range.",
        "El tamaño de página está fuera del rango permitido.",
    ),
    "invalid_content_type": Problem(
        415,
        "Unsupported content type",
        "Send the request body as application/json.",
        "Envía el cuerpo de la solicitud como application/json.",
    ),
    "invalid_analytics_selection": Problem(
        422,
        "Invalid analytics selection",
        "The selected period or filter is not supported.",
        "El período o el filtro seleccionado no es compatible.",
    ),
    "analytics_credentials_forbidden": Problem(
        400,
        "Credentials not allowed",
        "Analytics events must be sent without credentials.",
        "Los eventos de analítica deben enviarse sin credenciales.",
    ),
    "request_timeout": Problem(
        408,
        "Request timed out",
        "The request body took too long to arrive. Try again.",
        "El cuerpo de la solicitud tardó demasiado en llegar. Inténtalo de nuevo.",
        retryable=True,
    ),
    "session_required": Problem(
        401,
        "Session required",
        "Your session is missing or expired. Start a new session.",
        "Tu sesión no existe o venció. Inicia una sesión nueva.",
    ),
    "operations_unauthorized": Problem(
        401,
        "Unauthorized",
        "Valid operator credentials are required.",
        "Se requieren credenciales de operador válidas.",
    ),
    "csrf_denied": Problem(
        403,
        "CSRF check failed",
        "The request token is missing or invalid. Reload and try again.",
        "El token de la solicitud falta o no es válido. Recarga e inténtalo de nuevo.",
    ),
    "origin_denied": Problem(
        403,
        "Origin denied",
        "Requests from this origin are not allowed.",
        "No se permiten solicitudes desde este origen.",
    ),
    "bootstrap_denied": Problem(
        403,
        "Session bootstrap denied",
        "The session request is missing its required headers.",
        "A la solicitud de sesión le faltan los encabezados requeridos.",
    ),
    "not_found": Problem(
        404,
        "Not found",
        "The requested resource does not exist or is not yours.",
        "El recurso solicitado no existe o no te pertenece.",
    ),
    "analytics_disabled": Problem(
        404,
        "Analytics disabled",
        "Product analytics is turned off on this server.",
        "La analítica de producto está desactivada en este servidor.",
    ),
    "feedback_overview_disabled": Problem(
        404,
        "Feedback overview disabled",
        "The feedback overview is turned off on this server.",
        "El resumen de comentarios está desactivado en este servidor.",
    ),
    "method_not_allowed": Problem(
        405,
        "Method not allowed",
        "This method is not supported for this resource.",
        "Este método no es compatible con este recurso.",
    ),
    "run_already_exists": Problem(
        409,
        "Run already exists",
        "A run with this idempotency key already exists. Read its state instead.",
        "Ya existe una ejecución con esta clave de idempotencia. Consulta su estado.",
    ),
    "idempotency_conflict": Problem(
        409,
        "Idempotency conflict",
        "This idempotency key was already used with a different message.",
        "Esta clave de idempotencia ya se usó con un mensaje distinto.",
    ),
    "run_in_progress": Problem(
        409,
        "Run in progress",
        "This conversation already has an answer in progress.",
        "Esta conversación ya tiene una respuesta en curso.",
        retryable=True,
        retry_after_s=5,
    ),
    "rate_limited": Problem(
        429,
        "Too many requests",
        "You reached the hourly limit. Try again later.",
        "Alcanzaste el límite por hora. Inténtalo más tarde.",
        retryable=True,
        retry_after_s=3600,
    ),
    "analytics_rate_limited": Problem(
        429,
        "Too many analytics events",
        "Too many analytics events were sent. Try again later.",
        "Se enviaron demasiados eventos de analítica. Inténtalo más tarde.",
        retryable=True,
        retry_after_s=60,
    ),
    "conversation_limit": Problem(
        429,
        "Conversation limit reached",
        "You reached the maximum number of conversations. Delete one to continue.",
        "Alcanzaste el máximo de conversaciones. Elimina una para continuar.",
    ),
    "history_limit": Problem(
        429,
        "Conversation is full",
        "This conversation reached its message limit. Start a new conversation.",
        "Esta conversación alcanzó su límite de mensajes. Inicia una conversación nueva.",
    ),
    "busy": Problem(
        429,
        "Assistant busy",
        "The assistant is answering other questions. Try again in a few seconds.",
        "El asistente está respondiendo otras preguntas. Inténtalo de nuevo en unos segundos.",
        retryable=True,
        retry_after_s=5,
    ),
    "knowledge_updating": Problem(
        503,
        "Knowledge updating",
        "The portfolio knowledge is being updated. Try again shortly.",
        "El conocimiento del portafolio se está actualizando. Inténtalo de nuevo en breve.",
        retryable=True,
        retry_after_s=30,
    ),
    "dependency_unavailable": Problem(
        503,
        "Service unavailable",
        "The service is temporarily unavailable. Try again shortly.",
        "El servicio no está disponible por el momento. Inténtalo de nuevo en breve.",
        retryable=True,
    ),
    "operations_unconfigured": Problem(
        503,
        "Operations not configured",
        "The operations interface is not configured on this server.",
        "La interfaz de operaciones no está configurada en este servidor.",
    ),
    "operations_unavailable": Problem(
        503,
        "Operations unavailable",
        "Operational data is temporarily unavailable. Try again shortly.",
        "Los datos operativos no están disponibles por el momento. Inténtalo de nuevo en breve.",
        retryable=True,
    ),
}

# In-stream `run.failed` codes that never travel as HTTP errors. Only `retryable` and the text are
# used; the status is nominal, and `retry_after_s` is not sent in the stream.
STREAM_ONLY: dict[str, Problem] = {
    "generation_failed": Problem(
        502,
        "Answer failed",
        "The answer could not be completed. You can ask again.",
        "No se pudo completar la respuesta. Puedes volver a preguntar.",
        retryable=True,
    ),
    "provider_unavailable": Problem(
        503,
        "Answer service unavailable",
        "The answer service is temporarily unavailable. Try again shortly.",
        "El servicio de respuestas no está disponible por el momento. Inténtalo de nuevo en breve.",
        retryable=True,
    ),
    "budget_exhausted": Problem(
        503,
        "Monthly limit reached",
        "The assistant reached its monthly usage limit. Try again next month.",
        "El asistente alcanzó su límite de uso mensual. Inténtalo de nuevo el próximo mes.",
    ),
}


def stream_failure(code: str) -> dict[str, object]:
    """`retryable` and EN and ES `messages` for a `run.failed` code (contract v1.1, ADR 030).

    `retryable` invites an explicit visitor retry; clients never resubmit a run automatically.
    """
    problem = STREAM_ONLY.get(code) or CATALOG.get(code)  # type: ignore[call-overload]
    if problem is None:  # unlisted: generic text, and no retry invitation (the safe default)
        fallback = STREAM_ONLY["generation_failed"]
        return {"retryable": False, "messages": {"en": fallback.en, "es": fallback.es}}
    return {"retryable": problem.retryable, "messages": {"en": problem.en, "es": problem.es}}


FALLBACK_BY_STATUS: dict[int, ErrorCode] = {
    400: "malformed_body",
    401: "session_required",
    403: "origin_denied",
    404: "not_found",
    405: "method_not_allowed",
    408: "request_timeout",
    415: "invalid_content_type",
    429: "rate_limited",
}


def resolve(code: str, status: int) -> ErrorCode:
    """Map any raised code to the closed vocabulary; unknown text never reaches the body."""
    if code in CATALOG:
        return code
    if status in FALLBACK_BY_STATUS:
        return FALLBACK_BY_STATUS[status]
    return "dependency_unavailable" if status >= 500 else "invalid_request"


class ProblemMessages(BaseModel):
    model_config = ConfigDict(extra="forbid")

    en: str = Field(min_length=1)
    es: str = Field(min_length=1)


class ErrorBody(BaseModel):
    """RFC 9457 problem details plus the v1 error members (`code`, `message`, `request_id`).

    The component keeps its v1 name so generated consumer types stay stable.
    """

    model_config = ConfigDict(
        json_schema_extra=lambda schema, _cls: schema.update(
            # FastAPI drops nulls from OpenAPI examples, so inline ones carry a retry hint;
            # contracts/problem.examples.json has every code, including `retry_after_s: null`.
            examples=[document("busy", "0" * 32), document("knowledge_updating", "0" * 32)]
        )
    )

    type: str = Field(pattern=r"^urn:portfolio-assistant:error:[a-z_]+$")
    title: str
    status: int = Field(ge=400, le=599)
    detail: str
    instance: str = Field(pattern=r"^urn:request:[0-9a-f]{32}$")
    code: ErrorCode
    message: str
    request_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    retryable: bool
    retry_after_s: int | None = Field(ge=1)
    messages: ProblemMessages


def document(code: ErrorCode, request_id: str, status: int | None = None) -> dict[str, object]:
    problem = CATALOG[code]
    return {
        "type": TYPE_PREFIX + code,
        "title": problem.title,
        "status": status or problem.status,
        "detail": problem.en,
        "instance": f"urn:request:{request_id}",
        "code": code,
        "message": problem.en,
        "request_id": request_id,
        "retryable": problem.retryable,
        "retry_after_s": problem.retry_after_s,
        "messages": {"en": problem.en, "es": problem.es},
    }


def headers(code: ErrorCode) -> dict[str, str]:
    after = CATALOG[code].retry_after_s
    return {"Retry-After": str(after)} if after is not None else {}


def media_type(accept: str) -> str:
    """`application/problem+json` when the client asks for it; v1 clients keep `application/json`."""
    return PROBLEM_MEDIA_TYPE if PROBLEM_MEDIA_TYPE in accept.lower() else "application/json"


def response(code: str, status: int, request_id: str, accept: str = "") -> JSONResponse:
    """Render one problem document; the raised status wins, the body never echoes `code` text."""
    resolved = resolve(code, status)
    final = status if 400 <= status <= 599 else CATALOG[resolved].status
    return JSONResponse(
        document(resolved, request_id, final),
        status_code=final,
        headers={**headers(resolved), "Vary": "Accept"},
        media_type=media_type(accept),
    )


def document_problem_media(schema: dict[str, Any]) -> dict[str, Any]:
    """Offer `application/problem+json` on every documented error response (additive).

    The v1 `application/json` entries stay untouched, so the change is an expansion for oasdiff.
    """
    reference = {"$ref": "#/components/schemas/ErrorBody"}
    for operations in schema.get("paths", {}).values():
        for operation in operations.values():
            for status, documented in operation.get("responses", {}).items():
                if status.isdigit() and int(status) >= 400:
                    content = documented.setdefault("content", {})
                    content.setdefault(PROBLEM_MEDIA_TYPE, {"schema": reference})
    return schema


ERROR_CODES: tuple[str, ...] = get_args(ErrorCode)
