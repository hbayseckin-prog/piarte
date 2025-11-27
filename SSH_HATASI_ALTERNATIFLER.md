# 🔧 SSH Hatası - Alternatif Çözümler

## ❌ SSH Çalışmıyor - Ne Yapmalı?

SSH bağlantısı çalışmıyorsa, kurulumu başka yollarla yapabilirsiniz.

## ✅ Çözüm 1: cPanel Terminal (En Kolay)

### 1. cPanel'e Giriş Yapın
```
https://www.baycode.com.tr:2083
```
veya
```
https://www.baycode.com.tr/cpanel
```

### 2. Terminal'i Bulun
- **"Advanced"** bölümüne gidin
- **"Terminal"** veya **"Web Terminal"** tıklayın
- VEYA arama kutusuna "terminal" yazın

### 3. Terminal Açılır
- Tarayıcıda bir terminal penceresi açılır
- Komutları orada çalıştırabilirsiniz

### 4. Kurulum Komutlarını Çalıştırın
cPanel Terminal'de aynı komutları çalıştırın (SSH_KURULUM_KOMUTLARI.md'deki gibi)

---

## ✅ Çözüm 2: cPanel File Manager + Cron Job

### 1. Kurulum Scriptini Hazırlayın

FileZilla ile `kurulum.sh` dosyasını yüklediniz.

### 2. cPanel'den Çalıştırın

**Yöntem A: File Manager'dan**
1. cPanel → File Manager
2. `piarte` klasörüne gidin
3. `kurulum.sh` dosyasına sağ tıklayın
4. "Edit" → İçeriği kontrol edin
5. "Execute" veya "Run" seçeneğini arayın

**Yöntem B: Cron Job ile**
1. cPanel → Advanced → Cron Jobs
2. Yeni cron job oluşturun
3. Komut: `/bin/bash /home/baycode/public_html/piarte/kurulum.sh`
4. Bir kez çalıştırın

---

## ✅ Çözüm 3: Manuel Kurulum (cPanel Terminal)

cPanel Terminal'de adım adım:

### Adım 1: Dizine Git
```bash
cd ~/public_html/piarte
ls -la
```

### Adım 2: Python Kontrolü
```bash
python3 --version
```

### Adım 3: Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### Adım 4: Bağımlılıklar
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Adım 5: Manuel Başlatma (Systemd Yoksa)

**Shared hosting'de systemd olmayabilir, o zaman:**

```bash
# nohup ile arka planda çalıştır
cd ~/public_html/piarte
source venv/bin/activate
nohup uvicorn app.main:app --host 127.0.0.1 --port 8000 --root-path /piarte > piarte.log 2>&1 &
```

**Process ID'yi kaydedin:**
```bash
echo $! > piarte.pid
```

**Durdurmak için:**
```bash
kill $(cat piarte.pid)
```

---

## ✅ Çözüm 4: Hosting Sağlayıcınıza Sorun

SSH erişimi için hosting sağlayıcınıza başvurun:

**Sorulacak Sorular:**
1. "SSH erişimim var mı?"
2. "SSH port numarası nedir?"
3. "SSH nasıl aktif edilir?"
4. "cPanel Terminal kullanabilir miyim?"

---

## 🎯 Önerilen Yöntem: cPanel Terminal

**En kolay ve garantili yöntem:**

1. ✅ cPanel'e giriş yapın
2. ✅ Terminal'i açın
3. ✅ Komutları çalıştırın

**Avantajları:**
- SSH gerekmez
- Tarayıcıdan çalışır
- Aynı komutları kullanabilirsiniz

---

## 📋 cPanel Terminal'de Kurulum (Hızlı)

cPanel Terminal açıldıktan sonra:

```bash
# 1. Dizine git
cd ~/public_html/piarte

# 2. Dosyaları kontrol et
ls -la

# 3. Python kontrol
python3 --version

# 4. Virtual environment
python3 -m venv venv
source venv/bin/activate

# 5. Bağımlılıklar
pip install --upgrade pip
pip install -r requirements.txt

# 6. Manuel başlatma (systemd yoksa)
nohup uvicorn app.main:app --host 127.0.0.1 --port 8000 --root-path /piarte > piarte.log 2>&1 &
```

---

## ⚠️ Önemli Notlar

### Shared Hosting'de Systemd Olmayabilir

Eğer `sudo systemctl` komutu çalışmıyorsa:
- Systemd yok demektir
- `nohup` veya `screen` kullanın
- VEYA hosting sağlayıcınıza Python uygulaması çalıştırma desteği sorun

### Port 8000 Kullanılabilir mi?

Bazı shared hosting'lerde belirli portlar kullanılamayabilir:
- Hosting sağlayıcınıza sorun
- VEYA farklı bir port deneyin (8001, 8080 vb.)

---

## 🆘 Hala Çalışmıyorsa

1. **Hosting sağlayıcınızın destek ekibine başvurun**
   - "Python uygulaması nasıl çalıştırılır?"
   - "FastAPI uygulaması için ne gerekiyor?"

2. **Hosting türünüzü kontrol edin**
   - Shared hosting → Sınırlamalar olabilir
   - VPS → Daha fazla kontrol

3. **Alternatif platformlar**
   - Railway, Render, DigitalOcean gibi platformlar Python uygulamaları için daha uygundur


