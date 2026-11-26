# -*- coding: utf-8 -*-
"""اختبارات آلية لمخرجات مهمة تصميم المنظم والجدولة (المرحلة 3).

المهمة: AATM-06c3aca9-2eed-48fd-9f89-a70c3a911166

تؤكد هذه الاختبارات وجود وثيقة التصميم `docs/ORCHESTRATOR_DESIGN.md` وتغطية
الأقسام الملزمة (الجدولة الذرية، آلة الحالات، الإيجارات، عمال AgentLoop الأربعة،
بوابة المراجع)، وأن المسبار المضمّن صالح نحويًا ومكتفٍ بالمكتبة القياسية.
لا تختبر أي كود تطبيقي — المهمة توثيقية تصميمية فقط.

تشغيل المسبار الكامل اختياري: NEXUS_RUN_PROBE=1 python -m pytest tests/test_orchestrator_design.py
"""

import ast
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "ORCHESTRATOR_DESIGN.md"

TASK_ID = "AATM-06c3aca9-2eed-48fd-9f89-a70c3a911166"


def read_doc() -> str:
    assert DOC_PATH.exists(), f"ملف مفقود: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def extract_probe_source() -> str:
    """استخراج كتلة بايثون الوحيدة (المسبار) من الوثيقة."""
    blocks = re.findall(r"```python\n(.*?)```", read_doc(), flags=re.DOTALL)
    assert len(blocks) == 1, "يجب أن تحتوي الوثيقة كتلة بايثون واحدة بالضبط (المسبار)"
    return blocks[0]


# -------------------------------------------------
# وجود الوثيقة وهوية المهمة والنطاق
# -------------------------------------------------
def test_design_file_exists():
    assert DOC_PATH.is_file(), "docs/ORCHESTRATOR_DESIGN.md يجب أن يوجد"
    assert len(read_doc()) > 5000, "الوثيقة أقصر من المتوقع لتصميم شامل"


def test_task_identity_and_scope():
    t = read_doc()
    assert TASK_ID in t, "يجب أن تحمل الوثيقة معرّف المهمة"
    assert "توثيق تصميمي فقط" in t, "يجب أن تصرّح الوثيقة أن النطاق تصميمي فقط"
    assert "لا يُضاف أي كود تطبيقي" in t, "يجب أن تنص الوثيقة على عدم إضافة كود تطبيقي"
    assert "المرحلة 3" in t and "docs/ROADMAP.md" in t, "يجب ربط التصميم بخارطة الطريق"
    assert "#8" in t and "#9" in t, "يجب ذكر اعتماد التصميم على طلبات المرحلة 2 المفتوحة"


def test_verification_methodology_present():
    t = read_doc()
    assert "منهجية التحقق" in t, "يجب وجود قسم منهجية التحقق"
    assert "غير متحقق" in t, "يجب وسم الادعاءات غير المختبرة بعبارة «غير متحقق»"


# -------------------------------------------------
# الأقسام الملزمة
# -------------------------------------------------
REQUIRED_SECTIONS = [
    "المتطلبات",
    "المكونات والبنية",
    "نموذج البيانات",
    "آلة حالات المهمة",
    "الجدولة الذرية",
    "الإيجارات والنبضات والتعافي",
    "عامل AgentLoop",
    "مدير المهام",
    "الإعدادات المقترحة",
    "حالات الفشل والتعافي",
    "قابلية المراقبة",
    "حدود التصميم وغير المتحقق",
    "خطة التنفيذ اللاحقة",
    "الملحق أ",
]


def test_required_sections_present():
    t = read_doc()
    for section in REQUIRED_SECTIONS:
        assert section in t, f"الوثيقة تفتقر للقسم: {section}"


# -------------------------------------------------
# آلة الحالات والجدولة الذرية
# -------------------------------------------------
def test_state_machine_covers_all_states():
    t = read_doc()
    for state in ("queued", "running", "succeeded", "failed", "cancelled"):
        assert state in t, f"الحالة مفقودة من التصميم: {state}"
    assert "max_attempts" in t, "يجب توثيق سقف المحاولات"
    assert "cancel_requested" in t, "يجب توثيق الإلغاء التعاوني"


def test_atomic_claim_styles_documented():
    t = read_doc()
    assert "UPDATE tasks" in t, "يجب توثيق استعلام المطالبة"
    assert "RETURNING id" in t, "يجب توثيق نمط UPDATE … RETURNING"
    assert "BEGIN IMMEDIATE" in t, "يجب توثيق النمط المحمول BEGIN IMMEDIATE"
    assert "idx_tasks_claim" in t, "يجب توثيق فهرس المطالبة"
    assert "SKIP LOCKED" in t, "يجب ذكر مسار Postgres اللاحق (غير المتحقق)"


def test_connection_pragmas_documented():
    t = read_doc()
    assert "journal_mode=WAL" in t, "يجب توثيق وضع WAL"
    assert "busy_timeout" in t, "يجب توثيق مهلة انتظار القفل"


def test_measured_results_recorded():
    t = read_doc()
    assert "4000" in t, "يجب تسجيل إجمالي المطالبات المقيسة (4000)"
    assert "صفر ازدواج" in t, "يجب تسجيل نتيجة صفر ازدواج"
    assert "3.40.1" in t and "3.11.2" in t, "يجب تسجيل إصداري SQLite وPython المستخدمين في القياس"


# -------------------------------------------------
# العمال والإيجارات وبوابة المراجع
# -------------------------------------------------
def test_worker_default_is_four():
    t = read_doc()
    assert "أربعة افتراضيًا" in t, "يجب تثبيت العدد الافتراضي للعمال (أربعة) من المواصفة"
    assert "NEXUS_WORKER_COUNT" in t, "يجب توثيق متغير عدد العمال"


def test_leases_heartbeats_and_fencing():
    t = read_doc()
    assert "lease_expires_at" in t, "يجب توثيق عمود انتهاء الإيجار"
    assert "Reaper" in t, "يجب توثيق مكوّن الاسترجاع"
    assert "السياج" in t and "fencing" in t, "يجب توثيق السياج ضد العامل الزومبي"
    assert "at-least-once" in t, "يجب التصريح بدلالية التنفيذ at-least-once"
    assert "agent_sessions" in t, "يجب التكامل مع جلسات العمال من المرحلة 2 (#9)"


def test_reviewer_gate_and_isolated_branches():
    t = read_doc()
    assert "لا يدمج" in t, "يجب النص صراحةً على أن العامل لا يدمج الطلبات"
    assert "فروع Git معزولة" in t or "فرع Git معزول" in t, "يجب توثيق عزل العمل في فروع Git"
    assert "[AATM-" in t, "يجب توثيق عنوان PR بمعرّف المهمة"


def test_configuration_table_present():
    t = read_doc()
    for var in (
        "NEXUS_LEASE_SECONDS",
        "NEXUS_HEARTBEAT_SECONDS",
        "NEXUS_REAPER_INTERVAL_SECONDS",
        "NEXUS_MAX_ATTEMPTS",
        "NEXUS_TASK_TIMEOUT_SECONDS",
        "NEXUS_CLAIM_STYLE",
        "DATABASE_URL",
    ):
        assert var in t, f"متغير إعداد مفقود: {var}"


def test_degraded_mode_without_ai():
    t = read_doc()
    assert "تدهور" in t, "يجب توثيق مسار التدهور الآمن بلا ذكاء اصطناعي"
    assert "بلا AI" in t or "بلا ذكاء اصطناعي" in t, "يجب النص على العمل بلا مزوّد"


# -------------------------------------------------
# صلاحية المسبار المضمّن
# -------------------------------------------------
def test_embedded_probe_compiles():
    source = extract_probe_source()
    compile(source, "<orchestrator-probe>", "exec")


def test_embedded_probe_is_stdlib_only():
    tree = ast.parse(extract_probe_source())
    allowed = {"multiprocessing", "os", "sqlite3", "sys", "tempfile", "time"}
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported <= allowed, f"المسبار يستورد حزمًا خارج المكتبة القياسية: {imported - allowed}"


def test_embedded_probe_matches_documented_parameters():
    source = extract_probe_source()
    for constant in ("WORKERS = 8", "TASKS = 200", "ROUNDS = 5", "BUSY_TIMEOUT_MS = 5000"):
        assert constant in source, f"ثابت المسبار غير مطابق للنتائج الموثقة: {constant}"
    # فهرس المطالبة موجود في DDL المسبار وفي قسم نموذج البيانات معًا
    assert "CREATE INDEX idx_tasks_claim" in source
    assert "CREATE INDEX idx_tasks_claim" in read_doc().split("```python")[0]


@pytest.mark.skipif(
    os.environ.get("NEXUS_RUN_PROBE") != "1",
    reason="تشغيل المسبار الكامل اختياري؛ فعّله بـ NEXUS_RUN_PROBE=1",
)
def test_embedded_probe_runs_and_passes(tmp_path):
    """تشغيل المسبار فعليًا والتحقق من النتيجة ALL OK (اختياري، ~ثوانٍ)."""
    probe = tmp_path / "probe_scheduler.py"
    probe.write_text(extract_probe_source(), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(probe)],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, f"المسبار فشل:\n{result.stdout}\n{result.stderr}"
    assert "RESULT: ALL OK" in result.stdout
    assert "duplicates=0" in result.stdout
