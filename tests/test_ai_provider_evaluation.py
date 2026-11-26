# -*- coding: utf-8 -*-
"""
Tests for docs/AI_PROVIDER_EVALUATION.md — Ollama provider evaluation.

These tests ensure the documentation required by AATM-c77fe508 exists,
covers the real Ollama API surface, states the explicit no-auto-download
rule, works offline, provides a JSON contract with ai_generated vs
source_verified tags, and contains no implementation code.
"""

import re
import pathlib

DOC_PATH = pathlib.Path(__file__).resolve().parents[1] / "docs" / "AI_PROVIDER_EVALUATION.md"


def read_doc() -> str:
    assert DOC_PATH.exists(), f"Missing required file: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_file_exists():
    assert DOC_PATH.exists(), "docs/AI_PROVIDER_EVALUATION.md must exist"
    assert DOC_PATH.is_file()
    text = DOC_PATH.read_text(encoding="utf-8")
    assert len(text) > 5000, "Document seems too short — expected comprehensive evaluation"


def test_documents_actual_api_endpoints():
    t = read_doc()
    # Required Ollama endpoints per task: /api/tags, /api/generate, /api/chat, embeddings
    for ep in ["/api/tags", "/api/generate", "/api/chat", "/api/embed"]:
        assert ep in t, f"Missing API endpoint documentation: {ep}"
    # Additional management endpoints that prove depth of investigation
    for ep in ["/api/version", "/api/ps", "/api/show", "/api/pull"]:
        assert ep in t, f"Missing management endpoint: {ep}"


def test_documents_server_discovery():
    t = read_doc()
    # Host/port discovery
    assert "127.0.0.1:11434" in t or "11434" in t, "Must document default port 11434"
    assert "OLLAMA_HOST" in t, "Must document OLLAMA_HOST env var for host discovery"
    # Health check method
    assert "/api/version" in t, "Must document health-check via /api/version (or /api/tags)"
    # Discovery strategy prose
    assert "اكتشاف" in t, "Must have a section about local server discovery"


def test_explicit_no_auto_download_rule():
    t = read_doc()
    # The mandatory rule: no large-model download without explicit confirmation
    assert "تأكيد" in t, "Must mention explicit user confirmation"
    # Check for a prominent rule that app does not auto-download
    assert "لا ينزّل" in t or "لا ينزل" in t, "Must contain the explicit rule that the app does not auto-download models"
    # Also ensure the doc says download requires confirmation
    assert "دون تأكيد" in t or "بتأكيد" in t or "تأكيد صريح" in t


def test_app_works_without_ai():
    t = read_doc()
    # Safe degradation: app works fully without AI
    assert "بدون ذكاء اصطناعي" in t, "Must state that the app works fully without AI"
    assert "تدهور" in t, "Must document safe degradation / fallback path"
    # At least one occurrence of provider_unavailable or fallback logic
    assert "provider_unavailable" in t or "تدهور آمن" in t


def test_json_contract_and_provenance_tags():
    t = read_doc()
    assert "عقد" in t or "JSON" in t, "Must include a JSON contract proposal"
    # Structured contract fields
    assert '"provider"' in t or "'provider'" in t or "provider" in t
    assert '"task"' in t or "task" in t
    # Provenance tags
    assert "ai_generated" in t, "Must tag AI-generated content (ai_generated)"
    assert "source_verified" in t, "Must tag source-verified content (source_verified)"
    # Arabic description of tagging
    assert "مولّد" in t or "مولد" in t, "Must explain what is AI-generated in Arabic"
    assert "متحقق" in t, "Must explain what is source-verified in Arabic"


def test_six_usage_patterns_documented():
    t = read_doc()
    patterns = [
        "تلخيص نتائج البحث",
        "تصنيف النتائج",
        "كشف النتائج المكررة",
        "شرح علاقات المصادر",
        "توليد التقارير",
        "تلخيص التحقيق",
    ]
    for p in patterns:
        # Allow minor wording differences but require core phrase
        core = p.split()[0]  # first word should appear near pattern
        assert p in t or core in t, f"Missing usage pattern: {p}"
    # Strong check: all six headings appear
    missing = [p for p in patterns if p not in t]
    assert not missing, f"Missing patterns: {missing}"


def test_timeouts_and_rate_limits():
    t = read_doc()
    assert "مهلة" in t or "مهلات" in t or "timeout" in t.lower(), "Must discuss timeout strategies"
    assert "حد" in t and ("معدل" in t or "Rate" in t or "rate" in t), "Must discuss rate-limit strategies"
    assert "OLLAMA_KEEP_ALIVE" in t or "KeepAlive" in t or "keep_alive" in t


def test_offline_requirements():
    t = read_doc()
    assert "بلا اتصال" in t or "بدون اتصال" in t or "بلا إنترنت" in t or "offline" in t.lower(), "Must document offline/no-network requirements"
    assert "OLLAMA_MODELS" in t or ".ollama/models" in t, "Must document local model storage path"


def test_no_unverified_claims_without_tag():
    t = read_doc()
    # The doc must mark unverified claims explicitly — at least one occurrence
    assert "غير متحقق" in t, "Unverified claims must be tagged with «غير متحقق»"


def test_no_implementation_code():
    t = read_doc()
    # Ensure the doc does not contain provider implementation code.
    # JSON examples are allowed, but Go/Python class/function implementation is not.
    disallowed_patterns = [
        r"^\s*class\s+\w+Provider",      # python class definition
        r"^\s*def\s+\w+\(self",          # python method
        r"^\s*func\s+\(c\s+\*Client\)",  # Go client method copy-paste as implementation
        r"^\s*import\s+ollama",          # direct python import as if implementing
    ]
    for pat in disallowed_patterns:
        found = re.search(pat, t, flags=re.MULTILINE)
        assert not found, f"Document must not contain implementation code, found pattern: {pat} -> {found.group(0) if found else ''}"
    # Also ensure it explicitly states docs-only
    assert "لا يُنشأ أي مزوّد" in t or "بحث وتوثيق فقط" in t or "لا يوجد كود" in t or "توثيق فقط" in t


def test_abstract_interface_for_two_providers():
    t = read_doc()
    assert "واجهة مجرّدة" in t or "واجهة مجردة" in t or "abstract" in t.lower(), "Must propose an abstract provider interface"
    assert "Ollama" in t
    assert "المزوّد الثاني" in t or "second_provider" in t or "مزود ثان" in t
