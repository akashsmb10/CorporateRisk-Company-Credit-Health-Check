@echo off
REM ==========================================================================
REM  CorporateRisk - first-time setup (Windows 10/11, Python 3.11)
REM  1. checks Python  2. creates .venv  3. installs dependencies
REM  4. verifies imports  5. prepares and validates the data  6. prints next steps
REM  Calls .venv\Scripts\python.exe directly: no PowerShell activation needed.
REM ==========================================================================
setlocal EnableExtensions
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONPATH=%~dp0src"
set "VENV_PY=%~dp0.venv\Scripts\python.exe"

echo.
echo === CorporateRisk setup ==========================================
echo Project folder: %CD%
echo.

if exist "%VENV_PY%" goto have_venv

echo [1/6] Looking for Python 3.11 ...
set "BASE_PY="
py -3.11 -c "import sys" >nul 2>&1
if not errorlevel 1 set "BASE_PY=py -3.11"
if defined BASE_PY goto found_python
python -c "import sys; sys.exit(0 if sys.version_info[:2] in ((3,11),(3,12)) else 1)" >nul 2>&1
if not errorlevel 1 set "BASE_PY=python"
if defined BASE_PY goto found_python
echo [ERROR] Python 3.11 was not found.
echo         Install it from https://www.python.org/downloads/ and tick
echo         "Add python.exe to PATH" and "py launcher", then run this file again.
goto fail

:found_python
%BASE_PY% --version
echo [2/6] Creating virtual environment .venv ...
%BASE_PY% -m venv .venv
if errorlevel 1 goto fail
goto venv_ready

:have_venv
echo [1/6] Existing .venv found - Python check skipped.
echo [2/6] Using existing virtual environment .venv

:venv_ready
"%VENV_PY%" -c "import sys; print('    venv Python', sys.version.split()[0]); sys.exit(0 if sys.version_info[:2] in ((3,11),(3,12)) else 1)"
if errorlevel 1 (
  echo [ERROR] .venv uses an unsupported Python version. Delete the .venv folder and run this file again.
  goto fail
)

echo [3/6] Installing dependencies - this can take a few minutes ...
"%VENV_PY%" -m pip install --upgrade pip
if errorlevel 1 goto fail
"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 goto fail
"%VENV_PY%" -m pip install -e .
if errorlevel 1 goto fail

echo [4/6] Verifying essential imports ...
"%VENV_PY%" -c "import pandas, numpy, scipy, matplotlib, plotly, streamlit, openpyxl, reportlab, pytest, corporaterisk; print('    all packages import correctly')"
if errorlevel 1 goto fail
"%VENV_PY%" -m ipykernel install --user --name corporaterisk --display-name "Python (CorporateRisk)" >nul 2>&1

echo [5/6] Preparing and validating data ...
"%VENV_PY%" scripts\prepare_data.py
if errorlevel 1 (
  echo [ERROR] Data validation failed - see the messages above and data\processed\validation_report.csv
  goto fail
)

echo [6/6] Done.
echo.
echo === Next steps ===================================================
echo   run_project.bat   - open the dashboard at http://localhost:8501
echo   run_tests.bat     - run the automated tests
echo   Real companies    - see docs\data_sources.md (the bundled data is SYNTHETIC)
echo.
endlocal
pause
exit /b 0

:fail
echo.
echo [SETUP FAILED] See the message above. Nothing outside this folder was changed.
endlocal
pause
exit /b 1
