@echo off
setlocal
title LB Financas - Criar Atalho
cd /d "%~dp0"

set "TARGET="
for %%F in ("%~dp0*.bat") do (
    if /I not "%%~nxF"=="%~nx0" set "TARGET=%%~fF"
)

if "%TARGET%"=="" (
    echo [ERRO] Nao encontrei o arquivo do sistema nesta pasta.
    pause
    exit /b 1
)

echo Criando atalho na Area de Trabalho...
echo.

powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $desktop = [Environment]::GetFolderPath('Desktop'); $link = $ws.CreateShortcut((Join-Path $desktop 'LB Financas.lnk')); $link.TargetPath = $env:TARGET; $link.WorkingDirectory = Split-Path $env:TARGET; $link.Description = 'Iniciar o sistema LB Financas'; $icone = Join-Path (Split-Path $env:TARGET) 'core\static\core\img\logo.ico'; if (Test-Path $icone) { $link.IconLocation = $icone + ',0' }; $link.Save()"

if errorlevel 1 (
    echo [ERRO] Nao foi possivel criar o atalho.
    pause
    exit /b 1
)

echo Atalho "LB Financas" criado na Area de Trabalho com sucesso!
echo Pode fechar esta janela e usar o atalho a partir de agora.
echo.
pause
