@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem ============================================================
rem  Inicia el simulador de impresora fiscal (sim.py)
rem
rem  Uso:  inicia_impresora_fiscal.bat [modelo] [puerto]
rem    modelo: tfhka (por omision) | hasar | bixolon | epson
rem    puerto: COM5 (por omision). Debe ser un puerto real o
rem             virtual: con com0com, el spooler usa el otro
rem             extremo del par.
rem
rem  Ejemplos:
rem    inicia_impresora_fiscal.bat
rem    inicia_impresora_fiscal.bat tfhka COM5
rem    inicia_impresora_fiscal.bat hasar COM3
rem
rem  Requisito: Python 3.11+ en el PATH. El bat crea su propio
rem  entorno virtual (.venv) con pyserial si no existe.
rem
rem  Conexion con el spooler (SpoolerFiscal):
rem    1) com0com crea un par, por ejemplo COM3 <-> COM4
rem    2) este simulador escucha en COM4
rem    3) server.yaml: printer.transport = serial,
rem       printer.port.name = COM3
rem ============================================================

set "MODELO=%~1"
if "%MODELO%"=="" set "MODELO=tfhka"
set "PUERTO=%~2"
if "%PUERTO%"=="" set "PUERTO=COM5"

rem --- El puerto debe existir (real o virtual); si no, el simulador ---
rem --- caeria en modo interactivo y el spooler no podria usarlo.       ---
powershell -NoProfile -Command "if ([System.IO.Ports.SerialPort]::GetPortNames() -notcontains '%PUERTO%') { exit 1 }"
if errorlevel 1 (
    echo.
    echo ERROR: el puerto %PUERTO% no existe en este equipo.
    echo        Cree un par de COM virtuales con com0com y use aqui uno de
    echo        los extremos ^(el spooler usara el otro^):
    echo          com0com:  COM3 ^<^-^> COM4
    echo          este .bat: %PUERTO%     spooler: el otro del par
    echo.
    exit /b 1
)

rem --- Entorno virtual con las dependencias (pyserial) ---
if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual e instalando dependencias...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: no se pudo crear .venv. Instale Python 3.11+ y verifique el PATH.
        exit /b 1
    )
    .venv\Scripts\python.exe -m pip install --upgrade pip >nul
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: no se pudieron instalar las dependencias ^(requirements.txt^).
        exit /b 1
    )
)

echo Iniciando simulador %MODELO% en %PUERTO% ^(Ctrl+C para detener^)...
.venv\Scripts\python.exe sim.py --model %MODELO% --port %PUERTO%
exit /b %ERRORLEVEL%
