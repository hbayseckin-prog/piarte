# Railway'de Piarte Uygulamasını Deploy Etme Rehberi

## 🚀 Hızlı Başlangıç

Bu rehber, SSH desteği olmayan hosting'de Piarte uygulamanızı Railway üzerinde çalıştırmanızı sağlar.

---

## 📋 Gereksinimler

1. **GitHub hesabı** (ücretsiz)
2. **Railway hesabı** (ücretsiz)
3. **Git** (bilgisayarınızda yüklü olmalı)

---

## 🔧 Adım 1: GitHub Repository Oluşturma

### 1.1. GitHub'da Yeni Repository Oluşturun

1. https://github.com adresine gidin
2. Sağ üstteki **"+"** → **"New repository"** tıklayın
3. Repository bilgilerini doldurun:
   - **Repository name:** `piarte` (veya istediğiniz isim)
   - **Description:** `Piarte Kurs Yönetim Sistemi`
   - **Public** veya **Private** seçin
   - **"Add a README file"** işaretlemeyin (dosyalarınız zaten var)
4. **"Create repository"** tıklayın

### 1.2. Dosyalarınızı GitHub'a Yükleyin

**Windows PowerShell'de şu komutları çalıştırın:**

```powershell
# Proje klasörünüze gidin
cd "C:\Users\bayCode Danışma\Desktop\Piarte"

# Git'i başlatın (eğer daha önce yapmadıysanız)
git init

# Tüm dosyaları ekleyin
git add .

# İlk commit'i yapın
git commit -m "İlk commit - Piarte uygulaması"

# GitHub repository'nizi ekleyin (YOUR_USERNAME yerine GitHub kullanıcı adınızı yazın)
git remote add origin https://github.com/YOUR_USERNAME/piarte.git

# Dosyaları GitHub'a gönderin
git branch -M main
git push -u origin main
```

**Not:** GitHub kullanıcı adınızı ve şifrenizi isteyecektir. Şifre yerine **Personal Access Token** kullanmanız gerekebilir.

---

## 🚂 Adım 2: Railway'de Proje Oluşturma

### 2.1. Railway Hesabı Oluşturun

1. https://railway.app adresine gidin
2. **"Start a New Project"** veya **"Login"** tıklayın
3. **"Login with GitHub"** seçin
4. GitHub hesabınızla giriş yapın
5. Railway'e erişim izni verin

### 2.2. Yeni Proje Oluşturun

1. Railway dashboard'da **"New Project"** tıklayın
2. **"Deploy from GitHub repo"** seçin
3. GitHub repository'nizi seçin (`piarte`)
4. Railway otomatik olarak:
   - Dosyalarınızı tarar
   - `requirements.txt` dosyasını bulur
   - Python uygulamanızı deploy eder

### 2.3. Deploy İşlemi

- Railway otomatik olarak deploy başlatır
- **"Deploy Logs"** sekmesinden ilerlemeyi takip edebilirsiniz
- İlk deploy 2-5 dakika sürebilir

---

## 🗄️ Adım 3: PostgreSQL Veritabanı Ekleme

### 3.1. PostgreSQL Servisi Ekleme

1. Railway dashboard'da projenize gidin
2. **"+ New"** → **"Database"** → **"Add PostgreSQL"** tıklayın
3. Railway otomatik olarak PostgreSQL servisi oluşturur

### 3.2. Veritabanı Bağlantısını Ayarlama

1. PostgreSQL servisine tıklayın
2. **"Variables"** sekmesine gidin
3. **"DATABASE_URL"** değişkenini kopyalayın
4. Ana uygulama servisine gidin
5. **"Variables"** sekmesine gidin
6. **"+ New Variable"** tıklayın
7. Şunları ekleyin:
   - **Name:** `DATABASE_URL`
   - **Value:** (PostgreSQL'den kopyaladığınız URL)
8. **"Add"** tıklayın

**Not:** Railway otomatik olarak `DATABASE_URL` değişkenini ekleyebilir. Kontrol edin.

### 3.3. Veritabanını Başlatma

1. Ana uygulama servisine gidin
2. **"Deploy Logs"** sekmesine gidin
3. Uygulama başladıktan sonra, tarayıcıda şu adrese gidin:
   ```
   https://YOUR_APP_NAME.railway.app/setup-database
   ```
4. Veritabanı tabloları otomatik oluşturulur

---

## 🌐 Adım 4: Domain Ayarlama (Opsiyonel)

### 4.1. Railway Domain Kullanma

1. Ana uygulama servisine gidin
2. **"Settings"** sekmesine gidin
3. **"Generate Domain"** tıklayın
4. Railway size bir domain verir: `piarte-production.up.railway.app`
5. Bu domain'i kullanabilirsiniz

### 4.2. Custom Domain Ekleme (Opsiyonel)

Eğer `piarte.baycode.com.tr` gibi bir domain kullanmak istiyorsanız:

1. Railway'de **"Settings"** → **"Domains"** sekmesine gidin
2. **"+ New Domain"** tıklayın
3. Domain adını girin: `piarte.baycode.com.tr`
4. Railway size DNS kayıtlarını verir
5. Domain sağlayıcınızda (baycode.com.tr) DNS ayarlarını yapın:
   - **Type:** CNAME
   - **Name:** piarte
   - **Value:** Railway'in verdiği CNAME değeri

---

## ✅ Adım 5: Uygulamayı Test Etme

1. Railway'de verilen domain'e gidin (örn: `piarte-production.up.railway.app`)
2. Ana sayfa açılmalı (3 panel seçeneği)
3. Admin paneli: `/login/admin`
4. Öğretmen paneli: `/login/teacher`
5. Personel paneli: `/login/staff`

---

## 🔄 Güncelleme Yapma

Kodlarınızı güncellediğinizde:

```powershell
cd "C:\Users\bayCode Danışma\Desktop\Piarte"
git add .
git commit -m "Güncelleme açıklaması"
git push
```

Railway otomatik olarak yeni deploy başlatır (1-2 dakika).

---

## 🐛 Sorun Giderme

### Uygulama açılmıyor

1. Railway'de **"Deploy Logs"** kontrol edin
2. Hata mesajlarını okuyun
3. **"Variables"** sekmesinde `DATABASE_URL` olduğundan emin olun

### Veritabanı bağlantı hatası

1. PostgreSQL servisinin çalıştığından emin olun
2. `DATABASE_URL` değişkeninin doğru olduğundan emin olun
3. Uygulamayı yeniden deploy edin

### Port hatası

- Railway otomatik olarak `$PORT` değişkenini ayarlar
- `Procfile` dosyasında `$PORT` kullanıldığından emin olun

---

## 📊 Railway Ücretsiz Plan Limitleri

- **500 saat/ay** ücretsiz kullanım
- **$5 kredi** aylık (yaklaşık 100 saat)
- **PostgreSQL** dahil
- **Custom domain** desteği

---

## 🎯 Özet

1. ✅ GitHub'da repository oluşturun
2. ✅ Dosyalarınızı GitHub'a push edin
3. ✅ Railway'de proje oluşturun
4. ✅ PostgreSQL ekleyin
5. ✅ Domain ayarlayın
6. ✅ Uygulamayı test edin

**Artık panellerinize web üzerinden erişebilirsiniz!** 🎉

---

## 📞 Yardım

- Railway Dokümantasyon: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- GitHub Issues: Repository'nizde issue açın

