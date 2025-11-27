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



