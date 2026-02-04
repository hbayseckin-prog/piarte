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
		columns = [col['name'] for col in inspector.get_columns('students')]
		
		if 'is_active' not in columns:
			print("is_active kolonu bulunamadi, ekleniyor...")
			db = SessionLocal()
			try:
				if "sqlite" in str(engine.url):
					db.execute(text("ALTER TABLE students ADD COLUMN is_active BOOLEAN DEFAULT 1 NOT NULL"))
				else:
					db.execute(text("ALTER TABLE students ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL"))
				db.commit()
				print("is_active kolonu eklendi")
			except Exception as e:
				if "duplicate column" not in str(e).lower() and "already exists" not in str(e).lower():
					print(f"is_active kolonu eklenirken hata: {e}")
				db.rollback()
			finally:
				db.close()
	except Exception as e:
		print(f"is_active kolonu kontrol edilirken hata: {e}")

# Uygulama başlangıcında kolonu kontrol et
try:
	ensure_is_active_column()
except Exception as e:
	print(f"Baslangic migration kontrolu hatasi: {e}")



