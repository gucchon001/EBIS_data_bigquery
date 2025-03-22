@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul

echo ======================================================
echo BigQueryスキーマテスト実行ツール
echo ======================================================

REM カレントディレクトリをスクリプトの場所に変更
cd /d "%~dp0"

REM 環境変数ファイルのパス
set ENV_FILE=config\secrets.env

REM Pythonコマンドを設定
if exist venv\Scripts\python.exe (
    set PYTHON_CMD=venv\Scripts\python.exe
) else (
    set PYTHON_CMD=python
)

REM 必要なパッケージのチェック
%PYTHON_CMD% -c "import google.cloud.bigquery" 2>nul
if %errorlevel% neq 0 (
    echo 必要なパッケージをインストールしています...
    %PYTHON_CMD% -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo パッケージのインストールに失敗しました。
        exit /b 1
    )
)

REM 引数の解析
set SCHEMA_FILE=
set SCRIPT_MODE=all

:parse_args
if "%~1"=="" goto :end_parse_args
if /i "%~1"=="--schema" (
    set SCHEMA_FILE=%~2
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--mode" (
    set SCRIPT_MODE=%~2
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--help" (
    echo 使用方法: %~nx0 [オプション]
    echo オプション:
    echo   --schema FILE    使用するスキーマCSVファイル（デフォルト: data/SE_SSresult/AE_CVresult_schema.csv）
    echo   --mode MODE      実行モード（create: データ作成のみ、load: ロードのみ、all: 両方）
    exit /b 0
)
shift
goto :parse_args
:end_parse_args

if "%SCHEMA_FILE%"=="" (
    set SCHEMA_FILE=data\SE_SSresult\AE_CVresult_schema.csv
)

echo スキーマファイル: %SCHEMA_FILE%
echo 実行モード: %SCRIPT_MODE%

REM ステップ1: テストデータの作成
if /i "%SCRIPT_MODE%"=="all" (
    echo ステップ1: テストデータを作成しています...
    %PYTHON_CMD% create_test_data.py
    if %errorlevel% neq 0 (
        echo テストデータの作成に失敗しました。
        exit /b 1
    )
    
    REM 最新のテストデータとスキーマファイルを取得
    for /f %%i in ('dir /b /od data\SE_SSresult\test\test_data_*.csv') do set LATEST_CSV=data\SE_SSresult\test\%%i
    for /f %%i in ('dir /b /od data\SE_SSresult\test\test_schema_*.json') do set LATEST_SCHEMA=data\SE_SSresult\test\%%i
    
    echo 最新のテストデータ: !LATEST_CSV!
    echo 最新のスキーマ: !LATEST_SCHEMA!
) else if /i "%SCRIPT_MODE%"=="create" (
    echo ステップ1: テストデータを作成しています...
    %PYTHON_CMD% create_test_data.py
    if %errorlevel% neq 0 (
        echo テストデータの作成に失敗しました。
        exit /b 1
    )
    exit /b 0
) else (
    REM ロードのみの場合、既存のファイルを使用
    for /f %%i in ('dir /b /od data\SE_SSresult\test\test_data_*.csv') do set LATEST_CSV=data\SE_SSresult\test\%%i
    for /f %%i in ('dir /b /od data\SE_SSresult\test\test_schema_*.json') do set LATEST_SCHEMA=data\SE_SSresult\test\%%i
    
    if not exist "!LATEST_CSV!" (
        echo 利用可能なテストデータがありません。先にデータを作成してください。
        exit /b 1
    )
    
    echo 使用するテストデータ: !LATEST_CSV!
    echo 使用するスキーマ: !LATEST_SCHEMA!
)

REM ステップ2: BigQueryへのロード
if /i "%SCRIPT_MODE%"=="all" goto :load_to_bigquery
if /i "%SCRIPT_MODE%"=="load" goto :load_to_bigquery
goto :end

:load_to_bigquery
echo ステップ2: BigQueryにテストデータをロードしています...
%PYTHON_CMD% test_load_to_bigquery.py "!LATEST_CSV!" --schema "!LATEST_SCHEMA!"
if %errorlevel% neq 0 (
    echo BigQueryへのデータロードに失敗しました。
    exit /b 1
)

:end
echo ======================================================
echo BigQueryスキーマテストが完了しました。
echo ログを確認してください。
echo ======================================================

endlocal 