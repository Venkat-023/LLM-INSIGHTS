$ErrorActionPreference = "Stop"

$ProjectDir = Join-Path $PSScriptRoot "langsmith-playground"
Set-Location $ProjectDir

if (!(Test-Path ".env") -and (Test-Path ".env.example")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created langsmith-playground\.env from .env.example. Add your API keys before running LLM calls." -ForegroundColor Yellow
}

if (!(Test-Path ".venv")) {
    python -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host "Starting LangSmith Playground at http://127.0.0.1:8010" -ForegroundColor Cyan
.\.venv\Scripts\python.exe -m uvicorn web_app:app --host 127.0.0.1 --port 8010
