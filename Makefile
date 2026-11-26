# Makefile — NEXUS OSINT (أهداف التطوير في جذر المستودع)
# المنفذ: GNU Make. يتم تشغيل كل هدف من جذر المستودع.

.PHONY: setup dev-backend dev-frontend test lint format db-upgrade db-downgrade docker-up docker-down help

PYTHON ?= python3
PIP ?= pip
VENV := .venv
BACKEND := backend
VENV_BIN := $(VENV)/bin

help: ## عرض قائمة بالأهداف المتاحة
	@echo "أهداف Makefile متوفرة (NEXUS OSINT):"
	@echo "  setup          إنشاء البيئة وتثبيت الاعتماديات التشغيلية والتطويرية"
	@echo "  dev-backend    تشغيل خادم الخلفية للتطوير (يتطلب المرحلة 2)"
	@echo "  dev-frontend   تشغيل خادم الواجهة الأمامية للتطوير (يتطلب المرحلة 7)"
	@echo "  test           تشغيل اختبارات بايثون (pytest)"
	@echo "  lint           تدقيق الشيفرة باستخدام ruff (دليل backend فقط)"
	@echo "  format         تنسيق الشيفرة باستخدام ruff (دليل backend فقط)"
	@echo "  db-upgrade     ترحيل قاعدة البيانات إلى الأمام (alembic — المرحلة 2)"
	@echo "  db-downgrade   إرجاع ترحيل قاعدة البيانات (alembic — المرحلة 2)"
	@echo "  docker-up      رفع خدمات Docker Compose (يتطلب Docker)"
	@echo "  docker-down    إيقاف خدمات Docker Compose"

setup: ## إنشاء البيئة الافتراضية وتثبيت الاعتماديات
	$(PYTHON) -m venv $(VENV)
	. $(VENV_BIN)/activate && $(PIP) install --upgrade pip
	. $(VENV_BIN)/activate && $(PIP) install -r $(BACKEND)/requirements-dev.txt
	@if [ -f $(BACKEND)/requirements.txt ]; then \
		. $(VENV_BIN)/activate && $(PIP) install -r $(BACKEND)/requirements.txt; \
	fi
	@echo "انتهى الإعداد. فعّل البيئة: source $(VENV)/bin/activate"

test: ## تشغيل اختبارات بايثون (pytest)
	@$(PYTHON) -m pytest --version >/dev/null 2>&1 || { \
		echo "تثبيت pytest..."; \
		$(PIP) install --quiet --break-system-packages pytest pytest-cov 2>/dev/null \
		|| $(PIP) install --quiet pytest pytest-cov; \
	}
	$(PYTHON) -m pytest tests/ -v

lint: ## تدقيق الشيفرة باستخدام ruff (دليل backend فقط)
	@$(PYTHON) -m ruff --version >/dev/null 2>&1 || $(PIP) install --quiet --break-system-packages ruff 2>/dev/null || $(PIP) install --quiet ruff
	$(PYTHON) -m ruff check $(BACKEND)

format: ## تنسيق الشيفرة باستخدام ruff (دليل backend فقط)
	@$(PYTHON) -m ruff --version >/dev/null 2>&1 || $(PIP) install --quiet --break-system-packages ruff 2>/dev/null || $(PIP) install --quiet ruff
	$(PYTHON) -m ruff format $(BACKEND)

db-upgrade: ## ترحيل قاعدة البيانات إلى الأمام (alembic — غير متاح حتى المرحلة 2)
	@echo "db-upgrade: غير متاح بعد — تُنشأ ترحيلات Alembic في المرحلة 2 (الbackbone الخلفية)." >&2
	@exit 0

db-downgrade: ## إرجاع ترحيل قاعدة البيانات (alembic — غير متاح حتى المرحلة 2)
	@echo "db-downgrade: غير متاح بعد — تُنشأ ترحيلات Alembic في المرحلة 2 (الbackbone الخلفية)." >&2
	@exit 0

dev-backend: ## تشغيل خادم الخلفية للتطوير (غير متاح حتى المرحلة 2)
	@echo "dev-backend: خادم الخلفية غير موجود بعد — تُنشأ كود back-end في المرحلة 2 (backend/app)." >&2
	@exit 0

dev-frontend: ## تشغيل خادم الواجهة الأمامية للتطوير (غير متاح حتى المرحلة 7)
	@echo "dev-frontend: الواجهة الأمامية غير موجودة بعد — تُنشأ في المرحلة 7 (frontend/)." >&2
	@exit 0

docker-up: ## رفع خدمات Docker Compose (يتوفر Docker في البيئات التي تدعمه فقط)
	@echo "docker-up: Docker غير مثبت في هذه البيئة (ENVIRONMENT.md). يتطلب Docker Compose." >&2
	@exit 0

docker-down: ## إيقاف خدمات Docker Compose
	@echo "docker-down: Docker غير مثبت في هذه البيئة (ENVIRONMENT.md)." >&2
	@exit 0
