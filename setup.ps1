# ============================================================
# ERP Supermercado - Instalador Automatico (Windows PowerShell)
# ============================================================
# Uso: Abra PowerShell como Administrador e execute:
#        .\setup.ps1
# ============================================================

$ErrorActionPreference = "Stop"

function Write-Step($msg) {
    Write-Host "`n>>> $msg" -ForegroundColor Cyan
}

function Test-Command($cmd) {
    try { Get-Command $cmd -ErrorAction Stop | Out-Null; return $true }
    catch { return $false }
}

# 1. Verificar Python
Write-Step "Verificando Python..."
if (-not (Test-Command "python")) {
    Write-Host "[!] Python nao encontrado. Baixando..." -ForegroundColor Yellow
    $url = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    $out = "$env:TEMP\python-3.11.9-amd64.exe"
    try {
        Invoke-WebRequest -Uri $url -OutFile $out
        Start-Process -Wait -FilePath $out -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1"
        Write-Host "[OK] Python 3.11 instalado" -ForegroundColor Green
    } catch {
        Write-Host "[!] Falha ao baixar/instalar Python." -ForegroundColor Red
        Write-Host "    Baixe manualmente de: $url" -ForegroundColor Yellow
        exit 1
    }
} else {
    $v = python --version
    Write-Host "[OK] $v" -ForegroundColor Green
}

# 2. Instalar GTK (WeasyPrint)
Write-Step "Verificando dependencias WeasyPrint..."
$gtkCheck = Test-Path "C:\Program Files\GTK3-Runtime Win64\bin\libgobject-2.0-0.dll"
if (-not $gtkCheck) {
    Write-Host "[!] GTK nao encontrado. Baixando..." -ForegroundColor Yellow
    $gtkUrl = "https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases/download/2022-01-04/gtk3-runtime-3.24.31-2022-01-04-ts-win64.exe"
    $gtkOut = "$env:TEMP\gtk3-runtime-win64.exe"
    try {
        Invoke-WebRequest -Uri $gtkUrl -OutFile $gtkOut -UseBasicParsing
        Start-Process -Wait -FilePath $gtkOut -ArgumentList "/verysilent /tasks=""assoc"",""desktopicon"""
        $env:Path += ";C:\Program Files\GTK3-Runtime Win64\bin"
        [Environment]::SetEnvironmentVariable("Path", $env:Path, "User")
        Write-Host "[OK] GTK instalado" -ForegroundColor Green
    } catch {
        Write-Host "[!] Falha ao baixar GTK (WeasyPrint nao funcionara sem ele)" -ForegroundColor Yellow
    }
} else {
    Write-Host "[OK] GTK encontrado" -ForegroundColor Green
}

# 3. Verificar PostgreSQL
Write-Step "Verificando PostgreSQL..."
$pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
if (-not $pgService -or $pgService.Status -ne "Running") {
    Write-Host "[!] PostgreSQL nao detectado." -ForegroundColor Yellow
    Write-Host "    Instale em: https://www.postgresql.org/download/windows/" -ForegroundColor White
    Write-Host "    Ou use Docker: docker run -d --name pg-erp -e POSTGRES_PASSWORD=openpgpwd -p 5432:5432 postgres:15" -ForegroundColor White
    $resp = Read-Host "    Deseja continuar mesmo assim? (s/N)"
    if ($resp -ne "s") { exit }
} else {
    Write-Host "[OK] PostgreSQL rodando" -ForegroundColor Green
}

# 4. Criar .env
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
    $lines = @"
SECRET_KEY=$secret
DB_USER=$user
DB_PASS=$pass
DB_NAME=$db
DB_HOST=localhost
DB_PORT=5432
FLASK_DEBUG=False
SESSION_COOKIE_SECURE=False
SESSION_COOKIE_SAMESITE=Lax
"@
    $lines | Out-File -FilePath $envFile -Encoding default
    Write-Host "[OK] .env criado" -ForegroundColor Green
} else {
    Write-Host "[OK] .env ja existe" -ForegroundColor Green
}

# 5. Venv + Dependencias
Write-Step "Criando ambiente virtual..."
$venvDir = Join-Path $PSScriptRoot "venv"
if (-not (Test-Path $venvDir)) {
    python -m venv $venvDir
    Write-Host "[OK] venv criado" -ForegroundColor Green
} else {
    Write-Host "[OK] venv ja existe" -ForegroundColor Green
}

Write-Step "Instalando dependencias..."
& "$venvDir\Scripts\python" -m pip install --upgrade pip -q 2>$null
& "$venvDir\Scripts\pip" install -r "$PSScriptRoot\requirements.txt" -q
Write-Host "[OK] Dependencias instaladas" -ForegroundColor Green

# 6. Inicializar Banco
Write-Step "Inicializando banco de dados..."
try {
    $env:GLIB_GIO_WARNINGS = "0"
    $env:SECRET_KEY = (Get-Content $envFile | Where-Object { $_ -match "^SECRET_KEY=" } | ForEach-Object { $_ -replace "^SECRET_KEY=", "" })
    $proc = Start-Process -FilePath "$venvDir\Scripts\python.exe" -ArgumentList "$PSScriptRoot\run.py" -PassThru -NoNewWindow -RedirectStandardOutput "$env:TEMP\erp_startup.log" -RedirectStandardError "$env:TEMP\erp_startup_err.log"
    Start-Sleep -Seconds 3
    if (-not $proc.HasExited) {
        Write-Host "[OK] Servidor iniciado (PID $($proc.Id))" -ForegroundColor Green
    } else {
        $log = Get-Content "$env:TEMP\erp_startup_err.log" -Raw
        if ($log -match "error|Error") {
            Write-Host "[!] Erro ao iniciar servidor:" -ForegroundColor Yellow
            Write-Host $log -ForegroundColor Red
        } else {
            Write-Host "[OK] Banco inicializado" -ForegroundColor Green
        }
    }
    Write-Host "[OK] Banco inicializado" -ForegroundColor Green
} catch {
    Write-Host "[!] Erro ao inicializar banco: $_" -ForegroundColor Yellow
    Write-Host "    Verifique se o PostgreSQL esta rodando e as credenciais no .env" -ForegroundColor Yellow
}

# 7. Atalho Desktop
Write-Step "Criando atalho no Desktop..."
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "ERP Supermercado.lnk"
if (-not (Test-Path $shortcutPath)) {
    try {
        $wshell = New-Object -ComObject WScript.Shell
        $shortcut = $wshell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = "$PSScriptRoot\iniciar.bat"
        $shortcut.WorkingDirectory = $PSScriptRoot
        $shortcut.Description = "ERP Supermercado - Login: admin / Senha: Admin@123"
        $shortcut.Save()
        Write-Host "[OK] Atalho criado no Desktop" -ForegroundColor Green
    } catch {
        Write-Host "[!] Nao foi possivel criar atalho: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "[OK] Atalho ja existe" -ForegroundColor Green
}

# 8. Concluido
Write-Step "================== INSTALACAO CONCLUIDA ==================" -ForegroundColor Green
Write-Host ""
Write-Host "  Login:   admin" -ForegroundColor White
Write-Host "  Senha:   Admin@123" -ForegroundColor White
Write-Host ""
Write-Host "  Para iniciar:" -ForegroundColor White
Write-Host "    Clique no atalho do Desktop" -ForegroundColor Gray
Write-Host "    Ou rode: .\venv\Scripts\python run.py" -ForegroundColor Gray
Write-Host ""
Write-Host "  Acesse: http://localhost:5000" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Green

try { Start-Process "http://localhost:5000" } catch {}
