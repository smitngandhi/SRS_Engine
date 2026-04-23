@echo off
:: SpecForge AI - Startup Script
:: This script launches the core services in separate terminal windows.

echo ==========================================
echo   SpecForge AI - Starting Application
echo ==========================================

:: Conda Setup
set "CONDA_ACTIVATE=C:\miniconda3\Scripts\activate.bat"

:: 1. Start Redis (Queue & Concurrency Management)
echo [1/3] Starting Redis Service (Docker)...
start "SpecForge: Redis" cmd /k "docker run -it --rm --name redis -p 6379:6379 redis:alpine"

:: 2. Start FastAPI Backend
echo [2/3] Starting FastAPI Backend (Port 8000)...
start "SpecForge: API" cmd /k "call "%CONDA_ACTIVATE%" && conda activate srs_engine_venv && uvicorn srs_engine.main:app --reload --port 8000"

:: 3. Start Worker Manager
echo [3/3] Starting Worker Manager...
start "SpecForge: Worker Manager" cmd /k "call "%CONDA_ACTIVATE%" && conda activate srs_engine_venv && python -m srs_engine.worker_manager"

echo.
echo ==========================================
echo   All services are launching!
echo   - Website: http://localhost:8000
echo   - Admin Summary: python admin_summary.py
echo ==========================================
pause
