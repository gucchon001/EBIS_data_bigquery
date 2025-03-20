@echo off
chcp 65001 >nul

REM 仮想環境のパスを設定（必要に応じて変更してください）
set "VENV_PATH=.\venv"

REM 仮想環境が存在するか確認
if exist "%VENV_PATH%\Scripts\activate.bat" (
    echo [INFO] 仮想環境をアクティブ化しています...
    call "%VENV_PATH%\Scripts\activate.bat"
) else (
    echo [ERROR] 仮想環境が見つかりません: %VENV_PATH%
    echo 仮想環境を作成するか、正しいパスを設定してください。
    pause
    exit /b 1
)

REM 実行するPythonスクリプトのパスを設定（必要に応じて変更してください）
set "SCRIPT_PATH=src\main.py"

REM スクリプトが存在するか確認
if exist "%SCRIPT_PATH%" (
    echo [INFO] スクリプトを実行しています: %SCRIPT_PATH%
    python "%SCRIPT_PATH%"
    if errorlevel 1 (
        echo [ERROR] スクリプトの実行中にエラーが発生しました。
        pause
        exit /b 1
    )
) else (
    echo [ERROR] スクリプトが見つかりません: %SCRIPT_PATH%
    pause
    exit /b 1
)

REM 仮想環境をディアクティブ化
echo [INFO] 仮想環境をディアクティブ化しています...
deactivate

echo [INFO] 実行が完了しました。
pause
