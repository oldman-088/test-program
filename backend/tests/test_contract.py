"""اختبار تطابق العقد — ``backend/tests/test_contract.py`` · البند 21.

يقارن ``docs/API.md`` بالتطبيق الفعلي في ``backend/app/api/`` آلياً، في الاتجاهين:

1. أزواج ``(METHOD, path)`` تحت ``/api/v1`` من موجّهات ``app.routes`` **ومن مخطط OpenAPI**.
2. مسارا الصحة موثّقان كما في الكود، وبلا مصادقة (شرط المهمة الصريح).
3. عمود «المصادقة» = سلوك فعلي: صفّ ``yes`` بلا مفتاح ⇒ 401، وصفّ ``no`` ⇒ لا 401 ولا 403.
4. عمود «حالة النجاح» = الحالة التي تُرجعها النقطة فعلاً بطلب مكتمل الشروط.
5. جدول أكواد الخطأ = ``ERROR_REGISTRY ∪ HTTP_STATUS_TO_CODE`` في الاتجاهين.
6. قالب الخطأ (المفاتيح الجذرية + مفاتيح ``error`` + مفاتيح ``details[]``) = المثال الموثّق.
7. قائمة ``status`` في §4 = ``app.models.session.SESSION_STATUSES``.

حالات الفشل الموثّقة (النصف الثاني) تُثبت أن المقارنات تُحمّر فعلاً عند انحراف مسار، أو
تغيّر قالب الخطأ، أو كذب عمود المصادقة، أو حذف جدول — أي أن الاختبار ليس أخضر بالعادة.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api_contract import (
    API_DOC_PATH,
    actual_routes,
    auth_problems,
    contract_document,
    envelope_diff,
    error_code_diff,
    openapi_documented_paths,
    read_api_doc,
    route_diff,
    status_diff,
    success_problems,
)
from app.core.config import Settings
from app.core.database import Database
from app.core.errors import ERROR_REGISTRY, HTTP_STATUS_TO_CODE
from app.main import create_app
from app.models import SESSION_STATUSES

#: البادئة العقدية — يثبّتها ``test_documented_base_path_matches_settings`` على الإعدادات.
PREFIX = "/api/v1"

#: معرّف صالح الشكل لمعوّض ``{session_id}`` في الصفوف التي لا تحتاج سجلاً موجوداً.
PROBE_SESSION_ID = "ses_probe00000000000000"


@pytest.fixture
def document() -> Any:
    """العقد المحلَّل من ``docs/API.md`` كما هي في المستودع."""
    return contract_document(read_api_doc())


@pytest.fixture
def live_app(settings: Settings, database: Database) -> Any:
    return create_app(settings, database=database)


def _documented_pairs(document: Any) -> set[tuple[str, str]]:
    return {(route.method, route.path) for route in document.routes}


def _error_code_map() -> dict[str, int]:
    codes: dict[str, int] = {code: cls.status_code for code, cls in ERROR_REGISTRY.items()}
    codes.update({code: status for status, code in HTTP_STATUS_TO_CODE.items() if code not in codes})
    return codes


# ══════════════════ الاتجاه الأخضر: الوثيقة = الكود ══════════════════


def test_api_doc_exists_and_is_not_empty() -> None:
    """حالة نجاح شرطية: الوثيقة موجودة في ``docs/`` وتحوي الجداول والأمثلة العقدية."""
    text = read_api_doc()
    doc = contract_document(text)

    assert API_DOC_PATH.parts[-2:] == ("docs", "API.md")
    assert len(text) > 500
    assert doc.routes and doc.error_codes and doc.envelope_error_keys and doc.detail_keys


def test_documented_routes_match_the_api_exactly(live_app: Any, document: Any) -> None:
    """الشرط المطلوب: لا مسار موثّق بلا تنفيذ، ولا تنفيذ بلا توثيق."""
    assert route_diff(_documented_pairs(document), actual_routes(live_app, prefix=PREFIX)) == []


def test_openapi_spec_agrees_with_the_documented_table(live_app: Any, document: Any) -> None:
    """مخطط OpenAPI نفسه — يمسك الانحراف لو أُضيف مسار إلى موجّه بلا توثيق."""
    assert route_diff(_documented_pairs(document), openapi_documented_paths(live_app, prefix=PREFIX)) == []


def test_health_paths_are_documented(live_app: Any, document: Any) -> None:
    """شرط المهمة الصريح: مسارا الصحة موثّقان، موجودان، وعامّان بـ 200."""
    documented = _documented_pairs(document)

    assert ("GET", f"{PREFIX}/health") in documented
    assert ("GET", f"{PREFIX}/health/ready") in documented
    actual = actual_routes(live_app, prefix=PREFIX)
    assert ("GET", f"{PREFIX}/health") in actual
    assert ("GET", f"{PREFIX}/health/ready") in actual

    health_rows = [row for row in document.routes if "health" in row.path]
    assert len(health_rows) == 2
    assert [row.requires_auth for row in health_rows] == [False, False]
    assert {row.success_status for row in health_rows} == {200}


def test_documented_auth_column_matches_actual_behaviour(client: TestClient, document: Any) -> None:
    """كل صفّ ``yes`` ⇒ 401 بلا مفتاح، وكل صفّ ``no`` ⇒ لا 401 ولا 403 — بلا استثناءات."""
    assert len(document.routes) >= 6
    assert auth_problems(client, document.routes, samples={"session_id": PROBE_SESSION_ID}) == []


def test_documented_success_status_is_what_the_endpoint_returns(
    client: TestClient,
    document: Any,
    auth_headers: dict[str, str],
    session_payload: dict[str, str],
) -> None:
    """عمود «حالة النجاح» مُنفَّذ على طلب مكتمل: جلسة واحدة، وقراءة ثم حذف لها."""
    created = client.post(f"{PREFIX}/sessions", json=session_payload, headers=auth_headers)
    assert created.status_code == 201, created.text
    session_id = created.json()["id"]

    problems = success_problems(
        client,
        document.routes,
        headers=auth_headers,
        samples={"session_id": session_id},
        # صفّ POST يحتاج مهمة أخرى: تكرار نفس ``task_id`` يُرجع 409 وهو موثّق كسلوك آخر.
        bodies={f"{PREFIX}/sessions": {**session_payload, "task_id": "task-contract-post-01"}},
    )
    assert problems == [], problems

    # المسار المُعرَّف بمعوّض لا يعمل إلا بسجلّ موجود: التوثيق يصف ذلك صراحة.
    missing = client.get(f"{PREFIX}/sessions/{PROBE_SESSION_ID}", headers=auth_headers)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"


def test_documented_error_codes_match_the_registry_in_both_directions(document: Any) -> None:
    """جدول §3 = ``ERROR_REGISTRY ∪ HTTP_STATUS_TO_CODE`` حرفياً (أكواداً وحالات)."""
    assert error_code_diff(document.error_codes, _error_code_map()) == []


def test_documented_error_envelope_matches_every_real_error_body(
    client: TestClient,
    document: Any,
    auth_headers: dict[str, str],
    session_payload: dict[str, str],
) -> None:
    """شرط المهمة الصريح: القالب الموثّق هو ما يُخدَم فعلاً في 401/404/405/409/422."""
    assert client.post(f"{PREFIX}/sessions", json=session_payload, headers=auth_headers).status_code == 201
    error_responses = [
        client.get(f"{PREFIX}/nope"),  # 404 مسار غير معروف
        client.put(f"{PREFIX}/health"),  # 405 طريقة غير معروفة
        client.get(f"{PREFIX}/sessions", headers=auth_headers),  # 422 بارامتر مفقود
        client.post(f"{PREFIX}/sessions", json={"task_id": "x"}, headers=auth_headers),  # 422 جسم
        client.post(f"{PREFIX}/sessions", json=session_payload, headers=auth_headers),  # 409 تعارض
        client.get(f"{PREFIX}/sessions/{PROBE_SESSION_ID}", headers=auth_headers),  # 404 سجلّ غير موجود
        client.get(f"{PREFIX}/sessions/{PROBE_SESSION_ID}"),  # 401 بلا مفتاح
    ]
    assert [response.status_code for response in error_responses] == [404, 405, 422, 422, 409, 404, 401]
    assert all(response.headers["x-error-code"] for response in error_responses)

    assert envelope_diff(document, [response.json() for response in error_responses]) == []
    assert document.envelope_root_keys == ["error"]
    assert document.envelope_error_keys == ["code", "details", "message", "request_id"]
    assert document.detail_keys == ["field", "loc", "message", "type"]


def test_documented_session_statuses_match_the_model(document: Any) -> None:
    """قائمة §4 = ``SESSION_STATUSES`` في الاتجاهين: الحذف والإضافة يكسران العقد."""
    assert status_diff(document.session_statuses, SESSION_STATUSES) == []
    assert len(document.session_statuses) == len(SESSION_STATUSES)


def test_documented_base_path_matches_app_settings(live_app: Any) -> None:
    """البادئة الموثّقة ``/api/v1`` = ``api_v1_prefix`` الفعلي، لا رقم مكتوب في النص."""
    import re

    settings: Settings = live_app.state.settings
    match = re.search(r"البادئة العقدية لكل المسارات\s*\|\s*`([^`]+)`", read_api_doc())

    assert match, "وثيقة العقد يجب أن تنصّ صراحة على البادئة العقدية"
    assert match.group(1) == PREFIX == settings.api_v1_prefix


def test_no_real_network_is_possible_from_the_suite() -> None:
    """حارس ``conftest`` فعّال: اتصال خارج الحلقة المحلية يفشل قبل أن يخرج من الصندوق."""
    import socket

    with pytest.raises(AssertionError, match="شبكة حقيقية"):
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("1.1.1.1", 443))

    with pytest.raises(AssertionError, match="شبكة حقيقية"):
        socket.create_connection(("example.com", 80), timeout=1)

    # إنشاء المأخذ مسموح (تحتاجه أدوات pytest)، والمنفذ المحلي غير محجوب.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        assert sock.getsockname()[1] > 0


# ══════════════ الاتجاه الأحمر: العقد يُحمّر عند الانحراف ══════════════


def test_contract_fails_when_a_route_is_added_without_docs(live_app: Any, document: Any) -> None:
    """حالة فشل موثّقة: مسار جديد في ``backend/app/api`` بلا صفّ في الوثيقة ⇒ فرق غير فارغ."""
    actual = actual_routes(live_app, prefix=PREFIX) | {("GET", f"{PREFIX}/employees")}

    problems = route_diff(_documented_pairs(document), actual)
    assert any(line.endswith("GET /api/v1/employees") for line in problems), problems
    assert all("بلا تنفيذ فعلي" not in line for line in problems), problems


def test_contract_fails_when_a_documented_path_stops_existing(live_app: Any) -> None:
    """حالة فشل موثّقة: تعديل المسار في الوثيقة فقط (``/sessionz``) ⇒ العقد يفشل."""
    mutated = contract_document(read_api_doc().replace("/sessions/{session_id}", "/sessionz/{session_id}"))

    problems = route_diff(_documented_pairs(mutated), actual_routes(live_app, prefix=PREFIX))
    assert any("موثّق في docs/API.md بلا تنفيذ فعلي" in line for line in problems), problems
    assert any("/api/v1/sessionz/{session_id}" in line for line in problems), problems


def test_contract_fails_when_a_method_column_is_edited(document: Any, live_app: Any) -> None:
    """حالة فشل موثّقة: ``DELETE`` موثّق ``PUT`` على نفس المسار ⇒ لا مطابقة رغم صحة المسار."""
    swapped = read_api_doc().replace(
        "| `DELETE` | `/api/v1/sessions/{session_id}`", "| `PUT` | `/api/v1/sessions/{session_id}`"
    )
    mutated = contract_document(swapped)
    assert {("PUT", f"{PREFIX}/sessions/{{session_id}}")} <= _documented_pairs(mutated)

    problems = route_diff(_documented_pairs(mutated), actual_routes(live_app, prefix=PREFIX))
    # PUT موثّق بلا تنفيذ + DELETE منفّذ بلا توثيق: الاتجاهان معاً.
    put_row = "PUT /api/v1/sessions/{session_id}"
    delete_row = "DELETE /api/v1/sessions/{session_id}"
    assert any(put_row in line and "بلا تنفيذ فعلي" in line for line in problems), problems
    assert any(delete_row in line and "بلا توثيق" in line for line in problems), problems


def test_contract_fails_when_the_error_envelope_changes(client: TestClient) -> None:
    """حالة فشل موثّقة: ``trace_id`` بدل ``request_id`` في الوثيقة ⇒ بنية الاستجابة لم تعد مطابقة."""
    doc = contract_document(read_api_doc())
    mutated = contract_document(read_api_doc().replace('"request_id"', '"trace_id"'))
    real_body = client.get(f"{PREFIX}/nope").json()

    assert "request_id" in doc.envelope_error_keys
    assert "request_id" not in mutated.envelope_error_keys
    assert envelope_diff(doc, [real_body]) == []

    problems = envelope_diff(mutated, [real_body])
    assert problems and "مفاتيح ``error``" in problems[0], problems


def test_contract_fails_when_details_keys_change(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """حالة فشل موثّقة: مفتاح ``field`` من ``details`` محذوف من الوثيقة ⇒ العقد يرفض 422 الحقيقي."""
    mutated = contract_document(read_api_doc().replace('"field": "body.task_id",', ""))
    invalid_body = client.post(f"{PREFIX}/sessions", json={"task_id": "x"}, headers=auth_headers).json()
    assert invalid_body["error"]["details"], "الفحص بلا أخطاء تحقّق لا يُثبت شيئاً"

    assert "field" not in mutated.detail_keys
    problems = envelope_diff(mutated, [invalid_body])
    assert any("details[]" in line for line in problems), problems


def test_contract_fails_when_a_public_route_is_documented_as_authenticated(client: TestClient) -> None:
    """حالة فشل موثّقة: كذب عمود المصادقة يُمسك — ``/health`` عامّ لا يطلب مفتاحاً."""
    honest = contract_document(read_api_doc())
    lying_text = read_api_doc().replace(
        "| `GET` | `/api/v1/health` | `no` | `200` | `-` |",
        "| `GET` | `/api/v1/health` | `yes` | `200` | `-` |",
    )
    lying = contract_document(lying_text)
    health_rows = [row for row in lying.routes if row.path == f"{PREFIX}/health"]
    assert [row.requires_auth for row in health_rows] == [True]

    assert auth_problems(client, honest.routes, samples={"session_id": PROBE_SESSION_ID}) == []
    problems = auth_problems(client, health_rows)
    assert any("موثّقة أنها تتطلب مفتاحاً" in line for line in problems), problems


def test_contract_fails_when_an_error_code_status_is_stale(document: Any) -> None:
    """حالة فشل موثّقة: ``not_found`` موثّق 410 بدل 404 ⇒ ``error_code_diff`` يرفضه."""
    mutated_codes = dict(document.error_codes)
    mutated_codes["not_found"] = 410

    problems = error_code_diff(mutated_codes, _error_code_map())
    assert any("not_found" in line and "410" in line and "404" in line for line in problems), problems


def test_contract_fails_when_an_error_code_is_dropped_from_docs(document: Any) -> None:
    """حالة فشل موثّقة: حذف صفّ كود من الجدول ⇒ «كود منفَّذ بلا توثيق»."""
    mutated_codes = {code: status for code, status in document.error_codes.items() if code != "conflict"}

    problems = error_code_diff(mutated_codes, _error_code_map())
    assert any("كود منفَّذ بلا توثيق: conflict" in line for line in problems), problems


def test_contract_fails_when_session_statuses_drift(document: Any) -> None:
    """حالة فشل موثّقة: حالة جديدة في الكود أو الوثيقة وحدها ⇒ فرق في الاتجاهين."""
    assert status_diff(document.session_statuses, (*SESSION_STATUSES, "cancelled")) != []
    assert status_diff([*document.session_statuses, "archived"], SESSION_STATUSES) != []
    assert status_diff(document.session_statuses, SESSION_STATUSES) == []


@pytest.mark.parametrize("mutation", ["drop-routes-table", "drop-error-table", "broken-json", "missing-doc"])
def test_doc_reader_rejects_missing_or_unparseable_sections(tmp_path: Path, mutation: str) -> None:
    """حالة فشل للبنية نفسها: وثيقة ناقصة/مكسورة خطأ صريح، لا عقد فارغ أخضر."""
    if mutation == "missing-doc":
        with pytest.raises(AssertionError, match="مفقودة"):
            read_api_doc(tmp_path / "API.md")
        return

    text = read_api_doc()
    if mutation == "drop-routes-table":
        text = text.replace(
            "| Method | Path | Auth | Success | Example |", "| الطريقة | المسار | مصادقة | نجاح | مثال |"
        )
        expected = "لا جدول في docs/API.md"
    elif mutation == "drop-error-table":
        text = text.replace("| Code | HTTP | متى |", "| الرمز | الحالة | متى |")
        expected = "لا جدول في docs/API.md"
    else:
        text = text.replace('"error": {', '"error": { oops', 1)
        expected = "JSON غير صالحة"

    assert text != read_api_doc(), "التحوير يجب أن يغيّر الوثيقة فعلاً"
    with pytest.raises(AssertionError, match=expected):
        contract_document(text)


def test_empty_routes_table_is_not_treated_as_an_empty_contract() -> None:
    """حالة فشل للبنية: ترويسة بلا صفوف ≠ «لا شيء لنتحقق منه» — بل خطأ."""
    text = read_api_doc()
    stripped = "\n".join(
        line for line in text.splitlines() if not (line.startswith("| `") and "/api/v1/" in line)
    )
    assert stripped != text
    with pytest.raises(AssertionError, match="لا يحتوي أي صف"):
        contract_document(stripped)
