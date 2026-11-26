"""Contract tests for docs/AATM_ARENA_EVALUATION.md.

The deliverable of AATM-c4e0aae6 is a research/evaluation document, so the behaviour that
can regress is the document's *content contract*: the mandated sections, the named source
paths and functions, the five connection states, the seven mandatory constraints, the
optional-module design, and the explicit no-claim statement.

These tests are stdlib-only (``unittest``) so they run with no third-party packages, and
they are also collected by ``pytest`` if it is installed.
"""

from __future__ import annotations

import pathlib
import re
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "docs" / "AATM_ARENA_EVALUATION.md"
PROBE_PATH = REPO_ROOT / "tests" / "manual" / "probe_aatm_connector.py"


def _read_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


class DeliverableExistsTests(unittest.TestCase):
    def test_document_exists(self) -> None:
        self.assertTrue(DOC_PATH.is_file(), f"missing deliverable: {DOC_PATH}")

    def test_document_is_utf8_and_substantial(self) -> None:
        text = _read_doc()
        self.assertGreater(len(text), 15_000, "evaluation document is unexpectedly short")
        self.assertGreater(text.count("\n"), 250, "evaluation document needs more structure")
        # Arabic content is required: the document must not have drifted to English-only prose.
        arabic = re.findall(r"[\u0600-\u06FF]", text)
        self.assertGreater(len(arabic), 5_000, "document should be written in Arabic")

    def test_probe_script_is_present_and_parses(self) -> None:
        self.assertTrue(PROBE_PATH.is_file(), f"missing evidence script: {PROBE_PATH}")
        source = PROBE_PATH.read_text(encoding="utf-8")
        compile(source, str(PROBE_PATH), "exec")  # must be valid Python, never imported by tests
        self.assertIn("AATM_REPO", source, "probe must locate an external AATM checkout explicitly")
        self.assertNotIn("pytest", source.splitlines()[0], "probe is a manual tool, not a pytest module")


class SectionCoverageTests(unittest.TestCase):
    """The twelve aspects named by the task must each have their own section."""

    ASPECT_HEADINGS = (
        "## 2. البنية العامة",
        "## 3. إدارة الوكلاء",
        "## 4. موصل المتصفح",
        "## 5. تكامل Arena",
        "## 6. الجسر المحلي",
        "## 7. تنفيذ الـ userscript",
        "## 8. إدارة ملفات تعريف المتصفح",
        "## 9. نقل الرسائل",
        "## 10. تقرير حالة الاتصال",
        "## 11. الإعدادات",
        "## 12. معالجة الأخطاء",
        "## 13. نموذج الأمان",
    )

    REQUIRED_SECTIONS = (
        "## 0. جدول المطابقة مع بنود المهمة",
        "## 14. هل موصل Arena قابل لإعادة الاستخدام",
        "## 15. ما تم التحقق منه بالتنفيذ",
        "## 16. تدفق الاستخدام اليدوي للمصادقة",
        "## 17. حالات الحالة المطلوبة في NEXUS",
        "## 18. القيود الإلزامية",
        "## 19. تصميم وحدة `NEXUS Arena Bridge`",
        "## 20. تصميم محوّل `AATM Integration Adapter`",
        "## 21. ضمان استقلال نواة NEXUS عن AATM",
        "## 25. القيود المعروفة لهذا التقييم",
    )

    def test_twelve_aspects_have_sections(self) -> None:
        text = _read_doc()
        missing = [h for h in self.ASPECT_HEADINGS if h not in text]
        self.assertEqual(missing, [], f"missing aspect sections: {missing}")

    def test_required_sections_present(self) -> None:
        text = _read_doc()
        missing = [h for h in self.REQUIRED_SECTIONS if h not in text]
        self.assertEqual(missing, [], f"missing required sections: {missing}")

    def test_eleven_vs_twelve_count_is_explained(self) -> None:
        text = _read_doc()
        self.assertIn("اثني عشر", text)
        self.assertIn("أحد عشر", text)
        self.assertIn("اثني عشر جانباً", text.replace("\n", " "))


class NamedSourceReferenceTests(unittest.TestCase):
    """Acceptance: the document must name concrete paths or functions."""

    REQUIRED_PATHS = (
        "bridge/connector.py",
        "bridge/server.py",
        "bridge/mock_arena/agent.html",
        "backend/app/browser/arena_connector.py",
        "backend/app/browser/arena_sessions.py",
        "backend/app/browser/manager.py",
        "backend/app/browser/engines.py",
        "backend/app/browser/safety.py",
        "backend/app/browser/install_links.py",
        "backend/app/api/routes/arena.py",
        "backend/app/providers/adapters/arena_browser.py",
        "backend/app/providers/adapters/arena_agent.py",
        "backend/app/providers/adapters/arena_bridge.py",
        "backend/app/orchestration/scheduler.py",
        "backend/app/core/config.py",
        "frontend/src/views/ArenaViews.tsx",
        "docs/SECURITY.md",
        "docs/SETUP_AR.md",
        "THIRD_PARTY_NOTICES.md",
    )

    REQUIRED_FUNCTIONS = (
        "ConnectorHub",
        "ProfileState",
        "handle_socket",
        "_authenticate",
        "_on_message",
        "_mark_needs_human",
        "_validate_command",
        "register_connector_routes",
        "create_app",
        "_verify_bearer_auth",
        "arena_gate",
        "real_arena_enabled",
        "configured_origins",
        "allowed_origins",
        "match_patterns",
        "mock_url",
        "bridge_ws_url",
        "mint_token",
        "build_userscript",
        "USERSCRIPT_BODY",
        "register_profile_with_bridge",
        "bridge_call",
        "ensure_arena_browser_provider",
        "validate_userscript_policy",
        "validate_public_navigation_url",
        "redact_extracted_text",
        "InstallLinkStore",
        "run_userscript",
        "launch_profile",
        "_launch_playwright_context",
        "claim_session",
        "set_arena_mode",
        "apply_bridge_state",
        "sync_profiles_with_bridge",
        "_arena_disconnected_agent_ids",
        "ArenaBrowserAdapter",
        "ArenaAgentAdapter",
        "ArenaLocalBridgeAdapter",
        "ArenaSubmitQueue",
        "keep_working_allowed",
        "redact_reply",
        "_issue_userscript",
    )

    REQUIRED_CONSTANTS = (
        "AGENT_COMMANDS",
        "AGENT_STATES",
        "DEFAULT_STOP_SELECTORS",
        "DEFAULT_STOP_PHRASES",
        "READ_ONLY_COMMANDS",
        "SAFE_STOP_COMMANDS",
        "SCRIPT_VERSION",
        "BRIDGE_VERSION",
        "ARENA_CONNECTOR_ENABLED",
        "ARENA_ALLOWED_ORIGINS",
        "ARENA_BRIDGE_TOKEN",
        "ARENA_MOCK_URL",
        "ARENA_DOM_SELECTORS",
    )

    def test_named_paths_are_present(self) -> None:
        text = _read_doc()
        missing = [p for p in self.REQUIRED_PATHS if p not in text]
        self.assertEqual(missing, [], f"missing named paths: {missing}")

    def test_named_functions_are_present(self) -> None:
        text = _read_doc()
        missing = [f for f in self.REQUIRED_FUNCTIONS if f not in text]
        self.assertEqual(missing, [], f"missing named functions/symbols: {missing}")

    def test_named_constants_are_present(self) -> None:
        text = _read_doc()
        missing = [c for c in self.REQUIRED_CONSTANTS if c not in text]
        self.assertEqual(missing, [], f"missing named constants: {missing}")


class ConnectionStateTests(unittest.TestCase):
    """The five mandated states must be defined, with machine-readable codes."""

    REQUIRED_STATES = ("متصل", "غير متصل", "بانتظار المصادقة", "الموصل غير متاح", "خطأ")
    REQUIRED_CODES = ("connected", "disconnected", "awaiting_auth", "connector_unavailable", "error")
    EXTRA_STATES = ("busy", "blocked_human_check")

    def test_five_states_and_codes_documented(self) -> None:
        text = _read_doc()
        for state in self.REQUIRED_STATES:
            self.assertIn(state, text, f"missing required state: {state}")
        for code in self.REQUIRED_CODES:
            self.assertIn(f"`{code}`", text, f"missing required state code: {code}")

    def test_auth_wait_is_separated_from_human_check_block(self) -> None:
        text = _read_doc()
        for state in self.EXTRA_STATES:
            self.assertIn(f"`{state}`", text, f"missing state: {state}")
        # The document must warn that AATM conflates a login wall with a hard human-check block.
        self.assertIn("خلطهما", text)
        self.assertIn("يجب أن يحمل جملة النفي صريحة", text)
        section = text.split("## 17. حالات الحالة المطلوبة في NEXUS", 1)[1].split("## 18.", 1)[0]
        self.assertIn("`awaiting_auth`", section)
        self.assertIn("`blocked_human_check`", section)

    def test_transition_rules_documented(self) -> None:
        text = _read_doc()
        self.assertIn("جدول الانتقالات", text)
        self.assertIn("human_resolved", text)


class MandatoryConstraintTests(unittest.TestCase):
    """Acceptance: the seven mandatory constraints must appear verbatim."""

    CONSTRAINTS = (
        "لا تجاوز مصادقة",
        "لا تجاوز CAPTCHA",
        "لا استخراج كوكيز المتصفح",
        "لا تصدير رموز مصادقة",
        "لا تدوير حسابات",
        "لا تطبيع أي نشاط محظور",
        "عدم الادعاء بأن الوصول عبر المتصفح مدعوم رسمياً",
    )

    def test_all_seven_constraints_present_verbatim(self) -> None:
        text = _read_doc()
        for constraint in self.CONSTRAINTS:
            self.assertIn(constraint, text, f"missing mandatory constraint: {constraint}")

    def test_constraints_are_marked_binding_and_enumerated(self) -> None:
        text = _read_doc()
        section = text.split("## 18. القيود الإلزامية", 1)[1]
        for index, constraint in enumerate(self.CONSTRAINTS, start=1):
            self.assertIn(constraint, section, f"constraint {index} must sit inside section 18")
            self.assertIn(f"{index}. **{constraint}", section, f"constraint {index} must be numbered")

    def test_official_support_is_never_claimed(self) -> None:
        """Any mention of official support must be negated on the same line."""
        text = _read_doc()
        negations = ("لا ", "غير ", "لم ", "بلا ", "ممنوع", "عدم", "لم ")
        offending = []
        for number, line in enumerate(text.splitlines(), start=1):
            if "مدعوم رسمياً" in line or "مصرّح به رسمياً" in line:
                if not any(neg in line for neg in negations):
                    offending.append((number, line.strip()[:120]))
        self.assertEqual(offending, [], f"line(s) claim official support: {offending}")


class NoClaimTests(unittest.TestCase):
    """Acceptance: no claim that an integration works before it is actually tested."""

    def test_explicit_disclaimer_present(self) -> None:
        text = _read_doc()
        self.assertIn(
            "لا يوجد أي تكامل بين AATM وNEXUS، ولم يُختبر أي تكامل، ولا يُدّعى أنه يعمل.",
            text,
            "the explicit no-claim statement must be present",
        )

    def test_verification_levels_are_separated(self) -> None:
        text = _read_doc()
        self.assertIn("مقروء من المصدر", text)
        self.assertIn("مُتحقَّق بالتنفيذ", text)
        self.assertIn("غير متحقق", text)

    def test_unverified_marker_used(self) -> None:
        text = _read_doc()
        self.assertGreaterEqual(text.count("غير متحقق"), 3)

    def test_design_is_labelled_as_proposal(self) -> None:
        text = _read_doc()
        section = text.split("## 19. تصميم وحدة", 1)[1]
        self.assertIn("اقتراح تصميم", section)
        self.assertIn("غير منفّذ", section)


class DesignProposalTests(unittest.TestCase):
    """Acceptance: an optional module and an optional adapter, with core independence."""

    def test_optional_module_design(self) -> None:
        text = _read_doc()
        for token in (
            "NEXUS Arena Bridge",
            "ArenaTransport",
            "NEXUS_ARENA_BRIDGE_ENABLED",
            "NEXUS_ARENA_BRIDGE_HOST",
            "NEXUS_ARENA_BRIDGE_TOKEN",
            "NEXUS_ARENA_ALLOWED_ORIGINS",
            "NEXUS_ARENA_DISCLOSURE_ACK",
            "loopback",
        ):
            self.assertIn(token, text, f"missing module design element: {token}")

    def test_optional_adapter_design(self) -> None:
        text = _read_doc()
        for token in (
            "AATM Integration Adapter",
            "TaskDelegation",
            "AgentStatus",
            "TaskResult",
            "IntegrationError",
            "correlation_id",
            "idempotency",
            "circuit breaker",
            "env:AATM_API_TOKEN",
        ):
            self.assertIn(token, text, f"missing adapter design element: {token}")

    def test_core_independence_is_required(self) -> None:
        text = _read_doc()
        section = text.split("## 21. ضمان استقلال نواة NEXUS عن AATM", 1)[1]
        self.assertIn("لا استيراد", section)
        self.assertIn("تعطيل/حذف", section)
        self.assertIn("unavailable", section)
        # The core must be described as able to run without AATM.
        self.assertIn("تعمل بكامل وظائفها", text)


class ManualAuthFlowTests(unittest.TestCase):
    """Acceptance: the manual authentication usage flow must be documented step by step."""

    def test_flow_steps_and_endpoints(self) -> None:
        text = _read_doc()
        section = text.split("## 16. تدفق الاستخدام اليدوي للمصادقة", 1)[1].split("## 17.", 1)[0]
        for endpoint in (
            "open-for-sign-in",
            "/userscript",
            "install-link",
            "/resume",
            "/v1/connector/profiles",
        ):
            self.assertIn(endpoint, section, f"missing endpoint in manual flow: {endpoint}")
        for step in ("1. **تفعيل البوابة", "3. **فتح الملف", "4. **توليد السكربت", "5. **تثبيت السكربت", "9. **عند التحقق البشري"):
            self.assertIn(step, section, f"missing numbered flow step: {step}")

    def test_flow_forbids_credential_handling(self) -> None:
        text = _read_doc()
        section = text.split("## 16. تدفق الاستخدام اليدوي للمصادقة", 1)[1].split("## 17.", 1)[0]
        self.assertIn("لا تخزين لكلمة مرور", section)
        self.assertIn("لا قراءة كوكيز", section)


class ReusabilityVerdictTests(unittest.TestCase):
    """Acceptance: the document must state clearly whether the connector is reusable."""

    def test_verdict_section_states_both_sides(self) -> None:
        text = _read_doc()
        section = text.split("## 14. هل موصل Arena قابل لإعادة الاستخدام", 1)[1].split("## 15.", 1)[0]
        self.assertIn("قابل لإعادة الاستخدام", section)
        self.assertIn("لا يُنسخ", section)  # the userscript body must be explicitly excluded
        self.assertIn("ArenaBrowserAdapter", section)

    def test_licence_blocker_is_recorded(self) -> None:
        text = _read_doc()
        self.assertIn("license: null", text)
        self.assertIn("بلا ترخيص", text)

    def test_evidence_of_execution_is_recorded(self) -> None:
        text = _read_doc()
        self.assertIn("tests/manual/probe_aatm_connector.py", text)
        self.assertIn("28/28", text)
        section = text.split("## 15. ما تم التحقق منه بالتنفيذ", 1)[1].split("## 16.", 1)[0]
        self.assertIn("لم يُختبر", section)

    def test_documentation_drift_finding_is_recorded(self) -> None:
        text = _read_doc()
        self.assertIn("minimum delay between requests and a daily cap", text)
        self.assertIn("تناقض توثيقي", text)


if __name__ == "__main__":
    unittest.main()
