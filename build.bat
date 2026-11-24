@echo off
rem Crea IsaWard.exe.   build.bat           -> carpeta dist\IsaWard\ (abre mas rapido, recomendado)
rem                     build.bat onefile   -> un solo archivo dist\IsaWard.exe (tarda mas en abrir)
cd /d "%~dp0"
set MODE=--onedir
if /i "%1"=="onefile" set MODE=--onefile

echo === 1/4 Preparando entorno ===
python -m venv .venv-build
if errorlevel 1 goto error
call .venv-build\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller
if errorlevel 1 goto error

echo === 2/4 Probando la conversion de documentos ===
python -m unittest discover tests
if errorlevel 1 goto error

echo === 3/4 Compilando ===
pyinstaller --noconfirm --clean --windowed %MODE% --name IsaWard --icon assets\isaward.ico --collect-data docx --exclude-module tkinter run_isaward.py
if errorlevel 1 goto error

echo === 4/4 Listo ===
if /i "%1"=="onefile" (echo Tu programa: dist\IsaWard.exe) else (echo Tu programa: dist\IsaWard\IsaWard.exe  ^(copia la carpeta IsaWard completa^))
goto fin
:error
echo.
echo Algo fallo. Copia el mensaje de arriba y pegaselo a Claude junto con el proyecto.
:fin
pause
