# WisperMod — Iniciar servidores (Backend + Frontend)
# Execute com: powershell -ExecutionPolicy Bypass -File start.ps1

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "   WisperMod — Iniciando servidores    " -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""

# ── Verificar Python ────────────────────────────────────────────────────────
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[ERRO] Python nao encontrado. Instale em https://www.python.org" -ForegroundColor Red
    pause; exit 1
}

# ── Verificar FFmpeg ────────────────────────────────────────────────────────
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "[AVISO] FFmpeg nao encontrado no PATH." -ForegroundColor Yellow
    Write-Host "        Instale com: winget install Gyan.FFmpeg" -ForegroundColor Yellow
    Write-Host "        Depois feche e reabra este script." -ForegroundColor Yellow
    pause; exit 1
}

# ── Criar/ativar venv ───────────────────────────────────────────────────────
$venv = Join-Path $Root "venv"
if (-not (Test-Path $venv)) {
    Write-Host "[1/4] Criando ambiente virtual Python..." -ForegroundColor Green
    python -m venv $venv
}

$pip    = Join-Path $venv "Scripts\pip.exe"
$python = Join-Path $venv "Scripts\python.exe"

# ── Instalar dependencias Python ────────────────────────────────────────────
Write-Host "[2/4] Instalando dependencias Python (pode demorar na 1a vez)..." -ForegroundColor Green
& $pip install torch --index-url https://download.pytorch.org/whl/cpu -q
& $pip install -r (Join-Path $Root "requirements_web.txt") -q

# ── Instalar dependencias Node ──────────────────────────────────────────────
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "[ERRO] Node.js nao encontrado. Instale em https://nodejs.org" -ForegroundColor Red
    pause; exit 1
}

Write-Host "[3/4] Instalando dependencias do frontend..." -ForegroundColor Green
Set-Location $Root
npm install --silent

# ── Iniciar Backend ─────────────────────────────────────────────────────────
Write-Host "[4/4] Iniciando servidores..." -ForegroundColor Green
Write-Host ""
Write-Host "  Backend  -> http://localhost:8000" -ForegroundColor White
Write-Host "  Frontend -> http://localhost:3000  (abre automaticamente)" -ForegroundColor White
Write-Host ""
Write-Host "  Pressione Ctrl+C nesta janela para parar tudo." -ForegroundColor DarkGray
Write-Host ""

# Backend em janela separada
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '$python' '$Root\backend.py'" -WindowStyle Normal

# Aguardar backend subir
Start-Sleep -Seconds 3

# Frontend (Vite) na janela atual e abre o navegador
Start-Process "http://localhost:3000"
npm run dev
