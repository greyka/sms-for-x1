@echo off
REM Запуск SMS for X1 (без консольного окна)
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "run.pyw"
) else (
    start "" pythonw "run.pyw"
)
