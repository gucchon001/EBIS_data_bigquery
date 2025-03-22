@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul

echo ======================================================
echo BigQueryデータローダー単体テスト実行ツール
echo ======================================================

REM カレントディレクトリをスクリプトの場所に変更
cd /d "%~dp0"

REM Pythonコマンドを設定
if exist venv\Scripts\python.exe (
    set PYTHON_CMD=venv\Scripts\python.exe
) else (
    set PYTHON_CMD=python
)

REM 必要なパッケージのチェック
%PYTHON_CMD% -c "import pytest" 2>nul
if %errorlevel% neq 0 (
    echo pytest がインストールされていません。インストールします...
    %PYTHON_CMD% -m pip install pytest pytest-mock pytest-cov
    if %errorlevel% neq 0 (
        echo pytestのインストールに失敗しました。
        exit /b 1
    )
)

REM 引数の解析
set TEST_FILE=tests
set VERBOSE=

:parse_args
if "%~1"=="" goto :end_parse_args
if /i "%~1"=="--file" (
    set TEST_FILE=%~2
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--verbose" (
    set VERBOSE=-v
    shift
    goto :parse_args
)
if /i "%~1"=="--help" (
    echo 使用方法: %~nx0 [オプション]
    echo オプション:
    echo   --file FILE     特定のテストファイルまたはディレクトリを指定（デフォルト: tests）
    echo   --verbose       詳細な出力を表示
    exit /b 0
)
shift
goto :parse_args
:end_parse_args

echo テスト対象: %TEST_FILE%
if not "%VERBOSE%"=="" echo 詳細モード: 有効

REM テストの実行
echo テストを実行しています...
%PYTHON_CMD% -m pytest %TEST_FILE% %VERBOSE% --cov=src

if %errorlevel% neq 0 (
    echo テストが失敗しました。
    exit /b 1
)

echo ======================================================
echo テストが完了しました。
echo ======================================================

endlocal 