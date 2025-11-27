# ⚡ Hızlı Çözüm: "Sayfa Bulunamadı" Hatası

## 🔴 Sorun
Anasayfa açılıyor ama panel seçildiğinde "sayfa bulunamadı" hatası veriyor.

## ✅ Hızlı Çözüm

### 1. FastAPI Sunucusu Çalışıyor mu?

**Kontrol:**
Tarayıcıda şu adresi açın:
```
http://yourdomain.com/health
```

**Beklenen sonuç:**
```json
{"status": "ok", "message": "Server is running"}
```

**Eğer hata alıyorsanız → Sunucu çalışmıyor!**

### 2. Sunucuyu Başlatın

**SSH ile sunucuya bağlanın ve:**

```bash
# Proje dizinine gidin
cd /path/to/Piarte

# Virtual environment aktif edin (varsa)
source venv/bin/activate

# Sunucuyu başlatın
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Veya systemd service kullanıyorsanız:**
```bash
sudo systemctl start piarte
sudo systemctl status piarte
```

### 3. Web Sunucusu Yapılandırması

**Eğer Nginx kullanıyorsanız:**

`/etc/nginx/sites-available/piarte` dosyasını kontrol edin:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # TÜM istekleri FastAPI'ye yönlendir
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Yeniden başlatın:**
```bash
sudo nginx -t
sudo systemctl restart nginx
```

## 🧪 Test

### Test 1: Health Check
```bash
curl http://localhost:8000/health
```

### Test 2: Login Sayfası
```bash
curl http://localhost:8000/login/admin
```

### Test 3: Python Script ile
```bash
python test_server.py
# veya farklı domain için:
python test_server.py http://yourdomain.com
```

## 📋 Kontrol Listesi

- [ ] FastAPI sunucusu çalışıyor mu? (`/health` çalışıyor mu?)
- [ ] Port 8000 açık mı?
- [ ] Web sunucusu (Nginx/Apache) FastAPI'ye proxy yapıyor mu?
- [ ] `index.html` root dizinde mi?
- [ ] Firewall ayarları doğru mu?

## 🚨 En Yaygın Sorun

**%90 ihtimalle:** FastAPI sunucusu çalışmıyor!

**Çözüm:**
```bash
# Sunucuya SSH ile bağlan
ssh user@yourdomain.com

# Proje dizinine git
cd /path/to/Piarte

# Sunucuyu başlat
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Production için (arka planda çalıştır):**
```bash
# PM2 ile
pm2 start "uvicorn app.main:app --host 0.0.0.0 --port 8000" --name piarte

# veya nohup ile
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > piarte.log 2>&1 &
```

## 💡 İpucu

Eğer **Railway, Render, DigitalOcean App Platform** gibi bir platform kullanıyorsanız:
- Platform otomatik olarak sunucuyu başlatır
- Sadece `requirements.txt` ve dosyaların doğru yerde olduğundan emin olun
- Environment variables'ı ayarlayın


