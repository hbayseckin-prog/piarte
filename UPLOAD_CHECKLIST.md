# ✅ Yükleme Kontrol Listesi

## 📤 Yüklenecek Dosyalar (Zorunlu)

### 1. Uygulama Dosyaları
```
✅ app/
   ✅ __init__.py
   ✅ main.py
   ✅ db.py
   ✅ crud.py
   ✅ models.py
   ✅ schemas.py
   ✅ seed.py
   ✅ excel_loader.py
   ✅ excel_sync.py
```

### 2. Template Dosyaları
```
✅ templates/
   ✅ Tüm .html dosyaları (26 dosya)
```

### 3. Ana Dosyalar
```
✅ index.html
✅ requirements.txt
✅ piarte_logo.jpg (varsa)
```

## ❌ Yüklenmeyecek Dosyalar

```
❌ app/__pycache__/          (Python cache - otomatik oluşur)
❌ data.db                   (Production'da PostgreSQL kullanın!)
❌ venv/ veya env/           (Virtual environment)
❌ .env                      (Güvenlik - şifreler içerir)
❌ durum.xlsx                (Test dosyası)
❌ start_server.bat          (Windows script - sunucuda gerekmez)
❌ .git/                     (Git klasörü - opsiyonel)
❌ .vscode/                  (IDE ayarları)
```

## 📦 Hızlı Yükleme

### Seçenek 1: Tüm Klasörü Yükle (Sonra Temizle)

1. Tüm klasörü yükleyin
2. Sunucuda gereksiz dosyaları silin:
   ```bash
   rm -rf app/__pycache__
   rm -rf venv/
   rm -f .env
   rm -f data.db
   rm -f start_server*.bat
   ```

### Seçenek 2: Sadece Gerekli Dosyaları Yükle (Önerilen)

**Manuel seçim:**
- `app/` klasörü (sadece .py dosyaları, __pycache__ hariç)
- `templates/` klasörü (tümü)
- `index.html`
- `requirements.txt`
- `piarte_logo.jpg` (varsa)

## 🎯 Önerilen Yöntem

### Git ile (En İyi)

1. `.gitignore` dosyası oluşturuldu ✅
2. Git repository oluştur:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   ```
3. GitHub'a push et
4. Sunucuda clone et:
   ```bash
   git clone https://github.com/username/piarte.git
   ```

**Avantajları:**
- ✅ Gereksiz dosyalar otomatik hariç tutulur
- ✅ Versiyon kontrolü
- ✅ Kolay güncelleme

## 📊 Dosya Boyutları (Tahmini)

- `app/` klasörü: ~200-500 KB
- `templates/` klasörü: ~100-200 KB
- `index.html`: ~10 KB
- `requirements.txt`: ~1 KB
- `piarte_logo.jpg`: ~50-200 KB (varsa)

**Toplam:** ~400-1000 KB (1 MB altı)

## ⚠️ ÖNEMLİ: Veritabanı

**YEREL `data.db` DOSYASINI YÜKLEMEYİN!**

Bunun yerine:
1. PostgreSQL cloud veritabanı oluşturun (Railway, Supabase, Render)
2. `DATABASE_URL` environment variable'ını ayarlayın
3. Verileri `migrate_to_postgresql.py` ile taşıyın

## ✅ Son Kontrol

Yüklemeden önce:
- [ ] `app/` klasöründe sadece .py dosyaları var mı? (__pycache__ yok mu?)
- [ ] `templates/` klasörü tam mı?
- [ ] `index.html` var mı?
- [ ] `requirements.txt` var mı?
- [ ] `data.db` yüklenmedi mi?
- [ ] `.env` yüklenmedi mi?


