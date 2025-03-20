@echo off
chcp 65001 >nul
setlocal

echo ===== Python ライブラリアップデートツール =====
echo.

:: Python が利用可能か確認
python --version > nul 2>&1
if errorlevel 1 (
    echo エラー: Python が見つかりません。
    echo Python がインストールされていることを確認してください。
    goto END
)

:: 仮想環境の存在確認
if not exist "venv" (
    echo 仮想環境が見つかりません。新しく作成します...
    python -m venv venv
    if errorlevel 1 (
        echo 仮想環境の作成に失敗しました。
        goto END
    )
    echo 仮想環境を作成しました。
)

:: 仮想環境をアクティベート
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo 仮想環境のアクティベートに失敗しました。
    goto END
)

echo 仮想環境をアクティベートしました。

:: pip のアップグレード
echo pip をアップグレードしています...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo pip のアップグレードに失敗しました。
    goto DEACTIVATE
)

:: requirements.txt の存在確認
if not exist "requirements.txt" (
    echo requirements.txt が見つかりません。
    goto DEACTIVATE
)

:: ライブラリのアップデート
echo.
echo ライブラリをアップデートしています...
pip install -r requirements.txt --upgrade
if errorlevel 1 (
    echo ライブラリのアップデートに失敗しました。
    goto DEACTIVATE
)

echo.
echo 現在インストールされているパッケージ一覧:
pip list
echo.
echo ライブラリのアップデートが完了しました。

:DEACTIVATE
:: 仮想環境を非アクティベート
call venv\Scripts\deactivate.bat

:END
echo.
echo 処理を終了します。
pause
endlocal 