# 🔧 Sorun Giderme: "Sayfa Bulunamadı" Hatası

## ❌ Sorun
Anasayfa açılıyor ama panel seçildiğinde "sayfa bulunamadı" hatası veriyor.

## 🔍 Olası Nedenler

### 1. FastAPI Sunucusu Çalışmıyor ⚠️ (En Olası)

**Kontrol:**
```bash
# Sunucunun çalışıp çalışmadığını kontrol edin
curl http://localhost:8000/health
# veya tarayıcıda: http://yourdomain.com/health
```

**Çözüm:**
```bash
# Sunucuyu başlatın
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Veya production için:
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 2. index.html Static Olarak Serve Ediliyor

**Sorun:** index.html static dosya olarak açılıyor, FastAPI route'ları çalışmıyor.

**Kontrol:**
- URL'de `http://yourdomain.com/index.html` görünüyorsa → Sorun bu!
- Olması gereken: `http://yourdomain.com/` (sadece domain)

**Çözüm:**
- `index.html` dosyasını root dizine koyun
- FastAPI'nin `/` endpoint'i index.html'i serve etmeli
- Web sunucusu (Nginx/Apache) yapılandırmasını kontrol edin

### 3. Web Sunucusu Yapılandırması (Nginx/Apache)

**Nginx Örneği:**
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Static dosyalar için
    location /static {
        alias /path/to/Piarte;
    }

    # Tüm istekleri FastAPI'ye yönlendir
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. URL Yolları Yanlış

**Kontrol:**
- index.html'deki linkler: `/login/admin`, `/login/teacher`, `/login/staff`
- FastAPI endpoint'leri: `/login/admin`, `/login/teacher`, `/login/staff` ✅

**Doğru linkler:**
```html
<a href="/login/admin">   ✅ Doğru
<a href="login/admin">    ❌ Yanlış (göreceli path)
<a href="./login/admin">  ❌ Yanlış
```

## ✅ Adım Adım Çözüm

### Adım 1: Sunucunun Çalıştığını Kontrol Et

```bash
# Terminal'de
ps aux | grep uvicorn
# veya
netstat -tulpn | grep 8000
```

**Çalışmıyorsa başlatın:**
```bash
cd /path/to/Piarte
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Adım 2: index.html'in Doğru Yerde Olduğunu Kontrol Et

```bash
# index.html root dizinde olmalı
ls -la /path/to/Piarte/index.html
```

### Adım 3: FastAPI Route'larını Test Et

Tarayıcıda test edin:
- `http://yourdomain.com/` → index.html açılmalı
- `http://yourdomain.com/login/admin` → Admin giriş sayfası açılmalı
- `http://yourdomain.com/health` → `{"status": "ok"}` dönmeli

### Adım 4: Web Sunucusu Yapılandırmasını Kontrol Et

**Nginx:**
```bash
sudo nginx -t  # Yapılandırmayı test et
sudo systemctl restart nginx
```

**Apache:**
```bash
sudo apache2ctl configtest
sudo systemctl restart apache2
```

### Adım 5: Logları Kontrol Et

```bash
# FastAPI logları
tail -f /var/log/uvicorn.log

# Nginx logları
tail -f /var/log/nginx/error.log

# Systemd logları (eğer service olarak çalışıyorsa)
journalctl -u piarte -f
```

## 🚀 Hızlı Test

### Test 1: Health Check
```bash
curl http://localhost:8000/health
# Beklenen: {"status":"ok","message":"Server is running"}
```

### Test 2: Login Endpoint
```bash
curl http://localhost:8000/login/admin
# Beklenen: HTML içerik (giriş formu)
```

### Test 3: index.html
```bash
curl http://localhost:8000/
# Beklenen: index.html içeriği
```

## 🔧 Production İçin Systemd Service

`/etc/systemd/system/piarte.service`:
```ini
[Unit]
Description=Piarte Kurs Yönetimi
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/Piarte
Environment="PATH=/path/to/Piarte/venv/bin"
Environment="DATABASE_URL=postgresql://..."
ExecStart=/path/to/Piarte/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

[Install]
WantedBy=multi-user.target
```

**Başlat:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable piarte
sudo systemctl start piarte
sudo systemctl status piarte
```

## 📋 Kontrol Listesi

- [ ] FastAPI sunucusu çalışıyor mu? (`/health` endpoint'i çalışıyor mu?)
- [ ] `index.html` root dizinde mi?
- [ ] Web sunucusu (Nginx/Apache) FastAPI'ye proxy yapıyor mu?
- [ ] Port 8000 açık mı?
- [ ] Firewall ayarları doğru mu?
- [ ] Environment variables ayarlı mı? (`DATABASE_URL` vb.)

## 🆘 Hala Çalışmıyorsa

1. **Browser Console'u kontrol edin (F12)**
   - Network tab'ında hangi istekler başarısız?
   - Console'da hata var mı?

2. **Sunucu loglarını kontrol edin**
   - FastAPI logları
   - Web sunucusu logları
   - System logları

3. **Basit test:**
   ```bash
   # Direkt FastAPI'ye bağlan
   curl http://localhost:8000/login/admin
   # Çalışıyorsa → Web sunucusu sorunu
   # Çalışmıyorsa → FastAPI sorunu
   ```


