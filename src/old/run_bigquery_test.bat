@echo off
chcp 65001 >nul
REM BigQueryデータロードのテスト実行バッチファイル

echo ===== BigQueryデータロードテスト実行開始 =====
echo 実行日時: %date% %time%
echo.

REM Pandas/PyArrowをインストール
echo pandas/pyarrowをインストールしています...
pip install pandas pyarrow
echo.

REM 仮想環境が存在するか確認
if exist venv\Scripts\activate (
    echo 仮想環境を有効化します...
    call venv\Scripts\activate
) else (
    echo 警告: 仮想環境が見つかりません。インストールされているPythonを使用します。
)

echo.
echo ***** CSV形式テスト *****
echo.
echo ----- 日本語カラム名テスト (CSV) -----
python src/modules/bigquery/test_bigquery_load.py --file-format csv
set CSV_JAPANESE_RESULT=%ERRORLEVEL%

echo.
echo ----- 英語カラム名テスト (CSV) -----
python src/modules/bigquery/test_bigquery_load.py --english-headers --file-format csv
set CSV_ENGLISH_RESULT=%ERRORLEVEL%

echo.
echo ***** Parquet形式テスト *****
echo.
echo ----- 日本語カラム名テスト (Parquet) -----
python src/modules/bigquery/test_bigquery_load.py --file-format parquet
set PARQUET_JAPANESE_RESULT=%ERRORLEVEL%

echo.
echo ----- 英語カラム名テスト (Parquet) -----
python src/modules/bigquery/test_bigquery_load.py --english-headers --file-format parquet
set PARQUET_ENGLISH_RESULT=%ERRORLEVEL%

echo.
echo ===== テスト結果サマリー =====
echo CSV形式（日本語カラム名）: %CSV_JAPANESE_RESULT% (0=成功, 1=失敗)
echo CSV形式（英語カラム名）: %CSV_ENGLISH_RESULT% (0=成功, 1=失敗)
echo Parquet形式（日本語カラム名）: %PARQUET_JAPANESE_RESULT% (0=成功, 1=失敗)
echo Parquet形式（英語カラム名）: %PARQUET_ENGLISH_RESULT% (0=成功, 1=失敗)
echo.

REM テスト結果の判定
set FINAL_RESULT=0

if %CSV_JAPANESE_RESULT% NEQ 0 (
    echo [警告] CSV形式（日本語カラム名）テストが失敗しました
    set FINAL_RESULT=1
) else (
    echo [成功] CSV形式（日本語カラム名）テストが成功しました
)

if %CSV_ENGLISH_RESULT% NEQ 0 (
    echo [警告] CSV形式（英語カラム名）テストが失敗しました
    set FINAL_RESULT=1
) else (
    echo [成功] CSV形式（英語カラム名）テストが成功しました
)

if %PARQUET_JAPANESE_RESULT% NEQ 0 (
    echo [警告] Parquet形式（日本語カラム名）テストが失敗しました
    set FINAL_RESULT=1
) else (
    echo [成功] Parquet形式（日本語カラム名）テストが成功しました
)

if %PARQUET_ENGLISH_RESULT% NEQ 0 (
    echo [警告] Parquet形式（英語カラム名）テストが失敗しました
    set FINAL_RESULT=1
) else (
    echo [成功] Parquet形式（英語カラム名）テストが成功しました
)

echo.
echo テスト実行完了

if "%FINAL_RESULT%"=="1" (
    echo [全体結果] テストに失敗があります
    exit /b 1
) else (
    echo [全体結果] すべてのテストが成功しました
    exit /b 0
) 