"""قارئ ``docs/API.md`` — أدوات اختبار العقد (ليست ملف اختبار بذاتها).

القارئ متعمّد الصرامة: يفترض جداول Markdown قياسية، ويرفض بصمت كل جدول لا يتضمن
الترويسات المطلوبة. لا ``app`` هنا ولا ``pytest`` — دوال نقية فقط، حتى يمكن
اختبارها بدورها على نصّ معدَّل (وهذا ما يجعل «العقد يفشل تلقائياً» موثوقاً).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
API_DOC_PATH = REPO_ROOT / "docs" / "API.md"

HTTP_METHODS: frozenset[str] = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"})

# ترويسات الجداول العقدية (أسماء الأعمدة بحروف صغيرة).
ROUTE_TABLE_HEADERS = ("method", "path")
ERROR_TABLE_HEADERS = ("code", "http")

_ENVELOPE_HEADING = "قالب الخطأ"
_VALIDATION_HEADING = "مثال خطأ التحقق"
_STATUS_HEADING = "حالات الجلسة"

_CELL_SPLIT = re.compile(r"(?<!\\)\|")
_PLACEHOLDER_FALLBACK = "ses_00000000000000000000"
_SEPARATOR_CELL = re.compile(r"^:?-{2,}:?$")
_HEADING = re.compile(r"^#{1,6}\s+(.*)$")
_FENCE = re.compile(r"^\s*```(json)?\s*$")
_BULLET_CODE = re.compile(r"^[-*]\s*`([^`]+)`")


def read_api_doc(path: Path | None = None) -> str:
    """يقرأ الوثيقة. غيابها خطأ صريح — لا عقد صامت."""
    doc = API_DOC_PATH if path is None else path
    if not doc.exists():
        raise AssertionError(f"وثيقة العقد مفقودة: {doc}")
    return doc.read_text(encoding="utf-8")


def _clean_cell(cell: str) -> str:
    return cell.strip().strip("`").strip("*").strip()


def _is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(_SEPARATOR_CELL.match(cell.strip()) for cell in cells)


def parse_tables(text: str) -> list[list[list[str]]]:
    """كل الجداول في النص كقوائم صفوف من الخلايا المنظّفة (بلا صف الفواصل)."""
    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [_clean_cell(cell) for cell in _CELL_SPLIT.split(stripped.strip("|"))]
            if _is_separator_row(cells):
                continue
            current.append(cells)
        else:
            if current:
                tables.append(current)
                current = []
    if current:
        tables.append(current)
    return tables


def _find_table(text: str, headers: tuple[str, ...]) -> list[list[str]]:
    """يعيد جدولاً كاملاً (ترويسة + صفوف). غياب الترويسة أو الصفوف خطأ صريح."""
    for table in parse_tables(text):
        if not table:
            continue
        header = [cell.lower() for cell in table[0]]
        if all(name in header for name in headers):
            if len(table) < 2:
                raise AssertionError(
                    f"جدول docs/API.md بالترويسات {headers} لا يحتوي أي صفّ صالح."
                )
            return table
    raise AssertionError(
        f"لا جدول في docs/API.md يحمل الترويسات {headers} — حذف الجدول يكسر العقد عمداً."
    )


def _columns(table: list[list[str]]) -> dict[str, int]:
    return {cell.lower(): index for index, cell in enumerate(table[0])}


def _int_or_none(value: str) -> int | None:
    match = re.search(r"\d{3}", value or "")
    return int(match.group()) if match else None


@dataclass(frozen=True)
class DocumentedRoute:
    method: str
    path: str
    requires_auth: bool
    success_status: int
    example: str = ""

    def request_target(self, samples: Mapping[str, str] | None = None) -> str:
        """المسار مع مثال الاستعلام الموثّق، و``{param}`` معبّأة من ``samples``.

        أي معوّض بلا قيمة في ``samples`` يُملأ بمعرّف غير معروف — وهو مقصود:
            مسار لا يعمل إلا بمعرّف مُختلَق يعني أن الوثيقة تخفي اعتماداً غير موثّق.
        """
        provided = samples or {}
        path = self.path
        for placeholder in re.findall(r"\{([^}]+)\}", path):
            value = provided.get(placeholder, _PLACEHOLDER_FALLBACK)
            path = path.replace("{" + placeholder + "}", value)
        return path + (self.example if self.example.startswith("?") else "")


@dataclass
class ContractDocument:
    """كل ما يُلزم به ``docs/API.md`` التطبيقَ."""

    routes: list[DocumentedRoute] = field(default_factory=list)
    error_codes: dict[str, int] = field(default_factory=dict)
    envelope_root_keys: list[str] = field(default_factory=list)
    envelope_error_keys: list[str] = field(default_factory=list)
    detail_keys: list[str] = field(default_factory=list)
    session_statuses: list[str] = field(default_factory=list)


def documented_routes(text: str) -> list[DocumentedRoute]:
    table = _find_table(text, ROUTE_TABLE_HEADERS)
    cols = _columns(table)
    routes: list[DocumentedRoute] = []
    for row in table[1:]:
        if len(row) < len(cols):
            row = [*row, *[""] * (len(cols) - len(row))]
        method = row[cols["method"]].upper()
        path = row[cols["path"]]
        if method not in HTTP_METHODS or not path.startswith("/"):
            continue
        auth_cell = (row[cols["auth"]] if "auth" in cols else "yes").lower()
        requires_auth = auth_cell in {"yes", "y", "true", "نعم", "✔", "✓"}
        success = _int_or_none(row[cols["success"]]) if "success" in cols else None
        example = row[cols["example"]] if "example" in cols else ""
        if example in {"-", "—", ""}:
            example = ""
        if success is None:
            raise AssertionError(f"صف بلا حالة نجاح رقمية في docs/API.md: {row!r}")
        routes.append(
            DocumentedRoute(
                method=method,
                path=path,
                requires_auth=requires_auth,
                success_status=success,
                example=example,
            )
        )
    if not routes:
        raise AssertionError("جدول المسارات في docs/API.md لا يحتوي أي صفّ مسار صالح.")
    return routes


def documented_error_codes(text: str) -> dict[str, int]:
    table = _find_table(text, ERROR_TABLE_HEADERS)
    cols = _columns(table)
    codes: dict[str, int] = {}
    for row in table[1:]:
        code = row[cols["code"]]
        status = _int_or_none(row[cols["http"]])
        if not code or status is None:
            continue
        codes[code] = status
    if not codes:
        raise AssertionError("جدول أكواد الخطأ في docs/API.md فارغ.")
    return codes


def _json_blocks(text: str) -> list[tuple[str, str]]:
    """``[(آخر عنوان قبل الكتلة، نص الكتلة)]`` لكتل ```json```."""
    blocks: list[tuple[str, str]] = []
    heading = ""
    inside = False
    buffer: list[str] = []
    for line in text.splitlines():
        if not inside:
            heading_match = _HEADING.match(line)
            if heading_match:
                heading = heading_match.group(1)
            if _FENCE.match(line):
                inside = True
                buffer = []
            continue
        if _FENCE.match(line):
            blocks.append((heading, "\n".join(buffer)))
            inside = False
            continue
        buffer.append(line)
    return blocks


def _block_under(text: str, heading_part: str) -> dict[str, Any]:
    for heading, raw in _json_blocks(text):
        if heading_part in heading:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:  # pragma: no cover - خطأ في الوثيقة
                raise AssertionError(f"كتلة JSON غير صالحة تحت «{heading_part}»: {exc}") from exc
            if isinstance(parsed, dict):
                return parsed
    raise AssertionError(f"لا مثال JSON موثّق تحت عنوان يحوي «{heading_part}» في docs/API.md.")


def flatten_key_paths(payload: Any, prefix: str = "") -> set[str]:
    """مفاتيح متداخلة كمسارات منقّطة؛ القوائم تُفرد بعنصر واحد (المفاتيح لا الترتيب)."""
    keys: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            keys.add(path)
            keys |= flatten_key_paths(value, path)
    elif isinstance(payload, list):
        for item in payload:
            keys |= flatten_key_paths(item, prefix)
    return keys


def contract_document(text: str) -> ContractDocument:
    """يحلّل الوثيقة كاملة إلى عقد قابل للمقارنة (الجداول أولاً، ثم أمثلة JSON)."""
    routes = documented_routes(text)
    codes = documented_error_codes(text)
    envelope = _block_under(text, _ENVELOPE_HEADING)
    validation = _block_under(text, _VALIDATION_HEADING)
    error_node = validation.get("error", {}) if isinstance(validation.get("error"), dict) else {}
    details = error_node.get("details") or []
    detail_keys = sorted(details[0]) if details and isinstance(details[0], dict) else []

    statuses: list[str] = []
    inside_section = False
    for line in text.splitlines():
        heading_match = _HEADING.match(line)
        if heading_match:
            inside_section = _STATUS_HEADING in heading_match.group(1)
            continue
        if inside_section:
            bullet = _BULLET_CODE.match(line.strip())
            if bullet:
                statuses.append(bullet.group(1))

    return ContractDocument(
        routes=routes,
        error_codes=codes,
        envelope_root_keys=sorted(envelope),
        envelope_error_keys=sorted(envelope.get("error", {})),
        detail_keys=detail_keys,
        session_statuses=statuses,
    )



def error_code_diff(documented: Mapping[str, int], actual: Mapping[str, int]) -> list[str]:
    """فرق ثنائي الاتجاه بين جدول الأكواد في الوثيقة وخريطة الكود↔الحالة في الكود."""
    problems: list[str] = []
    for code, status in sorted(documented.items()):
        if code not in actual:
            problems.append(f"كود موثّق بلا تنفيذ: {code} ({status})")
        elif actual[code] != status:
            problems.append(f"حالة HTTP مختلف لكود {code}: موثّق {status} / فعلي {actual[code]}")
    for code, status in sorted(actual.items()):
        if code not in documented:
            problems.append(f"كود منفَّذ بلا توثيق: {code} ({status})")
    return problems


def envelope_diff(documented: ContractDocument, bodies: Iterable[dict[str, Any]]) -> list[str]:
    """يقارن بنية جسم الخطأ الفعلية بالمثال الموثّق — أي مفتاح زائد أو ناقض يفشل العقد."""
    problems: list[str] = []
    for index, body in enumerate(bodies):
        if set(body) != set(documented.envelope_root_keys):
            problems.append(
                f"مفاتيح الجذر في الاستجابة {index} {sorted(body)} ≠ الموثّق {documented.envelope_root_keys}"
            )
            continue
        error = body.get("error")
        if not isinstance(error, dict):
            problems.append(f"الاستجابة {index}: ``error`` ليس كائناً JSON")
            continue
        if set(error) != set(documented.envelope_error_keys):
            problems.append(
                f"مفاتيح ``error`` في الاستجابة {index} {sorted(error)} ≠ "
                f"الموثّق {sorted(documented.envelope_error_keys)}"
            )
        details = error.get("details")
        if not isinstance(details, list):
            problems.append(f"الاستجابة {index}: ``details`` ليست قائمة ({type(details).__name__})")
            continue
        if documented.detail_keys:
            for item in details:
                if set(item) != set(documented.detail_keys):
                    problems.append(
                        f"مفاتيح ``details[]`` {sorted(item)} ≠ الموثّق {sorted(documented.detail_keys)}"
                    )
    return problems


def status_diff(documented: list[str], actual: tuple[str, ...] | list[str]) -> list[str]:
    """فرق قائمة القيم الموثّقة عن قيم الكود (حالات الجلسة مثلاً)."""
    problems: list[str] = []
    for value in documented:
        if value not in actual:
            problems.append(f"قيمة موثّقة بلا تنفيذ: {value!r}")
    for value in actual:
        if value not in documented:
            problems.append(f"قيمة منفّذة بلا توثيق: {value!r}")
    return problems


def openapi_documented_paths(app: Any, *, prefix: str) -> set[tuple[str, str]]:
    """نفس الأزواج لكن من مخطط OpenAPI — يمسك الانحراف بين الموجّهات والمخطط."""
    spec = app.openapi()
    found: set[tuple[str, str]] = set()
    for path, item in spec.get("paths", {}).items():
        if not path.startswith(prefix):
            continue
        for method in item:
            if method.upper() in HTTP_METHODS:
                found.add((method.upper(), path))
    return found


def auth_problems(
    client: Any,
    routes: Iterable[DocumentedRoute],
    *,
    samples: Mapping[str, str] | None = None,
) -> list[str]:
    """يقارن عمود «المصادقة» بالسلوك الفعلي لكل صفّ (401 بلا بيانات اعتماد)."""
    problems: list[str] = []
    for route in routes:
        response = client.request(route.method, route.request_target(samples))
        if route.requires_auth:
            if response.status_code != 401:
                problems.append(
                    f"{route.method} {route.path} موثّقة أنها تتطلب مفتاحاً، "
                    f"لكنها أرجعت {response.status_code} بلا بيانات اعتماد"
                )
        elif response.status_code in {401, 403}:
            problems.append(
                f"{route.method} {route.path} موثّقة أنها عامة، لكنها رُفضت بـ {response.status_code}"
            )
    return problems


def success_problems(
    client: Any,
    routes: Iterable[DocumentedRoute],
    *,
    headers: Mapping[str, str],
    samples: Mapping[str, str] | None = None,
    bodies: Mapping[str, Any] | None = None,
) -> list[str]:
    """ينفّذ كل صفّ بطلب مكتمل ويقارن بحالة النجاح الموثّقة في العمود ``Success``."""
    problems: list[str] = []
    payload_by_path = bodies or {}
    for route in routes:
        kwargs: dict[str, Any] = {"headers": dict(headers)}
        body = payload_by_path.get(route.path)
        if body is not None:
            kwargs["json"] = body
        response = client.request(route.method, route.request_target(samples), **kwargs)
        if response.status_code != route.success_status:
            problems.append(
                f"{route.method} {route.path}: موثّق {route.success_status} "
                f"وأُرجع {response.status_code} → {response.text[:160]}"
            )
    return problems

def walk_api_routes(app: Any) -> list[tuple[str, Any]]:
    """``[(المسار الكامل, كائن المسار)]`` لكل ``APIRoute`` في التطبيق.

    يتتبّع البادئات عبر ``include_context`` لأن ``include_router`` حديث الإصدار يؤجّل
    تركيب البادئة إلى سياق الإدراج بدل نسخ المسارات. يعمل على الصيغتين (نسخ مسارات
    مُفلطَمة قديماً، وعُقد إدراج متداخلة حديثاً).
    """
    from fastapi.routing import APIRoute

    found: list[tuple[str, Any]] = []
    stack: list[tuple[str, Any]] = [("", app)]
    while stack:
        inherited, node = stack.pop()
        context = getattr(node, "include_context", None)
        own_prefix = str(getattr(context, "prefix", "") or "")
        prefix = inherited + own_prefix

        routes = getattr(node, "routes", None)
        if routes is None:
            original = getattr(node, "original_router", None)
            routes = getattr(original, "routes", None) if original is not None else None
        if routes:
            stack.extend((prefix, child) for child in routes)
            continue
        if isinstance(node, APIRoute) and getattr(node, "path", None):
            found.append((prefix + node.path, node))
    return found


def actual_routes(app: Any, *, prefix: str) -> set[tuple[str, str]]:
    """أزواج ``(METHOD, path)`` الفعلية من تطبيق FastAPI تحت ``prefix`` (حتى المخفي)."""
    found: set[tuple[str, str]] = set()
    for full_path, route in walk_api_routes(app):
        if not full_path.startswith(prefix):
            continue
        for method in route.methods or ():
            if method.upper() in HTTP_METHODS:
                found.add((method.upper(), full_path))
    return found


def hidden_routes(app: Any, *, prefix: str) -> list[str]:
    """مسارات ``include_in_schema=False`` تحت البادئة — يجب أن تكون موثّقة يدوياً أو ممنوعة."""
    return [
        full_path
        for full_path, route in walk_api_routes(app)
        if full_path.startswith(prefix) and not route.include_in_schema
    ]


def route_diff(documented: Iterable[tuple[str, str]], actual: Iterable[tuple[str, str]]) -> list[str]:
    """فرق ثنائي الاتجاه بصيغة يقرأها الإنسان؛ قائمة فارغة = عقد سليم."""
    doc = set(documented)
    act = set(actual)
    problems: list[str] = []
    for method, path in sorted(doc - act):
        problems.append(f"موثّق في docs/API.md بلا تنفيذ فعلي: {method} {path}")
    for method, path in sorted(act - doc):
        problems.append(f"منفَّذ في backend/app/api/ بلا توثيق: {method} {path}")
    return problems
