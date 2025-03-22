@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

:: GCSアップローダーの実行スクリプト
echo GCSアップローダーを実行します...

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

:: GCSアップローダースクリプトの実行
echo data/AE_SSresultディレクトリのファイルをGCSにアップロードします...
%PYTHON_CMD% src/gcs_uploader.py

if %ERRORLEVEL% neq 0 (
    echo エラーが発生しました。詳細はログを確認してください。
    pause
    exit /b 1
)

echo アップロード処理が完了しました。
pause 