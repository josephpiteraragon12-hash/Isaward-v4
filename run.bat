@echo off
rem Abre IsaWard desde el codigo (la primera vez instala lo necesario).
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
    echo Preparando IsaWard por primera vez, esto tarda unos minutos...
    python -m venv .venv
    if errorlevel 1 goto sin_python
    .venv\Scripts\python -m pip install --upgrade pip
    .venv\Scripts\python -m pip install -r requirements.txt
    if errorlevel 1 goto error
)
.venv\Scripts\python run_isaward.py %*
goto fin
:sin_python
echo No encontre Python. Instalalo desde https://www.python.org/downloads/ y marca "Add Python to PATH".
goto fin
:error
echo Algo fallo al instalar. Revisa tu conexion a internet y vuelve a intentar.
:fin
pause
