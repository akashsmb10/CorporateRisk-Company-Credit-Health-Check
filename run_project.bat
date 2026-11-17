@echo off
REM ==========================================================================
REM  CorporateRisk - launch the Streamlit dashboard at http://localhost:8501
REM ==========================================================================
setlocal EnableExtensions
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONPATH=%~dp0src"
set "VENV_PY=%~dp0.venv\Scripts\python.exe"

echo.
echo === CorporateRisk dashboard ======================================
echo Project folder: %CD%

if not exist "%VENV_PY%" (
  echo [ERROR] .venv not found. Run setup_project.bat first.
  goto fail
)
"%VENV_PY%" -c "import streamlit, plotly, corporaterisk" >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Dashboard packages are missing. Run setup_project.bat again.
  goto fail
)
if not exist "data\raw\company_financials.csv" if not exist "data\sample\synthetic_financials.csv" (
  echo [ERROR] No financial data found. Run setup_project.bat first.
  goto fail
)
if exist "data\raw\company_financials.csv" (
  echo Data: data\raw\company_financials.csv ^(your real company data^)
) else (
  echo Data: data\sample\synthetic_financials.csv ^(SYNTHETIC demonstration data^)
)

echo.
echo Starting the dashboard - your browser should open automatically.
echo If it does not, open:  http://localhost:8501
echo Press Ctrl+C in this window to stop.
echo.
"%VENV_PY%" -m streamlit run dashboard\app.py --server.port 8501 --server.headless false
endlocal
exit /b 0

:fail
endlocal
pause
exit /b 1
