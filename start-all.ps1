$ErrorActionPreference = "Stop"

Write-Host "Starting LangSmith in a new PowerShell window..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$PSScriptRoot\start-langsmith.ps1`""

Start-Sleep -Seconds 3

Write-Host "Starting Langfuse in a new PowerShell window..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$PSScriptRoot\start-langfuse.ps1`""

Write-Host "LangSmith: http://127.0.0.1:8010" -ForegroundColor Green
Write-Host "Langfuse:   http://127.0.0.1:5173" -ForegroundColor Green
