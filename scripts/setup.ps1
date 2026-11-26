# scripts/setup.ps1 — NEXUS OSINT fase 1 setup (PowerShell / Windows)
#
# ما يفعله هذا السكريبت:
# 1. إنشاء بيئة افتراضية بايثون (.venv) وتثبيت متطلبات الخلفية.
# 2. تثبيت حزم الواجهة الأمامية عبر npm (عند توفرها).
# 3. توليد ملف .env من .env.example باستخدام بايثون (إن لم يكن موجودًا).
#
# ملاحظة: fase 1 توثيقية وتأسيسية فقط. لا تُنفَّذ أي ميزة applicative هنا.
$ErrorActionPreference = "Stop"

$RootDir = (Get-Item (Join-Path $PSScriptRoot "..")).FullName
Set-Location $RootDir

Write-Host "=== NEXUS OSINT setup.ps1 (fase 1) ==="
Write-Host "Working directory: $RootDir"

# -------------------------------------------------
# 0. التحقق من توفر الأوامر
# -------------------------------------------------
function Test-Command {
    param([string]$Command)
    if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) {
        Write-Warning "الأمر '$Command' غير مثبت وقد يكون مطلوبًا."
        return $false
    }
    return $true
}

Test-Command "python" | Out-Null
Test-Command "python3" | Out-Null
Test-Command "npm" | Out-Null

# -------------------------------------------------
# 1. الخلفية: بيئة افتراضية بايثون + تثبيت المتطلبات
# -------------------------------------------------
Write-Host "[1/3] إعداد بيئة بايثون الافتراضية (.venv)..."
$PythonExe = if (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" } else { "python" }
$VenvDir = Join-Path $RootDir ".venv"

if (-not (Test-Path $VenvDir)) {
    & $PythonExe -m venv $VenvDir
    Write-Host "تم إنشاء .venv"
} else {
    Write-Host "يوجد .venv بالفعل، تخطي الإنشاء"
}

$ReqFile = Join-Path $RootDir "backend/requirements.txt"
if (Test-Path $ReqFile) {
    Write-Host "تثبيت متطلبات الخلفية من backend/requirements.txt..."
    $Activate = Join-Path $VenvDir @("Scripts","Activate.ps1") -ChildPath ''
    # تجاوز قيود ExecutionPolicy لهذا الجلسة فقط
    & $Activate
    & $PythonExe -m pip install --upgrade pip
    & $PythonExe -m pip install -r $ReqFile
} else {
    Write-Host "ملف backend/requirements.txt غير موجود بعد (سيُنشأ في fase 2). تخطي تثبيت الحزم الخلفية."
}

# -------------------------------------------------
# 2. الواجهة الأمامية: تثبيت الحزم عبر npm
# -------------------------------------------------
Write-Host "[2/3] تثبيت حزم الواجهة الأمامية..."
$FrontendDir = Join-Path $RootDir "frontend"
$PkgFile = Join-Path $FrontendDir "package.json"
if ((Test-Path $FrontendDir) -and (Test-Path $PkgFile)) {
    Push-Location $FrontendDir
    npm install
    Pop-Location
    Write-Host "تم تثبيت حزم الواجهة الأمامية."
} else {
    Write-Host "مجلد frontend أو package.json غير موجود بعد (سيُنشأ في fase 7). تخطي تثبيت واجهة الأمام."
}

# -------------------------------------------------
# 3. توليد .env من .env.example عبر بايثون
# -------------------------------------------------
Write-Host "[3/3] توليد .env من .env.example عبر بايثون..."
$Example = Join-Path $RootDir ".env.example"
$Target = Join-Path $RootDir ".env"

$PythonExe = if (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" } else { "python" }
& $PythonExe - "$RootDir" <<'PY'
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

Write-Host "=== اكتمل الإعداد بنجاح (fase 1) ==="
Write-Host "تنبيه: المراحل 2 إلى 7 لم تُنفذ بعد."
