from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Environment variable'dan al (cloud platformlar otomatik ekler)
# Eğer DATABASE_URL yoksa, varsayılan olarak SQLite kullan (geliştirme için)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data.db")

# PostgreSQL veya SQLite için farklı ayarlar
if DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://"):
	# PostgreSQL için
	engine = create_engine(
		DATABASE_URL,
		pool_pre_ping=True,  # Bağlantı kontrolü
		pool_size=5,  # Connection pool boyutu
		max_overflow=10
	)
else:
	# SQLite için (geliştirme)
	engine = create_engine(
		DATABASE_URL,
		connect_args={"check_same_thread": False},
	)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()

def ensure_is_active_column():
	"""is_active kolonunun var olduğundan emin ol"""
	try:
		from sqlalchemy import text, inspect
		inspector = inspect(engine)
		
		# Kolonları kontrol et
		try:
			columns = inspector.get_columns('students')
			column_names = [col['name'] for col in columns]
		except Exception:
			# Eğer tablo yoksa veya hata varsa, direkt eklemeyi dene
			column_names = []
		
		if 'is_active' not in column_names:
			print("is_active kolonu bulunamadi, ekleniyor...")
			db = SessionLocal()
			try:
				if "sqlite" in str(engine.url).lower():
					db.execute(text("ALTER TABLE students ADD COLUMN is_active BOOLEAN DEFAULT 1 NOT NULL"))
				else:
					# PostgreSQL için
					db.execute(text("ALTER TABLE students ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL"))
				db.commit()
				print("is_active kolonu basariyla eklendi")
			except Exception as e:
				error_str = str(e).lower()
				if "duplicate column" in error_str or "already exists" in error_str or "column" in error_str:
					print("is_active kolonu zaten mevcut")
				else:
					print(f"is_active kolonu eklenirken hata: {e}")
					import traceback
					traceback.print_exc()
				db.rollback()
			finally:
				db.close()
		else:
			print("is_active kolonu zaten mevcut")
	except Exception as e:
		print(f"is_active kolonu kontrol edilirken hata: {e}")
		import traceback
		traceback.print_exc()

# Uygulama başlangıcında kolonu kontrol et
try:
	ensure_is_active_column()
except Exception as e:
	print(f"Baslangic migration kontrolu hatasi: {e}")
	import traceback
	traceback.print_exc()



