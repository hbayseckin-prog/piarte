@echo off
REM Piarte Yerel Veritabanı Kurulum Scripti
REM Bu script yerel veritabanını kurar ve seed data ekler

echo ========================================
echo   Piarte Veritabanı Kurulumu
echo ========================================
echo.

cd /d "%~dp0"

REM Virtual environment kontrolü
if not exist "venv\Scripts\activate.bat" (
    echo [HATA] Virtual environment bulunamadı!
    echo.
    echo Lütfen önce virtual environment oluşturun:
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM Virtual environment'ı aktif et
call venv\Scripts\activate.bat

echo [BILGI] Veritabanı kurulumu başlatılıyor...
echo.

REM Veritabanı kurulum scriptini çalıştır
python setup_database.py

echo.
echo ========================================
if %ERRORLEVEL% EQU 0 (
    echo   [BASARILI] Veritabanı kurulumu tamamlandı!
    echo.
    echo   Sonraki adımlar:
    echo   1. start_server_local.bat ile sunucuyu başlatın
    echo   2. Tarayıcıda http://localhost:8000 adresine gidin
    echo   3. Admin ile giriş yapın (kullanıcı: admin, şifre: admin123)
    echo   4. Mutlaka şifrenizi değiştirin!
) else (
    echo   [HATA] Veritabanı kurulumu başarısız!
    echo   Lütfen hata mesajlarını kontrol edin.
)
echo ========================================
echo.
pause







