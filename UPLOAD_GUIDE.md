# 📤 Internet'e Yükleme Rehberi

## ✅ Yüklenecek Dosyalar

### Zorunlu Dosyalar

```
Piarte/
├── app/                    # ✅ TÜMÜ (tüm Python dosyaları)
│   ├── __init__.py
│   ├── main.py
│   ├── db.py
│   ├── crud.py
│   ├── models.py
│   ├── schemas.py
│   ├── seed.py
│   ├── excel_loader.py
│   ├── excel_sync.py
│   └── (tüm .py dosyaları)
│
├── templates/              # ✅ TÜMÜ (tüm HTML şablonları)
│   ├── *.html
│   └── (tüm template dosyaları)
│
├── index.html              # ✅ Ana sayfa
├── requirements.txt        # ✅ Python bağımlılıkları
├── piarte_logo.jpg         # ✅ Logo (varsa)
│
└── data.db                 # ⚠️ Sadece verileri taşıyorsanız
                            # Production'da PostgreSQL kullanın!
```

### Opsiyonel Dosyalar (Yüklenebilir)

```
├── README.md               # Dokümantasyon
├── DEPLOYMENT.md           # Deployment rehberi
├── DATABASE_GUIDE.md       # Veritabanı rehberi
├── EMBED_GUIDE.md          # Embed rehberi
└── embed_example.html      # Örnek embed dosyası
```

## ❌ Yüklenmeyecek Dosyalar

### Geliştirme Dosyaları

```
├── __pycache__/           # ❌ Python cache (otomatik oluşur)
├── *.pyc                   # ❌ Python bytecode
├── .git/                   # ❌ Git klasörü (opsiyonel)
├── .env                    # ❌ Environment variables (güvenlik)
├── venv/                   # ❌ Virtual environment
├── env/                    # ❌ Virtual environment
├── .vscode/                # ❌ VS Code ayarları
├── .idea/                  # ❌ IDE ayarları
├── start_server.bat        # ❌ Windows script (sunucuda gerekmez)
├── start_server_2.bat      # ❌ Windows script
└── durum.xlsx              # ❌ Test dosyası (gerekirse yükleyin)
```

## 📦 Hızlı Yükleme Listesi

### Minimum Gereksinimler

1. ✅ `app/` klasörü (tümü)
2. ✅ `templates/` klasörü (tümü)
3. ✅ `index.html`
4. ✅ `requirements.txt`
5. ✅ `piarte_logo.jpg` (varsa)

### Production İçin Ek

6. ✅ `.gitignore` (varsa)
7. ✅ `README.md` (opsiyonel)

## 🚀 Yükleme Adımları

### Yöntem 1: FTP/FileZilla ile

1. **FileZilla veya benzeri FTP programını açın**
2. **Sunucu bilgilerini girin:**
   - Host: sunucu IP veya domain
   - Username: FTP kullanıcı adı
   - Password: FTP şifresi
   - Port: 21 (genellikle)

3. **Dosyaları yükleyin:**
   ```
   Yerel (Sol) → Sunucu (Sağ)
   ├── app/ → /home/username/piarte/app/
   ├── templates/ → /home/username/piarte/templates/
   ├── index.html → /home/username/piarte/index.html
   ├── requirements.txt → /home/username/piarte/requirements.txt
   └── piarte_logo.jpg → /home/username/piarte/piarte_logo.jpg
   ```

4. **Klasör yapısı kontrol edin:**
   ```
   /home/username/piarte/
   ├── app/
   ├── templates/
   ├── index.html
   └── requirements.txt
   ```

### Yöntem 2: Git ile (Önerilen)

1. **Git repository oluşturun:**
   ```bash
   git init
   git add app/ templates/ index.html requirements.txt
   git commit -m "Initial commit"
   ```

2. **.gitignore oluşturun:**
   ```
   __pycache__/
   *.pyc
   *.pyo
   *.pyd
   .Python
   venv/
   env/
   .env
   data.db
   *.db
   .vscode/
   .idea/
   *.log
   ```

3. **GitHub/GitLab'a push edin**

4. **Sunucuda clone edin:**
   ```bash
   git clone https://github.com/username/piarte.git
   cd piarte
   ```

### Yöntem 3: ZIP ile

1. **Gerekli dosyaları seçin ve ZIP'leyin:**
   ```
   piarte.zip
   ├── app/
   ├── templates/
   ├── index.html
   └── requirements.txt
   ```

2. **Sunucuya yükleyin ve açın:**
   ```bash
   unzip piarte.zip
   ```

## 🔧 Sunucuda Kurulum

### 1. Python ve Bağımlılıkları Yükle

```bash
# Python 3.8+ kontrol et
python3 --version

# Virtual environment oluştur (önerilen)
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
venv\Scripts\activate  # Windows

# Bağımlılıkları yükle
pip install -r requirements.txt
```

### 2. Environment Variables Ayarla

```bash
# .env dosyası oluştur (production için)
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
export SECRET_KEY="güvenli-secret-key-buraya"
```

### 3. Sunucuyu Başlat

```bash
# Development
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production (systemd veya PM2 ile)
# Detaylar için DEPLOYMENT.md'ye bakın
```

## 📋 Kontrol Listesi

Yüklemeden önce kontrol edin:

- [ ] `app/` klasörü yüklendi mi?
- [ ] `templates/` klasörü yüklendi mi?
- [ ] `index.html` yüklendi mi?
- [ ] `requirements.txt` yüklendi mi?
- [ ] `piarte_logo.jpg` yüklendi mi? (varsa)
- [ ] `__pycache__/` yüklenmedi mi?
- [ ] `.env` dosyası yüklenmedi mi? (güvenlik)
- [ ] `data.db` yüklenmedi mi? (production'da PostgreSQL kullanın)

## ⚠️ Önemli Notlar

### 1. Veritabanı

**Yerel `data.db` dosyasını production'a yüklemeyin!**

Bunun yerine:
- PostgreSQL cloud veritabanı kullanın (Railway, Supabase, Render)
- `DATABASE_URL` environment variable'ını ayarlayın
- Verileri `migrate_to_postgresql.py` ile taşıyın

### 2. Güvenlik

**Asla yüklemeyin:**
- `.env` dosyası (şifreler içerir)
- `data.db` (production'da kullanmayın)
- `__pycache__/` (gereksiz)

**Mutlaka yapın:**
- Environment variables kullanın
- Secret key'i değiştirin
- HTTPS kullanın

### 3. Dosya İzinleri

Linux sunucularda:
```bash
chmod 755 app/
chmod 644 app/*.py
chmod 755 templates/
chmod 644 templates/*.html
chmod 644 index.html
```

## 🌐 Cloud Platform Önerileri

### Railway (En Kolay)

1. GitHub'a push edin
2. Railway'de "New Project" → GitHub repo seçin
3. Otomatik deploy!

### Render

1. GitHub'a push edin
2. Render'da "New Web Service"
3. GitHub repo'yu bağlayın
4. Deploy!

### DigitalOcean App Platform

1. GitHub'a push edin
2. "Create" → "Apps" → GitHub
3. Otomatik deploy!

## 📞 Sorun Giderme

**Dosyalar görünmüyor:**
- Dosya yollarını kontrol edin
- Klasör yapısını kontrol edin
- İzinleri kontrol edin

**Import hatası:**
- `requirements.txt` yüklendi mi?
- `pip install -r requirements.txt` çalıştırıldı mı?
- Virtual environment aktif mi?

**404 hatası:**
- `index.html` root dizinde mi?
- URL yollarını kontrol edin

## ✅ Özet

**Yüklenecek:**
- ✅ `app/` (tümü)
- ✅ `templates/` (tümü)
- ✅ `index.html`
- ✅ `requirements.txt`
- ✅ `piarte_logo.jpg` (varsa)

**Yüklenmeyecek:**
- ❌ `__pycache__/`
- ❌ `.env`
- ❌ `data.db` (production'da PostgreSQL kullanın)
- ❌ `venv/`
- ❌ `.git/` (opsiyonel)

**Toplam boyut:** ~2-5 MB (dosyalara göre değişir)


