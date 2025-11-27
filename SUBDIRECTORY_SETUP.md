# 📁 Alt Klasörde Çalıştırma Rehberi

## 🎯 Durum
Dosyalar `www.baycode.com.tr/piarte/` alt klasörüne yüklendi.

## ✅ Yapılan Değişiklikler

### 1. index.html Linkleri Güncellendi
- `/login/admin` → `./login/admin` (göreceli path)
- `/login/teacher` → `./login/teacher`
- `/login/staff` → `./login/staff`
- `/static/piarte_logo.jpg` → `./static/piarte_logo.jpg`

## 🔧 Nginx Yapılandırması

Eğer Nginx kullanıyorsanız, `/piarte` alt klasörü için yapılandırma:

```nginx
server {
    listen 80;
    server_name www.baycode.com.tr;

    # /piarte alt klasörü için
    location /piarte {
        # Trailing slash önemli!
        alias /path/to/Piarte;
        
        # index.html'i varsayılan olarak göster
        try_files $uri $uri/ /piarte/index.html;
        
        # FastAPI'ye proxy yap
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Root path'i koru
        rewrite ^/piarte/(.*)$ /$1 break;
    }
}
```

**VEYA daha iyi yöntem:**

```nginx
server {
    listen 80;
    server_name www.baycode.com.tr;

    location /piarte/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # /piarte prefix'ini kaldır
        rewrite ^/piarte/(.*)$ /$1 break;
    }
}
```

## 🚀 FastAPI'yi Alt Klasör İçin Yapılandırma

### Seçenek 1: FastAPI'de Root Path Ayarla

`app/main.py` dosyasına ekleyin:

```python
from fastapi import FastAPI
from fastapi.middleware.base import BaseHTTPMiddleware

app = FastAPI(title="Piarte Kurs Yönetimi")

# Alt klasör için root path
ROOT_PATH = "/piarte"

# Middleware ile path'i düzelt
class RootPathMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # /piarte prefix'ini kaldır
        if request.url.path.startswith("/piarte"):
            request.scope["path"] = request.url.path.replace("/piarte", "", 1)
        response = await call_next(request)
        return response

app.add_middleware(RootPathMiddleware)
```

### Seçenek 2: Uvicorn'da Root Path

```bash
uvicorn app.main:app --root-path /piarte --host 0.0.0.0 --port 8000
```

## 📋 Apache Yapılandırması

Eğer Apache kullanıyorsanız:

```apache
<VirtualHost *:80>
    ServerName www.baycode.com.tr
    
    # /piarte alt klasörü için
    Alias /piarte /path/to/Piarte
    
    <Directory "/path/to/Piarte">
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>
    
    # FastAPI'ye proxy
    ProxyPass /piarte http://127.0.0.1:8000/
    ProxyPassReverse /piarte http://127.0.0.1:8000/
    
    # Path'i düzelt
    ProxyPassMatch ^/piarte/(.*)$ http://127.0.0.1:8000/$1
</VirtualHost>
```

## 🔍 Test

### 1. index.html Erişimi
```
http://www.baycode.com.tr/piarte/
```
veya
```
http://www.baycode.com.tr/piarte/index.html
```

### 2. Login Sayfaları
```
http://www.baycode.com.tr/piarte/login/admin
http://www.baycode.com.tr/piarte/login/teacher
http://www.baycode.com.tr/piarte/login/staff
```

### 3. Health Check
```
http://www.baycode.com.tr/piarte/health
```

## ⚠️ Önemli Notlar

### 1. Static Dosyalar
Static dosyalar için path'ler göreceli olmalı:
- `./static/piarte_logo.jpg` ✅
- `/static/piarte_logo.jpg` ❌ (root'tan başlar)

### 2. Form Action'ları
Form action'ları da göreceli olmalı veya tam path kullanılmalı.

### 3. Redirect'ler
FastAPI'deki redirect'ler otomatik olarak doğru path'i kullanır (root_path ayarlıysa).

## 🎯 En Kolay Çözüm

**Eğer sadece static HTML olarak çalıştırıyorsanız:**

1. `index.html` linkleri zaten güncellendi ✅
2. FastAPI sunucusunu `/piarte` root path ile başlatın:
   ```bash
   uvicorn app.main:app --root-path /piarte --host 0.0.0.0 --port 8000
   ```

3. Nginx'te:
   ```nginx
   location /piarte/ {
       proxy_pass http://127.0.0.1:8000/;
       rewrite ^/piarte/(.*)$ /$1 break;
   }
   ```

## ✅ Kontrol Listesi

- [ ] `index.html` linkleri göreceli yapıldı (`./login/admin`)
- [ ] Logo path'i göreceli yapıldı (`./static/piarte_logo.jpg`)
- [ ] FastAPI `--root-path /piarte` ile başlatıldı
- [ ] Nginx/Apache yapılandırması `/piarte` için ayarlandı
- [ ] Test edildi: `www.baycode.com.tr/piarte/` açılıyor
- [ ] Test edildi: `www.baycode.com.tr/piarte/login/admin` çalışıyor


