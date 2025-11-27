# 🚀 Sunucuda Kurulum Rehberi (Adım Adım)

## 📋 Ön Hazırlık

SSH ile sunucuya bağlanın:
```bash
ssh kullanici@sunucu-ip
# veya
ssh kullanici@www.baycode.com.tr
```

## 🔧 Adım 1: Dosyaları Yükle

### Yöntem 1: FTP ile (En Kolay)

1. FileZilla veya WinSCP ile bağlanın
2. Dosyaları şu dizine yükleyin:
   ```
   /var/www/piarte/
   ```
   
   **Yüklenecek dosyalar:**
   - `app/` klasörü (tümü)
   - `templates/` klasörü (tümü)
   - `index.html`
   - `requirements.txt`
   - `piarte_logo.jpg` (varsa)

### Yöntem 2: SCP ile

```bash
# Yerel bilgisayarınızdan
scp -r app/ templates/ index.html requirements.txt kullanici@sunucu:/var/www/piarte/
```

### Yöntem 3: Git ile (Opsiyonel - FileZilla ile yükleme yaptıysanız gerekmez)

**ÖNCE:** GitHub'da repository oluşturmanız gerekir.

```bash
# SSH ile sunucuya bağlanın (PowerShell'den)
ssh baycode@www.baycode.com.tr
# VEYA farklı port: ssh -p 2222 baycode@www.baycode.com.tr

# Sunucuda dizine git
cd /var/www
# VEYA shared hosting için: cd ~/public_html

# Git repository'den clone et
git clone https://github.com/kullanici-adi/piarte.git piarte
# Not: GitHub'da repository oluşturmanız ve dosyaları push etmeniz gerekir

cd piarte
```

**Not:** FileZilla ile zaten yükleme yaptıysanız bu adımı atlayın!

## 🐍 Adım 2: Dosyaların Yerini Bul ve Kontrol Et

**ÖNEMLİ:** FileZilla ile yükleme yaptıysanız, dosyaların nerede olduğunu bulun:

```bash
# FileZilla'da dosyaları nereye yüklediğinizi kontrol edin
# Genellikle şu dizinlerden biri:

cd ~/public_html/piarte    # Shared hosting için
# VEYA
cd /var/www/piarte         # VPS için
# VEYA
cd ~/piarte                # Home dizini

# Dosyaları kontrol et
ls -la
# app/, templates/, index.html görünmeli
```

## 🐍 Adım 3: Python ve Gereksinimleri Kontrol Et

```bash
# Python versiyonunu kontrol et (3.8+ olmalı)
python3 --version

# Yoksa yükle
sudo apt update
sudo apt install -y python3 python3-pip python3-venv
```

## 📦 Adım 4: Virtual Environment Oluştur

**Not:** FileZilla ile yükleme yaptıysanız Adım 2'den devam edin, bu adımı atlayın.

```bash
cd /var/www/piarte

# Virtual environment oluştur
python3 -m venv venv

# Aktif et
source venv/bin/activate

# Pip'i güncelle
pip install --upgrade pip
```

## 📥 Adım 5: Bağımlılıkları Yükle

**Not:** FileZilla ile yükleme yaptıysanız, dosyaların olduğu dizinde bu adımdan devam edin.

```bash
# Virtual environment aktif olmalı (venv) yazıyor mu?
which python  # /var/www/piarte/venv/bin/python göstermeli

# Bağımlılıkları yükle
pip install -r requirements.txt

# Kontrol et
pip list
# fastapi, uvicorn, sqlalchemy görünmeli
```

## 🗄️ Adım 6: Veritabanı Ayarları

### Seçenek 1: SQLite (Hızlı Test)

```bash
# data.db dosyası otomatik oluşturulacak
# Bir şey yapmanıza gerek yok
```

### Seçenek 2: PostgreSQL (Production - Önerilen)

```bash
# PostgreSQL yükle (yoksa)
sudo apt install -y postgresql postgresql-contrib

# Veritabanı oluştur
sudo -u postgres psql
```

PostgreSQL'de:
```sql
CREATE DATABASE piarte_db;
CREATE USER piarte_user WITH PASSWORD 'güvenli_şifre';
GRANT ALL PRIVILEGES ON DATABASE piarte_db TO piarte_user;
\q
```

Environment variable ayarla (Adım 8'de)

## ⚙️ Adım 7: Test Çalıştırma

```bash
cd /var/www/piarte
source venv/bin/activate

# Test olarak çalıştır
uvicorn app.main:app --host 0.0.0.0 --port 8000 --root-path /piarte
```

**Başka bir terminal'de test et:**
```bash
curl http://localhost:8000/health
# {"status":"ok","message":"Server is running"} dönmeli
```

**Ctrl+C ile durdurun** (şimdilik)

## 🔄 Adım 8: Systemd Service Oluştur

```bash
sudo nano /etc/systemd/system/piarte.service
```

**İçeriği yapıştırın:**

```ini
[Unit]
Description=Piarte Kurs Yönetimi
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/piarte
Environment="PATH=/var/www/piarte/venv/bin"
Environment="ROOT_PATH=/piarte"
Environment="DATABASE_URL=sqlite:///./data.db"
# PostgreSQL kullanıyorsanız yukarıdaki satırı şununla değiştirin:
# Environment="DATABASE_URL=postgresql://piarte_user:şifre@localhost:5432/piarte_db"
ExecStart=/var/www/piarte/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --root-path /piarte
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Kaydedin (Ctrl+O, Enter, Ctrl+X)**

**Service'i başlat:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable piarte
sudo systemctl start piarte
sudo systemctl status piarte
```

**Başarılı olmalı - yeşil "active (running)" görmelisiniz**

## 🌐 Adım 9: Nginx Yapılandırması

```bash
sudo nano /etc/nginx/sites-available/piarte
```

**İçeriği yapıştırın:**

```nginx
server {
    listen 80;
    server_name www.baycode.com.tr baycode.com.tr;

    # /piarte alt klasörü için
    location /piarte/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        rewrite ^/piarte/(.*)$ /$1 break;
    }
    
    location = /piarte {
        return 301 /piarte/;
    }
}
```

**Kaydedin**

**Symlink oluştur:**
```bash
sudo ln -s /etc/nginx/sites-available/piarte /etc/nginx/sites-enabled/
```

**Test ve yeniden başlat:**
```bash
sudo nginx -t
# "syntax is ok" görmelisiniz

sudo systemctl restart nginx
```

## ✅ Adım 10: Test

### 1. Service Durumu
```bash
sudo systemctl status piarte
```

### 2. Port Kontrolü
```bash
sudo netstat -tulpn | grep 8000
# 127.0.0.1:8000 dinleniyor olmalı
```

### 3. Tarayıcıda Test
- `http://www.baycode.com.tr/piarte/` → Ana sayfa açılmalı
- `http://www.baycode.com.tr/piarte/login/admin` → Admin giriş açılmalı
- `http://www.baycode.com.tr/piarte/health` → `{"status":"ok"}` dönmeli

## 🔍 Sorun Giderme

### Service Başlamıyor

```bash
# Hata mesajlarını gör
sudo journalctl -u piarte -n 50

# Yaygın hatalar:
# 1. "No module named 'app'" → app/ klasörü yok veya yanlış dizinde
# 2. "Port already in use" → Port 8000 kullanılıyor
# 3. "Permission denied" → Dosya izinleri yanlış
```

### Dosya İzinleri Düzelt

```bash
sudo chown -R www-data:www-data /var/www/piarte
sudo chmod -R 755 /var/www/piarte
```

### Port Kullanımda

```bash
# Hangi process kullanıyor?
sudo lsof -i :8000
# veya
sudo fuser -k 8000/tcp  # Durdur (dikkatli!)
```

### Nginx 502 Bad Gateway

```bash
# FastAPI çalışıyor mu?
curl http://127.0.0.1:8000/health

# Nginx loglarını kontrol et
sudo tail -f /var/log/nginx/error.log
```

## 📝 Hızlı Komutlar

```bash
# Service yönetimi
sudo systemctl start piarte      # Başlat
sudo systemctl stop piarte       # Durdur
sudo systemctl restart piarte    # Yeniden başlat
sudo systemctl status piarte     # Durum

# Loglar
sudo journalctl -u piarte -f    # Canlı log

# Nginx
sudo nginx -t                    # Test
sudo systemctl restart nginx     # Yeniden başlat
```

## ✅ Kontrol Listesi

Kurulum tamamlandı mı?

- [ ] Dosyalar `/var/www/piarte` dizininde
- [ ] Virtual environment oluşturuldu (`venv/`)
- [ ] Bağımlılıklar yüklendi (`pip install -r requirements.txt`)
- [ ] Systemd service oluşturuldu ve çalışıyor
- [ ] Nginx yapılandırması yapıldı
- [ ] Port 8000 açık ve dinleniyor
- [ ] `www.baycode.com.tr/piarte/` açılıyor
- [ ] Login sayfaları çalışıyor

## 🎯 Özet

1. ✅ Dosyaları `/var/www/piarte` dizinine yükle
2. ✅ Virtual environment oluştur ve bağımlılıkları yükle
3. ✅ Systemd service oluştur ve başlat
4. ✅ Nginx yapılandırmasını yap
5. ✅ Test et!

**Hazır! Artık `www.baycode.com.tr/piarte/` adresinden erişebilirsiniz.**

