from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Environment variable'dan al (cloud platformlar otomatik ekler)
# Eğer DATABASE_URL yoksa, varsayılan olarak SQLite kullan (geliştirme için)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data.db")

# PostgreSQL veya SQLite için farklı ayarlar
if DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://"):
	# Railway ve diğer platformlar için PostgreSQL bağlantı string'ini düzelt
	# Railway genellikle postgres:// verir, SQLAlchemy için postgresql:// veya postgresql+psycopg2:// gerekir
	if DATABASE_URL.startswith("postgres://"):
		# postgres:// -> postgresql+psycopg2:// dönüştür
		DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
	
	# PostgreSQL için SSL ve connection pool ayarları
	# Railway PostgreSQL için SSL gerektirir
	engine = create_engine(
		DATABASE_URL,
		pool_pre_ping=True,  # Bağlantı kontrolü - kopmuş bağlantıları yeniden kurar
		pool_size=5,  # Connection pool boyutu
		max_overflow=10,  # Pool dolu olduğunda ekstra bağlantı sayısı
		pool_recycle=300,  # 5 dakika sonra bağlantıları yenile (Railway timeout'ları için)
		connect_args={
			"sslmode": "require",  # Railway PostgreSQL için SSL zorunlu
			"connect_timeout": 10,  # Bağlantı timeout'u
		}
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



