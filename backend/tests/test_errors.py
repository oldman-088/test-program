"""اختبارات قالب الخطأ الموحّد — ``backend/tests/test_errors.py`` · البند 21.

الأسلوب: تطبيق probe صغير يُبنى فوق ``create_app`` نفسه (نفس معالجات الاستثناء ونفس
وسيط ``X-Request-ID``) وتُضاف إليه مسارات تثير كل نوع خطأ — فتُقاس الاستجابة كما يراها
العميل، لا كما يصفها الكود. مسارات الـ probe خارج ``/api/v1`` عمداً، فلا تمسّ اختبار العقد.

* حالة النجاح الموثّقة: ``GET /api/v1/health`` ⇒ ``200`` بلا جسم خطأ وبلا ``X-Error-Code``.
* حالات الفشل الموثّقة: ``401/403/404/405/409/413/418/422/500/502/503`` — كلها بنفس البنية؛
  و``500`` لا تسرّب نصّ الاستثناء لكنها تسجّله؛ وأخطاء تحقّق Pydantic تحمل ``details``
  بأربعة مفاتيح عقدية (``field/loc/message/type``).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import Settings
from app.core.database import Database, DatabaseUnavailableError
from app.core.errors import (
    ENVELOPE_FIELDS,
    ERROR_REGISTRY,
    HTTP_STATUS_TO_CODE,
    APIError,
    AuthenticationError,
    ConfigurationError,
    ConflictError,
    DatabaseError,
    NotFoundError,
    PermissionDeniedError,
    UpstreamError,
    ValidationError_,
    error_envelope,
)
from app.main import create_app
from app.schemas import SessionCreate
from conftest import make_settings

#: ``المسار → (حالة HTTP، الرمز المتوقع)`` لكل نوع خطأ.
PROBE_EXPECTATIONS: dict[str, tuple[int, str]] = {
    "/_probe/not-found": (404, "not_found"),
    "/_probe/validation": (422, "validation_error"),
    "/_probe/pydantic": (422, "validation_error"),
    "/_probe/unauthenticated": (401, "unauthenticated"),
    "/_probe/forbidden": (403, "permission_denied"),
    "/_probe/conflict": (409, "conflict"),
    "/_probe/configuration": (500, "configuration_error"),
    "/_probe/upstream": (502, "upstream_unavailable"),
    "/_probe/database": (503, "database_unavailable"),
    "/_probe/db-driver": (503, "database_unavailable"),
    "/_probe/payload": (413, "payload_too_large"),
    "/_probe/teapot": (418, "http_418"),
    "/_probe/unexpected": (500, "internal_error"),
}


def _attach_probe_routes(app: FastAPI) -> None:
    """يضيف مسارات تثير كل نوع خطأ. كل دالة صريحة: لا تكرار ولا سحر."""

    async def not_found() -> None:
        raise NotFoundError("الجلسة ses_missing غير موجودة.")

    async def validation() -> None:
        raise ValidationError_(
            "تحقق واحد على الأقل فشل (1).",
            details=[
                {
                    "field": "body.branch",
                    "loc": ["body", "branch"],
                    "message": "must not be blank",
                    "type": "value_error",
                }
            ],
        )

    async def pydantic_directly() -> None:
        # تحقّق Pydantic خارج مسار FastAPI (بناء مخطّط داخل خدمة) — نفس القالب.
        SessionCreate.model_validate({"task_id": "tiny", "employee_id": "", "branch": "b"})
        raise AssertionError("التحقّق كان يجب أن يفشل قبل هذا السطر")  # pragma: no cover

    async def unauthenticated() -> None:
        raise AuthenticationError()

    async def forbidden() -> None:
        raise PermissionDeniedError()

    async def conflict() -> None:
        raise ConflictError()

    async def configuration() -> None:
        raise ConfigurationError()

    async def upstream() -> None:
        raise UpstreamError()

    async def database() -> None:
        raise DatabaseError()

    async def db_driver_failure() -> None:
        raise DatabaseUnavailableError("connection refused")

    async def payload_too_large() -> None:
        raise HTTPException(status_code=413, detail="payload exceeds 8 MiB")

    async def teapot() -> None:
        raise StarletteHTTPException(status_code=418, detail="no brew")

    async def unexpected() -> None:
        raise RuntimeError("secret-internal-detail: password=hunter2")

    handlers: dict[str, object] = {
        "/_probe/not-found": not_found,
        "/_probe/validation": validation,
        "/_probe/pydantic": pydantic_directly,
        "/_probe/unauthenticated": unauthenticated,
        "/_probe/forbidden": forbidden,
        "/_probe/conflict": conflict,
        "/_probe/configuration": configuration,
        "/_probe/upstream": upstream,
        "/_probe/database": database,
        "/_probe/db-driver": db_driver_failure,
        "/_probe/payload": payload_too_large,
        "/_probe/teapot": teapot,
        "/_probe/unexpected": unexpected,
    }
    assert set(handlers) == set(PROBE_EXPECTATIONS), "كل مسار probe يحتاج توقعاً موثقاً"
    for path, handler in handlers.items():
        app.add_api_route(path, handler, methods=["GET"])


@pytest.fixture
def probe_app(settings: Settings, database: Database) -> FastAPI:
    app = create_app(settings, database=database)
    _attach_probe_routes(app)
    return app


@pytest.fixture
def probe_client(probe_app: FastAPI) -> Iterator[TestClient]:
    # raise_server_exceptions=False: نريد قياس استجابة 500 كما تُخدَم فعلاً للعميل.
    with TestClient(probe_app, raise_server_exceptions=False) as client:
        yield client


def assert_error_envelope(payload: object, *, code: str) -> dict[str, object]:
    """فحص العقد: الجذر ``error`` وأربعة مفاتيح داخلية، لا شيء آخر."""
    assert isinstance(payload, dict), f"جسم الخطأ يجب أن يكون كائناً JSON: {payload!r}"
    assert set(payload) == {"error"}, f"مفاتيح الجذر يجب أن تكون ['error'] فقط: {sorted(payload)}"
    error = payload["error"]
    assert isinstance(error, dict)
    assert set(error) == set(ENVELOPE_FIELDS), f"مفاتيح error انحرفت: {sorted(error)}"
    assert error["code"] == code
    assert isinstance(error["message"], str) and error["message"]
    assert isinstance(error["details"], list)
    assert error["request_id"] is None or isinstance(error["request_id"], str)
    return error


# ─────────────────────────── حالة النجاح ───────────────────────────


def test_success_response_carries_no_error_body(client: TestClient) -> None:
    """حالة نجاح موثّقة: 200 نظيفة، ولا ``X-Error-Code`` — القالب لا يتسرّب للنجاح."""
    response = client.get("/api/v1/health", headers={"X-Request-ID": "ok-0001"})

    assert response.status_code == 200
    assert "error" not in response.json()
    assert response.json()["status"] == "ok"
    assert "x-error-code" not in {key.lower() for key in response.headers}
    assert response.headers["x-request-id"] == "ok-0001"


# ─────────────────── بنية القالب نفسها ───────────────────


def test_envelope_builder_is_the_single_source_of_shape() -> None:
    """البنية من ``error_envelope`` وحده: مفاتيح ثابتة، و``details`` قائمة دائماً."""
    minimal = error_envelope("not_found", "لا شيء")
    assert set(minimal) == {"error"}
    assert set(minimal["error"]) == set(ENVELOPE_FIELDS)
    assert minimal["error"]["details"] == []
    assert minimal["error"]["request_id"] is None

    full = error_envelope(
        "conflict",
        "تعارض",
        details=[{"field": "task_id", "loc": ["body", "task_id"], "message": "dup", "type": "x"}],
        request_id="abc",
    )
    assert full["error"]["request_id"] == "abc"
    assert full["error"]["details"][0]["field"] == "task_id"
    assert ENVELOPE_FIELDS == ("code", "message", "details", "request_id")


@pytest.mark.parametrize("error_class", list(ERROR_REGISTRY.values()), ids=lambda c: c.__name__)
def test_every_registered_error_renders_the_same_template(error_class: type[APIError]) -> None:
    """كل نوع مسجّل يحمل كوده وحالته، ويُخرج القالب نفسه من ``to_envelope``."""
    exc = error_class("رسالة اختبارية", details=[{"field": "f"}])

    assert isinstance(exc, APIError)
    assert 400 <= exc.status_code < 600
    assert exc.code in ERROR_REGISTRY
    assert_error_envelope(exc.to_envelope("rid-1"), code=exc.code)
    assert exc.details == [{"field": "f"}]

    without_message = error_class()
    assert without_message.message == error_class.default_detail
    assert without_message.details == []


# ─────── قياس الاستجابات عبر HTTP: كل نوع خطأ بنفس القالب ───────


@pytest.mark.parametrize("path,expectation", sorted(PROBE_EXPECTATIONS.items()))
def test_error_template_is_identical_for_every_error_type(
    probe_client: TestClient, path: str, expectation: tuple[int, str]
) -> None:
    """حالات الفشل الموثّقة: الحالة والرمز والبنية — لكل نوع خطأ بلا استثناء."""
    status_code, code = expectation
    response = probe_client.get(path)

    assert response.status_code == status_code, response.text
    error = assert_error_envelope(response.json(), code=code)
    assert response.headers["x-error-code"] == code
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["x-request-id"] == error["request_id"]


def test_unhandled_exception_is_logged_but_never_leaked(
    probe_client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    """فشل موثّق: 500 برسالة عامة، والتفاصيل الداخلية في السجلّ فقط (القاعدة 5)."""
    with caplog.at_level("ERROR", logger="app.errors"):
        response = probe_client.get("/_probe/unexpected")

    assert response.status_code == 500
    assert_error_envelope(response.json(), code="internal_error")
    body = response.text
    assert "hunter2" not in body and "RuntimeError" not in body
    assert "secret-internal-detail" in caplog.text
    assert "/_probe/unexpected" in caplog.text


def test_pydantic_validation_outside_fastapi_uses_same_template(probe_client: TestClient) -> None:
    """فشل موثّق: ``ValidationError`` من Pydantic مباشرة ⇒ 422 بنفس القالب."""
    response = probe_client.get("/_probe/pydantic")

    assert response.status_code == 422
    error = assert_error_envelope(response.json(), code="validation_error")
    assert {item["field"] for item in error["details"]} == {"task_id", "employee_id"}


# ─────────────── تحققات Pydantic عبر العقد العام ───────────────


def test_request_validation_details_have_documented_keys(
    client: TestClient, auth_headers: dict[str, str], invalid_session_payload: dict[str, object]
) -> None:
    """فشل موثّق عبر HTTP: ثلاثة أخطاء تحقّق، لكل منها المفاتيح الثابتة الأربعة."""
    response = client.post("/api/v1/sessions", json=invalid_session_payload, headers=auth_headers)

    assert response.status_code == 422
    error = assert_error_envelope(response.json(), code="validation_error")
    details = error["details"]
    assert len(details) == 3, details
    for item in details:
        assert set(item) == {"field", "loc", "message", "type"}
        assert isinstance(item["loc"], list) and item["loc"]
        assert item["loc"][0] in {"body", "query", "path"}

    by_field = {item["field"]: item["type"] for item in details}
    assert by_field["task_id"] == "string_too_short"
    assert by_field["employee_id"] == "value_error"
    assert by_field["unexpected"] == "extra_forbidden"


def test_query_parameter_validation_uses_the_same_template(client: TestClient, auth_headers: dict[str, str]) -> None:
    """فشل موثّق: بارامتر استعلام خارج المدى ⇒ نفس القالب و``loc`` يبدأ بـ``query``."""
    response = client.get(
        "/api/v1/sessions", params={"employee_id": "worker-7", "limit": 500}, headers=auth_headers
    )

    assert response.status_code == 422
    error = assert_error_envelope(response.json(), code="validation_error")
    detail = error["details"][0]
    assert detail["loc"] == ["query", "limit"]
    assert detail["type"] == "less_than_equal"


def test_missing_required_query_parameter_is_422(client: TestClient, auth_headers: dict[str, str]) -> None:
    """فشل موثّق: ``employee_id`` مفقود ⇒ ``missing`` في التفاصيل، لا 500."""
    response = client.get("/api/v1/sessions", headers=auth_headers)

    assert response.status_code == 422
    detail = assert_error_envelope(response.json(), code="validation_error")["details"][0]
    assert detail["type"] == "missing"
    assert detail["loc"] == ["query", "employee_id"]


def test_unparseable_json_body_is_422_not_500(client: TestClient, auth_headers: dict[str, str]) -> None:
    """فشل موثّق: جسم ليس JSON ⇒ 422 بالقالب نفسه، لا صفحة HTML ولا 500."""
    response = client.post(
        "/api/v1/sessions", content="{not json", headers={**auth_headers, "Content-Type": "application/json"}
    )

    assert response.status_code == 422
    assert_error_envelope(response.json(), code="validation_error")


# ─────────────── أخطاء المسار والصلاحية من الموجّهات ───────────────


def test_unknown_api_path_is_404_with_the_same_template(client: TestClient) -> None:
    """مسار غير معروف تحت البادئة ⇒ 404 من معالج Starlette بنفس القالب."""
    response = client.get("/api/v1/nope")

    assert response.status_code == 404
    assert_error_envelope(response.json(), code="not_found")


def test_wrong_method_on_known_path_is_405(client: TestClient, auth_headers: dict[str, str]) -> None:
    """فشل موثّق: طريقة غير معرّفة على مسار موجود ⇒ 405 ``method_not_allowed``."""
    response = client.put("/api/v1/health", headers=auth_headers)

    assert response.status_code == 405
    assert_error_envelope(response.json(), code="method_not_allowed")


def test_wrong_api_key_is_401_and_returns_no_data(client: TestClient) -> None:
    """مفتاح خاطئ لا يُرجع بيانات: 401 ``unauthenticated`` لا ``detail`` العاري."""
    response = client.get("/api/v1/sessions", params={"employee_id": "w"}, headers={"X-API-Key": "wrong-key"})

    assert response.status_code == 401
    assert_error_envelope(response.json(), code="unauthenticated")
    assert "detail" not in response.json()


def test_missing_server_api_key_fails_closed(tmp_path: Path) -> None:
    """فشل موثّق (Q5 + قاعدة الأسرار): خادم بلا ``API_KEY`` يرفض العمل ولا يفتح البيانات."""
    settings = make_settings(api_key="", database_url=f"sqlite:///{tmp_path / 'no-key.db'}")
    database = Database(settings.database_url)
    database.create_all()
    try:
        with TestClient(create_app(settings, database=database), raise_server_exceptions=False) as test_client:
            allowed = test_client.get("/api/v1/health")
            refused = test_client.post(
                "/api/v1/sessions",
                json={"task_id": "task-00000001", "employee_id": "w", "branch": "b"},
                headers={"X-API-Key": "whatever"},
            )
    finally:
        database.dispose()

    assert allowed.status_code == 200, "الصحة تبقى عامة حتى مع سوء الضبط"
    assert refused.status_code == 500
    assert_error_envelope(refused.json(), code="configuration_error")


# ─────────────── معرّف الطلب وترميز الجسم ───────────────


def test_request_id_is_shared_between_header_and_body(probe_client: TestClient) -> None:
    """نفس المعرّف في الترويسة والجسم — وإلا يستحيل ربط خطأ العميل بالسجلّات."""
    response = probe_client.get("/_probe/not-found", headers={"X-Request-ID": "req-42"})

    assert response.headers["x-request-id"] == "req-42"
    assert assert_error_envelope(response.json(), code="not_found")["request_id"] == "req-42"


def test_generated_request_id_when_client_sends_none(client: TestClient) -> None:
    """لا طلب بلا معرّف: يُولَّد معرّف من 32 حرفاً ويُعاد في الترويسة."""
    response = client.get("/api/v1/health")
    echoed = response.headers["x-request-id"]

    assert len(echoed) == 32
    assert all(ch in "0123456789abcdef" for ch in echoed)


@pytest.mark.parametrize("evil", ["a b", "x\r\nInjected: 1", "a" * 200])
def test_client_supplied_request_id_is_sanitised(client: TestClient, evil: str) -> None:
    """معرّف غير سليم (فراغ/سطر جديد/طول زائد) يُستبدل — لا حقن ترويسة."""
    response = client.get("/api/v1/health", headers={"X-Request-ID": evil})

    assert response.status_code == 200
    echoed = response.headers["x-request-id"]
    assert echoed != evil
    assert "\n" not in echoed and " " not in echoed and len(echoed) <= 64


def test_error_body_is_utf8_json(client: TestClient) -> None:
    """الرسائل العربية تصل صحيحة: JSON صالح بترميز UTF-8، لا مزدوج ولا repr."""
    response = client.delete("/api/v1/sessions/ses_nope", headers={"X-API-Key": "wrong"})

    payload = json.loads(response.content.decode("utf-8"))
    assert payload["error"]["code"] == "unauthenticated"
    assert json.dumps(payload, ensure_ascii=False)
    assert response.headers["content-type"].startswith("application/json")


# ─────────────── خريطة الحالات ↔ الأكواد ───────────────


@pytest.mark.parametrize("status_code", sorted(HTTP_STATUS_TO_CODE))
def test_http_status_map_returns_the_documented_code(status_code: int) -> None:
    """كل حالة موثّقة في docs/API.md §3 لها رمز ثابت، والرموز ليست ``api_error`` العامة."""
    code = HTTP_STATUS_TO_CODE[status_code]
    assert code != "api_error"
    assert code.replace("_", "").isalnum()
    assert 400 <= status_code < 600


def test_unmapped_http_status_falls_back_to_a_stable_code(probe_client: TestClient) -> None:
    """حالة غير مرسومة (418) ⇒ رمز احتياطي ``http_418`` لا انهيار المعالج."""
    assert 418 not in HTTP_STATUS_TO_CODE
    response = probe_client.get("/_probe/teapot")

    assert response.status_code == 418
    assert_error_envelope(response.json(), code="http_418")
