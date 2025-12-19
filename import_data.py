"""
Export edilmiş verileri PostgreSQL veritabanına import eder
Bu script, export_data.py ile oluşturulan JSON dosyasını PostgreSQL'e yükler
"""
import json
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.db import Base, engine
from app import models

def import_data_from_json(json_file="data_export.json", db_session=None):
    """JSON dosyasından verileri veritabanına import eder"""
    
    if not os.path.exists(json_file):
        print(f"❌ Dosya bulunamadı: {json_file}")
        return False
    
    # JSON'u oku
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if db_session is None:
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
    else:
        db = db_session
    
    try:
        # Tabloları sırayla import et (foreign key bağımlılıklarına dikkat ederek)
        import_order = [
            'courses',      # Foreign key yok
            'teachers',     # Foreign key yok
            'students',     # Foreign key yok
            'users',        # teachers'a bağlı olabilir
            'enrollments',  # students ve courses'a bağlı
            'lessons',      # courses ve teachers'a bağlı
            'teacher_students',  # teachers ve students'a bağlı
            'lesson_students',   # lessons ve students'a bağlı
            'attendances',  # lessons ve students'a bağlı
            'payments',     # students'a bağlı
        ]
        
        total_imported = 0
        
        for table_name in import_order:
            if table_name not in data:
                continue
            
            table_data = data[table_name]
            if not table_data:
                continue
            
            # Model sınıfını bul
            model_map = {
                'courses': models.Course,
                'teachers': models.Teacher,
                'students': models.Student,
                'users': models.User,
                'enrollments': models.Enrollment,
                'lessons': models.Lesson,
                'teacher_students': models.TeacherStudent,
                'lesson_students': models.LessonStudent,
                'attendances': models.Attendance,
                'payments': models.Payment,
            }
            
            model_class = model_map.get(table_name)
            if not model_class:
                print(f"⚠️ Model bulunamadı: {table_name}")
                continue
            
            imported_count = 0
            for row_data in table_data:
                try:
                    # ID'yi çıkar (eğer varsa)
                    row_id = row_data.pop('id', None)
                    
                    # Model instance oluştur
                    instance = model_class(**row_data)
                    
                    # ID'yi manuel set et (eğer varsa)
                    if row_id is not None:
                        instance.id = row_id
                    
                    db.add(instance)
                    imported_count += 1
                except Exception as e:
                    print(f"⚠️ {table_name} import hatası (satır {row_data}): {e}")
                    continue
            
            db.commit()
            print(f"✅ {table_name}: {imported_count} kayıt import edildi")
            total_imported += imported_count
        
        print(f"\n🎉 Toplam {total_imported} kayıt başarıyla import edildi!")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Import hatası: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if db_session is None:
            db.close()

if __name__ == "__main__":
    import sys
    
    json_file = sys.argv[1] if len(sys.argv) > 1 else "data_export.json"
    
    # Veritabanı bağlantısını kontrol et
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("⚠️ DATABASE_URL environment variable bulunamadı")
        print("Lütfen .env dosyasında DATABASE_URL'yi ayarlayın")
        sys.exit(1)
    
    print(f"📦 Veritabanı: {database_url.split('@')[1] if '@' in database_url else 'local'}")
    print(f"📄 Import dosyası: {json_file}\n")
    
    # Tabloları oluştur
    print("📦 Veritabanı tabloları oluşturuluyor...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tablolar hazır\n")
    
    # Import işlemini başlat
    import_data_from_json(json_file)







