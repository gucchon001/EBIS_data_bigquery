@echo off
REM BigQueryローダーのテストを実行するためのバッチファイル

SETLOCAL ENABLEDELAYEDEXPANSION

REM Pythonが利用可能か確認
WHERE python >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    ECHO Pythonが見つかりません。インストールしてください。
    EXIT /B 1
)

REM 必要なパッケージがインストールされているか確認
python -c "import pytest" >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    ECHO pytestがインストールされていません。インストールします...
    pip install pytest pytest-cov
    IF %ERRORLEVEL% NEQ 0 (
        ECHO pytestのインストールに失敗しました。
        EXIT /B 1
    )
)

REM コマンドラインオプションを解析
SET verbose=0
SET coverage=0
SET specific_test=

:parse_args
IF "%~1"=="" GOTO end_parse_args
IF "%~1"=="--verbose" SET verbose=1
IF "%~1"=="-v" SET verbose=1
IF "%~1"=="--coverage" SET coverage=1
IF "%~1"=="-c" SET coverage=1
IF "%~1"=="--test" (
    SET specific_test=%~2
    SHIFT
)
SHIFT
GOTO parse_args
:end_parse_args

REM テスト実行コマンドを構築
SET cmd=python -m pytest tests/bigquery

IF %verbose%==1 (
    SET cmd=!cmd! -v
)

IF %coverage%==1 (
    SET cmd=!cmd! --cov=src --cov-report=term --cov-report=html
)

IF NOT "%specific_test%"=="" (
    SET cmd=!cmd! !specific_test!
)

ECHO テストを実行中...
ECHO !cmd!
!cmd!

REM 終了コードを表示
SET exit_code=%ERRORLEVEL%
IF %exit_code%==0 (
    ECHO テストが正常に完了しました。
) ELSE (
    ECHO テストが失敗しました。終了コード: %exit_code%
)

EXIT /B %exit_code% 