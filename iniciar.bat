@echo off
rem Levanta el aula virtual en Windows con doble clic. Prepara Python con uv y
rem deja el resto (clave de IA, base y servidor) a scripts\iniciar.py.
chcp 65001 >nul
cd /d "%~dp0"

rem Abierto desde adentro del ZIP, Windows extrae solo este archivo a una carpeta temporal.
if not exist manage.py (
    echo Primero descomprimi el ZIP: clic derecho, "Extraer todo", y abri iniciar.bat desde la carpeta extraida.
    pause
    exit /b 1
)

where uv >nul 2>nul
if errorlevel 1 (
    echo Instalando uv, que prepara Python automaticamente...
    powershell -NoProfile -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)

if not exist .venv\Scripts\python.exe (
    uv venv --quiet --python ">=3.12" .venv || goto :error
)
uv pip install --quiet --python .venv\Scripts\python.exe -r requirements.txt || goto :error
.venv\Scripts\python.exe scripts\iniciar.py || goto :error
goto :eof

:error
echo.
echo Algo fallo. Copia el mensaje de arriba y mandaselo al grupo.
pause
