# =============================================================================
# scripts/dev.ps1 — تشغيل الخلفية والواجهة الأمامية محليًا بدون Docker (PowerShell)
# مقابل scripts/dev.sh — البند 3 و 22 من المواصفة.
#
# ماذا يفعل:
#   1. يولّد .env من .env.example إن لم يكن موجودًا (نفس منطق setup.ps1).
#   2. يقرأ متغيّرات .env بأمان (تحليل سطور، لا Invoke-Expression).
#   3. يهيّئ بيئة بايثون (.venv) ويثبّت backend/requirements.txt عند تغيّرها.
#   4. يشغّل uvicorn بـ --reload على المضيف/المنفذ المطلوبين.
#   5. يشغّل خادم تطوير الواجهة (npm run dev) عند وجود frontend/package.json.
#   6. يوقف كل العمليات التابعة عند Ctrl+C أو عند موت إحداها.
#
# الاستخدام:
#   .\scripts\dev.ps1 [-BackendOnly] [-FrontendOnly] [-NoInstall]
#                     [[-Port] <int>] [[-HostName_] <string>] [-DryRun] [-Help]
#   .\scripts\dev.ps1 -DryRun
#
# لا يحتاج هذا المسار إلى Docker. للتشغيل بالحاويات:
#   docker compose up --build
#
# ملاحظات توافق: لا تستخدم صيغة heredoc الخاصة بـ bash، وJoin-Path بمعلمة واحدة،
# و Python يُستدعى بـ -c (وليس -Command).
# =============================================================================
[CmdletBinding()]
param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$NoInstall,
    [switch]$DryRun,
    [int]$Port = 0,
    [string]$HostName_ = '',
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

function Show-Usage {
    @"
الاستخدام: .\scripts\dev.ps1 [خيارات]

  -BackendOnly     تشغيل الخلفية وحدها
  -FrontendOnly    تشغيل الواجهة الأمامية وحدها
  -NoInstall       تخطّي تثبيت الاعتماديات (venv / pip / npm install)
  -Port N          تجاوز منفذ الخلفية (افتراضي: BACKEND_PORT أو 8000)
  -HostName_ H     تجاوز مضيف استماع الخلفية (افتراضي: BACKEND_HOST أو 127.0.0.1)
  -DryRun          طباعة الأوامر دون تنفيذها والخروج 0
  -Help            عرض هذه الرسالة
"@ | Write-Host
}

function Write-Info([string]$Message) { Write-Host "==> $Message" }
function Write-Warn([string]$Message) { Write-Host "تنبيه: $Message" -ForegroundColor Yellow }
function Stop-Dev([string]$Message) {
    Write-Host "خطأ: $Message" -ForegroundColor Red
    exit 1
}

if ($Help) { Show-Usage; exit 0 }
if ($BackendOnly -and $FrontendOnly) { Stop-Dev 'لا يمكن جمع -BackendOnly مع -FrontendOnly.' }

$RootDir = (Get-Item (Join-Path $PSScriptRoot '..')).FullName
Set-Location $RootDir

$RunBackend  = -not [bool]$FrontendOnly
$RunFrontend = -not [bool]$BackendOnly

# -------------------------------------------------
# 1) ملف .env: توليد من .env.example، ثم قراءة آمنة
# -------------------------------------------------
$ExamplePath = Join-Path $RootDir '.env.example'
$EnvPath     = Join-Path $RootDir '.env'

if (-not (Test-Path $ExamplePath)) {
    Write-Warn '.env.example غير موجود — تخطّي توليد .env'
}
elseif (Test-Path $EnvPath) {
    Write-Info 'ملف .env موجود بالفعل، لا يُكتب فوقه.'
}
else {
    Copy-Item -LiteralPath $ExamplePath -Destination $EnvPath
    Write-Info 'تم توليد .env من .env.example (مستثنى من Git — لا تُلزمه أبدًا).'
}

# قراءة KEY=VALUE فقط؛ التعليقات والأسطر الفارغة والمفاتيح غير الصالحة تُتجاهل،
# فلا تُنفَّذ أي قيمة ككود (لهذا لا نستخدم Invoke-Expression).
$EnvMap = @{}
if (Test-Path $EnvPath) {
    foreach ($line in (Get-Content -LiteralPath $EnvPath -Encoding UTF8)) {
        $text = ($line -replace "`r", '').Trim()
        if ($text -eq '' -or $text.StartsWith('#')) { continue }
        $idx = $text.IndexOf('=')
        if ($idx -lt 1) { continue }
        $key = $text.Substring(0, $idx).Trim()
        $val = $text.Substring($idx + 1).Trim()
        if ($key -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') { continue }
        if (($val.Length -ge 2) -and (($val.StartsWith('"') -and $val.EndsWith('"')) -or ($val.StartsWith("'") -and $val.EndsWith("'")))) {
            $val = $val.Substring(1, $val.Length - 2)
        }
        $EnvMap[$key] = $val
        Set-Item -Path "Env:$key" -Value $val
    }
}

function Get-EnvValue([string]$Key, [string]$Fallback) {
    if ($EnvMap.ContainsKey($Key) -and $EnvMap[$Key]) { return $EnvMap[$Key] }
    return $Fallback
}

$BackendHost = if ($HostName_) { $HostName_ } else { Get-EnvValue 'BACKEND_HOST' '127.0.0.1' }
$BackendPort = if ($Port -gt 0) { "$Port" } else { Get-EnvValue 'BACKEND_PORT' '8000' }
$AppImport   = Get-EnvValue 'APP_IMPORT' 'backend.app.main:app'
$ApiPrefix   = Get-EnvValue 'API_PREFIX' '/api'
$FrontendPort = Get-EnvValue 'FRONTEND_PORT' '3000'

# -------------------------------------------------
# 2) أدوات: مفسّر بايثون، وuvicorn، وأمر التشغيل
# -------------------------------------------------
function Get-PlatformPython([string]$VenvDir) {
    $candidates = @(
        (Join-Path $VenvDir 'Scripts/python.exe'),
        (Join-Path $VenvDir 'bin/python'),
        (Join-Path $VenvDir 'bin/python3')
    )
    foreach ($c in $candidates) {
        if (Test-Path -LiteralPath $c) { return $c }
    }
    foreach ($name in @('python', 'python3')) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { return $cmd.Source }
    }
    return $null
}

function Test-PythonModule([string]$PythonExe, [string]$Module) {
    if (-not $PythonExe) { return $false }
    try {
        & $PythonExe -c "import $Module" 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    }
    catch { return $false }
}

# -------------------------------------------------
# 3) الخلفية: venv + متطلبات + uvicorn --reload
# -------------------------------------------------
$VenvDir   = Join-Path $RootDir '.venv'
$BackendDir = Join-Path $RootDir 'backend'
$ReqFile   = Join-Path $BackendDir 'requirements.txt'
$PythonExe = Get-PlatformPython $VenvDir
$MarkerFile = Join-Path $VenvDir '.requirements-hash'
$BackendLaunched = $false

if ($RunBackend) {
    if (-not (Test-Path $ReqFile) -and -not (Test-Path (Join-Path $BackendDir 'app'))) {
        Write-Warn 'لا يوجد backend/ في هذه النسخة من المستودع (مهمة النواة الخلفية لم تُدمج بعد) — تخطّي تشغيل الخلفية.'
        $RunBackend = $false
    }
    else {
        Write-Info 'الخلفية: تحضير بيئة بايثون...'
        if ($DryRun) {
            if (-not $NoInstall -and -not (Test-Path $VenvDir)) {
                Write-Host "[dry-run] $PythonExe -m venv '$VenvDir'"
            }
            if (-not $NoInstall -and (Test-Path $ReqFile)) {
                Write-Host "[dry-run] python -m pip install --upgrade pip; python -m pip install -r backend/requirements.txt"
            }
        }
        elseif (-not $NoInstall) {
            if (-not (Test-Path $VenvDir)) {
                if (-not $PythonExe) { Stop-Dev 'python3 غير متوفر — ثبّت Python 3.11+ أو شغّل scripts/setup.ps1' }
                Write-Info 'إنشاء .venv...'
                $sysPython = $PythonExe
                & $sysPython -c "import venv, sys" | Out-Null
                & $sysPython -m venv $VenvDir
                $PythonExe = Get-PlatformPython $VenvDir
            }
            if ((Test-Path $ReqFile) -and $PythonExe) {
                $hash = & $PythonExe -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest()[:16])" $ReqFile
                $have = if (Test-Path $MarkerFile) { (Get-Content -LiteralPath $MarkerFile -Raw).Trim() } else { '' }
                if ($hash -ne $have) {
                    Write-Info 'تثبيت اعتماديات الخلفية من backend/requirements.txt...'
                    & $PythonExe -m pip install --upgrade pip | Out-Null
                    & $PythonExe -m pip install -r $ReqFile
                    if ($LASTEXITCODE -ne 0) { Stop-Dev 'فشل تثبيت backend/requirements.txt' }
                    Set-Content -LiteralPath $MarkerFile -Value $hash -Encoding UTF8
                }
                else {
                    Write-Info 'اعتماديات الخلفية مثبتة ومطابقة لـ requirements.txt — تخطّي التثبيت.'
                }
            }
        }

        $UvicornArgs = @($AppImport, '--host', $BackendHost, '--port', $BackendPort, '--reload', '--reload-dir', $BackendDir)
        if ($DryRun) {
            Write-Host "[dry-run] uvicorn $($UvicornArgs -join ' ')"
        }
        else {
            $UvExe = $null
            foreach ($c in @((Join-Path $VenvDir 'Scripts/uvicorn.exe'), (Join-Path $VenvDir 'bin/uvicorn'))) {
                if (Test-Path -LiteralPath $c) { $UvExe = $c; break }
            }
            if ($UvExe) {
                $DevFile = $UvExe; $DevArgs = $UvicornArgs
            }
            elseif (Test-PythonModule $PythonExe 'uvicorn') {
                $DevFile = $PythonExe; $DevArgs = @('-m', 'uvicorn') + $UvicornArgs
            }
            elseif (Get-Command uvicorn -ErrorAction SilentlyContinue) {
                $DevFile = (Get-Command uvicorn).Source; $DevArgs = $UvicornArgs
            }
            else {
                Stop-Dev 'uvicorn غير مثبت. شغّل: .\scripts\setup.ps1  أو: python -m pip install -r backend/requirements.txt'
            }
            Write-Info "الخلفية على http://$BackendHost`:$BackendPort$ApiPrefix  (APP_IMPORT=$AppImport)"
            $script:BackendProc = Start-Process -FilePath $DevFile -ArgumentList $DevArgs -NoNewWindow -PassThru -WorkingDirectory $RootDir
            $BackendLaunched = $true
        }
    }
}

# -------------------------------------------------
# 4) الواجهة الأمامية: npm install + npm run dev
# -------------------------------------------------
$FrontendDir = Join-Path $RootDir 'frontend'
$PkgFile     = Join-Path $FrontendDir 'package.json'
$FrontendLaunched = $false

if ($RunFrontend) {
    if (-not (Test-Path $PkgFile)) {
        Write-Warn 'لا يوجد frontend/package.json بعد (مهمة الواجهة الأمامية لم تُدمج بعد) — تخطّي تشغيل الواجهة.'
        $RunFrontend = $false
    }
    elseif (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        Stop-Dev 'npm غير متوفر — ثبّت Node.js 20+ لتشغيل الواجهة الأمامية.'
    }
    else {
        if ($DryRun) {
            if (-not $NoInstall) { Write-Host "[dry-run] npm install --no-audit --no-fund  (في $FrontendDir)" }
            Write-Host "[dry-run] npm run dev -- --host 0.0.0.0 --port $FrontendPort  (في $FrontendDir)"
        }
        else {
            if (-not $NoInstall -and -not (Test-Path (Join-Path $FrontendDir 'node_modules'))) {
                Write-Info 'تثبيت حزم الواجهة الأمامية (npm install)...'
                Push-Location $FrontendDir
                try {
                    npm install --no-audit --no-fund
                    if ($LASTEXITCODE -ne 0) { Stop-Dev 'فشل npm install في frontend/' }
                }
                finally { Pop-Location }
            }
            $npmCmd = (Get-Command npm).Source
            $npmFile = if ($npmCmd -match '\.cmd$') { 'cmd.exe' } else { $npmCmd }
            $npmArgs = if ($npmFile -eq 'cmd.exe') { @('/c', $npmCmd, 'run', 'dev', '--', '--host', '0.0.0.0', '--port', $FrontendPort) } else { @('run', 'dev', '--', '--host', '0.0.0.0', '--port', $FrontendPort) }
            Push-Location $FrontendDir
            try {
                Write-Info "الواجهة على http://localhost:$FrontendPort  (خادم التطوير يوجّه /api إلى http://$BackendHost`:$BackendPort)"
                $script:FrontendProc = Start-Process -FilePath $npmFile -ArgumentList $npmArgs -NoNewWindow -PassThru -WorkingDirectory $FrontendDir
                $FrontendLaunched = $true
            }
            finally { Pop-Location }
        }
    }
}

if (-not $RunBackend -and -not $RunFrontend) {
    Write-Info 'لا شيء للتشغيل: لا backend/ ولا frontend/ في هذه النسخة من المستودع.'
    Write-Info 'مسار الحاويات جاهز متى وُجد Docker: docker compose up --build'
    if ($DryRun) { exit 0 }
    exit 1
}

if ($DryRun) {
    Write-Info 'dry-run اكتمل — لم تُشغَّل أي عملية.'
    exit 0
}

# -------------------------------------------------
# 5) المراقبة والتنظيف
# -------------------------------------------------
function Get-DevChildPids([int]$ParentPid) {
    $all = @()
    try {
        $procs = Get-CimInstance -ClassName Win32_Process -Filter "ParentProcessId=$ParentPid" -ErrorAction Stop
        foreach ($p in $procs) {
            $all += [int]$p.ProcessId
            $all += Get-DevChildPids -ParentPid ([int]$p.ProcessId)
        }
    }
    catch {
        # Linux/macOS (pwsh) حيث Win32_Process غير متاح: الاعتماد على pgrep عند توفره.
        try {
            $kids = & pgrep -P $ParentPid 2>$null
            foreach ($k in $kids) {
                $all += [int]$k
                $all += Get-DevChildPids -ParentPid ([int]$k)
            }
        }
        catch { }
    }
    return $all
}

function Stop-DevProcesses {
    foreach ($proc in @($script:BackendProc, $script:FrontendProc)) {
        if (-not $proc) { continue }
        try {
            if ($proc.HasExited) { continue }
        }
        catch { }
        $tree = @(Get-DevChildPids -ParentPid ([int]$proc.Id)) + [int]$proc.Id
        foreach ($procId in ($tree | Select-Object -Unique)) {
            try { Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue } catch { }
        }
    }
}

Write-Info 'ابدأ التطوير — Ctrl+C يوقف الخدمتين معًا.'
try {
    $watch = @()
    if ($BackendLaunched -and $script:BackendProc)  { $watch += $script:BackendProc }
    if ($FrontendLaunched -and $script:FrontendProc) { $watch += $script:FrontendProc }
    if ($watch.Count -eq 0) { Stop-Dev 'لم تُشغَّل أي عملية.' }
    # ننتظر أول عملية تموت ثم نُوقف البقية (سلوك dev.sh نفسه).
    while ($true) {
        Start-Sleep -Milliseconds 750
        $dead = @($watch | Where-Object { $_.HasExited })
        if ($dead.Count -gt 0) {
            $code = 0
            try { $code = $dead[0].ExitCode } catch { }
            if ($code -ne 0) { Write-Warn "عملية انتهت برمز $code" }
            break
        }
    }
}
finally {
    Write-Info 'إيقاف العمليات التابعة...'
    Stop-DevProcesses
}
