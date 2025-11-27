# 📤 Yüklenecek Dosya Listesi

## ✅ ZORUNLU - Mutlaka Yükleyin

### 1. Uygulama Dosyaları
```
✅ app/
   ✅ __init__.py
   ✅ main.py          (GÜNCELLENMİŞ - root_path desteği eklendi)
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
✅ index.html          (GÜNCELLENMİŞ - göreceli linkler)
✅ requirements.txt
✅ piarte_logo.jpg     (varsa)
```

## ⚠️ OPSİYONEL - İsterseniz Yükleyin

### Yardımcı Scriptler (Sunucuda kullanmak için)
```
⚠️ LINUX_SETUP.sh      (Sunucuda kurulum için - isterseniz)
⚠️ nginx_piarte.conf   (Nginx yapılandırması - referans için)
```

### Dokümantasyon (Referans için)
```
📄 LINUX_DEPLOYMENT.md
📄 SUBDIRECTORY_SETUP.md
📄 TROUBLESHOOTING.md
📄 QUICK_FIX.md
📄 UPLOAD_GUIDE.md
📄 DATABASE_GUIDE.md
📄 EMBED_GUIDE.md
📄 README.md
📄 DEPLOYMENT.md
```

**Not:** Dokümantasyon dosyaları sadece referans içindir, uygulamanın çalışması için gerekli değildir.

## ❌ YÜKLEMEYİN

```
❌ __pycache__/
❌ .git/
❌ venv/ veya env/
❌ .env
❌ data.db
❌ test_server.py
❌ migrate_to_postgresql.py (sadece veri taşıma için)
❌ *.bat dosyaları
```

## 🎯 ÖZET

### Minimum Yükleme (Çalışması için yeterli):
1. ✅ `app/` klasörü (tümü, __pycache__ hariç)
2. ✅ `templates/` klasörü (tümü)
3. ✅ `index.html` (güncellenmiş)
4. ✅ `requirements.txt`

### Önerilen Yükleme:
Yukarıdakilere ek olarak:
- ✅ `piarte_logo.jpg` (varsa)
- ⚠️ `LINUX_SETUP.sh` (kurulum için)
- ⚠️ `nginx_piarte.conf` (referans için)

### Dokümantasyon (İsteğe bağlı):
- Tüm `.md` dosyaları (sadece okumak için)

## 📋 Hızlı Kontrol

Yüklemeden önce:
- [ ] `app/main.py` güncellenmiş mi? (root_path desteği var mı?)
- [ ] `index.html` güncellenmiş mi? (./login/admin linkleri var mı?)
- [ ] `__pycache__` yüklenmedi mi?
- [ ] `data.db` yüklenmedi mi? (production'da PostgreSQL kullanın)


