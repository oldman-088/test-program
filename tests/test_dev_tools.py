"""اختبارات آلية لمخرجات مهمة أدوات المطورين (AATM-ca93a34d).

تؤكد هذه الاختبارات وجود ملفات إعداد أدوات المطورين وصلاحيتها. لا تختبر أي ميزة
تطبيقية من المرحلة 2 أو المرحلة 7، ولا تستدعي `make test` لتجنب التكرار اللانهائي
(يتم التحقق من نجاح `make test` يدويًا في جذر المستودع).
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# -------------------------------------------------
# الملفات المتوقعة لهذه المهمة
# -------------------------------------------------
EXPECTED_FILES = [
    ".editorconfig",
    ".pre-commit-config.yaml",
    ".vscode/extensions.json",
    ".vscode/settings.json",
    "Makefile",
    "backend/pyproject.toml",
    "backend/requirements-dev.txt",
]


def test_dev_tools_files_exist():
    """يجب أن توجد كل ملفات أدوات المطورين المتوقعة في جذر المستودع."""
    for rel in EXPECTED_FILES:
        assert (ROOT / rel).is_file(), f"ملف مفقود: {rel}"


# -------------------------------------------------
# .editorconfig
# -------------------------------------------------
def test_editorconfig_has_required_settings():
    """يجب أن يضبط .editorconfig الترميز ونهاية السطر وإزالة المسافات البادئة."""
    editorconfig = (ROOT / ".editorconfig").read_text(encoding="utf-8")
    assert "root = true" in editorconfig
    assert "charset = utf-8" in editorconfig
    assert "end_of_line = lf" in editorconfig
    assert "trim_trailing_whitespace = true" in editorconfig
    assert "insert_final_newline = true" in editorconfig


# -------------------------------------------------
# .pre-commit-config.yaml
# -------------------------------------------------
PRE_COMMIT_REQUIRED_HOOKS = ["trailing-whitespace", "end-of-file-fixer", "ruff-check", "ruff-format"]


def test_pre_commit_has_required_hooks():
    """يجب أن يحتوي .pre-commit-config.yaml على الخطافات الأربعة المستهدفة لـ backend/."""
    pre_commit = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    for hook in PRE_COMMIT_REQUIRED_HOOKS:
        assert hook in pre_commit, f".pre-commit-config.yaml يفتقر للخطاف: {hook}"
    assert "backend/" in pre_commit, ".pre-commit-config.yaml غير موجه إلى دليل backend/"


# -------------------------------------------------
# .vscode
# -------------------------------------------------
def test_vscode_recommends_python_and_eslint():
    """يجب أن توصي ملفات VS Code بإضافة Python و ESLint."""
    extensions = (ROOT / ".vscode/extensions.json").read_text(encoding="utf-8")
    settings = (ROOT / ".vscode/settings.json").read_text(encoding="utf-8")
    assert "ms-python.python" in extensions, "extensions.json لا توصي بإضافة Python"
    assert "dbaeumer.vscode-eslint" in extensions, "extensions.json لا توصي بإضافة ESLint"
    assert "python" in settings.lower(), "settings.json لا يضبط إعدادات Python"
    assert "eslint" in settings.lower(), "settings.json لا يضبط إعدادات ESLint"


# -------------------------------------------------
# Makefile
# -------------------------------------------------
MAKEFILE_REQUIRED_TARGETS = [
    "setup",
    "dev-backend",
    "dev-frontend",
    "test",
    "lint",
    "format",
    "db-upgrade",
    "db-downgrade",
    "docker-up",
    "docker-down",
]


def test_makefile_has_required_targets():
    """يجب أن يحتوي Makefile على كل الأهداف المطلوبة."""
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in MAKEFILE_REQUIRED_TARGETS:
        assert f"{target}:" in makefile, f"Makefile يفتقر للهدف: {target}"


# -------------------------------------------------
# backend/pyproject.toml
# -------------------------------------------------
def test_backend_pyproject_ruff_and_pytest_only():
    """يجب أن يحتوي backend/pyproject.toml على إعدادات ruff و pytest فقط، بدون اعتماديات تشغيلية."""
    pyproject = (ROOT / "backend/pyproject.toml").read_text(encoding="utf-8")
    assert "[tool.ruff]" in pyproject, "backend/pyproject.toml يفتقر لإعدادات ruff"
    assert "[tool.pytest.ini_options]" in pyproject, "backend/pyproject.toml يفتقر لإعدادات pytest"
    assert "dependencies" not in pyproject, "backend/pyproject.toml يكرر الاعتمادات التشغيلية"


# -------------------------------------------------
# backend/requirements-dev.txt
# -------------------------------------------------
REQUIREMENTS_DEV_REQUIRED = ["ruff", "pytest", "pytest-cov", "mypy"]


def test_backend_requirements_dev_contains_dev_tools():
    """يجب أن يحتوي backend/requirements-dev.txt على أدوات التطوير المطلوبة."""
    requirements_dev = (ROOT / "backend/requirements-dev.txt").read_text(encoding="utf-8")
    for tool in REQUIREMENTS_DEV_REQUIRED:
        assert tool in requirements_dev, f"backend/requirements-dev.txt يفتقر للأداة: {tool}"
