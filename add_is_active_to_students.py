"""
Öğrenci tablosuna is_active kolonu ekleme scripti
Bu script mevcut veritabanına is_active kolonunu ekler ve tüm mevcut öğrencileri aktif yapar
"""
from app.db import engine, get_db
from sqlalchemy import text

def add_is_active_column():
    """Öğrenci tablosuna is_active kolonu ekle"""
    print("📦 Öğrenci tablosuna is_active kolonu ekleniyor...")
    
    db = next(get_db())
    try:
        # SQLite için
        if "sqlite" in str(engine.url):
            # SQLite'da kolon ekleme
            db.execute(text("""
                ALTER TABLE students ADD COLUMN is_active BOOLEAN DEFAULT 1 NOT NULL;
            """))
            # Mevcut öğrencileri aktif yap
            db.execute(text("UPDATE students SET is_active = 1 WHERE is_active IS NULL"))
        else:
            # PostgreSQL için
            # Önce kolonun var olup olmadığını kontrol et
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='students' AND column_name='is_active'
            """))
            if result.fetchone() is None:
                # Kolon yoksa ekle
                db.execute(text("ALTER TABLE students ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL"))
                print("✅ is_active kolonu eklendi")
            else:
                print("ℹ️ is_active kolonu zaten mevcut")
        
        db.commit()
        print("✅ Migration tamamlandı!")
        print("✅ Tüm mevcut öğrenciler aktif olarak işaretlendi")
        return True
    except Exception as e:
        db.rollback()
        print(f"❌ Hata: {e}")
        # Eğer kolon zaten varsa hata verme
        if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
            print("ℹ️ is_active kolonu zaten mevcut, devam ediliyor...")
            return True
        return False
    finally:
        db.close()

if __name__ == "__main__":
    add_is_active_column()
