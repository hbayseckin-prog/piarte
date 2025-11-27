# 🚀 Tüm Kurulum Adımları (Sade ve Net)

## 📍 Nerede Yapılacak?

- **PowerShell:** Windows bilgisayarınızda (SSH bağlantısı için)
- **SSH Terminal:** Sunucuda (SSH ile bağlandıktan sonra)
- **cPanel Terminal:** cPanel'den açılan terminal (SSH çalışmıyorsa)

---

## 🔌 ADIM 0: SSH Bağlantısı (PowerShell'de)

**Nerede:** Windows PowerShell'de

**Komutlar (sırayla deneyin):**
```powershell
ssh -p 2222 baycode@www.baycode.com.tr
# VEYA
ssh -p 2200 baycode@www.baycode.com.tr
# VEYA
ssh baycode@www.baycode.com.tr
```

**Başarılı olursa:** Şifre ister, şifreyi girin → Sunucuya bağlanırsınız

**VEYA cPanel Terminal:**
- cPanel → Advanced → Terminal
- Terminal açılır

---

## 📁 ADIM 1: Dosyaların Yerini Bul (SSH Terminal'de)

**Nerede:** SSH Terminal'de (sunucuda)

**Komutlar:**
```bash
# Dosyaların nerede olduğunu bul
cd ~/public_html/piarte
# VEYA
cd /var/www/piarte

# Kontrol et
ls -la
```

**Görmeli:** `app/`, `templates/`, `index.html` dosyaları

---

## 🐍 ADIM 2: Python Kontrolü (SSH Terminal'de)

**Nerede:** SSH Terminal'de

**Komut:**
```bash
python3 --version
```

**Görmeli:** `Python 3.8.x` veya üzeri

**Yoksa yükle:**
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv
```

---

## 🔐 ADIM 3: Virtual Environment (SSH Terminal'de)

**Nerede:** SSH Terminal'de (dosyaların olduğu dizinde)

**Komutlar:**
```bash
# 1. Virtual environment oluştur
python3 -m venv venv

# 2. Aktif et
source venv/bin/activate

# 3. Kontrol et (başında (venv) görünmeli)
which python
```

**Görmeli:** Komut satırında `(venv)` yazısı

---

## 📥 ADIM 4: Bağımlılıkları Yükle (SSH Terminal'de)

**Nerede:** SSH Terminal'de (venv aktifken)

**Komutlar:**
```bash
# 1. Pip güncelle
pip install --upgrade pip

# 2. Bağımlılıkları yükle
pip install -r requirements.txt

# 3. Kontrol et
pip list | grep fastapi
```

**Görmeli:** `fastapi` listelenmeli

---

## ⚙️ ADIM 5: Systemd Service (SSH Terminal'de)

**Nerede:** SSH Terminal'de

**Komut:**
```bash
sudo nano /etc/systemd/system/piarte.service
```

**Ne yapacaksınız:**
1. Dosya açılır (nano editör)
2. Aşağıdaki içeriği yapıştırın (Ctrl+Shift+V)
3. **ÖNEMLİ:** Dosya yollarını düzenleyin (`/var/www/piarte` yerine gerçek yolunuzu yazın)
4. Kaydedin: Ctrl+O, Enter
5. Çıkın: Ctrl+X

**İçerik (dosya yolunu düzenleyin!):**
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

**Not:** `WorkingDirectory` ve `ExecStart` içindeki `/var/www/piarte` yolunu gerçek yolunuzla değiştirin!

**Service'i başlat:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable piarte
sudo systemctl start piarte
sudo systemctl status piarte
```

**Görmeli:** Yeşil "active (running)" yazısı

---

## 🌐 ADIM 6: Nginx Yapılandırması (SSH Terminal'de)

**Nerede:** SSH Terminal'de

**Komut:**
```bash
sudo nano /etc/nginx/sites-available/piarte
```

**Ne yapacaksınız:**
1. Dosya açılır
2. Aşağıdaki içeriği yapıştırın
3. Kaydedin: Ctrl+O, Enter
4. Çıkın: Ctrl+X

**İçerik:**
```nginx
server {
    listen 80;
    server_name www.baycode.com.tr;

    location /piarte/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        rewrite ^/piarte/(.*)$ /$1 break;
    }
}
```

**Aktif et:**
```bash
sudo ln -s /etc/nginx/sites-available/piarte /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## ✅ ADIM 7: Test (SSH Terminal'de)

**Nerede:** SSH Terminal'de

**Komutlar:**
```bash
# Service durumu
sudo systemctl status piarte

# Health check
curl http://localhost:8000/health
```

**Görmeli:** `{"status":"ok","message":"Server is running"}`

---

## 🎯 Özet: Nerede Ne Yapılacak?

| Adım | Nerede | Ne Yapılacak |
|------|--------|--------------|
| 0 | PowerShell | SSH bağlantısı kur |
| 1 | SSH Terminal | Dosyaların yerini bul |
| 2 | SSH Terminal | Python kontrolü |
| 3 | SSH Terminal | Virtual environment oluştur |
| 4 | SSH Terminal | Bağımlılıkları yükle |
| 5 | SSH Terminal | Systemd service oluştur |
| 6 | SSH Terminal | Nginx yapılandır |
| 7 | SSH Terminal | Test et |

**Hepsi SSH Terminal'de (sunucuda) yapılacak!**

---

## 📋 Hızlı Kopyala-Yapıştır (Tüm Komutlar)

SSH Terminal'de sırayla çalıştırın:

```bash
# 1. Dizine git
cd ~/public_html/piarte

# 2. Python kontrol
python3 --version

# 3. Virtual environment
python3 -m venv venv
source venv/bin/activate

# 4. Bağımlılıklar
pip install --upgrade pip
pip install -r requirements.txt

# 5. Service oluştur (nano ile düzenleyin)
sudo nano /etc/systemd/system/piarte.service

# 6. Service başlat
sudo systemctl daemon-reload
sudo systemctl enable piarte
sudo systemctl start piarte

# 7. Nginx (nano ile düzenleyin)
sudo nano /etc/nginx/sites-available/piarte

# 8. Nginx aktif et
sudo ln -s /etc/nginx/sites-available/piarte /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# 9. Test
sudo systemctl status piarte
curl http://localhost:8000/health
```


