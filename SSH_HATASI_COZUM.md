# 🔧 SSH Bağlantı Hatası Çözümü

## ❌ Hata: "Connection timed out"

Bu hata genellikle şu nedenlerden olur:
1. SSH portu (22) kapalı
2. Hosting sağlayıcısı SSH erişimine izin vermiyor
3. Firewall engelliyor
4. Farklı port kullanılıyor

## ✅ Çözüm: FileZilla Kullanın (Önerilen)

SSH çalışmıyorsa, **FileZilla** ile dosyaları yükleyebilirsiniz.

### 1. FileZilla'yı İndirin
https://filezilla-project.org/download.php?type=client

### 2. Bağlanın

**Hızlı Bağlantı (Quickconnect):**
- **Host:** `ftp://www.baycode.com.tr` veya `www.baycode.com.tr`
- **Username:** `baycode` (cPanel kullanıcı adınız)
- **Password:** FTP şifreniz
- **Port:** `21` (FTP) veya `22` (SFTP - deneyin)

**Bağlan** butonuna tıklayın.

### 3. Dosyaları Yükleyin

**Sol taraf (Yerel):**
- `C:\Users\bayCode Danışma\Desktop\Piarte` klasörüne gidin

**Sağ taraf (Sunucu):**
- `public_html/piarte` veya `piarte` klasörüne gidin
- Yoksa sağ tarafta sağ tıklayın → "Create directory" → `piarte`

**Yükleyin:**
1. Sol taraftan `app` klasörünü seçin
2. Sağ tarafa sürükleyip bırakın
3. Aynı şekilde `templates` klasörünü yükleyin
4. `index.html` dosyasını yükleyin
5. `requirements.txt` dosyasını yükleyin
6. `kurulum.sh` dosyasını yükleyin

## 🔄 Alternatif: cPanel File Manager

### 1. cPanel'e Giriş Yapın
```
https://www.baycode.com.tr:2083
```
veya
```
https://www.baycode.com.tr/cpanel
```

### 2. File Manager'ı Açın
- Ana sayfada "Files" bölümünden **"File Manager"** tıklayın

### 3. Dizine Gidin
- Sol menüden `public_html` klasörüne tıklayın
- `piarte` klasörü yoksa oluşturun:
  - Üstteki **"+ Folder"** butonuna tıklayın
  - İsim: `piarte`
  - **"Create New Folder"** tıklayın

### 4. Dosyaları Yükleyin
- `piarte` klasörüne girin
- Üstteki **"Upload"** butonuna tıklayın
- **"Select File"** ile dosyaları seçin:
  - `app/` klasörü (tüm içeriği)
  - `templates/` klasörü (tüm içeriği)
  - `index.html`
  - `requirements.txt`
  - `kurulum.sh`

**Not:** Klasörleri tek tek yükleyemezsiniz, içindeki dosyaları yüklemeniz gerekir.

## 🔍 SSH Portunu Kontrol Etme

Eğer yine de SSH denemek isterseniz:

### Farklı Portları Deneyin

```powershell
# Port 2222 deneyin
ssh -p 2222 baycode@www.baycode.com.tr

# Port 2200 deneyin
ssh -p 2200 baycode@www.baycode.com.tr
```

### Hosting Sağlayıcınıza Sorun

- "SSH erişimim var mı?"
- "SSH port numarası nedir?"
- "SSH nasıl aktif edilir?"

## 📋 Özet

**SSH çalışmıyorsa:**
1. ✅ **FileZilla kullanın** (En kolay)
2. ✅ **cPanel File Manager kullanın** (Tarayıcıdan)
3. ⚠️ Hosting sağlayıcınıza SSH erişimi sorun

**FileZilla ile yükleme en pratik çözümdür!**


