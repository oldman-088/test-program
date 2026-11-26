"""اختبارات آلية لطبقة اختبارات الواجهة الأمامية (AATM-9eac8ff5).

تؤكد وجود مخرجات هذه المهمة وصلاحيتها الأساسية دون تشغيل npm:
- `frontend/vitest.config.ts` ببيئة jsdom وملف التهيئة `src/test/setup.ts`
- ملفات الاختبارات الأربعة المطلوبة في مساراتها المحددة
- سكربت `test` في `frontend/package.json` واعتمادية @testing-library/user-event
- عدم اعتماد أي اختبار على خدمة خارجية حقيقية (لا عناوين شبكة في ملفات الاختبار)

تشغيل الاختبارات الفعلية عبر npm يُنفَّذ في وظيفة `frontend` داخل CI.
"""

from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"

TEST_FILES = [
    "frontend/src/test/setup.ts",
    "frontend/src/components/ui/button.test.tsx",
    "frontend/src/lib/api.test.ts",
    "frontend/src/store/uiStore.test.ts",
    "frontend/src/pages/Dashboard.test.tsx",
]

# عناوين مسموحة فقط في سياق التحقق من تطبيق base URL (نطاق محجوز لا يُطلب فعلياً).
ALLOWED_URL_PATTERNS = [
    r"https://backend\.example\.test",
]


def test_test_layer_files_exist():
    for rel in ["frontend/vitest.config.ts", *TEST_FILES]:
        assert (FRONTEND.parent / rel).is_file(), f"ملف مفقود: {rel}"


def test_vitest_config_uses_jsdom_and_setup_file():
    config = (FRONTEND / "vitest.config.ts").read_text(encoding="utf-8")
    assert "environment: 'jsdom'" in config or 'environment: "jsdom"' in config
    assert "src/test/setup.ts" in config
    assert "include:" in config


def test_setup_file_loads_jest_dom():
    setup = (FRONTEND / "src/test/setup.ts").read_text(encoding="utf-8")
    assert "@testing-library/jest-dom" in setup
    assert "afterEach" in setup and "cleanup" in setup


def test_package_json_has_test_script_and_testing_deps():
    pkg = json.loads((FRONTEND / "package.json").read_text(encoding="utf-8"))
    assert "test" in pkg["scripts"], "سكربت test مفقود"
    assert "vitest" in pkg["scripts"]["test"], "سكربت test لا يشغّل vitest"

    dev_deps = pkg.get("devDependencies", {})
    for dep in [
        "vitest",
        "jsdom",
        "@testing-library/react",
        "@testing-library/jest-dom",
        "@testing-library/user-event",
    ]:
        assert dep in dev_deps, f"اعتمادية مفقودة: {dep}"


def test_button_test_covers_behaviour_and_accessibility():
    text = (FRONTEND / "src/components/ui/button.test.tsx").read_text(encoding="utf-8")
    # استعلامات الوصولية: الدور والاسم المتاح، لا أصناف CSS.
    assert "getByRole('button'" in text
    assert "name:" in text
    assert "toHaveAccessibleName" in text
    assert "user.click" in text or "userEvent" in text
    assert "disabled" in text
    assert "aria-busy" in text


def test_api_test_covers_requests_base_url_and_documented_error_template():
    text = (FRONTEND / "src/lib/api.test.ts").read_text(encoding="utf-8")
    # بناء الطلبات
    assert "'POST'" in text and "JSON.parse(init.body" in text
    # تطبيق base URL
    assert "VITE_API_BASE_URL" in text
    # قالب الخطأ الموحد الموثق في docs/API.md
    assert "parseApiError" in text
    assert "UNKNOWN_ERROR" in text
    assert "NETWORK_ERROR" in text
    assert "'NOT_FOUND'" in text or '"NOT_FOUND"' in text
    # استبدال fetch بـ mock
    assert "stubGlobal('fetch'" in text


def test_api_test_matches_error_template_documented_in_docs():
    docs = (ROOT / "docs/API.md").read_text(encoding="utf-8")
    test = (FRONTEND / "src/lib/api.test.ts").read_text(encoding="utf-8")

    # الحقول الثلاثة المذكورة في القالب الموثق موجودة في الاختبار.
    for field in ["code", "message", "details"]:
        assert f"error.{field}" in docs, f"docs/API.md لا يذكر الحقل: {field}"
        assert field in test, f"api.test.ts لا يتحقق من الحقل: {field}"

    # رمز الشبكة الموثق يُستخدم حرفياً.
    assert "NETWORK_ERROR" in docs
    assert "NETWORK_ERROR" in test

    # القالب نفسه: { "error": { code, message, details } } — يظهر حرفياً في docs/API.md
    compact_docs = re.sub(r"\s+", "", docs)
    assert '"error":{"code":"string","message":"string","details":"string|null"}' in compact_docs, (
        "قالب الخطأ الموحد غير موجود حرفياً في docs/API.md"
    )
    # والاختبار يبني نفس الشكل { error: { code, message, details } }
    assert re.search(r"error:\s*\{[^}]*code[^}]*\}", test), (
        "api.test.ts لا يبني قالب الخطأ { error: { code, ... } }"
    )


def test_ui_store_test_covers_theme_language_and_direction():
    text = (FRONTEND / "src/store/uiStore.test.ts").read_text(encoding="utf-8")
    assert "setTheme" in text
    assert "toggleTheme" in text
    assert "setLocale" in text
    assert "'rtl'" in text and "'ltr'" in text
    assert "direction" in text


def test_dashboard_test_covers_render_loading_and_error_states():
    text = (FRONTEND / "src/pages/Dashboard.test.tsx").read_text(encoding="utf-8")
    # عرض العناصر
    assert "Search query" in text
    assert "Start Investigation" in text
    # حالة التحميل
    assert "Loading" in text
    # حالة الخطأ عند فشل طلب الصحة تحديداً
    assert "/api/health" in text
    assert "findByRole('alert')" in text
    # كل طلب في الاختبار يمر عبر mock
    assert "stubGlobal('fetch'" in text


def test_dashboard_test_has_health_failure_case():
    """شرط القبول: اختبار Dashboard يتحقق من ظهور حالة الخطأ عند فشل طلب الصحة."""
    text = (FRONTEND / "src/pages/Dashboard.test.tsx").read_text(encoding="utf-8")
    assert "when GET /api/health fails" in text
    assert "503" in text or "TypeError" in text


def test_no_test_reaches_a_real_network():
    for rel in TEST_FILES:
        text = (FRONTEND.parent / rel).read_text(encoding="utf-8")
        scrubbed = text
        for pattern in ALLOWED_URL_PATTERNS:
            scrubbed = re.sub(pattern, "", scrubbed)
        assert "localhost" not in scrubbed, f"{rel} يشير إلى localhost"
        assert "127.0.0.1" not in scrubbed, f"{rel} يشير إلى 127.0.0.1"
        assert "XMLHttpRequest" not in scrubbed, f"{rel} يستخدم XMLHttpRequest"
        assert "http://" not in scrubbed, f"{rel} يحتوي عنوان HTTP فعلي"
        assert "https://" not in scrubbed, f"{rel} يحتوي عنوان HTTPS فعلي"
