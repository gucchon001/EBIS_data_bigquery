@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

:: カラム名前処理付きGCSからBigQueryへのデータロード実行スクリプト
echo カラム名前処理付きGCSからBigQueryへのデータロード処理を実行します...

:: カレントディレクトリをスクリプトの場所に変更
cd /d %~dp0

:: Python環境の確認
if exist venv\Scripts\python.exe (
    set PYTHON_CMD=venv\Scripts\python.exe
) else (
    set PYTHON_CMD=python
)

:: 依存関係のインストール確認
echo 依存関係をチェックしています...
%PYTHON_CMD% -m pip install -r requirements.txt

:: コマンドライン引数を解析
set "GCS_PATH="
set "TABLE_PREFIX="
set "DATASET="
set "FILE_TYPE=all"
set "WRITE_DISPOSITION=WRITE_TRUNCATE"

:parse_args
if "%~1"=="" goto :execute
if /i "%~1"=="--help" goto :show_help
if /i "%~1"=="-h" goto :show_help

if /i "%~1"=="--gcs-path" (
    set "GCS_PATH=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--table-prefix" (
    set "TABLE_PREFIX=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--dataset" (
    set "DATASET=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--file-type" (
    set "FILE_TYPE=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--write-disposition" (
    set "WRITE_DISPOSITION=%~2"
    shift
    shift
    goto :parse_args
)

shift
goto :parse_args

:show_help
echo 使用方法: %0 [options]
echo.
echo オプション:
echo   --gcs-path PATH           GCSのパス（例: gs://bucket_name/folder または bucket_name/folder）
echo   --table-prefix PREFIX     テーブル名のプレフィックス
echo   --dataset DATASET         BigQueryデータセット名
echo   --file-type TYPE          ロードするファイルタイプ（csv, parquet, all）
echo   --write-disposition DISP  書き込み設定（WRITE_TRUNCATE, WRITE_APPEND, WRITE_EMPTY）
echo.
echo 例:
echo   %0 --gcs-path gs://ebis_data/AE_SSresult --table-prefix ae_data --file-type csv
goto :end

:execute
:: AE_SSresultデータのロード（パラメータが指定されていない場合）
if "%GCS_PATH%"=="" (
    echo AE_SSresultディレクトリのデータをカラム名前処理してBigQueryにロードします...
    %PYTHON_CMD% src/modules/bigquery/load_preprocessed_ae_ssresult.py
    if %ERRORLEVEL% neq 0 (
        echo エラーが発生しました。詳細はログを確認してください。
        pause
        exit /b 1
    )
) else (
    echo 指定されたGCSパスからカラム名前処理してBigQueryにデータをロードします...
    
    set "ARGS=--gcs-path %GCS_PATH%"
    
    if not "%TABLE_PREFIX%"=="" (
        set "ARGS=!ARGS! --table-prefix %TABLE_PREFIX%"
    )
    
    if not "%DATASET%"=="" (
        set "ARGS=!ARGS! --dataset %DATASET%"
    )
    
    if not "%FILE_TYPE%"=="all" (
        set "ARGS=!ARGS! --file-pattern *.%FILE_TYPE%"
    )
    
    if not "%WRITE_DISPOSITION%"=="WRITE_TRUNCATE" (
        set "ARGS=!ARGS! --write-disposition %WRITE_DISPOSITION%"
    )
    
    %PYTHON_CMD% src/modules/bigquery/load_preprocessed_files.py !ARGS!
    
    if %ERRORLEVEL% neq 0 (
        echo エラーが発生しました。詳細はログを確認してください。
        pause
        exit /b 1
    )
)

echo データロード処理が完了しました。
echo 詳細はログファイルを確認してください: logs/gcs_to_bigquery_*.log

:end
pause 