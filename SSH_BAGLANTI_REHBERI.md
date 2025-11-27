# 🔐 SSH Bağlantı Rehberi

## 📝 "kullanici@" Kısmına Ne Yazılır?

Bu, **sunucuya SSH ile bağlanırken kullandığınız kullanıcı adı**dır.

## 🔍 Kullanıcı Adını Nasıl Bulursunuz?

### Yöntem 1: Hosting Panel'den (cPanel, Plesk vb.)

1. **cPanel'e giriş yapın**
2. **"SSH Access"** veya **"Terminal"** bölümüne bakın
3. Kullanıcı adınız genellikle:
   - cPanel kullanıcı adınız ile aynıdır
   - Örnek: `baycode` veya `baycode_tr`

### Yöntem 2: Hosting Sağlayıcınızdan

Hosting sağlayıcınızın size verdiği bilgilerde:
- **SSH Username**
- **FTP Username** (genellikle aynıdır)
- **cPanel Username**

### Yöntem 3: VPS Kullanıyorsanız

- Genellikle: `root` (ilk kurulumda)
- Veya: Oluşturduğunuz kullanıcı adı

## 📋 Örnekler

### Örnek 1: cPanel Kullanıcısı
```bash
# Eğer cPanel kullanıcı adınız "baycode" ise:
scp -r app/ baycode@www.baycode.com.tr:/var/www/piarte/
```

### Örnek 2: Root Kullanıcı (VPS)
```bash
# VPS'de genellikle root kullanılır:
scp -r app/ root@www.baycode.com.tr:/var/www/piarte/
```

### Örnek 3: Özel Kullanıcı
```bash
# Kendi oluşturduğunuz kullanıcı:
scp -r app/ piarte@www.baycode.com.tr:/var/www/piarte/
```

## 🔑 SSH Bağlantısını Test Edin

Önce SSH ile bağlanabildiğinizi test edin:

```powershell
# Windows PowerShell'de
ssh kullanici-adi@www.baycode.com.tr
```

**Başarılı olursa:** Sunucuya bağlanırsınız ve şifre ister.

**Hata alırsanız:** Kullanıcı adı veya sunucu adresi yanlış olabilir.

## ⚠️ Önemli Notlar

### 1. Windows'ta SCP Komutu

Windows 10/11'de genellikle SCP komutu yüklüdür. Eğer yoksa:

**Seçenek 1: WinSCP Kullanın (Önerilen)**
- WinSCP programını indirin: https://winscp.net
- GUI ile kolayca yükleyebilirsiniz

**Seçenek 2: PowerShell'de Test**
```powershell
# SCP komutu var mı test edin
scp
# Hata verirse yüklü değildir
```

### 2. Alternatif: FileZilla (Daha Kolay)

SCP yerine **FileZilla** kullanmak daha kolay olabilir:

1. FileZilla'yı indirin: https://filezilla-project.org
2. Açın ve bağlanın:
   - Host: `sftp://www.baycode.com.tr` (SFTP protokolü)
   - Username: cPanel/FTP kullanıcı adınız
   - Password: Şifreniz
   - Port: 22 (SSH portu)

3. Dosyaları sürükleyip bırakın

## 🎯 Hızlı Çözüm

**Eğer kullanıcı adınızı bilmiyorsanız:**

1. **cPanel'e giriş yapın**
2. **Sağ üstteki kullanıcı adınıza bakın** (genellikle bu)
3. **Veya FTP bilgilerinize bakın** (FTP kullanıcı adı genellikle aynıdır)

**Örnek:**
- cPanel kullanıcı adınız: `baycode`
- Komut: `scp -r app/ baycode@www.baycode.com.tr:/var/www/piarte/`

## 📞 Hala Bulamıyorsanız

Hosting sağlayıcınızın destek ekibine sorun:
- "SSH kullanıcı adım nedir?"
- "SSH erişimim var mı?"
- "SSH bağlantı bilgilerim nelerdir?"


