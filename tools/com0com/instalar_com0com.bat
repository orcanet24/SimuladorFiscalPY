@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

rem ============================================================
rem  Instala com0com y crea el par de puertos COM virtuales
rem  para SimuladorFiscalPY.
rem
rem  Uso: doble clic, o desde una consola (pedira elevacion).
rem
rem  Flujo:
rem    1) Si com0com no esta instalado: activa test signing,
rem       instala el driver y pide reiniciar.
rem    2) Tras reiniciar, vuelva a ejecutar este .bat: crea el
rem       par COM3 <-> COM5 (si no, COM5 <-> COM6).
rem    3) Ya puede ejecutar inicia_impresora_fiscal.bat.
rem ============================================================

rem --- Elevacion automatica a administrador ---
net session >nul 2>&1
if errorlevel 1 (
    echo.
    echo Se necesitan permisos de administrador.
    echo Se abrira una ventana de elevacion ^(UAC^).
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b 1
)

set "DEST=%~dp0"
set "SETUP=%DEST%Setup_com0com_v3.0.0.0_W7_x64_signed.exe"
set "CDIR=%ProgramFiles%\com0com"
if not exist "%CDIR%\setupc.exe" set "CDIR=%ProgramFiles(x86)%\com0com"

echo ============================================================
echo  com0com para SimuladorFiscalPY
echo ============================================================
echo.

if not exist "%CDIR%\setupc.exe" (
    echo [1/4] Driver com0com NO instalado.
    echo.
    echo Comprobando test signing...
    set "NEED_REBOOT="
    bcdedit /enum >"%TEMP%\com0com_bcd.txt" 2>nul
    findstr /i "testsigning" "%TEMP%\com0com_bcd.txt" >nul
    if errorlevel 1 (
        bcdedit /set testsigning on >nul
        set "NEED_REBOOT=1"
        echo   Test signing activado.
    ) else (
        findstr /i "testsigning.*Yes" "%TEMP%\com0com_bcd.txt" >nul
        if errorlevel 1 (
            bcdedit /set testsigning on >nul
            set "NEED_REBOOT=1"
            echo   Test signing activado.
        ) else (
            echo   Test signing ya esta activo.
        )
    )

    echo.
    echo [2/4] Preparando instalador...
    if not exist "%SETUP%" (
        if not exist "%DEST%com0com.zip" (
            echo   Descargando com0com 3.0.0.0...
            curl.exe -L --fail --silent -o "%DEST%com0com.zip" "https://sourceforge.net/projects/com0com/files/com0com/3.0.0.0/com0com-3.0.0.0-i386-and-x64-signed.zip/download"
        )
        echo   Extrayendo...
        powershell -NoProfile -Command "Expand-Archive -LiteralPath '%DEST%com0com.zip' -DestinationPath '%DEST%' -Force"
    )
    if not exist "%SETUP%" (
        echo ERROR: no se pudo descargar o extraer el instalador.
        exit /b 1
    )

    echo.
    echo [3/4] Instalando com0com en silencio...
    "%SETUP%" /S
    if errorlevel 1 (
        echo ERROR: no se pudo instalar com0com.
        exit /b 1
    )

    rem Re-detectar la ruta real de instalacion.
    set "CDIR=%ProgramFiles%\com0com"
    if not exist "%CDIR%\setupc.exe" set "CDIR=%ProgramFiles(x86)%\com0com"
    echo   Instalado en %CDIR%

    echo.
    if "!NEED_REBOOT!"=="1" (
        echo ============================================================
        echo  REINICIE el equipo para activar el driver.
        echo  Despues vuelva a ejecutar este .bat: creara el par
        echo  COM3 ^<^-^> COM5.
        echo ============================================================
        choice /c SN /n /m "Reiniciar ahora? [S/N] "
        if errorlevel 2 exit /b 0
        shutdown /r /t 5 /c "com0com: activando test signing"
        exit /b 0
    )
) else (
    echo [1/4] Driver com0com ya instalado en %CDIR%
)

echo.
echo [4/4] Creando par de puertos virtuales ^(clase Ports^)...
cd /d "%CDIR%"

rem Evita el asistente "Found New Hardware" durante la creacion.
reg add HKLM\Software\Policies\Microsoft\Windows\DeviceInstall\Settings /v SuppressNewHWUI /t REG_DWORD /d 1 /f >nul 2>&1

rem PortName=COM# crea el par en la clase Ports para que las
rem aplicaciones ^(y GetPortNames^) lo reconozcan como puerto real.
setupc install PortName=COM# PortName=COM#
if errorlevel 1 (
    echo   Reintentando con nombres explicitos...
    setupc install PortName=COM3 PortName=COM5
    if errorlevel 1 (
        reg add HKLM\Software\Policies\Microsoft\Windows\DeviceInstall\Settings /v SuppressNewHWUI /t REG_DWORD /d 0 /f >nul 2>&1
        echo ERROR: no se pudo crear el par de puertos.
        echo Ejecute 'setupc list' para ver el estado.
        exit /b 1
    )
)
setupc update >nul 2>&1

echo.
echo Fijando nombres COM3 y COM5...
set "PORTA="
set "PORTB="
for /f "tokens=1" %%a in ('setupc list ^| findstr "CNCA0"') do set "PORTA=%%a"
for /f "tokens=1" %%b in ('setupc list ^| findstr "CNCB0"') do set "PORTB=%%b"
if defined PORTA (
    setupc change !PORTA! RealPortName=COM3
    if errorlevel 1 setupc change !PORTA! RealPortName=COM1
)
if defined PORTB (
    setupc change !PORTB! RealPortName=COM5
    if errorlevel 1 setupc change !PORTB! RealPortName=COM6
)

rem Restaura la UI de nuevo hardware.
reg add HKLM\Software\Policies\Microsoft\Windows\DeviceInstall\Settings /v SuppressNewHWUI /t REG_DWORD /d 0 /f >nul 2>&1

echo.
echo Puertos COM detectados por Windows:
powershell -NoProfile -Command "[System.IO.Ports.SerialPort]::GetPortNames()"

echo.
echo Estado de com0com:
setupc list

echo.
echo ============================================================
echo  Listo. Ejecute inicia_impresora_fiscal.bat
echo  ^(COM5 por defecto; el spooler usara el otro extremo^).
echo ============================================================
echo.
pause
