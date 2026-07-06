# start.ps1 – One-command startup script for the Langfuse Chatbot
# Run from the project root: .\start.ps1

Write-Host "Starting Langfuse AI Chatbot..." -ForegroundColor Cyan

# Start backend
Write-Host "Starting FastAPI backend on http://localhost:8000" -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000"

Start-Sleep -Seconds 2

# Start frontend
Write-Host "Starting Vite frontend on http://localhost:5173" -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\frontend'; npm run dev"

Write-Host ""
Write-Host "Both servers starting up!" -ForegroundColor Cyan
Write-Host "   Frontend:  http://localhost:5173" -ForegroundColor White
Write-Host "   Backend:   http://localhost:8000" -ForegroundColor White
Write-Host "   API Docs:  http://localhost:8000/api/docs" -ForegroundColor White
Write-Host "   Langfuse:  https://cloud.langfuse.com" -ForegroundColor White
