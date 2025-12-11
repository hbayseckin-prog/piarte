# 🚀 IHS Telekom Sunucusuna Deployment - Hızlı Başlangıç

## ⚡ Hızlı Kurulum (5 Adım)

### 1️⃣ Dosyaları Sunucuya Yükleyin
- Tüm proje dosyalarını IHS Telekom sunucusuna yükleyin
- `data.db` dosyasını **YÜKLEMEYİN** (yeni oluşturulacak)

### 2️⃣ Sunucuda Hazırlık
```bash
# SSH ile sunucuya bağlanın
ssh kullanici@sunucu-ip

# Proje dizinine gidin
cd /var/www/piarte  # veya projenizin dizini

# Deployment script'ini çalıştırın
chmod +x deploy.sh
./deploy.sh
```

### 3️⃣ Ortam Değişkenlerini Ayarlayın
```bash
# .env dosyasını düzenleyin
nano .env
```

Şu değerleri mutlaka ayarlayın:
- `DATABASE_URL`: PostgreSQL bağlantı bilgileri
- `SECRET_KEY`: Güvenli bir rastgele string (en az 32 karakter)

### 4️⃣ Veritabanını Başlatın
Tarayıcıda şu adrese gidin:
```
http://sunucu-ip:8000/setup-database
```

### 5️⃣ Uygulamayı Başlatın

**Manuel başlatma:**
```bash
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Systemd service ile (önerilen):**
```bash
# Service dosyasını kopyalayın
sudo cp piarte.service /etc/systemd/system/

# Dizin yolunu düzenleyin
sudo nano /etc/systemd/system/piarte.service

# Service'i başlatın
sudo systemctl daemon-reload
sudo systemctl enable piarte
sudo systemctl start piarte
```

## 📋 Detaylı Rehber

Detaylı adımlar için `DEPLOYMENT_GUIDE.md` dosyasına bakın.

## 🔄 Mevcut Verileri Taşıma

Eğer yerel SQLite veritabanınızdan verileri taşımak istiyorsanız:

1. **Yerel bilgisayarınızda:**
```bash
python export_data.py data.db
```

2. **Export edilen `data_export.json` dosyasını sunucuya yükleyin**

3. **Sunucuda:**
```bash
source venv/bin/activate
python import_data.py data_export.json
```

## ⚠️ Önemli Notlar

- ✅ `.env` dosyasındaki `SECRET_KEY` mutlaka değiştirin
- ✅ Veritabanı şifresi güçlü olmalı
- ✅ İlk girişten sonra admin şifresini değiştirin
- ✅ Firewall ayarlarını kontrol edin
- ✅ HTTPS/SSL sertifikası kurun (production için)

## 🆘 Sorun mu Yaşıyorsunuz?

1. Logları kontrol edin: `sudo journalctl -u piarte -f`
2. Manuel çalıştırıp hataları görün
3. IHS Telekom teknik destek ile iletişime geçin


