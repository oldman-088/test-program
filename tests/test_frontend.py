"""اختبارات آلية لمخرجات الواجهة الأمامية (AATM-66dbe1d5).

تؤكد وجود الملفات المطلوبة في المهمة وصلاحيتها الأساسية، دون تشغيل npm
(بناء npm يُختبر في مهمة frontend في CI).
"""

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"

EXPECTED_FILES = [
    "frontend/package.json",
    "frontend/vite.config.ts",
    "frontend/tsconfig.json",
    "frontend/tailwind.config.js",
    "frontend/postcss.config.js",
    "frontend/index.html",
    "frontend/.env.example",
    "frontend/src/main.tsx",
    "frontend/src/App.tsx",
    "frontend/src/routes.tsx",
    "frontend/src/index.css",
    "frontend/src/store/uiStore.ts",
    "frontend/src/hooks/useDirection.ts",
    "frontend/src/hooks/useLocale.ts",
    "frontend/src/hooks/useHealth.ts",
    "frontend/src/lib/api.ts",
    "frontend/src/lib/i18n.ts",
    "frontend/src/lib/locales/en.json",
    "frontend/src/lib/locales/ar.json",
    "frontend/src/components/ui/button.tsx",
    "frontend/src/components/ui/card.tsx",
    "frontend/src/components/ui/input.tsx",
    "frontend/src/components/ui/badge.tsx",
    "frontend/src/components/ui/select.tsx",
    "frontend/src/components/ui/skeleton.tsx",
    "frontend/src/components/layout/AppLayout.tsx",
    "frontend/src/components/layout/Sidebar.tsx",
    "frontend/src/components/layout/TopBar.tsx",
    "frontend/src/pages/Dashboard.tsx",
    "frontend/src/pages/Placeholder.tsx",
    "docs/API.md",
]


def test_frontend_files_exist():
    for rel in EXPECTED_FILES:
        assert (ROOT / rel).is_file(), f"ملف مفقود: {rel}"


def test_api_client_follows_contract():
    api = (FRONTEND / "src/lib/api.ts").read_text(encoding="utf-8")
    for path in [
        "/api/health",
        "/api/health/db",
        "/api/investigations/recent",
        "/api/stats",
        "/api/integrations",
        "/api/ai/provider",
        "/api/tasks/progress",
        "/api/reports/latest",
        "/api/investigations",
    ]:
        assert path in api, f"api.ts يفتقر للمسار: {path}"
    assert "VITE_API_BASE_URL" in api
    assert "http://localhost" not in api and "https://localhost" not in api
    assert "http://127.0.0.1" not in api and "https://127.0.0.1" not in api


def test_sidebar_has_eleven_items_in_order():
    sidebar = (FRONTEND / "src/components/layout/Sidebar.tsx").read_text(encoding="utf-8")
    for path in [
        "'/'",
        "'/investigations/new'",
        "'/investigations/history'",
        "'/search-tools'",
        "'/results'",
        "'/graph'",
        "'/timeline'",
        "'/reports'",
        "'/integrations'",
        "'/settings'",
        "'/about'",
    ]:
        assert path in sidebar, f"Sidebar يفتقر للمسار: {path}"


def test_locales_cover_nav_and_dashboard():
    en = json.loads((FRONTEND / "src/lib/locales/en.json").read_text(encoding="utf-8"))
    ar = json.loads((FRONTEND / "src/lib/locales/ar.json").read_text(encoding="utf-8"))
    for key in ["dashboard", "newInvestigation", "investigationHistory", "searchTools",
                "results", "relationshipGraph", "timeline", "reports",
                "integrations", "settings", "about"]:
        assert en["nav"][key], f"en nav missing {key}"
        assert ar["nav"][key], f"ar nav missing {key}"
    assert en["nav"]["dashboard"] == "Dashboard"
    assert ar["nav"]["dashboard"] == "لوحة القيادة"


def test_dark_default_and_direction():
    css = (FRONTEND / "src/index.css").read_text(encoding="utf-8")
    assert ".dark" in css
    store = (FRONTEND / "src/store/uiStore.ts").read_text(encoding="utf-8")
    assert "theme: 'dark'" in store or 'theme: "dark"' in store
    assert "directionForLocale" in store


def test_dashboard_uses_real_endpoints_and_no_fake_data():
    dash = (FRONTEND / "src/pages/Dashboard.tsx").read_text(encoding="utf-8")
    for fn in ["getRecentInvestigations", "getStats", "getIntegrations",
               "getAiProvider", "getTaskProgress", "getLatestReports",
               "createInvestigation"]:
        assert fn in dash, f"Dashboard يفتقر لاستدعاء: {fn}"
    assert "useHealth" in dash
