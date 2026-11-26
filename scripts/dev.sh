#!/usr/bin/env bash
# =============================================================================
# scripts/dev.sh — تشغيل الخلفية والواجهة الأمامية محليًا بدون Docker
# (البند 3 و 22 من المواصفة — مسار التطوير البديل عن حاويات Compose)
#
# ماذا يفعل:
#   1. يولّد .env من .env.example إن لم يكن موجودًا (نفس منطق setup.sh).
#   2. يقرأ متغيّرات .env بأمان (بدون source/eval) مثل BACKEND_PORT و APP_IMPORT.
#   3. يهيّئ بيئة بايثون (.venv) ويثبّت backend/requirements.txt عند تغيّرها.
#   4. يشغّل uvicorn بـ --reload على المضيف/المنفذ المطلوبين.
#   5. يشغّل خادم تطوير الواجهة (npm run dev) عند وجود frontend/package.json.
#   6. ينهي العمليتين معًا عند Ctrl+C (SIGINT/SIGTERM) أو عند موت إحداهما.
#
# الخيارات:
#   --backend-only      الخلفية وحدها
#   --frontend-only     الواجهة وحدها
#   --no-install        تخطّي تثبيت الاعتماديات (venv / npm install)
#   --port N            تجاوز منفذ الخلفية (افتراضيًا BACKEND_PORT أو 8000)
#   --host H            تجاوز مضيف استماع الخلفية (افتراضيًا BACKEND_HOST أو 127.0.0.1)
#   --migrate           يطبّق هجرات Alembic قبل التشغيل (مثل MIGRATE_ON_START=1)
#   --dry-run           يطبع الأوامر التي كان سينفّذها ثم يخرج 0 بلا تشغيل
#   -h, --help          هذه الرسالة
#
# لا يحتاج هذا المسار إلى Docker. للتشغيل بالحاويات: docker compose up --build
# =============================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

usage() {
  cat <<'USAGE'
الاستخدام: ./scripts/dev.sh [خيارات]

  --backend-only     تشغيل الخلفية وحدها
  --frontend-only    تشغيل الواجهة الأمامية وحدها
  --no-install       تخطّي تثبيت الاعتماديات (venv / pip / npm install)
  --port N           تجاوز منفذ الخلفية (افتراضي: BACKEND_PORT أو 8000)
  --host H           تجاوز مضيف استماع الخلفية (افتراضي: BACKEND_HOST أو 127.0.0.1)
  --migrate          تطبيق هجرات Alembic (alembic upgrade head) قبل التشغيل
  --dry-run          طباعة الأوامر دون تنفيذها والخروج بالقيمة 0
  -h, --help         عرض هذه الرسالة
USAGE
}

die()  { printf 'خطأ: %s\n' "$*" >&2; exit 1; }
info() { printf '==> %s\n' "$*"; }
warn() { printf 'تنبيه: %s\n' "$*" >&2; }

RUN_BACKEND=1
RUN_FRONTEND=1
DO_INSTALL=1
DRY_RUN=0
DO_MIGRATE=0
PORT_SET=0
HOST_SET=0

# -------------------------------------------------
# 0) تحليل الوسائط
# -------------------------------------------------
while [ $# -gt 0 ]; do
  case "$1" in
    --backend-only)  RUN_FRONTEND=0 ;;
    --frontend-only) RUN_BACKEND=0 ;;
    --no-install)    DO_INSTALL=0 ;;
    --dry-run)       DRY_RUN=1 ;;
    --migrate)       DO_MIGRATE=1 ;;
    --port)   [ $# -ge 2 ] || die "--port يحتاج قيمة"; DEV_PORT_ARG="$2"; PORT_SET=1; shift ;;
    --host)   [ $# -ge 2 ] || die "--host يحتاج قيمة"; DEV_HOST_ARG="$2"; HOST_SET=1; shift ;;
    --port=*) DEV_PORT_ARG="${1#*=}"; PORT_SET=1 ;;
    --host=*) DEV_HOST_ARG="${1#*=}"; HOST_SET=1 ;;
    -h|--help) usage; exit 0 ;;
    *) die "وسيط غير معروف: $1 — جرّب: ./scripts/dev.sh --help" ;;
  esac
  shift
done

# -------------------------------------------------
# 1) ملف .env: توليد من .env.example، ثم قراءة آمنة
# -------------------------------------------------
ensure_env_file() {
  local example="$ROOT_DIR/.env.example" target="$ROOT_DIR/.env"
  if [ ! -f "$example" ]; then
    warn ".env.example غير موجود — تخطّي توليد .env"
    return 0
  fi
  if [ -f "$target" ]; then
    info "ملف .env موجود بالفعل، لا يُكتب فوقه."
  else
    cp -- "$example" "$target"
    info "تم توليد .env من .env.example (مستثنى من Git — لا تُلزمه أبدًا)."
  fi
}

# يصدّر سطور KEY=VALUE من ملف .env. التعليقات والأسطر الفارغة تُتجاهل، والمفاتيح
# غير الصالحة تُتجاهل أيضًا — لهذا لا نستخدم source (قيمة مثل APP_NAME=NEXUS OSINT
# ستُفسَّر كأمر عند source).
load_env_file() {
  local file="$1" line key val
  [ -f "$file" ] || return 0
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%$'\r'}"
    case "$line" in ''|'#'*) continue ;; esac
    case "$line" in *=*) ;; *) continue ;; esac
    key="${line%%=*}"
    val="${line#*=}"
    key="$(printf '%s' "$key" | tr -d '[:space:]')"
    val="${val#"${val%%[![:space:]]*}"}"
    case "$key" in
      ''|*[!A-Za-z0-9_]*) continue ;;
      [0-9]*) continue ;;
    esac
    case "$val" in
      \"*\") val="${val#\"}"; val="${val%\"}" ;;
      \'*\') val="${val#\'}"; val="${val%\'}" ;;
    esac
    export "$key=$val"
  done < "$file"
}

ensure_env_file
load_env_file "$ROOT_DIR/.env"

DEV_HOST="${BACKEND_HOST:-127.0.0.1}"
DEV_PORT="${BACKEND_PORT:-8000}"
[ "$HOST_SET" = "1" ] && DEV_HOST="$DEV_HOST_ARG"
[ "$PORT_SET" = "1" ] && DEV_PORT="$DEV_PORT_ARG"
APP_IMPORT="${APP_IMPORT:-app.main:app}"
API_V1_PREFIX="${API_V1_PREFIX:-/api/v1}"
FRONTEND_DEV_PORT="${FRONTEND_PORT:-3000}"

# -------------------------------------------------
# 2) أدوات: إيجاد مفسّر بايثون و أمر uvicorn
# -------------------------------------------------
VENV_DIR="$ROOT_DIR/.venv"
PY_BIN=""
if [ -x "$VENV_DIR/bin/python" ]; then
  PY_BIN="$VENV_DIR/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PY_BIN="$(command -v python)"
fi

uvicorn_launcher() {
  if [ -x "$VENV_DIR/bin/uvicorn" ]; then
    printf '%s' "$VENV_DIR/bin/uvicorn"
  elif [ -n "$PY_BIN" ] && "$PY_BIN" -c 'import uvicorn' >/dev/null 2>&1; then
    printf '%s -m uvicorn' "$PY_BIN"
  elif command -v uvicorn >/dev/null 2>&1; then
    printf 'uvicorn'
  else
    printf ''
  fi
}

file_hash() {
  # بصمة قصيرة لملف المتطلبات، لتفادي إعادة التثبيت بلا داعٍ.
  if [ -n "$PY_BIN" ]; then
    "$PY_BIN" -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest()[:16])' "$1"
  else
    printf 'no-hash'
  fi
}

# -------------------------------------------------
# 3) الخلفية: venv + متطلبات + uvicorn --reload
# -------------------------------------------------
BACKEND_DIR="$ROOT_DIR/backend"
REQS_FILE="$BACKEND_DIR/requirements.txt"
BACKEND_CMD=""

if [ "$RUN_BACKEND" = "1" ]; then
  if [ ! -f "$REQS_FILE" ] && [ ! -d "$BACKEND_DIR/app" ]; then
    warn "لا يوجد backend/ في هذه النسخة من المستودع (مهمة النواة الخلفية لم تُدمج بعد) — تخطّي تشغيل الخلفية."
    RUN_BACKEND=0
  else
    info "الخلفية: تحضير بيئة بايثون..."
    if [ "$DRY_RUN" = "1" ]; then
      [ "$DO_INSTALL" = "1" ] && [ ! -d "$VENV_DIR" ] && printf '[dry-run] %s\n' "${PY_BIN:-python3} -m venv $VENV_DIR"
      [ "$DO_INSTALL" = "1" ] && [ -f "$REQS_FILE" ] && printf '[dry-run] %s\n' "${PY_BIN:-python3} -m pip install --upgrade pip && ${PY_BIN:-python3} -m pip install -r backend/requirements.txt && ${PY_BIN:-python3} -m pip install 'uvicorn>=0.30'"
    elif [ "$DO_INSTALL" = "1" ]; then
      if [ ! -d "$VENV_DIR" ]; then
        [ -n "$PY_BIN" ] || die "python3 غير متوفر — ثبّت Python 3.11+ أو شغّل scripts/setup.sh"
        info "إنشاء .venv..."
        "$PY_BIN" -m venv "$VENV_DIR"
        PY_BIN="$VENV_DIR/bin/python"
      fi
      if [ -f "$REQS_FILE" ]; then
        marker="$VENV_DIR/.requirements-hash"
        want="$(file_hash "$REQS_FILE")"
        have="$(cat "$marker" 2>/dev/null || printf '')"
        if [ "$want" != "$have" ]; then
          info "تثبيت اعتماديات الخلفية من backend/requirements.txt..."
          "$PY_BIN" -m pip install --upgrade pip >/dev/null
          "$PY_BIN" -m pip install -r "$REQS_FILE"
          printf '%s\n' "$want" > "$marker"
        else
          info "اعتماديات الخلفية مثبتة ومطابقة لـ requirements.txt — تخطّي التثبيت."
        fi
      fi
      # ملاحظة: backend/requirements.txt لا يعلن uvicorn (ولا requirements-dev.txt)،
      # فيُثبَّت هنا صراحة لأن تشغيل الخادم يحتاجه.
      if ! "$PY_BIN" -c 'import uvicorn' >/dev/null 2>&1; then
        info "تثبيت uvicorn (غير معلن في requirements.txt)..."
        "$PY_BIN" -m pip install "uvicorn>=0.30"
      fi
    fi
    # الحزمة الجذرية هي app داخل backend/، لذا التشغيل يكون من backend/ مع
    # PYTHONPATH=backend (نفس ما تفعله الصورة في الحاوية).
    if [ "$DRY_RUN" = "1" ]; then
      BACKEND_CMD="(cd '$BACKEND_DIR' && env PYTHONPATH='$BACKEND_DIR' uvicorn '$APP_IMPORT' --host '$DEV_HOST' --port '$DEV_PORT' --reload --reload-dir '$BACKEND_DIR')"
    else
      UV_CMD="$(uvicorn_launcher)"
      [ -n "$UV_CMD" ] || die "uvicorn غير مثبت. شغّل: ./scripts/setup.sh  أو: ${PY_BIN:-python3} -m pip install 'uvicorn>=0.30'"
      BACKEND_CMD="(cd '$BACKEND_DIR' && env PYTHONPATH='$BACKEND_DIR' $UV_CMD '$APP_IMPORT' --host '$DEV_HOST' --port '$DEV_PORT' --reload --reload-dir '$BACKEND_DIR')"
    fi
    if [ "$DO_MIGRATE" = "1" ]; then
      if [ "$DRY_RUN" = "1" ]; then
        printf '[dry-run] %s\n' "(cd '$BACKEND_DIR' && env PYTHONPATH='$BACKEND_DIR' alembic upgrade head)"
      elif [ -f "$BACKEND_DIR/alembic.ini" ]; then
        info "تطبيق هجرات Alembic قبل التشغيل..."
        (cd "$BACKEND_DIR" && PYTHONPATH="$BACKEND_DIR" "${PY_BIN:-python3}" -m alembic upgrade head)
      else
        warn "لا backend/alembic.ini — تخطّي الهجرات."
      fi
    fi
    info "الخلفية ستعمل على http://$DEV_HOST:$DEV_PORT$API_V1_PREFIX/health  (APP_IMPORT=$APP_IMPORT)"
  fi
fi

# -------------------------------------------------
# 4) الواجهة الأمامية: npm install + npm run dev
# -------------------------------------------------
FRONTEND_DIR="$ROOT_DIR/frontend"
FRONTEND_CMD=""

if [ "$RUN_FRONTEND" = "1" ]; then
  if [ ! -f "$FRONTEND_DIR/package.json" ]; then
    warn "لا يوجد frontend/package.json بعد (مهمة الواجهة الأمامية لم تُدمج بعد) — تخطّي تشغيل الواجهة."
    RUN_FRONTEND=0
  elif ! command -v npm >/dev/null 2>&1; then
    die "npm غير متوفر — ثبّت Node.js 20+ لتشغيل الواجهة الأمامية."
  else
    if [ "$DRY_RUN" = "1" ]; then
      [ "$DO_INSTALL" = "1" ] && printf '[dry-run] %s\n' "(cd $FRONTEND_DIR && npm install --no-audit --no-fund)"
      FRONTEND_CMD="(cd '$FRONTEND_DIR' && npm run dev -- --host 0.0.0.0 --port '$FRONTEND_DEV_PORT')"
    else
      if [ "$DO_INSTALL" = "1" ] && [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        info "تثبيت حزم الواجهة الأمامية (npm install)..."
        (cd "$FRONTEND_DIR" && npm install --no-audit --no-fund)
      fi
      FRONTEND_CMD="(cd '$FRONTEND_DIR' && npm run dev -- --host 0.0.0.0 --port '$FRONTEND_DEV_PORT')"
    fi
    info "الواجهة ستعمل على http://localhost:$FRONTEND_DEV_PORT  (خادم التطوير يوجّه /api إلى http://$DEV_HOST:$DEV_PORT)"
  fi
fi

if [ "$RUN_BACKEND" = "0" ] && [ "$RUN_FRONTEND" = "0" ]; then
  info "لا شيء للتشغيل: لا backend/ ولا frontend/ في هذه النسخة من المستودع."
  info "مسار الحاويات جاهز متى وُجد Docker: docker compose up --build"
  [ "$DRY_RUN" = "1" ] && exit 0
  exit 1
fi

if [ "$DRY_RUN" = "1" ]; then
  [ -n "$BACKEND_CMD" ]  && printf '[dry-run] %s\n' "$BACKEND_CMD"
  [ -n "$FRONTEND_CMD" ] && printf '[dry-run] %s\n' "$FRONTEND_CMD"
  info "dry-run اكتمل — لم تُشغَّل أي عملية."
  exit 0
fi

# -------------------------------------------------
# 5) التشغيل والمراقبة والتنظيف
# -------------------------------------------------
PIDS=()
HAVE_SETSID=0
command -v setsid >/dev/null 2>&1 && HAVE_SETSID=1
SELF_PGID="$(ps -o pgid= -p $$ 2>/dev/null | tr -d '[:space:]')"

child_alive() { kill -0 "$1" 2>/dev/null; }

# مجموعة العمليات الخاصة بعملية ابن، بشرط أن تكون معزولة (setsid) حتى لا نُطبق
# الإشارة على مجموعة dev.sh نفسها.
job_pgid() {
  local pgid
  pgid="$(ps -o pgid= -p "$1" 2>/dev/null | tr -d '[:space:]')"
  [ -n "$pgid" ] || return 1
  [ "$pgid" != "$SELF_PGID" ] || return 1
  printf '%s' "$pgid"
}

# الأبناء قد يتركون أبناءً لهم؛ نجمع النسل من جدول العمليات حين لا تكون هناك
# مجموعة معزولة نقتلها دفعة واحدة.
descendants() {
  ps -ax -o pid=,ppid= 2>/dev/null | awk -v root="$1" '
    { ppid[$1] = $2; order[++n] = $1 }
    END {
      for (i = 1; i <= n; i++) {
        q = order[i]; d = 0
        while (q in ppid && q != 1) { if (ppid[q] + 0 == root + 0) { d = 1; break } q = ppid[q] }
        if (d) print order[i]
      }
    }'
}

job_pids() {
  local pid kid
  for pid in "${PIDS[@]:-}"; do
    [ -n "$pid" ] || continue
    printf '%s\n' "$pid"
    for kid in $(descendants "$pid"); do printf '%s\n' "$kid"; done
  done
}

signal_job() {
  local sig="$1" pid pgid target
  for pid in "${PIDS[@]:-}"; do
    [ -n "$pid" ] || continue
    if pgid="$(job_pgid "$pid")"; then
      kill "-$sig" -- "-$pgid" 2>/dev/null || kill "-$sig" "$pid" 2>/dev/null || true
    else
      for target in "$pid" $(descendants "$pid"); do
        kill "-$sig" "$target" 2>/dev/null || true
      done
    fi
  done
}

job_alive() {
  local pid pgid member
  for pid in "${PIDS[@]:-}"; do
    [ -n "$pid" ] || continue
    if pgid="$(job_pgid "$pid")"; then
      for member in $(ps -ax -o pid=,pgid= 2>/dev/null | awk -v g="$pgid" '$2==g{print $1}'); do
        child_alive "$member" && return 0
      done
    fi
    child_alive "$pid" && return 0
  done
  return 1
}

kill_children() {
  job_alive || return 0
  info "إيقاف عمليات التطوير ومنسلها (SIGTERM)..."
  signal_job TERM
  local round
  for round in 1 2 3 4 5 6 7 8 9 10 11 12; do
    job_alive || return 0
    sleep 0.5
  done
  warn "عمليات لم تستجب لـ SIGTERM، تُنهى قسرًا (SIGKILL)."
  signal_job KILL
  for round in 1 2 3 4; do
    job_alive || return 0
    sleep 0.5
  done
}

# تنظيف عند الخروج العادي: يحافظ على رمز خروج العملية المنتهية.
cleanup() {
  local saved=$?
  trap - EXIT
  kill_children
  return "$saved"
}
# تنظيف عند الإشارة: إيقاف مُتعَمَّد برمز 0 — Ctrl+C في التطوير ليس فشلًا.
on_signal() {
  trap - INT TERM HUP EXIT
  kill_children
  exit 0
}
# الأبناء يعملون في مجموعات معزولة (setsid) حين تكون متاحة، فيقتلهم هذا الفخّ
# دفعة واحدة بلا عمليات يتيمة تحتجز المنافذ؛ وعند غياب setsid نقتل الابن ونسله.
trap on_signal INT TERM HUP
trap cleanup EXIT

start_job() {
  if [ "$HAVE_SETSID" = "1" ]; then
    setsid sh -c "$1" &
  else
    sh -c "$1" &
  fi
  PIDS+=("$!")
}

info "ابدأ التطوير — Ctrl+C يوقف الخدمتين معًا."
[ -n "$BACKEND_CMD" ]  && start_job "$BACKEND_CMD"
[ -n "$FRONTEND_CMD" ] && start_job "$FRONTEND_CMD"

EXIT_CODE=0
if [ "${BASH_VERSINFO[0]}" -gt 4 ] || { [ "${BASH_VERSINFO[0]}" -eq 4 ] && [ "${BASH_VERSINFO[1]}" -ge 3 ]; }; then
  # انتظار أي عملية: إذا ماتت إحداهما نُوقف البقية ونخرج برمزها.
  wait -n || EXIT_CODE=$?
  # الإشارة تُعالج في on_signal؛ هنا خروج عادي بعد موت إحدى العمليتين.
  case "$EXIT_CODE" in 128*) EXIT_CODE=0 ;; esac
else
  while job_alive; do sleep 1; done
fi
cleanup
exit "$EXIT_CODE"
