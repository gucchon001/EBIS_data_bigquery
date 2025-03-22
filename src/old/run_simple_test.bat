@echo off
chcp 65001 >nul
setlocal

echo ======================================================
echo シンプルなBigQueryロードテストを実行します
echo ======================================================

REM 必要なパッケージをインストール
echo パッケージをインストールしています...
pip install -r requirements.txt

REM 実行環境をセットアップ
set PYTHONIOENCODING=utf-8
set PYTHONPATH=%cd%

REM シンプルテストを実行
echo シンプルテストを実行します...
python src/modules/bigquery/test_simple.py

if %ERRORLEVEL% EQU 0 (
  echo テスト成功！
) else (
  echo テスト失敗。エラーを確認してください。
)

endlocal 