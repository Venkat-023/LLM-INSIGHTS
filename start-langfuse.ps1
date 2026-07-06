$ErrorActionPreference = "Stop"

$ProjectDir = Join-Path $PSScriptRoot "langfuse-test"
Set-Location $ProjectDir

if (!(Test-Path ".env") -and (Test-Path ".env.example")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created langfuse-test\.env from .env.example. Add your API keys before running LLM calls." -ForegroundColor Yellow
}

if (!(Test-Path ".venv")) {
    python -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install -r requirements.txt

if (!(Test-Path "frontend\node_modules")) {
    Push-Location "frontend"
    npm install
    Pop-Location
}

Write-Host "Starting Langfuse backend at http://127.0.0.1:8000" -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectDir'; .\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000"

Start-Sleep -Seconds 2

Write-Host "Starting Langfuse frontend at http://127.0.0.1:5173" -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectDir\frontend'; npm run dev -- --host 127.0.0.1 --port 5173"

Write-Host "Langfuse app is starting. Open http://127.0.0.1:5173" -ForegroundColor Green
