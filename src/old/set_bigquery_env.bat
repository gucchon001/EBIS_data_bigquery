@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul

echo ======================================================
echo BigQuery環境変数設定ツール
echo ======================================================

REM カレントディレクトリをスクリプトの場所に変更
cd /d "%~dp0"

REM 環境変数ファイルのパス
set ENV_FILE=config\secrets.env

REM 環境変数ファイルの存在チェック
if not exist "%ENV_FILE%" (
    echo 環境変数ファイル %ENV_FILE% が見つかりません。
    echo サンプルファイルを作成します。
    
    if not exist config mkdir config
    
    (
        echo #GCS
        echo GCP_PROJECT_ID=your-project-id
        echo GCS_BUCKET_NAME=your-bucket-name
        echo GCS_KEY_PATH=config/your-key-file.json
        echo.
        echo #bigquery
        echo BIGQUERY_PROJECT_ID=your-project-id
        echo BIGQUERY_DATASET=your-dataset
        echo LOG_TABLE=rawdata_log
    ) > "%ENV_FILE%"
    
    echo %ENV_FILE% を編集して、適切な値を設定してください。
    start notepad "%ENV_FILE%"
    exit /b 1
)

REM 環境変数ファイルを読み込む
echo 環境変数ファイル %ENV_FILE% から設定を読み込んでいます...
for /f "tokens=1,2 delims==" %%a in ('type "%ENV_FILE%" ^| findstr /v "^#" ^| findstr /r /c:"="') do (
    set "key=%%a"
    set "value=%%b"
    
    REM 先頭と末尾の空白を削除
    set "key=!key: =!"
    
    REM 値が空でなければ環境変数を設定
    if not "!value!"=="" (
        setx !key! "!value!" > nul
        set "!key!=!value!"
        echo - !key! を設定しました
    )
)

REM BigQueryの設定を確認
echo.
echo 設定された環境変数:
echo - BIGQUERY_PROJECT_ID: %BIGQUERY_PROJECT_ID%
echo - BIGQUERY_DATASET: %BIGQUERY_DATASET%
echo - GCS_KEY_PATH: %GCS_KEY_PATH%

REM キーファイルの存在確認
if not exist "%GCS_KEY_PATH%" (
    echo.
    echo 警告: サービスアカウントキーファイル %GCS_KEY_PATH% が見つかりません。
    echo BigQuery APIにアクセスするには、有効なサービスアカウントキーが必要です。
    echo GCPコンソールからキーをダウンロードして、指定されたパスに配置してください。
)

echo.
echo 環境変数の設定が完了しました。
echo この設定はシステム再起動後も保持されます。

endlocal 