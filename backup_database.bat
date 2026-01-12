@echo off
REM Piarte Veritabanı Yedekleme Scripti
REM Bu script veritabanını yedekler

echo ========================================
echo   Piarte Veritabanı Yedekleme
echo ========================================
echo.

cd /d "%~dp0"

REM Tarih al
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%b%%a)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a%%b)
set mytime=%mytime: =0%

REM Yedek dizini oluştur
if not exist "backups" mkdir backups

REM SQLite yedekleme
if exist "data.db" (
    echo [BILGI] SQLite veritabanı yedekleniyor...
    copy "data.db" "backups\data_backup_%mydate%_%mytime%.db" >nul
    if %ERRORLEVEL% EQU 0 (
        echo [BASARILI] Yedek oluşturuldu: backups\data_backup_%mydate%_%mytime%.db
    ) else (
        echo [HATA] Yedek oluşturulamadı!
    )
) else (
    echo [UYARI] data.db dosyası bulunamadı!
)

REM PostgreSQL yedekleme (eğer DATABASE_URL PostgreSQL ise)
REM Not: PostgreSQL bin dizininin PATH'te olması gerekir
where pg_dump >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo.
    echo [BILGI] PostgreSQL yedekleme seçeneği mevcut.
    echo PostgreSQL yedekleme için manuel olarak çalıştırın:
    echo   pg_dump -U postgres piarte_db ^> backups\piarte_backup_%mydate%.sql
)

echo.
echo ========================================
echo   Yedekleme tamamlandı!
echo ========================================
echo.
pause













