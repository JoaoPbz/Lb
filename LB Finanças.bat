@echo off
setlocal
title LB Financas
cd /d "%~dp0"

echo ================================================
echo   LB Financas - iniciando o sistema...
echo ================================================
echo.

REM --- Verifica se o Python esta instalado ---
where python >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao foi encontrado nesta maquina.
    echo Instale o Python 3.13 e execute este arquivo novamente.
    echo.
    pause
    exit /b 1
)

REM --- Cria o ambiente virtual na primeira execucao ---
if not exist "venv\Scripts\python.exe" (
    echo Preparando o sistema pela primeira vez, aguarde...
    echo.
    python -m venv venv
    if errorlevel 1 (
        echo [ERRO] Nao foi possivel criar o ambiente virtual.
        pause
        exit /b 1
    )

    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip >nul
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERRO] Falha ao instalar as dependencias do sistema.
        pause
        exit /b 1
    )
) else (
    call venv\Scripts\activate.bat
)

REM --- Verifica se o arquivo .env existe ---
if not exist ".env" (
    echo [ERRO] Arquivo .env nao encontrado na pasta do sistema.
    echo Configure o arquivo .env com os dados do banco de dados e execute novamente.
    echo.
    pause
    exit /b 1
)

REM --- Verifica e, se necessario, inicia o servico do PostgreSQL ---
echo Verificando o PostgreSQL...
set PG_SERVICE=
for /f "usebackq delims=" %%S in (`powershell -NoProfile -Command "(Get-Service -Name 'postgresql*' -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Name)"`) do set PG_SERVICE=%%S

if "%PG_SERVICE%"=="" (
    echo [ERRO] Nenhum servico do PostgreSQL foi encontrado nesta maquina.
    echo Verifique se o PostgreSQL esta instalado corretamente.
    echo.
    pause
    exit /b 1
)

powershell -NoProfile -Command "try { $s = Get-Service -Name '%PG_SERVICE%'; if ($s.Status -ne 'Running') { Start-Service -Name '%PG_SERVICE%' -ErrorAction Stop } } catch { exit 1 }"
if errorlevel 1 (
    echo [ERRO] Nao foi possivel iniciar o PostgreSQL automaticamente.
    echo Abra "Servicos" no Windows, inicie o servico "%PG_SERVICE%" manualmente
    echo e execute este arquivo novamente.
    echo.
    pause
    exit /b 1
)

REM --- Aplica migracoes pendentes no banco ---
echo Verificando o banco de dados...
python manage.py migrate --noinput
if errorlevel 1 (
    echo [ERRO] Falha ao preparar o banco de dados.
    echo Verifique os dados de conexao no arquivo .env.
    echo.
    pause
    exit /b 1
)

REM --- Abre o navegador automaticamente apos alguns segundos ---
start "" cmd /c "timeout /t 3 >nul & start http://127.0.0.1:8000/"

echo.
echo ================================================
echo   Sistema pronto! Abrindo no navegador...
echo   Para FECHAR o sistema, feche esta janela.
echo ================================================
echo.

python manage.py runserver 127.0.0.1:8000 --insecure

pause
