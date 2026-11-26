#!/usr/bin/env bash
#
# scripts/setup.sh — NEXUS OSINT fase 1 setup (Linux/macOS)
#
# ما يفعله هذا السكريبت:
# 1. إنشاء بيئة افتراضية بايثون (.venv) وتثبيت متطلبات الخلفية.
# 2. تثبيت حزم الواجهة الأمامية عبر npm (عند توفرها).
# 3. توليد ملف .env من .env.example باستخدام بايثون (إن لم يكن موجودًا).
#
# ملاحظة: fase 1 توثيقية وتأسيسية فقط. لا تُنفَّذ أي ميزة applicative هنا.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== NEXUS OSINT setup.sh (fase 1) ==="
echo "Working directory: $ROOT_DIR"

# -------------------------------------------------
# 0. متطلبات النظام
# -------------------------------------------------
require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "خطأ: الأمر '$1' غير مثبت وقد يكون مطلوبًا." >&2
    return 1
  fi
}

require_command python3 || true
require_command npm   || true

# -------------------------------------------------
# 1. الخلفية: بيئة افتراضية بايثون + تثبيت المتطلبات
# -------------------------------------------------
echo "[1/3] إعداد بيئة بايثون الافتراضية (.venv)..."
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  echo "تم إنشاء .venv"
else
  echo "يوجد .venv بالفعل، تخطي الإنشاء"
fi

# تفعيل البيئة وتثبيت المتطلبات إذا وُجد ملف المتطلبات
if [ -f "backend/requirements.txt" ]; then
  echo "تثبيت متطلبات الخلفية من backend/requirements.txt..."
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install --upgrade pip
  pip install -r backend/requirements.txt
else
  echo "ملف backend/requirements.txt غير موجود بعد (سيُنشأ في fase 2). تخطي تثبيت الحزم الخلفية."
fi

# -------------------------------------------------
# 2. الواجهة الأمامية: تثبيت الحزم عبر npm
# -------------------------------------------------
echo "[2/3] تثبيت حزم الواجهة الأمامية..."
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
  (cd frontend && npm install)
  echo "تم تثبيت حزم الواجهة الأمامية."
else
  echo "مجلد frontend أو package.json غير موجود بعد (سيُنشأ في fase 7). تخطي تثبيت واجهة الأمام."
fi

# -------------------------------------------------
# 3. توليد .env من .env.example عبر بايثون
# -------------------------------------------------
echo "[3/3] توليد .env من .env.example..."
python3 - "$ROOT_DIR" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
example = root / ".env.example"
target = root / ".env"

if not example.exists():
    print("تحذير: .env.example غير موجود، لا يمكن توليد .env.")
    raise SystemExit(0)

if target.exists():
    print("ملف .env موجود بالفعل، لا يُ overwrite.")
else:
    target.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
    print("تم توليد .env من .env.example (لا تُلزم أبدًا — مستثنى من Git).")
PY

echo "=== اكتمل الإعداد بنجاح (fase 1) ==="
echo "تنبيه: المراحل 2 إلى 7 لم تُنفذ بعد."
