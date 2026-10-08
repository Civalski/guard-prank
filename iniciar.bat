@echo off
cd /d "%~dp0"

rem Pede privilegio de Administrador (bloqueio pega de forma confiavel)
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo Iniciando o Guardiao de Tela...
python "%~dp0guardiao.py"
echo.
echo O Guardiao foi encerrado.
pause
