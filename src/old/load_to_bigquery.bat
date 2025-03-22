@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul

echo ======================================================
echo BigQueryデータロードツール
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
set INPUT_FILE=data\SE_SSresult\AE_CVresult_schema.csv
set OUTPUT_TABLE=AE_CVresult

:parse_args
if "%~1"=="" goto :end_parse_args
if /i "%~1"=="--input" (
    set INPUT_FILE=%~2
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--output" (
    set OUTPUT_TABLE=%~2
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--help" (
    echo 使用方法: %~nx0 [オプション]
    echo オプション:
    echo   --input FILE      入力CSVファイルパス（デフォルト: data\AE_CV\SE_SSresult\result_schema.csv）
    echo   --output NAME     出力BigQueryテーブル名（デフォルト: AE_CVresult）
    exit /b 0
)
shift
goto :parse_args
:end_parse_args

echo 入力ファイル: %INPUT_FILE%
echo 出力テーブル: %OUTPUT_TABLE%

REM ファイルの存在確認
if not exist "%INPUT_FILE%" (
    echo エラー: 入力ファイル %INPUT_FILE% が存在しません。
    exit /b 1
)

REM 環境変数ファイルの読み込み確認
if not exist "%ENV_FILE%" (
    echo エラー: 環境変数ファイル %ENV_FILE% が存在しません。
    exit /b 1
)

REM BigQueryにデータをロードする

echo BigQueryにデータをロードしています...
set PYTHONPATH=C:\dev\CODE\EBIS_BIGQUERY
%PYTHON_CMD% src/load_to_bigquery.py --data "%INPUT_FILE%" --table "%OUTPUT_TABLE%"
if %errorlevel% neq 0 (
    echo BigQueryへのデータロードに失敗しました。
    exit /b 1
)

echo ======================================================
echo BigQueryへのデータロードが完了しました。
echo テーブル名: %OUTPUT_TABLE%
echo ======================================================

endlocal 