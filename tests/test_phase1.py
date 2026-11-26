"""اختبارات آلية لمخرجات المرحلة 1 من مشروع NEXUS OSINT.

هذه الاختبارات تؤكد وجود الملفات التأسيسية وصلاحيتها، ولا تختبر أي ميزة تطبيقية
لأن المرحلة 1 توثيقية وتأسيسية فقط ولا تُنفذ أي ميزة تطبيقية.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# -------------------------------------------------
# ملفات المخرجات المتوقعة
# -------------------------------------------------
EXPECTED_FILES = [
    "README.md",
    "LICENSE",
    ".gitignore",
    ".env.example",
    "docs/ENVIRONMENT.md",
    "docs/ROADMAP.md",
    "scripts/setup.sh",
    "scripts/setup.ps1",
]


def test_expected_phase1_files_exist():
    """يجب أن توجد كل ملفات مخرجات المرحلة 1 في جذر المستودع."""
    for rel in EXPECTED_FILES:
        assert (ROOT / rel).is_file(), f"ملف مفقود: {rel}"


def test_setup_scripts_are_executable():
    """يجب أن يكون setup.sh قابل للتنفيذ."""
    assert (ROOT / "scripts/setup.sh").stat().st_mode & 0o111, "setup.sh غير قابل للتنفيذ"


# -------------------------------------------------
# .gitignore
# -------------------------------------------------
GITIGNORE_REQUIRED = [
    "node_modules",
    "dist",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".env",
    "*.sqlite3",
    ".mypy_cache",
]


def test_gitignore_contains_required_patterns():
    """يجب أن يستثني .gitignore الأنماط المطلوبة."""
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in GITIGNORE_REQUIRED:
        assert pattern in gitignore, f".gitignore لا يستثني: {pattern}"


# -------------------------------------------------
# LICENSE
# -------------------------------------------------
def test_license_is_mit():
    """يجب أن تكون LICENSE رخصة MIT."""
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in license_text
    assert "Permission is hereby granted" in license_text


# -------------------------------------------------
# README.md
# -------------------------------------------------
README_REQUIRED_SECTIONS = [
    "NEXUS OSINT",
    "المرحلة 1",
    "المراحل 2",
    "لم تُنفذ",
    "بنية المشروع",
    "تعليمات تشغيل سريعة",
]


def test_readme_contains_required_sections():
    """يجب أن يحتوي README.md على الأقسام المطلوبة."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for section in README_REQUIRED_SECTIONS:
        assert section in readme, f"README.md يفتقر للقسم: {section}"


# -------------------------------------------------
# ROADMAP.md
# -------------------------------------------------
ROADMAP_REQUIRED = ["المرحلة 1", "المرحلة 2", "المرحلة 7", "غير منفذة", "مكتملة"]


def test_roadmap_lists_seven_phases():
    """يجب أن يسرد ROADMAP.md المراحل السبعة مع حالة كل مرحلة."""
    roadmap = (ROOT / "docs/ROADMAP.md").read_text(encoding="utf-8")
    for item in ROADMAP_REQUIRED:
        assert item in roadmap, f"ROADMAP.md يفتقر للبند: {item}"


# -------------------------------------------------
# ENVIRONMENT.md
# -------------------------------------------------
ENV_REQUIRED = ["Linux", "Python", "Node", "Docker", "Git"]


def test_environment_documents_versions():
    """يجب أن توثق ENVIRONMENT.md إصدارات النظام والأدوات."""
    env = (ROOT / "docs/ENVIRONMENT.md").read_text(encoding="utf-8")
    for item in ENV_REQUIRED:
        assert item in env, f"ENVIRONMENT.md يفتقر للبند: {item}"


def test_environment_confirms_docker_unavailable():
    """يجب أن تؤكد ENVIRONMENT.md أن Docker غير مثبت بأمر فعلي."""
    env = (ROOT / "docs/ENVIRONMENT.md").read_text(encoding="utf-8")
    assert "docker --version" in env
    assert "command not found" in env


# -------------------------------------------------
# .env generation logic (mirrors setup scripts)
# -------------------------------------------------
def generate_env_from_example(root: Path) -> Path:
    """توليد .env من .env.example (منطق مشترك مع السكريبتات) دون overwriting."""
    example = root / ".env.example"
    target = root / ".env"
    assert example.exists(), ".env.example مفقود"
    if target.exists():
        return target
    target.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
    return target


def test_env_generation_from_example(tmp_path, monkeypatch):
    """يجب أن يُولّد .env من .env.example بدقة عند عدم وجوده."""
    # إنشاء نسخة مؤقتة من الجذر للاختبار دون touching الملفات الحقيقية
    example_content = "APP_NAME=example\nKEY=env:KEY\n"
    (tmp_path / ".env.example").write_text(example_content, encoding="utf-8")

    target = generate_env_from_example(tmp_path)
    assert target.exists()
    assert target.read_text(encoding="utf-8") == example_content

    # عند وجود .env مسبقًا لا يُ overwrite
    target.write_text("CUSTOM=keep\n", encoding="utf-8")
    generate_env_from_example(tmp_path)
    assert target.read_text(encoding="utf-8") == "CUSTOM=keep\n"


# -------------------------------------------------
# setup.ps1 validation
# -------------------------------------------------
def test_setup_ps1_has_no_bash_heredoc():
    """يجب ألا يحتوي setup.ps1 على صيغة heredoc من نوع bash (<<'PY') غير صالحة في PowerShell."""
    ps1 = (ROOT / "scripts/setup.ps1").read_text(encoding="utf-8")
    assert "<<'PY'" not in ps1, "setup.ps1 يحتوي على heredoc من bash غير صالح في PowerShell"


def test_setup_ps1_correct_join_path():
    """يجب ألا يستخدم setup.ps1 معلمة -ChildPath مكررة في Join-Path."""
    ps1 = (ROOT / "scripts/setup.ps1").read_text(encoding="utf-8")
    assert "-ChildPath ''" not in ps1, "setup.ps1 يستخدم -ChildPath مكررة"


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="pwsh غير متاح في هذه البيئة")
def test_setup_ps1_parses_with_pwsh():
    """إذا كان pwsh متاحًا، يجب أن يُحلل setup.ps1 بنجاح."""
    result = subprocess.run(
        ["pwsh", "-NoProfile", "-Command", f"try {{ $null = [System.Management.Automation.Language.Parser]::ParseFile('{ROOT / 'scripts/setup.ps1'}', [ref] $null, [ref] $null) -ne $null }} catch {{ exit 1 }}"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"setup.ps1 لا يُحلل عبر pwsh: {result.stderr}"


# -------------------------------------------------
# setup.sh syntax
# -------------------------------------------------
def test_setup_sh_bash_syntax():
    """يجب أن يجتاز setup.sh فحص bash -n."""
    result = subprocess.run(
        ["bash", "-n", str(ROOT / "scripts/setup.sh")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"setup.sh فشل في bash -n: {result.stderr}"
