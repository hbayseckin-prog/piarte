"""
Veritabanı kurulum scripti
Bu script veritabanını oluşturur ve seed data ekler
"""
from app.db import Base, engine, get_db
from app import models, crud, schemas

def setup_database():
    """Veritabanını oluştur ve seed data ekle"""
    print("📦 Veritabanı oluşturuluyor...")
    
    # Tüm tabloları oluştur
    Base.metadata.create_all(bind=engine)
    print("✅ Tablolar oluşturuldu")
    
    # Seed data ekle
    try:
        db = next(get_db())
        try:
            from app.seed import seed_courses, seed_admin
            if seed_courses:
                seed_courses(db)
                print("✅ Kurslar eklendi")
            if seed_admin:
                seed_admin(db)
                print("✅ Admin kullanıcısı eklendi (kullanıcı adı: admin, şifre: admin123)")
        except Exception as e:
            print(f"⚠️ Seed data hatası: {e}")
        finally:
            db.close()
    except Exception as e:
        print(f"❌ Veritabanı bağlantı hatası: {e}")
        return False
    
    print("\n🎉 Veritabanı kurulumu tamamlandı!")
    print("\n📝 Sonraki adımlar:")
    print("1. Sunucuyu başlatın: python -m uvicorn app.main:app --reload")
    print("2. Tarayıcıda açın: http://localhost:8000")
    print("3. Admin ile giriş yapın ve şifrenizi değiştirin!")
    return True

if __name__ == "__main__":
    setup_database()


