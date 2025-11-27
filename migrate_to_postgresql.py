"""
SQLite'dan PostgreSQL'e veri taşıma scripti

Kullanım:
1. PostgreSQL veritabanınızı hazırlayın (Railway, Supabase, Render vb.)
2. DATABASE_URL environment variable'ını ayarlayın
3. Bu scripti çalıştırın: python migrate_to_postgresql.py
"""
import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
import sqlite3

# PostgreSQL connection string (environment variable'dan al)
POSTGRES_URL = os.getenv("DATABASE_URL")
if not POSTGRES_URL or not POSTGRES_URL.startswith(("postgresql://", "postgres://")):
    print("❌ HATA: DATABASE_URL environment variable'ı PostgreSQL connection string olmalı!")
    print("Örnek: postgresql://user:password@host:5432/database")
    print("\nRailway/Supabase/Render'dan connection string'i alın ve şu şekilde ayarlayın:")
    print("export DATABASE_URL='postgresql://...'")
    sys.exit(1)

# SQLite bağlantısı
SQLITE_DB = "data.db"
if not os.path.exists(SQLITE_DB):
    print(f"❌ HATA: {SQLITE_DB} dosyası bulunamadı!")
    sys.exit(1)

print("📦 Veri taşıma başlıyor...")
print(f"📂 Kaynak: {SQLITE_DB} (SQLite)")
print(f"📂 Hedef: {POSTGRES_URL.split('@')[1] if '@' in POSTGRES_URL else 'PostgreSQL'}")

# SQLite bağlantısı
sqlite_conn = sqlite3.connect(SQLITE_DB)
sqlite_cursor = sqlite_conn.cursor()

# PostgreSQL bağlantısı
try:
    pg_engine = create_engine(POSTGRES_URL)
    pg_session = sessionmaker(bind=pg_engine)()
    
    # Tabloları oluştur
    print("\n🔨 PostgreSQL'de tablolar oluşturuluyor...")
    from app.db import Base
    Base.metadata.create_all(bind=pg_engine)
    print("✅ Tablolar oluşturuldu")
    
    # SQLite'daki tabloları listele
    sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in sqlite_cursor.fetchall()]
    
    print(f"\n📊 {len(tables)} tablo bulundu: {', '.join(tables)}")
    
    # Her tablo için veri taşı
    total_rows = 0
    for table in tables:
        try:
            # SQLite'dan veri sayısını al
            sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = sqlite_cursor.fetchone()[0]
            
            if count == 0:
                print(f"⏭️  {table}: Veri yok, atlanıyor")
                continue
            
            print(f"\n📥 {table}: {count} satır taşınıyor...")
            
            # SQLite'dan veri al
            sqlite_cursor.execute(f"SELECT * FROM {table}")
            rows = sqlite_cursor.fetchall()
            columns = [desc[0] for desc in sqlite_cursor.description]
            
            # PostgreSQL'de tablo var mı kontrol et
            inspector = inspect(pg_engine)
            if table not in inspector.get_table_names():
                print(f"⚠️  {table} tablosu PostgreSQL'de yok, atlanıyor")
                continue
            
            # PostgreSQL'deki sütunları al
            pg_columns = [col['name'] for col in inspector.get_columns(table)]
            
            # Ortak sütunları bul
            common_columns = [col for col in columns if col in pg_columns]
            
            if not common_columns:
                print(f"⚠️  {table}: Ortak sütun bulunamadı, atlanıyor")
                continue
            
            # Verileri ekle
            inserted = 0
            for row in rows:
                try:
                    # Sadece ortak sütunları kullan
                    row_dict = dict(zip(columns, row))
                    filtered_dict = {k: v for k, v in row_dict.items() if k in common_columns}
                    
                    # INSERT statement oluştur
                    columns_str = ', '.join(common_columns)
                    values_str = ', '.join([f":{col}" for col in common_columns])
                    insert_sql = f"INSERT INTO {table} ({columns_str}) VALUES ({values_str}) ON CONFLICT DO NOTHING"
                    
                    pg_session.execute(text(insert_sql), filtered_dict)
                    inserted += 1
                except Exception as e:
                    print(f"⚠️  Satır eklenirken hata: {e}")
                    continue
            
            pg_session.commit()
            total_rows += inserted
            print(f"✅ {table}: {inserted}/{count} satır taşındı")
            
        except Exception as e:
            print(f"❌ {table} taşınırken hata: {e}")
            pg_session.rollback()
            continue
    
    print(f"\n🎉 Veri taşıma tamamlandı!")
    print(f"📊 Toplam {total_rows} satır taşındı")
    print("\n✅ Artık PostgreSQL kullanabilirsiniz!")
    print("💡 DATABASE_URL environment variable'ını production'da ayarlayın")
    
except Exception as e:
    print(f"\n❌ HATA: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
    
finally:
    sqlite_conn.close()
    if 'pg_session' in locals():
        pg_session.close()


