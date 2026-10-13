@echo off
echo ============================================================
echo   Iniciando Haar Impurity Inspector (Backend + Frontend)
echo ============================================================

start "Backend - FastAPI" cmd /k "cd backend && .venv\Scripts\activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 2 /nobreak >nul
start "Frontend - Next.js" cmd /k "cd frontend && npm run dev"

echo.
echo Servicos iniciados em janelas dedicadas:
echo   - Frontend: http://localhost:3000
echo   - Backend:  http://localhost:8000/docs
echo.
pause
