@echo off
REM ==========================================================================
REM  CorporateRisk - run the automated tests with the project's .venv
REM  Exit code is non-zero if any test fails.
REM ==========================================================================
setlocal EnableExtensions
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONPATH=%~dp0src"
set "VENV_PY=%~dp0.venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
  echo [ERROR] .venv not found. Run setup_project.bat first.
  endlocal
  exit /b 1
)

echo === CorporateRisk tests ==========================================
"%VENV_PY%" -m pytest -v
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (
  echo ALL TESTS PASSED
) else (
  echo SOME TESTS FAILED - exit code %RESULT%
)
endlocal & exit /b %RESULT%
