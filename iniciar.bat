@echo off
REM ERP Supermercado - Iniciar Servidor
cd /d "%~dp0"
set GLIB_GIO_WARNINGS=0
"%~dp0venv\Scripts\python" "%~dp0run.py"
pause
