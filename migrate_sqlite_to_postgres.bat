@echo off
REM SQLite'dan PostgreSQL'e Veri Taşıma Scripti
REM Bu script mevcut SQLite verilerini PostgreSQL'e taşır

echo ========================================
echo   SQLite -^> PostgreSQL Veri Taşıma
echo ========================================
echo.

cd /d "%~dp0"

REM Virtual environment kontrolü
if not exist "venv\Scripts\activate.bat" (
    echo [HATA] Virtual environment bulunamadı!
    pause
    exit /b 1
)

REM Virtual environment'ı aktif et
call venv\Scripts\activate.bat

REM SQLite veritabanı kontrolü
if not exist "data.db" (
    echo [HATA] data.db dosyası bulunamadı!
    pause
    exit /b 1
)

echo [BILGI] SQLite veritabanından veriler export ediliyor...
python export_data.py data.db

if not exist "data_export.json" (
    echo [HATA] Export işlemi başarısız!
    pause
    exit /b 1
)

echo.
echo [BASARILI] Veriler export edildi: data_export.json
echo.
echo [ONEMLI] Şimdi .env dosyasında DATABASE_URL'yi PostgreSQL olarak ayarlayın:
echo   DATABASE_URL=postgresql://postgres:sifre@localhost:5432/piarte_db
echo.
echo PostgreSQL veritabanınız hazır mı? (Y/N)
set /p confirm=
if /i not "%confirm%"=="Y" (
    echo İşlem iptal edildi.
    pause
    exit /b 0
)

echo.
echo [BILGI] Veriler PostgreSQL'e import ediliyor...
python import_data.py data_export.json

echo.
if %ERRORLEVEL% EQU 0 (
    echo [BASARILI] Veri taşıma işlemi tamamlandı!
    echo.
    echo [ONEMLI] Artık .env dosyasında PostgreSQL kullanabilirsiniz.
    echo SQLite veritabanı (data.db) yedek olarak saklanabilir.
) else (
    echo [HATA] Import işlemi başarısız!
    echo Lütfen hata mesajlarını kontrol edin.
)

echo.
pause













