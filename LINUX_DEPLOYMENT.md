# 🐧 Linux Deployment Rehberi

## 📋 Ön Gereksinimler

- Ubuntu/Debian Linux sunucu
- Root veya sudo erişimi
- Domain: www.baycode.com.tr
- Alt klasör: `/piarte`

## 🚀 Hızlı Kurulum

### Adım 1: Dosyaları Yükle

```bash
# Proje dizinine git
cd /var/www
sudo mkdir -p piarte
cd piarte

# Dosyaları buraya yükle (FTP, SCP, Git vb.)
# Örnek Git ile:
sudo git clone https://github.com/yourusername/piarte.git .
# veya dosyaları manuel yükle
```

### Adım 2: Kurulum Scriptini Çalıştır

```bash
# Script'i çalıştırılabilir yap
chmod +x LINUX_SETUP.sh

# Çalıştır
sudo ./LINUX_SETUP.sh
```

**VEYA manuel kurulum:**

```bash
# 1. Virtual environment oluştur
cd /var/www/piarte
python3 -m venv venv
source venv/bin/activate

# 2. Bağımlılıkları yükle
pip install -r requirements.txt

# 3. Systemd service oluştur (aşağıdaki bölüme bakın)
```

### Adım 3: Systemd Service Oluştur

```bash
sudo nano /etc/systemd/system/piarte.service
```

İçeriği:

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
Environment="DATABASE_URL=postgresql://user:pass@host:5432/dbname"
ExecStart=/var/www/piarte/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --root-path /piarte
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Service'i başlat:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable piarte
sudo systemctl start piarte
sudo systemctl status piarte
```

### Adım 4: Nginx Yapılandırması

```bash
# Yapılandırma dosyasını oluştur
sudo nano /etc/nginx/sites-available/piarte
```

İçeriği `nginx_piarte.conf` dosyasındaki gibi yapın veya dosyayı kopyalayın:

```bash
sudo cp nginx_piarte.conf /etc/nginx/sites-available/piarte
```

**Symlink oluştur:**

```bash
sudo ln -s /etc/nginx/sites-available/piarte /etc/nginx/sites-enabled/
```

**Test ve yeniden başlat:**

```bash
sudo nginx -t
sudo systemctl restart nginx
```

## 🔍 Kontrol ve Test

### 1. Service Durumu

```bash
sudo systemctl status piarte
```

### 2. Logları İzle

```bash
# Service logları
sudo journalctl -u piarte -f

# Nginx logları
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

### 3. Port Kontrolü

```bash
# Port 8000 dinleniyor mu?
sudo netstat -tulpn | grep 8000
# veya
sudo ss -tulpn | grep 8000
```

### 4. Test Endpoint'leri

```bash
# Health check
curl http://localhost:8000/health

# Ana sayfa
curl http://localhost:8000/

# Login sayfası
curl http://localhost:8000/login/admin
```

### 5. Tarayıcıda Test

- `http://www.baycode.com.tr/piarte/` → Ana sayfa
- `http://www.baycode.com.tr/piarte/login/admin` → Admin giriş
- `http://www.baycode.com.tr/piarte/health` → Health check

## 🔧 Sorun Giderme

### Service Başlamıyor

```bash
# Hata mesajlarını kontrol et
sudo journalctl -u piarte -n 50

# Manuel başlatmayı dene
cd /var/www/piarte
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --root-path /piarte
```

### Nginx 502 Bad Gateway

```bash
# FastAPI çalışıyor mu?
curl http://127.0.0.1:8000/health

# Port doğru mu?
sudo netstat -tulpn | grep 8000

# Nginx yapılandırmasını kontrol et
sudo nginx -t
```

### Permission Hataları

```bash
# Dosya sahipliğini düzelt
sudo chown -R www-data:www-data /var/www/piarte

# İzinleri düzelt
sudo chmod -R 755 /var/www/piarte
sudo chmod -R 644 /var/www/piarte/*.py
```

### Database Bağlantı Hatası

```bash
# Environment variable'ı kontrol et
sudo systemctl show piarte | grep DATABASE_URL

# .env dosyası oluştur (gerekirse)
sudo nano /var/www/piarte/.env
# DATABASE_URL=postgresql://...
```

## 🔐 Güvenlik

### 1. Firewall

```bash
# UFW ile
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2. SSL/HTTPS (Let's Encrypt)

```bash
# Certbot yükle
sudo apt install certbot python3-certbot-nginx

# SSL sertifikası al
sudo certbot --nginx -d www.baycode.com.tr -d baycode.com.tr
```

### 3. Secret Key Değiştir

`app/main.py` dosyasında:
```python
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "güvenli-key-buraya"))
```

Environment variable olarak ekle:
```bash
sudo systemctl edit piarte
```

İçeriği:
```ini
[Service]
Environment="SECRET_KEY=güvenli-secret-key-buraya"
```

## 📊 Monitoring

### Systemd Service Logları

```bash
# Son 100 satır
sudo journalctl -u piarte -n 100

# Canlı izleme
sudo journalctl -u piarte -f

# Bugünkü loglar
sudo journalctl -u piarte --since today
```

### Nginx Logları

```bash
# Access log
sudo tail -f /var/log/nginx/access.log

# Error log
sudo tail -f /var/log/nginx/error.log
```

## 🔄 Güncelleme

```bash
# 1. Service'i durdur
sudo systemctl stop piarte

# 2. Dosyaları güncelle (Git, FTP vb.)
cd /var/www/piarte
git pull  # veya dosyaları yükle

# 3. Bağımlılıkları güncelle (gerekirse)
source venv/bin/activate
pip install -r requirements.txt

# 4. Service'i başlat
sudo systemctl start piarte

# 5. Durumu kontrol et
sudo systemctl status piarte
```

## 📝 Özet Komutlar

```bash
# Service yönetimi
sudo systemctl start piarte      # Başlat
sudo systemctl stop piarte       # Durdur
sudo systemctl restart piarte    # Yeniden başlat
sudo systemctl status piarte     # Durum
sudo systemctl enable piarte     # Otomatik başlat

# Loglar
sudo journalctl -u piarte -f     # Canlı log

# Nginx
sudo nginx -t                    # Test
sudo systemctl restart nginx     # Yeniden başlat

# Dosya izinleri
sudo chown -R www-data:www-data /var/www/piarte
```

## ✅ Kontrol Listesi

- [ ] Dosyalar `/var/www/piarte` dizininde
- [ ] Virtual environment oluşturuldu
- [ ] Bağımlılıklar yüklendi (`pip install -r requirements.txt`)
- [ ] Systemd service oluşturuldu ve çalışıyor
- [ ] Nginx yapılandırması yapıldı
- [ ] Port 8000 açık ve dinleniyor
- [ ] `www.baycode.com.tr/piarte/` açılıyor
- [ ] Login sayfaları çalışıyor
- [ ] Database bağlantısı çalışıyor
- [ ] SSL sertifikası yüklendi (opsiyonel)


