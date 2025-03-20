@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

rem Initialize environment variables
set "VENV_PATH=.\venv"
set "PYTHON_CMD=python"
set "PIP_CMD=pip"
set "DEFAULT_SCRIPT=src.main"
set "APP_ENV="
set "SCRIPT_TO_RUN="
set "TEST_MODE="

rem Parse command line arguments
:parse_args
if "%~1"=="-m" (
    set "SCRIPT_TO_RUN=src.%~2"
    shift
    shift
    goto parse_args
)

rem Display help message if --help is provided
if "%~1"=="--help" (
    echo 使用方法:
    echo   run.bat [オプション]
    echo
    echo オプション:
    echo   --env [dev|prd] : 実行環境を指定します。
    echo                         ^(dev=development, prd=production^)
    echo   --help               : このヘルプを表示します。
    echo
    echo 環境モード:
    echo   dev  : テストモードで実行、詳細なログとデバッグ情報を表示
    echo   prd  : 本番運用環境、安定性重視でユーザー向け
    echo
    echo 例:
    echo   run.bat --env dev
    echo   run.bat --env prd
    goto END
)

rem If no arguments are provided, prompt the user
if "%~1"=="" (
    echo 実行環境を選択してください:
    echo   1. Development (dev)
    echo   2. Production (prd)
    set /p "CHOICE=選択肢を入力してください (1/2): "
    if "%CHOICE%"=="1" (
        set "APP_ENV=development"
        set "TEST_MODE=--test"
    )
    if "%CHOICE%"=="2" (
        set "APP_ENV=production"
        set "TEST_MODE="
    )
    if not defined APP_ENV (
        echo Error: 無効な選択肢です。再実行してください。
        exit /b 1
    )
    if not defined SCRIPT_TO_RUN set "SCRIPT_TO_RUN=%DEFAULT_SCRIPT%"
)

rem Check if Python is installed
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python がインストールされていないか、環境パスが設定されていません。
    pause
    exit /b 1
)

rem Create virtual environment if it doesn't exist
if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo [LOG] 仮想環境が存在しません。作成中...
    %PYTHON_CMD% -m venv "%VENV_PATH%"
    if errorlevel 1 (
        echo Error: 仮想環境の作成に失敗しました。
        pause
        exit /b 1
    )
    echo [LOG] 仮想環境が正常に作成されました。
)

rem Activate virtual environment
if exist "%VENV_PATH%\Scripts\activate" (
    call "%VENV_PATH%\Scripts\activate"
) else (
    echo Error: 仮想環境の有効化に失敗しました。activate スクリプトが見つかりません。
    pause
    exit /b 1
)

rem Check requirements.txt
if not exist requirements.txt (
    echo Error: requirements.txt が見つかりません。
    pause
    exit /b 1
)

rem Install requirements if needed
for /f "skip=1 delims=" %%a in ('certutil -hashfile requirements.txt SHA256') do if not defined CURRENT_HASH set "CURRENT_HASH=%%a"

if exist .req_hash (
    set /p STORED_HASH=<.req_hash
) else (
    set "STORED_HASH="
)

if not "%CURRENT_HASH%"=="%STORED_HASH%" (
    echo [LOG] 必要なパッケージをインストール中...
    %PIP_CMD% install -r requirements.txt
    if errorlevel 1 (
        echo Error: パッケージのインストールに失敗しました。
        pause
        exit /b 1
    )
    echo %CURRENT_HASH%>.req_hash
)

rem Run the script
echo [LOG] 環境: %APP_ENV%
echo [LOG] 実行スクリプト: %SCRIPT_TO_RUN%
%PYTHON_CMD% -m %SCRIPT_TO_RUN% %TEST_MODE%
if errorlevel 1 (
    echo Error: スクリプトの実行に失敗しました。
    pause
    exit /b 1
)

:END
endlocal
