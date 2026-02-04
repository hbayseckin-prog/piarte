# Railway'de Migration Çalıştırma

## Yöntem 1: Railway CLI (En Kolay)

1. Railway CLI'yi yükleyin (eğer yoksa):
   ```bash
   npm i -g @railway/cli
   ```

2. Railway'e login olun:
   ```bash
   railway login
   ```

3. Projenize bağlanın:
   ```bash
   railway link
   ```

4. Migration scriptini çalıştırın:
   ```bash
   railway run python add_is_active_to_students.py
   ```

## Yöntem 2: Railway Dashboard'dan

1. Railway dashboard'a gidin: https://railway.app
2. Projenizi seçin
3. **Service'in ana sayfasına** gidin (Deployments değil, servisin kendisi)
4. **"Connect"** veya **"Settings"** sekmesine bakın
5. Orada **"Shell"** veya **"Terminal"** butonu olmalı

## Yöntem 3: Manuel SQL (PostgreSQL için)

1. Railway dashboard'da projenize gidin
2. PostgreSQL servisinizi seçin (web servisi değil, PostgreSQL servisi)
3. **"Data"** veya **"Query"** sekmesine gidin
4. Şu SQL komutunu çalıştırın:
   ```sql
   ALTER TABLE students ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL;
   UPDATE students SET is_active = TRUE;
   ```

## Yöntem 4: Otomatik Migration (Önerilen)

Otomatik migration kodu eklendi. Sadece uygulamayı yeniden deploy edin:
- Railway otomatik olarak deploy edecek
- Uygulama başladığında `is_active` kolonu otomatik eklenecek
