"""
Hızlı sunucu test scripti
Bu script sunucunun çalışıp çalışmadığını test eder
"""
import requests
import sys

def test_server(base_url="http://localhost:8000"):
    """Sunucu endpoint'lerini test et"""
    
    print("🔍 Sunucu testi başlıyor...\n")
    
    tests = [
        ("/health", "Health Check"),
        ("/", "Ana Sayfa (index.html)"),
        ("/login/admin", "Admin Giriş Sayfası"),
        ("/login/teacher", "Öğretmen Giriş Sayfası"),
        ("/login/staff", "Personel Giriş Sayfası"),
    ]
    
    results = []
    
    for endpoint, name in tests:
        try:
            url = f"{base_url}{endpoint}"
            print(f"📡 Test: {name} ({endpoint})")
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                print(f"   ✅ Başarılı (Status: {response.status_code})")
                results.append((name, True, response.status_code))
            else:
                print(f"   ⚠️  Uyarı (Status: {response.status_code})")
                results.append((name, False, response.status_code))
                
        except requests.exceptions.ConnectionError:
            print(f"   ❌ Bağlantı hatası - Sunucu çalışmıyor!")
            results.append((name, False, "Connection Error"))
        except requests.exceptions.Timeout:
            print(f"   ❌ Zaman aşımı")
            results.append((name, False, "Timeout"))
        except Exception as e:
            print(f"   ❌ Hata: {e}")
            results.append((name, False, str(e)))
        
        print()
    
    # Özet
    print("\n" + "="*50)
    print("📊 Test Özeti:")
    print("="*50)
    
    success_count = sum(1 for _, success, _ in results if success)
    total_count = len(results)
    
    for name, success, status in results:
        status_icon = "✅" if success else "❌"
        print(f"{status_icon} {name}: {status}")
    
    print(f"\nToplam: {success_count}/{total_count} başarılı")
    
    if success_count == total_count:
        print("\n🎉 Tüm testler başarılı! Sunucu çalışıyor.")
        return True
    else:
        print("\n⚠️  Bazı testler başarısız. Sunucuyu kontrol edin.")
        return False

if __name__ == "__main__":
    # Komut satırından URL al (varsa)
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    print(f"🌐 Test URL: {base_url}\n")
    
    success = test_server(base_url)
    sys.exit(0 if success else 1)


