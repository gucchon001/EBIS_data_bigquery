pushd \\nas\public\事務業務資料\100000管理部門\101000システム\事業部プログラム\講師求人部門\AE_parquet
call C:\Users\tmnk015\anaconda3\Scripts\activate.bat
python main.py

REM エラーレベルの確認
if %ERRORLEVEL% neq 0 (
    echo Pythonスクリプトでエラーが発生しました。
)

REM 一時的なドライブを解除（エラーが発生しても必ず実行）
popd

echo 1分待っています...
timeout /t 60 /nobreak >nul
exit/b