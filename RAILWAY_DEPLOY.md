# 🚂 Railway Deployment Rehberi

## ✅ Yapılan İşlemler

1. ✅ Tüm değişiklikler commit edildi
2. ✅ GitHub'a push edildi
3. ✅ Railway deployment dosyaları hazırlandı:
   - `Procfile` - Uygulama başlatma komutu
   - `railway.json` - Railway yapılandırması
   - `.railwayignore` - Deploy edilmeyecek dosyalar
   - `runtime.txt` - Python versiyonu

## 🚀 Railway'de Deploy

### Adım 1: Railway'de Proje Oluştur

1. [Railway.app](https://railway.app) adresine gidin
2. "New Project" tıklayın
3. "Deploy from GitHub repo" seçin
4. GitHub repository'nizi seçin: `hbayseckin-prog/piarte`

### Adım 2: Environment Variables Ayarlayın

Railway dashboard'da "Variables" sekmesine gidin ve şunları ekleyin:

```
DATABASE_URL=postgresql://user:password@host:port/database
SECRET_KEY=güvenli-bir-rastgele-anahtar-en-az-32-karakter
ROOT_PATH=
```

**ÖNEMLİ:** 
- Railway otomatik olarak PostgreSQL veritabanı oluşturur
- "Add PostgreSQL" butonuna tıklayın
- Railway otomatik olarak `DATABASE_URL` environment variable'ını ekler
- `SECRET_KEY`'i mutlaka güçlü bir değerle değiştirin!

### Adım 3: Deploy

Railway otomatik olarak:
1. GitHub'dan kodu çeker
2. Bağımlılıkları yükler (`requirements.txt`)
3. Uygulamayı başlatır (`Procfile`)

### Adım 4: İlk Kurulum

Deploy tamamlandıktan sonra:

1. Railway'de "Settings" > "Generate Domain" ile domain oluşturun
2. Tarayıcıda şu adrese gidin: `https://your-app.railway.app/setup-database`
3. Veritabanı tabloları oluşturulacak
4. Admin ile giriş yapın:
   - Kullanıcı: `admin`
   - Şifre: `admin123`
5. **HEMEN** şifreyi değiştirin!

## 📝 Önemli Notlar

### Veritabanı

Railway PostgreSQL veritabanı sağlar. `DATABASE_URL` otomatik olarak ayarlanır.

### Static Dosyalar

Logo ve diğer static dosyalar `/static` endpoint'inden servis edilir.

### Port

Railway otomatik olarak `$PORT` environment variable'ını sağlar. `Procfile`'da kullanılıyor.

### Logs

Railway dashboard'da "Deployments" > "View Logs" ile logları görebilirsiniz.

## 🔄 Güncelleme

Her `git push` işleminde Railway otomatik olarak yeniden deploy eder.

## 🐛 Sorun Giderme

### Deploy Başarısız

1. Railway dashboard'da "Deployments" sekmesine gidin
2. Başarısız deployment'ı seçin
3. "View Logs" ile hata mesajlarını kontrol edin
4. Genellikle:
   - `requirements.txt` eksik bağımlılık
   - Environment variable eksik
   - Veritabanı bağlantı hatası

### Veritabanı Bağlantı Hatası

1. Railway'de PostgreSQL servisinin çalıştığını kontrol edin
2. `DATABASE_URL` environment variable'ının doğru olduğunu kontrol edin
3. Veritabanı tablolarının oluşturulduğunu kontrol edin: `/setup-database`

### Uygulama Başlamıyor

1. Logları kontrol edin
2. `Procfile`'ın doğru olduğunu kontrol edin
3. Port'un doğru kullanıldığını kontrol edin (`$PORT`)

## ✅ Deployment Kontrol Listesi

- [ ] Railway'de proje oluşturuldu
- [ ] GitHub repository bağlandı
- [ ] PostgreSQL veritabanı eklendi
- [ ] Environment variables ayarlandı:
  - [ ] `DATABASE_URL` (otomatik)
  - [ ] `SECRET_KEY` (manuel)
  - [ ] `ROOT_PATH` (opsiyonel)
- [ ] Deploy başarılı
- [ ] Domain oluşturuldu
- [ ] `/setup-database` çalıştırıldı
- [ ] Admin girişi yapıldı
- [ ] Admin şifresi değiştirildi

---

**Deploy başarılı! 🎉**

