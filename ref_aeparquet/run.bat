pushd \\nas\public\�����Ɩ�����\100000�Ǘ�����\101000�V�X�e��\���ƕ��v���O����\�u�t���l����\AE_parquet
call C:\Users\tmnk015\anaconda3\Scripts\activate.bat
python main.py

REM �G���[���x���̊m�F
if %ERRORLEVEL% neq 0 (
    echo Python�X�N���v�g�ŃG���[���������܂����B
)

REM �ꎞ�I�ȃh���C�u�������i�G���[���������Ă��K�����s�j
popd

echo 1���҂��Ă��܂�...
timeout /t 60 /nobreak >nul
exit/b