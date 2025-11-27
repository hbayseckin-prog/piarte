# 🔧 SSH ile Kurulum Komutları (PowerShell)

## 🔌 SSH Bağlantısı Sorunları

SSH timeout hatası alıyorsanız şunları deneyin:

### 1. Farklı Portları Deneyin

```powershell
# Port 2222
ssh -p 2222 baycode@www.baycode.com.tr

# Port 2200
ssh -p 2200 baycode@www.baycode.com.tr

# Port 22222
ssh -p 22222 baycode@www.baycode.com.tr
```

### 2. cPanel Terminal Kullanın

SSH çalışmıyorsa, cPanel'de Terminal erişimi olabilir:

1. cPanel'e giriş yapın: `https://www.baycode.com.tr:2083`
2. "Advanced" veya "Terminal" bölümünü arayın
3. "Terminal" veya "Web Terminal" açın
4. Aşağıdaki komutları orada çalıştırın

### 3. Hosting Sağlayıcınıza Sorun

- "SSH erişimim var mı?"
- "SSH port numarası nedir?"
- "SSH nasıl aktif edilir?"

## 📋 Kurulum Komutları (SSH Bağlandıktan Sonra)

SSH bağlantısı kurulduğunda, şu komutları sırayla çalıştırın:

### Adım 1: Dizine Git

```bash
# Dosyaların yüklendiği dizine git
cd /var/www/piarte
# VEYA shared hosting için:
cd ~/public_html/piarte
# VEYA
cd ~/piarte
```

**Hangi dizini kullanacağınızı FileZilla'da dosyaların nerede olduğuna bakarak anlayın.**

### Adım 2: Dosyaları Kontrol Et

```bash
# Dosyalar var mı kontrol et
ls -la

# Şunları görmelisiniz:
# app/  templates/  index.html  requirements.txt  kurulum.sh
```

### Adım 3: Python Kontrolü

```bash
# Python versiyonunu kontrol et
python3 --version

# 3.8+ olmalı, yoksa yükle:
# sudo apt update && sudo apt install -y python3 python3-pip python3-venv
```

### Adım 4: Virtual Environment Oluştur

```bash
# Virtual environment oluştur
python3 -m venv venv

# Aktif et
source venv/bin/activate

# Kontrol et (başında (venv) yazmalı)
which python
```

### Adım 5: Bağımlılıkları Yükle

```bash
# Pip'i güncelle
pip install --upgrade pip

# Bağımlılıkları yükle
pip install -r requirements.txt

# Kontrol et
pip list | grep fastapi
```

### Adım 6: Systemd Service Oluştur

```bash
# Service dosyasını oluştur
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
ExecStart=/var/www/piarte/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --root-path /piarte
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Kaydedin:** Ctrl+O, Enter, Ctrl+X

**Not:** `WorkingDirectory` ve `ExecStart` yolunu dosyaların gerçek konumuna göre değiştirin!

### Adım 7: Service'i Başlat

```bash
# Systemd'yi yenile
sudo systemctl daemon-reload

# Service'i aktif et (otomatik başlatma)
sudo systemctl enable piarte

# Service'i başlat
sudo systemctl start piarte

# Durumu kontrol et
sudo systemctl status piarte
```

### Adım 8: Nginx Yapılandırması

```bash
# Nginx yapılandırma dosyası oluştur
sudo nano /etc/nginx/sites-available/piarte
```

**İçeriği yapıştırın:**

```nginx
server {
    listen 80;
    server_name www.baycode.com.tr baycode.com.tr;

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

**Kaydedin:** Ctrl+O, Enter, Ctrl+X

**Aktif edin:**

```bash
# Symlink oluştur
sudo ln -s /etc/nginx/sites-available/piarte /etc/nginx/sites-enabled/

# Yapılandırmayı test et
sudo nginx -t

# Nginx'i yeniden başlat
sudo systemctl restart nginx
```

### Adım 9: Test

```bash
# Service durumu
sudo systemctl status piarte

# Port kontrolü
sudo netstat -tulpn | grep 8000

# Health check
curl http://localhost:8000/health
```

## 🔍 Sorun Giderme Komutları

### Service Başlamıyorsa

```bash
# Hata mesajlarını gör
sudo journalctl -u piarte -n 50

# Logları canlı izle
sudo journalctl -u piarte -f
```

### Dosya İzinleri

```bash
# İzinleri düzelt
sudo chown -R www-data:www-data /var/www/piarte
sudo chmod -R 755 /var/www/piarte
sudo chmod +x /var/www/piarte/kurulum.sh
```

### Port Kullanımda

```bash
# Hangi process kullanıyor?
sudo lsof -i :8000

# Durdur (dikkatli!)
sudo fuser -k 8000/tcp
```

## 📝 Hızlı Komutlar (Kopyala-Yapıştır)

```bash
# Tüm kurulumu tek seferde (dikkatli kullanın!)
cd /var/www/piarte
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
sudo chown -R www-data:www-data /var/www/piarte
sudo systemctl daemon-reload
sudo systemctl restart piarte
sudo systemctl status piarte
```

## ⚠️ Önemli Notlar

1. **Dizin Yolu:** Dosyaların gerçek konumunu FileZilla'da kontrol edin
   - Shared hosting: `~/public_html/piarte` veya `~/piarte`
   - VPS: `/var/www/piarte`

2. **Sudo Yetkisi:** Bazı komutlar için sudo gerekebilir
   - Shared hosting'de sudo olmayabilir, o zaman farklı yöntemler gerekir

3. **Systemd:** Shared hosting'de systemd olmayabilir
   - O zaman PM2 veya nohup kullanın

## 🎯 Shared Hosting İçin Alternatif

Eğer systemd yoksa (shared hosting):

```bash
# PM2 ile (önce yükleyin: npm install -g pm2)
cd /var/www/piarte
source venv/bin/activate
pm2 start "uvicorn app.main:app --host 127.0.0.1 --port 8000 --root-path /piarte" --name piarte
pm2 save
pm2 startup
```

VEYA

```bash
# nohup ile
cd /var/www/piarte
source venv/bin/activate
nohup uvicorn app.main:app --host 127.0.0.1 --port 8000 --root-path /piarte > piarte.log 2>&1 &
```


