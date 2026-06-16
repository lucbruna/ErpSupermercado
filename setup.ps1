# ============================================================
# ERP Supermercado — Instalador Automático (Windows PowerShell)
# ============================================================
# Uso:  Abra PowerShell como Administrador e execute:
#        .\setup.ps1
# ============================================================

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "ERP Supermercado — Instalador"

function Write-Step($msg) {
    Write-Host "`n>>> $msg" -ForegroundColor Cyan
}

function Test-Command($cmd) {
    try { Get-Command $cmd -ErrorAction Stop | Out-Null; return $true }
    catch { return $false }
}

# ── 1. Verificar Python ──
Write-Step "Verificando Python..."
if (-not (Test-Command "python")) {
    Write-Host "[!] Python nao encontrado. Baixando..." -ForegroundColor Yellow
    $url = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    $out = "$env:TEMP\python-3.11.9-amd64.exe"
    Invoke-WebRequest -Uri $url -OutFile $out
    Start-Process -Wait -FilePath $out -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1"
    refreshenv
    Write-Host "[OK] Python 3.11 instalado" -ForegroundColor Green
} else {
    $v = python --version
    Write-Host "[OK] $v" -ForegroundColor Green
}

# ── 2. Verificar PostgreSQL ──
Write-Step "Verificando PostgreSQL..."
$pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
if (-not $pgService -or $pgService.Status -ne "Running") {
    Write-Host "[!] PostgreSQL nao detectado." -ForegroundColor Yellow
    Write-Host "    Instale em: https://www.postgresql.org/download/windows/"
    Write-Host "    Ou use Docker: docker run -d --name pg-erp -e POSTGRES_PASSWORD=openpgpwd -p 5432:5432 postgres:15"
    $resp = Read-Host "    Deseja continuar mesmo assim? (s/N)"
    if ($resp -ne "s") { exit }
} else {
    Write-Host "[OK] PostgreSQL rodando" -ForegroundColor Green
}

# ── 3. Criar .env ──
Write-Step "Configurando ambiente..."
$envFile = Join-Path $PSScriptRoot ".env"
if (-not (Test-Path $envFile)) {
    $user = Read-Host "Usuario PostgreSQL (padrao: openpg)"
    if ([string]::IsNullOrWhiteSpace($user)) { $user = "openpg" }
    $pass = Read-Host "Senha PostgreSQL (padrao: openpgpwd)"
    if ([string]::IsNullOrWhiteSpace($pass)) { $pass = "openpgpwd" }
    $db = Read-Host "Database (padrao: erp_supermercado)"
    if ([string]::IsNullOrWhiteSpace($db)) { $db = "erp_supermercado" }

    $secret = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
    @"
SECRET_KEY=$secret
DB_USER=$user
DB_PASS=$pass
DB_NAME=$db
DB_HOST=localhost
DB_PORT=5432
FLASK_DEBUG=False
SESSION_COOKIE_SECURE=False
SESSION_COOKIE_SAMESITE=Lax
"@ | Out-File -FilePath $envFile -Encoding UTF8
    Write-Host "[OK] .env criado" -ForegroundColor Green
} else {
    Write-Host "[OK] .env ja existe" -ForegroundColor Green
}

# ── 4. Venv + Dependencias ──
Write-Step "Criando ambiente virtual..."
$venvDir = Join-Path $PSScriptRoot "venv"
if (-not (Test-Path $venvDir)) {
    python -m venv $venvDir
    Write-Host "[OK] venv criado" -ForegroundColor Green
} else {
    Write-Host "[OK] venv ja existe" -ForegroundColor Green
}

Write-Step "Instalando dependencias..."
& "$venvDir\Scripts\pip" install --upgrade pip -q
& "$venvDir\Scripts\pip" install -r "$PSScriptRoot\requirements.txt" -q
Write-Host "[OK] Dependencias instaladas" -ForegroundColor Green

# ── 5. Inicializar Banco ──
Write-Step "Inicializando banco de dados..."
try {
    & "$venvDir\Scripts\python" "$PSScriptRoot\run.py" 3>&1 2>&1 | Out-Null
    # run.py ja roda db.create_all() + seed admin + setores + plano contas
    Write-Host "[OK] Banco inicializado" -ForegroundColor Green
} catch {
    Write-Host "[!] Erro ao inicializar banco: $_" -ForegroundColor Yellow
    Write-Host "    Verifique se o PostgreSQL esta rodando e as credenciais no .env"
}

# ── 6. Atalho Desktop ──
Write-Step "Criando atalho no Desktop..."
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "ERP Supermercado.lnk"
if (-not (Test-Path $shortcutPath)) {
    $wshell = New-Object -ComObject WScript.Shell
    $shortcut = $wshell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = "$venvDir\Scripts\python.exe"
    $shortcut.Arguments = "$PSScriptRoot\run.py"
    $shortcut.WorkingDirectory = $PSScriptRoot
    $shortcut.Description = "ERP Supermercado"
    $shortcut.Save()

    $wshell2 = New-Object -ComObject WScript.Shell
    $shortcut2 = $wshell2.CreateShortcut((Join-Path $desktop "ERP Supermercado (Admin).lnk"))
    $shortcut2.TargetPath = "$venvDir\Scripts\python.exe"
    $shortcut2.Arguments = "$PSScriptRoot\run.py"
    $shortcut2.WorkingDirectory = $PSScriptRoot
    $shortcut2.Description = "ERP Supermercado (Admin - senha: Admin@123)"
    $shortcut2.Save()
    Write-Host "[OK] Atalhos criados no Desktop" -ForegroundColor Green
} else {
    Write-Host "[OK] Atalho ja existe" -ForegroundColor Green
}

# ── 7. Concluido ──
Write-Step "`====================== INSTALACAO CONCLUIDA ======================" -ForegroundColor Green
Write-Host "  Login: admin" -ForegroundColor White
Write-Host "  Senha: Admin@123" -ForegroundColor White
Write-Host ""
Write-Host "  Para iniciar, execute o atalho no Desktop ou:" -ForegroundColor White
Write-Host "  .\venv\Scripts\python run.py" -ForegroundColor Gray
Write-Host ""
Write-Host "  Acesse: http://localhost:5000" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Green

Start-Process "http://localhost:5000"
