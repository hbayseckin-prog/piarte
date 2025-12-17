@echo off
REM Piarte Yerel Sunucu Başlatma Scripti
REM Bu script yerel bilgisayarda sunucuyu başlatır

echo ========================================
echo   Piarte Kurs Yönetim Sistemi
echo   Yerel Sunucu Başlatılıyor...
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

REM .env dosyası kontrolü
if not exist ".env" (
    echo [UYARI] .env dosyası bulunamadı!
    echo.
    if exist "env.example" (
        echo env.example dosyasından .env oluşturuluyor...
        copy env.example .env
        echo.
        echo [ONEMLI] Lütfen .env dosyasını düzenleyin ve DATABASE_URL ile SECRET_KEY değerlerini ayarlayın!
        echo.
        pause
    ) else (
        echo [HATA] env.example dosyası da bulunamadı!
        pause
        exit /b 1
    )
)

REM Veritabanı kontrolü (SQLite için)
if "%DATABASE_URL%"=="" (
    if not exist "data.db" (
        echo [BILGI] Veritabanı bulunamadı. Kurulum yapılıyor...
        python setup_database.py
        echo.
    )
)

echo.
echo ========================================
echo   Sunucu Başlatılıyor...
echo   Tarayıcıda açın: http://localhost:8000
echo   Durdurmak için: Ctrl+C
echo ========================================
echo.

REM Sunucuyu başlat
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

REM Sunucu kapatıldığında
echo.
echo Sunucu kapatıldı.
pause






