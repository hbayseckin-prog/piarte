"""
SQLite veritabanından verileri export eder
Bu script, mevcut SQLite veritabanındaki verileri JSON formatında export eder
"""
import sqlite3
import json
from datetime import date, datetime

def json_serial(obj):
    """JSON serialization için date ve datetime desteği"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def export_sqlite_data(db_path="data.db", output_file="data_export.json"):
    """SQLite veritabanından tüm verileri export eder"""
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    export_data = {}
    
    # Tüm tabloları al
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"📦 {len(tables)} tablo bulundu: {', '.join(tables)}")
    
    for table in tables:
        if table == "sqlite_sequence":  # SQLite internal table
            continue
            
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        
        # Row'ları dict'e çevir
        table_data = []
        for row in rows:
            row_dict = {}
            for key in row.keys():
                value = row[key]
                # None değerleri None olarak bırak
                if value is None:
                    row_dict[key] = None
                else:
                    row_dict[key] = value
            table_data.append(row_dict)
        
        export_data[table] = table_data
        print(f"✅ {table}: {len(table_data)} kayıt")
    
    conn.close()
    
    # JSON'a yaz
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2, default=json_serial)
    
    print(f"\n🎉 Veriler başarıyla export edildi: {output_file}")
    print(f"📊 Toplam {sum(len(v) for v in export_data.values())} kayıt")
    
    return export_data

if __name__ == "__main__":
    import sys
    
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data.db"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "data_export.json"
    
    try:
        export_sqlite_data(db_path, output_file)
    except Exception as e:
        print(f"❌ Hata: {e}")
        import traceback
        traceback.print_exc()







