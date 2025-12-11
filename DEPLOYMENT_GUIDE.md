# IHS Telekom Sunucusuna Deployment Rehberi

Bu rehber, Piarte Kurs Yönetim Sistemi'ni IHS Telekom sunucusuna taşımanız için adım adım talimatlar içermektedir.

## 📋 Ön Hazırlık

### 1. Gerekli Bilgileri Toplayın
IHS Telekom'dan aşağıdaki bilgileri alın:
- **Sunucu IP adresi veya domain adı**
- **SSH erişim bilgileri** (kullanıcı adı, şifre veya SSH key)
- **Veritabanı bilgileri** (PostgreSQL veya MySQL):
  - Host adresi
  - Port (genellikle 5432 PostgreSQL için)
  - Veritabanı adı
  - Kullanıcı adı
  - Şifre
- **Python versiyonu** (Python 3.8+ gerekli)
- **Sunucu işletim sistemi** (Linux/Windows)

### 2. Yerel Veritabanınızı Yedekleyin
```bash
# SQLite veritabanınızı yedekleyin
cp data.db data.db.backup
```

## 🚀 Deployment Adımları

### Adım 1: Dosyaları Sunucuya Yükleme

#### Seçenek A: FTP/SFTP ile Yükleme
1. FileZilla, WinSCP veya benzeri bir FTP/SFTP istemcisi kullanın
2. IHS Telekom'dan aldığınız bilgilerle bağlanın
3. Tüm proje dosyalarını sunucuya yükleyin (data.db hariç - bu yeni oluşturulacak)

#### Seçenek B: Git ile Yükleme (Önerilen)
```bash
# Sunucuya SSH ile bağlanın
ssh kullanici@sunucu-ip

# Proje dizini oluşturun
mkdir -p /var/www/piarte
cd /var/www/piarte

# Git repository'nizi clone edin (eğer Git kullanıyorsanız)
# VEYA dosyaları manuel olarak yükleyin
```

### Adım 2: Python Ortamını Hazırlama

```bash
# Sunucuya SSH ile bağlanın
ssh kullanici@sunucu-ip

# Proje dizinine gidin
cd /var/www/piarte  # veya projenizin bulunduğu dizin

# Python virtual environment oluşturun
python3 -m venv venv

# Virtual environment'ı aktif edin
source venv/bin/activate  # Linux için
# veya
venv\Scripts\activate  # Windows için

# Bağımlılıkları yükleyin
pip install --upgrade pip
pip install -r requirements.txt
```

### Adım 3: Ortam Değişkenlerini Ayarlama

```bash
# .env dosyası oluşturun
nano .env  # veya vi .env
```

`.env` dosyasına şunları ekleyin:
```env
# Veritabanı Bağlantısı (PostgreSQL için)
DATABASE_URL=postgresql://kullanici:sifre@host:port/veritabani_adi

# Örnek:
# DATABASE_URL=postgresql://piarte_user:güvenli_şifre@localhost:5432/piarte_db

# Session Secret Key (GÜVENLİK İÇİN MUTLAKA DEĞİŞTİRİN!)
SECRET_KEY=değiştirin-bu-çok-güvenli-bir-anahtar-olmalı-en-az-32-karakter

# Root Path (eğer uygulama alt dizinde çalışacaksa)
ROOT_PATH=

# Sunucu ayarları
HOST=0.0.0.0
PORT=8000
```

**ÖNEMLİ:** `SECRET_KEY` değerini mutlaka güçlü bir rastgele string ile değiştirin!

### Adım 4: Veritabanını Yapılandırma

#### PostgreSQL Kullanıyorsanız:

```bash
# PostgreSQL'e bağlanın
psql -U postgres

# Veritabanı oluşturun
CREATE DATABASE piarte_db;

# Kullanıcı oluşturun (eğer yoksa)
CREATE USER piarte_user WITH PASSWORD 'güvenli_şifre';

# Yetkileri verin
GRANT ALL PRIVILEGES ON DATABASE piarte_db TO piarte_user;
\q
```

#### SQLite'dan PostgreSQL'e Veri Taşıma:

Eğer mevcut SQLite veritabanınız varsa ve verileri taşımak istiyorsanız:

1. **Yerel bilgisayarınızda** verileri export edin:
```bash
# Python script ile export (export_data.py oluşturun - aşağıda)
python export_data.py
```

2. **Sunucuda** veritabanını kurun:
```bash
# Sunucuda virtual environment aktifken
python setup_database.py
```

### Adım 5: Uygulamayı Başlatma

#### Seçenek A: Manuel Başlatma (Test için)
```bash
# Virtual environment aktifken
cd /var/www/piarte
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### Seçenek B: Systemd Service ile (Production - Linux için)

`/etc/systemd/system/piarte.service` dosyası oluşturun:

```ini
[Unit]
Description=Piarte Kurs Yönetim Sistemi
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/piarte
Environment="PATH=/var/www/piarte/venv/bin"
EnvironmentFile=/var/www/piarte/.env
ExecStart=/var/www/piarte/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Service'i başlatın:
```bash
sudo systemctl daemon-reload
sudo systemctl enable piarte
sudo systemctl start piarte
sudo systemctl status piarte
```

#### Seçenek C: Nginx Reverse Proxy ile (Önerilen)

`/etc/nginx/sites-available/piarte` dosyası oluşturun:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # Domain adresiniz

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static dosyalar için (opsiyonel)
    location /static {
        alias /var/www/piarte;
    }
}
```

Nginx'i yeniden başlatın:
```bash
sudo ln -s /etc/nginx/sites-available/piarte /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Adım 6: İlk Kurulum

1. Tarayıcıda şu adrese gidin: `http://sunucu-ip:8000/setup-database`
2. Veritabanı tabloları otomatik oluşturulacak
3. Admin kullanıcısı oluşturulacak:
   - Kullanıcı adı: `admin`
   - Şifre: `admin123`
4. **HEMEN** admin paneline giriş yapıp şifreyi değiştirin!

## 🔒 Güvenlik Kontrol Listesi

- [ ] `.env` dosyasındaki `SECRET_KEY` değiştirildi
- [ ] `app/main.py` dosyasındaki `secret_key` değiştirildi (satır 45)
- [ ] Veritabanı şifresi güçlü ve güvenli
- [ ] Admin şifresi değiştirildi
- [ ] Firewall ayarları yapıldı (sadece gerekli portlar açık)
- [ ] HTTPS/SSL sertifikası kuruldu (Let's Encrypt önerilir)
- [ ] CORS ayarları production için güncellendi (app/main.py satır 39)

## 📊 Veritabanı Yedekleme

Düzenli yedekleme için cron job oluşturun:

```bash
# Crontab düzenle
crontab -e

# Her gün saat 02:00'de yedek al
0 2 * * * pg_dump -U piarte_user piarte_db > /backup/piarte_$(date +\%Y\%m\%d).sql
```

## 🐛 Sorun Giderme

### Uygulama başlamıyor
```bash
# Logları kontrol edin
sudo journalctl -u piarte -f

# Manuel olarak çalıştırıp hataları görün
cd /var/www/piarte
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Veritabanı bağlantı hatası
- `.env` dosyasındaki `DATABASE_URL` değerini kontrol edin
- Veritabanı servisinin çalıştığını kontrol edin: `sudo systemctl status postgresql`
- Firewall ayarlarını kontrol edin

### Port erişilemiyor
- Firewall'da port 8000'in açık olduğundan emin olun
- Nginx kullanıyorsanız, Nginx'in çalıştığını kontrol edin

## 📞 Destek

Sorun yaşarsanız:
1. Log dosyalarını kontrol edin
2. IHS Telekom teknik destek ile iletişime geçin
3. Hata mesajlarını not edin

## 🔄 Güncelleme

Kod güncellemeleri için:
```bash
cd /var/www/piarte
source venv/bin/activate
git pull  # Eğer Git kullanıyorsanız
# VEYA yeni dosyaları yükleyin
pip install -r requirements.txt
sudo systemctl restart piarte
```

---

**Not:** Bu rehber genel bir kılavuzdur. IHS Telekom'un sunucu yapılandırmasına göre bazı adımlar değişiklik gösterebilir.


