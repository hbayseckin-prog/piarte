from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Environment variable'dan al (cloud platformlar otomatik ekler)
# Eğer DATABASE_URL yoksa, varsayılan olarak SQLite kullan (geliştirme için)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data.db")
# Railway vb. postgres:// verir; SQLAlchemy psycopg2 için postgresql:// gerekir
if DATABASE_URL.startswith("postgres://"):
	DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

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


def ensure_teacher_is_active_column():
	"""teachers.is_active kolonunun var olduğundan emin ol"""
	try:
		from sqlalchemy import text, inspect
		inspector = inspect(engine)
		try:
			columns = inspector.get_columns('teachers')
			column_names = [col['name'] for col in columns]
		except Exception:
			column_names = []

		if 'is_active' not in column_names:
			print("teachers.is_active kolonu bulunamadi, ekleniyor...")
			db = SessionLocal()
			try:
				if "sqlite" in str(engine.url).lower():
					db.execute(text("ALTER TABLE teachers ADD COLUMN is_active BOOLEAN DEFAULT 1 NOT NULL"))
				else:
					db.execute(text("ALTER TABLE teachers ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL"))
				db.commit()
				print("teachers.is_active kolonu basariyla eklendi")
			except Exception as e:
				error_str = str(e).lower()
				if "duplicate column" not in error_str and "already exists" not in error_str:
					print(f"teachers.is_active kolonu eklenirken hata: {e}")
				db.rollback()
			finally:
				db.close()
	except Exception as e:
		print(f"teachers.is_active kolonu kontrol edilirken hata: {e}")


def ensure_attendance_lesson_fk_restrict():
	"""PostgreSQL'de attendances.lesson_id FK'yi RESTRICT yap (yoklama kayıtları ders silinirken silinmesin)"""
	try:
		from sqlalchemy import text
		if "postgresql" not in str(engine.url).lower() and "postgres" not in str(engine.url).lower():
			return
		db = SessionLocal()
		try:
			# Şu an delete_rule CASCADE mı kontrol et; RESTRICT ise dokunma
			r = db.execute(text("""
				SELECT rc.constraint_name, rc.delete_rule
				FROM information_schema.referential_constraints rc
				JOIN information_schema.key_column_usage kcu
				  ON rc.constraint_name = kcu.constraint_name AND kcu.table_name = 'attendances'
				WHERE kcu.table_schema = current_schema() AND kcu.table_name = 'attendances' AND kcu.column_name = 'lesson_id'
			"""))
			row = r.fetchone()
			if not row or row[1].upper() == "RESTRICT":
				return
			old_constraint = row[0]
			db.execute(text(f"ALTER TABLE attendances DROP CONSTRAINT IF EXISTS {old_constraint}"))
			db.execute(text("""
				ALTER TABLE attendances ADD CONSTRAINT attendances_lesson_id_fkey
				FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE RESTRICT
			"""))
			db.commit()
			print("attendances.lesson_id FK RESTRICT olarak güncellendi")
		except Exception as e:
			db.rollback()
		finally:
			db.close()
	except Exception:
		pass


def ensure_lesson_students_backfill_from_attendance():
	"""
	Tek seferlik onarım: LessonStudent'ı boş olan ama yoklaması bulunan derslere
	son yoklama öğrencisini gerçek atama olarak yazar.

	Eski program görünümü yoklamadan isim gösteriyordu; Dersten çıkar ise yalnızca
	LessonStudent'a bakıyordu. Bu backfill ikisini hizalar. Bayrak sayesinde
	Dersten çıkar sonrası yeniden ekleme yapmaz.
	"""
	try:
		from sqlalchemy import text, inspect
		inspector = inspect(engine)
		table_names = set(inspector.get_table_names())
		if "lessons" not in table_names or "attendances" not in table_names or "lesson_students" not in table_names:
			return

		db = SessionLocal()
		try:
			db.execute(text("""
				CREATE TABLE IF NOT EXISTS app_meta (
					key VARCHAR(100) PRIMARY KEY,
					value VARCHAR(255),
					created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
				)
			"""))
			db.commit()

			flag = db.execute(
				text("SELECT value FROM app_meta WHERE key = :k"),
				{"k": "lesson_student_att_backfill_v1"},
			).fetchone()
			if flag:
				return

			# LessonStudent'ı olmayan dersler
			empty_lessons = db.execute(text("""
				SELECT l.id
				FROM lessons l
				WHERE NOT EXISTS (
					SELECT 1 FROM lesson_students ls WHERE ls.lesson_id = l.id
				)
			""")).fetchall()
			created = 0
			for (lesson_id,) in empty_lessons:
				row = db.execute(text("""
					SELECT student_id
					FROM attendances
					WHERE lesson_id = :lid AND student_id IS NOT NULL
					ORDER BY marked_at DESC
					LIMIT 1
				"""), {"lid": lesson_id}).fetchone()
				if not row:
					continue
				student_id = row[0]
				exists = db.execute(text("""
					SELECT 1 FROM lesson_students
					WHERE lesson_id = :lid AND student_id = :sid
					LIMIT 1
				"""), {"lid": lesson_id, "sid": student_id}).fetchone()
				if exists:
					continue
				db.execute(text("""
					INSERT INTO lesson_students (lesson_id, student_id, created_at)
					VALUES (:lid, :sid, CURRENT_TIMESTAMP)
				"""), {"lid": lesson_id, "sid": student_id})
				created += 1

			db.execute(text("""
				INSERT INTO app_meta (key, value) VALUES (:k, :v)
			"""), {"k": "lesson_student_att_backfill_v1", "v": str(created)})
			db.commit()
			print(f"lesson_students yoklama backfill tamamlandi: {created} kayit")
		except Exception as e:
			db.rollback()
			print(f"lesson_students backfill hatasi: {e}")
		finally:
			db.close()
	except Exception as e:
		print(f"lesson_students backfill kontrol hatasi: {e}")


# Uygulama başlangıcında kolonu kontrol et
try:
	ensure_is_active_column()
except Exception as e:
	print(f"Baslangic migration kontrolu hatasi: {e}")
	import traceback
	traceback.print_exc()

try:
	ensure_teacher_is_active_column()
except Exception:
	pass

try:
	ensure_attendance_lesson_fk_restrict()
except Exception as e:
	pass

try:
	ensure_lesson_students_backfill_from_attendance()
except Exception:
	pass


def ensure_expenses_table():
	"""expenses tablosunun var olduğundan emin ol (Finans / Giderler)."""
	try:
		from sqlalchemy import inspect, text
		inspector = inspect(engine)
		if "expenses" in set(inspector.get_table_names()):
			return
		print("expenses tablosu bulunamadi, olusturuluyor...")
		is_pg = "postgres" in str(engine.url).lower()
		ddl = """
			CREATE TABLE expenses (
				id SERIAL PRIMARY KEY,
				title VARCHAR(120) NOT NULL,
				category VARCHAR(40) NOT NULL DEFAULT 'Diger',
				amount_try NUMERIC(12, 2) NOT NULL,
				expense_date DATE NOT NULL,
				method VARCHAR(30),
				note TEXT,
				created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
			)
		""" if is_pg else """
			CREATE TABLE expenses (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				title VARCHAR(120) NOT NULL,
				category VARCHAR(40) NOT NULL DEFAULT 'Diger',
				amount_try NUMERIC(12, 2) NOT NULL,
				expense_date DATE NOT NULL,
				method VARCHAR(30),
				note TEXT,
				created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
			)
		"""
		db = SessionLocal()
		try:
			db.execute(text(ddl))
			db.commit()
			print("expenses tablosu olusturuldu")
		except Exception as e:
			db.rollback()
			print(f"expenses tablo olusturma: {e}")
		finally:
			db.close()
	except Exception as e:
		print(f"expenses tablo kontrol hatasi: {e}")


try:
	ensure_expenses_table()
except Exception:
	pass



