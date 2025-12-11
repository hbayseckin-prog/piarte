# 🖥️ Yerel Bilgisayarda Sunucu ve Veritabanı Kurulumu

Bu rehber, Piarte uygulamasını kendi bilgisayarınızda çalıştırmak için gerekli tüm adımları içerir.

## 📋 Gereksinimler

- Windows 10/11
- Python 3.8 veya üzeri
- PostgreSQL (veya SQLite - daha basit)
- İnternet bağlantısı (ilk kurulum için)

## 🚀 Hızlı Kurulum (SQLite ile - Basit)

### Adım 1: Python Kurulumu

1. [Python.org](https://www.python.org/downloads/) adresinden Python'u indirin
2. Kurulum sırasında **"Add Python to PATH"** seçeneğini işaretleyin
3. Kurulumu tamamlayın

Kontrol edin:
```cmd
python --version
```

### Adım 2: Proje Bağımlılıklarını Yükleyin

```cmd
cd C:\Users\bayCode Danışma\Desktop\Piarte
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Adım 3: Ortam Değişkenlerini Ayarlayın

`env.example` dosyasını `.env` olarak kopyalayın ve düzenleyin:

```env
# SQLite kullanımı için (basit)
DATABASE_URL=sqlite:///./data.db

# Session Secret Key (güvenli bir değer oluşturun)
SECRET_KEY=yerel-gelistirme-icin-guvensiz-ama-uygun-bir-anahtar

ROOT_PATH=
HOST=127.0.0.1
PORT=8000
```

### Adım 4: Veritabanını Başlatın

```cmd
python setup_database.py
```

### Adım 5: Sunucuyu Başlatın

```cmd
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Tarayıcıda açın: `http://localhost:8000`

---

## 🗄️ PostgreSQL ile Kurulum (Production Benzeri)

### Adım 1: PostgreSQL Kurulumu

1. [PostgreSQL Windows Installer](https://www.postgresql.org/download/windows/) indirin
2. Kurulum sırasında:
   - **Port**: 5432 (varsayılan)
   - **Superuser (postgres) şifresi**: Güçlü bir şifre belirleyin
   - **Locale**: Turkish, Turkey (opsiyonel)

### Adım 2: PostgreSQL Veritabanı Oluşturma

**pgAdmin ile (Grafik Arayüz):**
1. pgAdmin 4'ü açın
2. Sol tarafta "Servers" > "PostgreSQL" > sağ tık > "Create" > "Database"
3. Database name: `piarte_db`
4. Owner: `postgres` (veya kendi kullanıcınız)
5. "Save" tıklayın

**Komut Satırı ile:**
```cmd
# PostgreSQL bin dizinine gidin
cd "C:\Program Files\PostgreSQL\15\bin"

# psql'i çalıştırın
psql -U postgres

# Veritabanı oluşturun
CREATE DATABASE piarte_db;

# Kullanıcı oluşturun (opsiyonel)
CREATE USER piarte_user WITH PASSWORD 'güvenli_şifre';
GRANT ALL PRIVILEGES ON DATABASE piarte_db TO piarte_user;

# Çıkış
\q
```

### Adım 3: .env Dosyasını Ayarlayın

`.env` dosyasını düzenleyin:

```env
# PostgreSQL bağlantısı
DATABASE_URL=postgresql://postgres:şifreniz@localhost:5432/piarte_db

# Veya özel kullanıcı ile:
# DATABASE_URL=postgresql://piarte_user:güvenli_şifre@localhost:5432/piarte_db

SECRET_KEY=yerel-gelistirme-icin-guvensiz-ama-uygun-bir-anahtar
ROOT_PATH=
HOST=127.0.0.1
PORT=8000
```

### Adım 4: Veritabanını Başlatın

```cmd
python setup_database.py
```

### Adım 5: Sunucuyu Başlatın

```cmd
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## 🔄 Mevcut SQLite Verilerini PostgreSQL'e Taşıma

Eğer mevcut `data.db` dosyanız varsa ve PostgreSQL'e taşımak istiyorsanız:

### 1. Verileri Export Edin

```cmd
python export_data.py data.db
```

Bu işlem `data_export.json` dosyası oluşturur.

### 2. PostgreSQL'e Import Edin

`.env` dosyasında `DATABASE_URL`'i PostgreSQL olarak ayarlayın, sonra:

```cmd
python import_data.py data_export.json
```

---

## ⚙️ Otomatik Başlatma (Windows Service)

### Yöntem 1: Windows Task Scheduler ile

1. **Task Scheduler'ı açın** (Başlat > Görev Zamanlayıcı)

2. **Yeni Görev Oluşturun:**
   - Ad: "Piarte Server"
   - Tetikleyici: "Oturum açıldığında" veya "Bilgisayar başlatıldığında"
   - Eylem: Program başlat
   - Program: `C:\Users\bayCode Danışma\Desktop\Piarte\venv\Scripts\python.exe`
   - Argümanlar: `-m uvicorn app.main:app --host 127.0.0.1 --port 8000`
   - Başlangıç konumu: `C:\Users\bayCode Danışma\Desktop\Piarte`

### Yöntem 2: Batch Dosyası ile Başlatma

`start_server_local.bat` dosyası zaten mevcut. Bunu düzenleyebilirsiniz:

```batch
@echo off
cd /d "%~dp0"
call venv\Scripts\activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
```

### Yöntem 3: NSSM ile Windows Service (Gelişmiş)

1. [NSSM](https://nssm.cc/download) indirin
2. Komut satırından:

```cmd
# NSSM'i extract edin ve dizine gidin
cd C:\nssm\win64

# Service oluşturun
nssm install PiarteServer

# Açılan pencerede:
# Path: C:\Users\bayCode Danışma\Desktop\Piarte\venv\Scripts\python.exe
# Startup directory: C:\Users\bayCode Danışma\Desktop\Piarte
# Arguments: -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Service'i başlatın
nssm start PiarteServer
```

---

## 🔧 Veritabanı Yönetimi

### SQLite Veritabanı Yönetimi

**DB Browser for SQLite** kullanın:
1. [DB Browser for SQLite](https://sqlitebrowser.org/) indirin
2. `data.db` dosyasını açın
3. Verileri görüntüleyin, düzenleyin, sorgu çalıştırın

### PostgreSQL Veritabanı Yönetimi

**pgAdmin 4** kullanın (PostgreSQL ile birlikte gelir):
1. pgAdmin 4'ü açın
2. Sol tarafta veritabanınızı seçin
3. "Query Tool" ile SQL sorguları çalıştırın
4. "View/Edit Data" ile tabloları görüntüleyin

**Komut Satırı ile:**
```cmd
cd "C:\Program Files\PostgreSQL\15\bin"
psql -U postgres -d piarte_db
```

---

## 📊 Veritabanı Yedekleme

### SQLite Yedekleme

```cmd
# Basit kopyalama
copy data.db data_backup_%date%.db

# Veya PowerShell ile
Copy-Item data.db "data_backup_$(Get-Date -Format 'yyyyMMdd').db"
```

### PostgreSQL Yedekleme

```cmd
cd "C:\Program Files\PostgreSQL\15\bin"

# Yedek al
pg_dump -U postgres piarte_db > backup_%date%.sql

# Yedekten geri yükle
psql -U postgres piarte_db < backup_20240101.sql
```

**Otomatik Yedekleme (Task Scheduler):**
1. Task Scheduler'da yeni görev oluşturun
2. Günlük çalışacak şekilde ayarlayın
3. Program: `C:\Program Files\PostgreSQL\15\bin\pg_dump.exe`
4. Argümanlar: `-U postgres piarte_db > C:\Backups\piarte_%date%.sql`

---

## 🌐 Yerel Ağdan Erişim

Diğer cihazlardan erişmek için:

### 1. Firewall Ayarları

```cmd
# Windows Firewall'da port 8000'i açın
netsh advfirewall firewall add rule name="Piarte Server" dir=in action=allow protocol=TCP localport=8000
```

### 2. Sunucuyu Tüm Ağa Açın

`.env` dosyasında:
```env
HOST=0.0.0.0  # Tüm ağlardan erişim
PORT=8000
```

Sunucuyu başlatın:
```cmd
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. IP Adresinizi Bulun

```cmd
ipconfig
```

"IPv4 Address" değerini not edin (örn: 192.168.1.100)

### 4. Diğer Cihazlardan Erişin

Tarayıcıda: `http://192.168.1.100:8000`

---

## 🐛 Sorun Giderme

### Port Zaten Kullanımda

```cmd
# Hangi program port 8000'i kullanıyor?
netstat -ano | findstr :8000

# Process ID'yi bulun ve görev yöneticisinden kapatın
```

### PostgreSQL Bağlantı Hatası

1. PostgreSQL servisinin çalıştığını kontrol edin:
   - Services (Hizmetler) > PostgreSQL > Başlat

2. `.env` dosyasındaki `DATABASE_URL`'i kontrol edin
3. Şifrenin doğru olduğundan emin olun

### Python Modül Bulunamadı

```cmd
# Virtual environment aktif mi kontrol edin
venv\Scripts\activate

# Bağımlılıkları yeniden yükleyin
pip install -r requirements.txt
```

### Veritabanı Tabloları Oluşmuyor

```cmd
# Manuel olarak oluşturun
python setup_database.py

# Veya tarayıcıda
http://localhost:8000/setup-database
```

---

## 📝 Günlük Kullanım

### Sunucuyu Başlatma

```cmd
cd C:\Users\bayCode Danışma\Desktop\Piarte
venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Sunucuyu Durdurma

Terminal'de `Ctrl+C` tuşlarına basın

### Veritabanını Sıfırlama (DİKKAT: Tüm veriler silinir!)

```cmd
# SQLite için
del data.db
python setup_database.py

# PostgreSQL için
psql -U postgres
DROP DATABASE piarte_db;
CREATE DATABASE piarte_db;
\q
python setup_database.py
```

---

## ✅ Kontrol Listesi

- [ ] Python kurulu ve PATH'te
- [ ] Virtual environment oluşturuldu
- [ ] Bağımlılıklar yüklendi
- [ ] `.env` dosyası oluşturuldu ve ayarlandı
- [ ] Veritabanı oluşturuldu (SQLite veya PostgreSQL)
- [ ] `setup_database.py` çalıştırıldı
- [ ] Sunucu başarıyla başlatıldı
- [ ] Tarayıcıda `http://localhost:8000` açılıyor
- [ ] Admin girişi yapılabiliyor (admin/admin123)
- [ ] Admin şifresi değiştirildi

---

**İyi çalışmalar! 🚀**


