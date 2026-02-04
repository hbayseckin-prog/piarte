from fastapi import FastAPI, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, select
import os

from .db import Base, engine, get_db
from . import crud, schemas, models
try:
    from . import excel_sync
except ImportError:
    excel_sync = None
try:
    from .seed import seed_courses, seed_admin
except ImportError:
    seed_courses = None
    seed_admin = None


def redirect_teacher(user):
    if user and user.get("role") == "teacher":
        return RedirectResponse(url="/ui/teacher", status_code=302)
    return None


def calculate_next_lesson_date(original_date):
    """
    Haftalık tekrarlanan dersler için bugünden sonraki ilgili günü hesaplar.
    Örneğin: Orijinal tarih Pazartesi ise, bugün Pazartesi ise bugünü, 
    değilse bugünden sonraki Pazartesi'yi döndürür.
    
    Args:
        original_date: Orijinal ders tarihi (date objesi)
    
    Returns:
        Bugün veya bugünden sonraki ilgili günün tarihi (date objesi)
    """
    from datetime import date, timedelta
    
    today = date.today()
    original_weekday = original_date.weekday()  # 0=Pazartesi, 6=Pazar
    today_weekday = today.weekday()
    
    # Bugünden sonraki ilgili günü bul
    days_ahead = original_weekday - today_weekday
    if days_ahead < 0:  # Bu hafta geçtiyse gelecek hafta
        days_ahead += 7
    # days_ahead == 0 ise bugün o gün, bugünü döndür
    
    next_date = today + timedelta(days=days_ahead)
    return next_date


# Alt klasör desteği için root_path (eğer /piarte altında çalışıyorsa)
# Production'da environment variable veya Nginx yapılandırması ile ayarlanabilir
ROOT_PATH = os.getenv("ROOT_PATH", "")  # Varsayılan: boş (root'ta çalışır)

app = FastAPI(title="Piarte Kurs Yönetimi", root_path=ROOT_PATH)

# CORS ayarları - iframe ve farklı domain'den erişim için
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production'da belirli domain'ler belirtin: ["https://example.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session secret key - environment variable'dan al, yoksa varsayılan kullan
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
templates = Jinja2Templates(directory="templates")

# Static files için - logo ve diğer statik dosyalar (proje root dizini)
# Logo dosyası root dizininde olduğu için root'u mount ediyoruz
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.exists(base_dir):
    app.mount("/static", StaticFiles(directory=base_dir), name="static")


# iframe güvenlik header'ları için middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
	response = await call_next(request)
	# iframe'de çalışması için - SAMEORIGIN: aynı domain'den iframe'e izin verir
	# Tüm origin'ler için izin vermek isterseniz bu satırı kaldırın
	response.headers["X-Frame-Options"] = "SAMEORIGIN"
	# Güvenlik için
	response.headers["X-Content-Type-Options"] = "nosniff"
	return response

# Basit health check endpoint
@app.get("/health")
def health_check():
	return {"status": "ok", "message": "Server is running"}

# Veritabanı kurulum endpoint'i
@app.get("/setup-database", response_class=HTMLResponse)
def setup_database_endpoint(request: Request):
	"""Veritabanını oluştur ve seed data ekle - HTML response ile"""
	try:
		reset_performed = False
		try:
			# Tüm tabloları oluştur
			Base.metadata.create_all(bind=engine)
		except Exception as e:
			# Eğer DuplicateTable / already exists hatası ise tüm tabloları silip yeniden oluştur
			msg = str(e)
			pgcode = getattr(getattr(e, "orig", None), "pgcode", "")
			if "DuplicateTable" in msg or "already exists" in msg or pgcode == "42P07":
				reset_performed = True
				Base.metadata.drop_all(bind=engine)
				Base.metadata.create_all(bind=engine)
			else:
				raise
		
		# Seed data ekle
		db = next(get_db())
		messages = []
		errors = []
		
		try:
			from app.seed import seed_courses, seed_admin
			
			# Kursları ekle
			if seed_courses:
				try:
					seed_courses(db)
					messages.append("✅ Kurslar başarıyla eklendi")
				except Exception as e:
					errors.append(f"⚠️ Kurs ekleme hatası: {str(e)}")
			
			# Admin kullanıcısını ekle
			if seed_admin:
				try:
					seed_admin(db)
					messages.append("✅ Admin kullanıcısı eklendi (kullanıcı adı: admin, şifre: admin123)")
				except Exception as e:
					errors.append(f"⚠️ Admin ekleme hatası: {str(e)}")
			
			db.commit()
		except Exception as e:
			errors.append(f"❌ Seed data hatası: {str(e)}")
			db.rollback()
		finally:
			db.close()
		
		# HTML response oluştur
		if reset_performed:
			messages.insert(0, "ℹ️ Mevcut tablolar silinip yeniden oluşturuldu (duplicate hata nedeniyle).")
		messages_html = "\n".join([f"<p style='color: green;'>{msg}</p>" for msg in messages])
		errors_html = "\n".join([f"<p style='color: orange;'>{err}</p>" for err in errors])
		
		html_content = f"""
		<!DOCTYPE html>
		<html lang="tr">
		<head>
			<meta charset="UTF-8">
			<meta name="viewport" content="width=device-width, initial-scale=1.0">
			<title>Veritabanı Kurulumu - Piarte</title>
			<style>
				body {{
					font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
					background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
					margin: 0;
					padding: 20px;
					min-height: 100vh;
					display: flex;
					justify-content: center;
					align-items: center;
				}}
				.container {{
					background: white;
					border-radius: 15px;
					padding: 40px;
					max-width: 600px;
					box-shadow: 0 10px 40px rgba(0,0,0,0.2);
				}}
				h1 {{
					color: #667eea;
					margin-bottom: 20px;
					text-align: center;
				}}
				.status {{
					background: #f0f9ff;
					border-left: 4px solid #667eea;
					padding: 15px;
					margin: 20px 0;
					border-radius: 5px;
				}}
				.success {{
					background: #f0fdf4;
					border-left: 4px solid #22c55e;
				}}
				.warning {{
					background: #fffbeb;
					border-left: 4px solid #f59e0b;
				}}
				.error {{
					background: #fef2f2;
					border-left: 4px solid #ef4444;
				}}
				.button {{
					display: inline-block;
					background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
					color: white;
					padding: 12px 30px;
					text-decoration: none;
					border-radius: 5px;
					margin-top: 20px;
					text-align: center;
					width: 100%;
					box-sizing: border-box;
				}}
				.button:hover {{
					opacity: 0.9;
				}}
				.info {{
					background: #f8fafc;
					padding: 15px;
					border-radius: 5px;
					margin-top: 20px;
					font-size: 14px;
					color: #64748b;
				}}
			</style>
		</head>
		<body>
			<div class="container">
				<h1>📦 Veritabanı Kurulumu</h1>
				
				<div class="status success">
					<strong>✅ Tablolar başarıyla oluşturuldu!</strong>
				</div>
				
				{messages_html if messages_html else ""}
				{errors_html if errors_html else ""}
				
				<div class="info">
					<strong>📝 Sonraki Adımlar:</strong><br>
					1. Ana sayfaya dönün ve giriş yapın<br>
					2. Admin kullanıcısı ile giriş yapın (kullanıcı adı: <strong>admin</strong>, şifre: <strong>admin123</strong>)<br>
					3. Güvenlik için şifrenizi değiştirin!
				</div>
				
				<a href="/" class="button">🏠 Ana Sayfaya Dön</a>
			</div>
		</body>
		</html>
		"""
		
		return HTMLResponse(content=html_content)
		
	except Exception as e:
		# Hata durumunda HTML response
		html_content = f"""
		<!DOCTYPE html>
		<html lang="tr">
		<head>
			<meta charset="UTF-8">
			<meta name="viewport" content="width=device-width, initial-scale=1.0">
			<title>Veritabanı Kurulum Hatası - Piarte</title>
			<style>
				body {{
					font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
					background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
					margin: 0;
					padding: 20px;
					min-height: 100vh;
					display: flex;
					justify-content: center;
					align-items: center;
				}}
				.container {{
					background: white;
					border-radius: 15px;
					padding: 40px;
					max-width: 600px;
					box-shadow: 0 10px 40px rgba(0,0,0,0.2);
				}}
				h1 {{
					color: #ef4444;
					margin-bottom: 20px;
					text-align: center;
				}}
				.error {{
					background: #fef2f2;
					border-left: 4px solid #ef4444;
					padding: 15px;
					margin: 20px 0;
					border-radius: 5px;
					color: #991b1b;
				}}
				.button {{
					display: inline-block;
					background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
					color: white;
					padding: 12px 30px;
					text-decoration: none;
					border-radius: 5px;
					margin-top: 20px;
					text-align: center;
					width: 100%;
					box-sizing: border-box;
				}}
			</style>
		</head>
		<body>
			<div class="container">
				<h1>❌ Veritabanı Kurulum Hatası</h1>
				
				<div class="error">
					<strong>Hata:</strong><br>
					{str(e)}
				</div>
				
				<div style="margin-top: 20px; color: #64748b; font-size: 14px;">
					<strong>Çözüm Önerileri:</strong><br>
					1. Railway'de DATABASE_URL değişkeninin doğru olduğundan emin olun<br>
					2. PostgreSQL servisinin çalıştığını kontrol edin<br>
					3. Railway'de "Deploy Logs" sekmesinden hata detaylarını kontrol edin
				</div>
				
				<a href="/" class="button">🏠 Ana Sayfaya Dön</a>
			</div>
		</body>
		</html>
		"""
		return HTMLResponse(content=html_content, status_code=500)

# Startup event'ini kaldırdık - lazy initialization kullanacağız
# İlk database isteğinde otomatik olarak tablolar oluşturulacak


def require_user(request: Request):
	user = request.session.get("user")
	if not user:
		raise HTTPException(status_code=401, detail="Giriş gerekiyor")
	return user


def require_admin(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Giriş gerekiyor")
    role = (user.get("role") or "").strip().lower()
    if role != "admin":
        raise HTTPException(status_code=403, detail="Yetki yok")
    return user


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
	# Kullanıcı giriş yapmışsa dashboard'a, yoksa index.html'i göster
	user = request.session.get("user")
	if user:
		if user.get("role") == "teacher":
			return RedirectResponse(url="/ui/teacher", status_code=302)
		elif user.get("role") == "staff":
			return RedirectResponse(url="/ui/staff", status_code=302)
		else:
			return RedirectResponse(url="/dashboard", status_code=302)
	# index.html'i göster
	try:
		with open("index.html", "r", encoding="utf-8") as f:
			return HTMLResponse(content=f.read())
	except FileNotFoundError:
		# index.html yoksa login sayfasına yönlendir
		return RedirectResponse(url="/login/admin", status_code=302)



@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    try:
        from passlib.hash import pbkdf2_sha256
        user = crud.get_user_by_username(db, username)
        if not user:
            return RedirectResponse(url="/", status_code=302)
        try:
            password_valid = pbkdf2_sha256.verify(password, user.password_hash)
        except Exception as e:
            import logging
            logging.error(f"Şifre doğrulama hatası: {e}")
            return RedirectResponse(url="/", status_code=302)
        if not password_valid:
            return RedirectResponse(url="/", status_code=302)
        request.session["user"] = {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role or "admin",
            "teacher_id": getattr(user, 'teacher_id', None),
        }
        return RedirectResponse(url="/dashboard", status_code=302)
    except Exception as e:
        import logging
        import traceback
        logging.error(f"Login hatası: {e}")
        logging.error(traceback.format_exc())
        return RedirectResponse(url="/", status_code=302)

@app.get("/logout")
def logout(request: Request):
	# Kullanıcının rolünü al (session temizlenmeden önce)
	user = request.session.get("user")
	role = user.get("role") if user else None
	
	# Session'ı temizle
	request.session.clear()
	
	# Rolüne göre ilgili giriş sayfasına yönlendir
	if role == "teacher":
		return RedirectResponse(url="/login/teacher", status_code=302)
	elif role == "staff":
		return RedirectResponse(url="/login/staff", status_code=302)
	else:
		# admin veya diğer durumlar için admin giriş sayfasına yönlendir
		return RedirectResponse(url="/login/admin", status_code=302)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    teacher_id: str | None = None,
    student_id: str | None = None,
    course_id: str | None = None,
    status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    order_by: str = "marked_at_desc",
):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login/admin", status_code=302)
    if user.get("role") == "staff":
        return RedirectResponse(url="/ui/staff", status_code=302)
    if user.get("role") == "teacher":
        return RedirectResponse(url="/ui/teacher", status_code=302)
    courses = crud.list_courses(db)
    students = crud.list_students(db)
    teachers = crud.list_teachers(db)
    # Staff (personel) kullanıcılarını getir
    from sqlalchemy import select
    staff_users = db.scalars(select(models.User).where(models.User.role == "staff").order_by(models.User.created_at.desc())).all()
    
    # Query parametrelerini integer'a çevir (boş string'leri None yap)
    teacher_id_int = None
    student_id_int = None
    course_id_int = None
    if teacher_id and teacher_id.strip():
        try:
            teacher_id_int = int(teacher_id)
        except (ValueError, TypeError):
            teacher_id_int = None
    if student_id and student_id.strip():
        try:
            student_id_int = int(student_id)
        except (ValueError, TypeError):
            student_id_int = None
    if course_id and course_id.strip():
        try:
            course_id_int = int(course_id)
        except (ValueError, TypeError):
            course_id_int = None
    
    # Tarih filtrelerini parse et
    from datetime import date, datetime
    start_date_obj = None
    end_date_obj = None
    if start_date:
        try:
            y, m, d = map(int, start_date.split("-"))
            start_date_obj = date(y, m, d)
        except Exception:
            pass
    if end_date:
        try:
            y, m, d = map(int, end_date.split("-"))
            end_date_obj = date(y, m, d)
        except Exception:
            pass
    
    # #region agent log - Direct DB query before list_all_attendances
    import logging
    # Direct query to check all attendances in DB
    all_attendances_direct = db.scalars(select(models.Attendance)).all()
    logging.warning(f"🔍 DASHBOARD DEBUG: Veritabanında toplam {len(all_attendances_direct)} yoklama kaydı var")
    if len(all_attendances_direct) > 0:
        logging.warning(f"🔍 DASHBOARD DEBUG: İlk 5 yoklama ID: {[a.id for a in all_attendances_direct[:5]]}")
        logging.warning(f"🔍 DASHBOARD DEBUG: Lesson ID'ler: {list(set([a.lesson_id for a in all_attendances_direct[:10]]))}")
        logging.warning(f"🔍 DASHBOARD DEBUG: Student ID'ler: {list(set([a.student_id for a in all_attendances_direct[:10]]))}")
    # #endregion
    
    # DIRECT QUERY: list_all_attendances fonksiyonunu bypass et, direkt sorgu kullan
    # Bu, sorunun kaynağını bulmak için geçici bir çözüm
    import logging
    logging.warning("🔍 Dashboard: list_all_attendances bypass ediliyor, direkt sorgu kullanılıyor!")
    
    # Filtrelerin olup olmadığını kontrol et
    has_filters = any([
        teacher_id_int is not None,
        student_id_int is not None,
        course_id_int is not None,
        status is not None and status.strip(),
        start_date_obj is not None,
        end_date_obj is not None
    ])
    
    # Eğer hiçbir filtre yoksa, boş liste döndür
    if not has_filters:
        attendances = []
        logging.warning("🔍 Dashboard: Hiçbir filtre yok, boş liste döndürülüyor")
    else:
        # Direkt sorgu ile tüm yoklamaları al
        all_attendances_direct = db.scalars(select(models.Attendance)).all()
        logging.warning(f"🔍 Dashboard: Direkt sorgu sonucu: {len(all_attendances_direct)} yoklama")
        
        # Filtreleri manuel uygula
        attendances = list(all_attendances_direct)
        logging.warning(f"🔍 Dashboard: Filtre öncesi: {len(attendances)} yoklama")
        
        # Teacher filter
        if teacher_id_int:
            filtered = []
            for att in attendances:
                lesson = db.get(models.Lesson, att.lesson_id)
                if lesson and lesson.teacher_id == teacher_id_int:
                    filtered.append(att)
            attendances = filtered
        
        # Student filter
        if student_id_int:
            attendances = [a for a in attendances if a.student_id == student_id_int]
        
        # Status filter
        if status:
            attendances = [a for a in attendances if a.status.upper() == status.upper()]
        
        # Course filter
        if course_id_int:
            filtered = []
            for att in attendances:
                lesson = db.get(models.Lesson, att.lesson_id)
                if lesson and lesson.course_id == course_id_int:
                    filtered.append(att)
            attendances = filtered
        
        # Date filters - artık yoklama zamanına (marked_at) göre
        if start_date_obj:
            from datetime import datetime
            start_datetime = datetime.combine(start_date_obj, datetime.min.time())
            attendances = [a for a in attendances if a.marked_at and a.marked_at >= start_datetime]
        
        if end_date_obj:
            from datetime import datetime
            end_datetime = datetime.combine(end_date_obj, datetime.max.time())
            attendances = [a for a in attendances if a.marked_at and a.marked_at <= end_datetime]
        
        # Sort - artık sadece marked_at'e göre (lesson_date kaldırıldı)
        if order_by == "marked_at_desc" or order_by == "lesson_date_desc":
            attendances.sort(key=lambda x: x.marked_at if x.marked_at else datetime.min, reverse=True)
        elif order_by == "marked_at_asc" or order_by == "lesson_date_asc":
            attendances.sort(key=lambda x: x.marked_at if x.marked_at else datetime.min, reverse=False)
        
        # Limit
        attendances = attendances[:200]
        logging.warning(f"🔍 Dashboard: Filtre sonrası: {len(attendances)} yoklama (limit: 200)")
    if len(attendances) > 0:
        logging.warning(f"🔍 Dashboard: İlk 5 yoklama ID: {[a.id for a in attendances[:5]]}")
    
    # Yoklamaları ders ve öğrenci bilgileriyle birlikte hazırla
    # ÖNEMLİ: Tüm yoklamaları göster, lesson/student yoksa bile
    attendances_with_details = []
    orphaned_count = 0
    for att in attendances:
        lesson = db.get(models.Lesson, att.lesson_id)
        student = db.get(models.Student, att.student_id)
        # Lesson veya student yoksa bile yoklamayı göster (sadece uyarı ver)
        if not lesson:
            import logging
            logging.warning(f"⚠️ Yoklama {att.id} için lesson {att.lesson_id} bulunamadı!")
        if not student:
            import logging
            logging.warning(f"⚠️ Yoklama {att.id} için student {att.student_id} bulunamadı!")
        
        teacher = db.get(models.Teacher, lesson.teacher_id) if lesson and lesson.teacher_id else None
        course = db.get(models.Course, lesson.course_id) if lesson and lesson.course_id else None
        attendances_with_details.append({
            "attendance": att,
            "lesson": lesson,  # None olabilir
            "student": student,  # None olabilir
            "teacher": teacher,
            "course": course,
        })
        if not lesson or not student:
            orphaned_count += 1
    
    import logging
    logging.warning(f"🔍 Dashboard: attendances_with_details hazırlandı: {len(attendances_with_details)} kayıt, {orphaned_count} orphaned")
    
    # #region agent log
    import json, os, time
    log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cursor", "debug.log")
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"id": f"log_{int(time.time())}_dashboard_details", "timestamp": int(time.time() * 1000), "location": "main.py:500", "message": "Dashboard attendances with details", "data": {"total_attendances": len(attendances), "with_details": len(attendances_with_details), "orphaned_count": orphaned_count}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "C"}) + "\n")
    except Exception as e:
        import logging
        logging.error(f"Debug log error: {e}")
    # #endregion
    # Puantaj raporunu getir (sadece admin için ve sadece filtreler varsa)
    attendance_report = []
    attendance_totals_by_teacher = {}
    if user.get("role") == "admin" and has_filters:
        attendance_report = crud.get_attendance_report_by_teacher(
            db,
            teacher_id=teacher_id_int,
            student_id=student_id_int,
            course_id=course_id_int,
            start_date=start_date_obj,
            end_date=end_date_obj
        )
        
        # Her öğretmen için toplamları hesapla
        for teacher_report in attendance_report:
            if teacher_report.get("students"):
                totals = {
                    "total_present": sum(s.get("present", 0) for s in teacher_report["students"]),
                    "total_excused_absent": sum(s.get("excused_absent", 0) for s in teacher_report["students"]),
                    "total_telafi": sum(s.get("telafi", 0) for s in teacher_report["students"]),
                    "total_unexcused_absent": sum(s.get("unexcused_absent", 0) for s in teacher_report["students"]),
                    "total_lessons": sum(s.get("total", 0) for s in teacher_report["students"])
                }
                attendance_totals_by_teacher[teacher_report["teacher"].id] = totals
        
        # #region agent log
        import json, os, time
        log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cursor", "debug.log")
        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"id": f"log_{int(time.time())}_dashboard_report", "timestamp": int(time.time() * 1000), "location": "main.py:511", "message": "Dashboard attendance report fetched", "data": {"report_count": len(attendance_report), "teachers_in_report": [r["teacher"].id for r in attendance_report]}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "B"}) + "\n")
        except Exception as e:
            import logging
            logging.error(f"Debug log error: {e}")
        # #endregion
    
    # Tüm öğretmenler için haftalık ders programını hazırla (saat bazlı grid için)
    from datetime import datetime
    weekday_map = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    teachers_schedules = []
    for teacher in teachers:
        lessons_with_students = crud.lessons_with_students_by_teacher(db, teacher.id)
        formatted_lessons = []
        for entry in lessons_with_students:
            lesson = entry["lesson"]
            weekday = weekday_map[lesson.lesson_date.weekday()] if hasattr(lesson.lesson_date, "weekday") else ""
            # Dinamik tarih hesapla (bugünden sonraki ilgili gün)
            current_lesson_date = calculate_next_lesson_date(lesson.lesson_date)
            formatted_lessons.append({
                "weekday": weekday,
                "lesson": lesson,
                "current_lesson_date": current_lesson_date,  # Dinamik hesaplanan tarih
                "students": entry["students"],
            })
        teachers_schedules.append({
            "teacher": teacher,
            "lessons": formatted_lessons
        })
    
    # Ödeme gerekli öğrencileri getir (sadece admin için)
    students_needing_payment = []
    if user.get("role") == "admin":
        students_needing_payment = crud.list_students_needing_payment(db)
    
    context = {
        "request": request,
        "courses": courses,
        "students": students,
        "teachers": teachers,
        "staff_users": staff_users,
        "attendances": attendances_with_details,
        "attendance_report": attendance_report,
        "attendance_totals_by_teacher": attendance_totals_by_teacher,
        "teachers_schedules": teachers_schedules,
        "students_needing_payment": students_needing_payment,
        "user": user,
        "filters": {
            "teacher_id": str(teacher_id_int) if teacher_id_int else "",
            "student_id": str(student_id_int) if student_id_int else "",
            "course_id": str(course_id_int) if course_id_int else "",
            "status": status or "",
            "start_date": start_date or "",
            "end_date": end_date or "",
            "order_by": order_by,
        },
    }
    return templates.TemplateResponse("dashboard.html", context)


@app.get("/dashboard/export/excel")
def export_punctuality_excel(
    request: Request,
    db: Session = Depends(get_db),
    teacher_id: str | None = None,
    student_id: str | None = None,
    course_id: str | None = None,
    status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
):
    """Puantaj tablosunu Excel formatında export eder"""
    user = request.session.get("user")
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Yetki yok")
    
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from datetime import datetime, date
    from io import BytesIO
    
    # Filtreleri parse et
    teacher_id_int = None
    student_id_int = None
    course_id_int = None
    start_date_obj = None
    end_date_obj = None
    
    if teacher_id and teacher_id.strip():
        try:
            teacher_id_int = int(teacher_id)
        except (ValueError, TypeError):
            pass
    if student_id and student_id.strip():
        try:
            student_id_int = int(student_id)
        except (ValueError, TypeError):
            pass
    if course_id and course_id.strip():
        try:
            course_id_int = int(course_id)
        except (ValueError, TypeError):
            pass
    if start_date:
        try:
            y, m, d = map(int, start_date.split("-"))
            start_date_obj = date(y, m, d)
        except Exception:
            pass
    if end_date:
        try:
            y, m, d = map(int, end_date.split("-"))
            end_date_obj = date(y, m, d)
        except Exception:
            pass
    
    # Puantaj raporunu getir
    attendance_report = crud.get_attendance_report_by_teacher(db)
    
    # Filtreleri uygula
    if teacher_id_int:
        attendance_report = [r for r in attendance_report if r["teacher"].id == teacher_id_int]
    
    # Excel workbook oluştur
    wb = Workbook()
    ws = wb.active
    ws.title = "Puantaj Raporu"
    
    # Stil tanımlamaları
    header_font = Font(bold=True, color="FFFFFF", size=12)
    header_fill = PatternFill(start_color="1f2937", end_color="1f2937", fill_type="solid")
    border_style = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    center_alignment = Alignment(horizontal='center', vertical='center')
    
    # Başlık satırı
    row = 1
    ws.merge_cells(f'A{row}:G{row}')
    title_cell = ws[f'A{row}']
    title_cell.value = f"Puantaj Raporu - {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    title_cell.font = Font(bold=True, size=14)
    title_cell.alignment = Alignment(horizontal='center', vertical='center')
    row += 2
    
    # Her öğretmen için ayrı bölüm
    for teacher_report in attendance_report:
        # Öğretmen başlığı
        ws.merge_cells(f'A{row}:G{row}')
        teacher_cell = ws[f'A{row}']
        teacher_cell.value = f"Öğretmen: {teacher_report['teacher'].first_name} {teacher_report['teacher'].last_name}"
        teacher_cell.font = Font(bold=True, size=12, color="001F2937")
        teacher_cell.fill = PatternFill(start_color="E5E7EB", end_color="E5E7EB", fill_type="solid")
        teacher_cell.alignment = Alignment(horizontal='left', vertical='center')
        row += 1
        
        # Öğrenci verilerini filtrele
        students_data = teacher_report['students']
        if student_id_int:
            students_data = [s for s in students_data if s['student'].id == student_id_int]
        if course_id_int:
            # Course filtresi için lesson bilgisi gerekli, şimdilik tüm öğrencileri göster
            pass
        if status:
            # Status filtresi için attendance bilgisi gerekli, şimdilik tüm öğrencileri göster
            pass
        
        if not students_data:
            ws.merge_cells(f'A{row}:G{row}')
            no_data_cell = ws[f'A{row}']
            no_data_cell.value = "Bu öğretmen için filtre kriterlerine uygun veri bulunmuyor."
            no_data_cell.alignment = Alignment(horizontal='center', vertical='center')
            row += 2
            continue
        
        # Tablo başlıkları
        headers = ["Öğrenci", "Geldi", "Haberli Gelmedi", "Telafi", "Habersiz Gelmedi", "Toplam Ders", "Yoklama Tarihleri"]
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=col_idx)
            cell.value = header
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_alignment
            cell.border = border_style
        row += 1
        
        # Öğrenci verileri
        for student_data in students_data:
            # Öğrenci adı
            cell = ws.cell(row=row, column=1)
            cell.value = f"{student_data['student'].first_name} {student_data['student'].last_name}"
            cell.border = border_style
            cell.alignment = Alignment(horizontal='left', vertical='center')
            
            # Geldi
            cell = ws.cell(row=row, column=2)
            cell.value = student_data['present']
            cell.border = border_style
            cell.alignment = center_alignment
            cell.font = Font(color="0010B981", bold=True)  # RGB format
            
            # Haberli Gelmedi
            cell = ws.cell(row=row, column=3)
            cell.value = student_data['excused_absent']
            cell.border = border_style
            cell.alignment = center_alignment
            cell.font = Font(color="00F97316", bold=True)  # RGB format
            
            # Telafi
            cell = ws.cell(row=row, column=4)
            cell.value = student_data['telafi']
            cell.border = border_style
            cell.alignment = center_alignment
            cell.font = Font(color="008B5CF6", bold=True)  # RGB format
            
            # Habersiz Gelmedi
            cell = ws.cell(row=row, column=5)
            cell.value = student_data['unexcused_absent']
            cell.border = border_style
            cell.alignment = center_alignment
            cell.font = Font(color="00EF4444", bold=True)  # RGB format
            
            # Toplam Ders
            cell = ws.cell(row=row, column=6)
            cell.value = student_data['total']
            cell.border = border_style
            cell.alignment = center_alignment
            cell.font = Font(bold=True)
            
            # Yoklama Tarihleri
            cell = ws.cell(row=row, column=7)
            dates = student_data.get('dates', [])
            if dates:
                # Tarihleri sırala ve tekrar edenleri kaldır
                unique_dates = sorted(list(set(dates)))
                cell.value = ', '.join(unique_dates)
            else:
                cell.value = '-'
            cell.border = border_style
            cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
            cell.font = Font(size=10)
            
            row += 1
        
        # Öğretmen bölümü sonrası boş satır
        row += 1
    
    # Sütun genişliklerini ayarla
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 12
    ws.column_dimensions['C'].width = 18
    ws.column_dimensions['D'].width = 12
    ws.column_dimensions['E'].width = 20
    ws.column_dimensions['F'].width = 15
    ws.column_dimensions['G'].width = 50  # Yoklama Tarihleri sütunu için geniş sütun
    
    # Excel dosyasını memory'de oluştur
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    # Dosya adı
    filename = f"puantaj_raporu_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return Response(
        content=output.read(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


# UI: Quick search
@app.get("/ui/search", response_class=HTMLResponse)
def quick_search(request: Request, q: str, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    term = f"%{q.strip()}%"
    s = db.query(models.Student).filter((models.Student.first_name.ilike(term)) | (models.Student.last_name.ilike(term))).limit(20).all()
    t = db.query(models.Teacher).filter((models.Teacher.first_name.ilike(term)) | (models.Teacher.last_name.ilike(term))).limit(20).all()
    c = db.query(models.Course).filter(models.Course.name.ilike(term)).limit(20).all()
    return templates.TemplateResponse("search_results.html", {"request": request, "q": q, "students": s, "teachers": t, "courses": c})


# UI: Teacher panel
@app.get("/ui/teacher", response_class=HTMLResponse)
def teacher_panel(request: Request, selected_teacher_id: int | None = None, start_date: str | None = None, end_date: str | None = None, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login/teacher", status_code=302)
    if user.get("role") != "teacher":
        # Öğretmen harici biri geldi: kendi paneline yönlendir
        if user.get("role") == "admin":
            return RedirectResponse(url="/dashboard", status_code=302)
        elif user.get("role") == "staff":
            return RedirectResponse(url="/ui/staff", status_code=302)
        else:
            return RedirectResponse(url="/login/teacher", status_code=302)
    current_teacher_id = user.get("teacher_id")
    if not current_teacher_id:
        # Öğretmen ID yoksa hata göster
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head><title>Hata - Piarte</title></head>
        <body>
            <h2>Hata</h2>
            <p>Öğretmen bilgisi bulunamadı. Lütfen yönetici ile iletişime geçin.</p>
            <a href="/logout">Çıkış Yap</a>
        </body>
        </html>
        """, status_code=400)
    try:
        # Seçilen öğretmen ID'si yoksa, kendi ID'sini kullan
        display_teacher_id = selected_teacher_id if selected_teacher_id else current_teacher_id
        
        # Tarih filtrelerini parse et
        from datetime import date
        start_date_obj = None
        end_date_obj = None
        if start_date:
            try:
                y, m, d = map(int, start_date.split("-"))
                start_date_obj = date(y, m, d)
            except Exception:
                start_date_obj = None
        if end_date:
            try:
                y, m, d = map(int, end_date.split("-"))
                end_date_obj = date(y, m, d)
            except Exception:
                end_date_obj = None
        
        # Tüm öğretmenleri getir
        all_teachers = crud.list_teachers(db)
        
        # Seçilen öğretmenin derslerini getir
        lessons_with_students = crud.lessons_with_students_by_teacher(db, display_teacher_id)
        from datetime import datetime
        weekday_map = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        formatted_lessons = []
        for entry in lessons_with_students:
            lesson = entry["lesson"]
            weekday = weekday_map[lesson.lesson_date.weekday()] if hasattr(lesson.lesson_date, "weekday") else ""
            # Dinamik tarih hesapla (bugünden sonraki ilgili gün)
            current_lesson_date = calculate_next_lesson_date(lesson.lesson_date)
            formatted_lessons.append({
                "weekday": weekday,
                "lesson": lesson,
                "current_lesson_date": current_lesson_date,  # Dinamik hesaplanan tarih
                "students": entry["students"],
            })
        # Öğretmene atanmış öğrencileri getir
        teacher_students = []
        if current_teacher_id:
            try:
                teacher_students = crud.list_students_by_teacher(db, current_teacher_id)
                # Debug: Eğer öğrenci yoksa, tüm öğrencileri kontrol et
                if not teacher_students:
                    # Tüm öğrencileri getir ve öğretmene atanmış olanları filtrele
                    all_students = crud.list_students(db)
                    for student in all_students:
                        # Öğrencinin bu öğretmene atanıp atanmadığını kontrol et
                        link = db.scalars(
                            select(models.TeacherStudent)
                            .where(
                                models.TeacherStudent.student_id == student.id,
                                models.TeacherStudent.teacher_id == current_teacher_id
                            )
                        ).first()
                        if link:
                            teacher_students.append(student)
            except Exception as e:
                # Hata durumunda boş liste döndür
                import logging
                logging.error(f"Öğrenci listesi hatası: {e}")
                teacher_students = []
        
        # Tüm öğretmenler için haftalık ders programını hazırla (saat bazlı grid için)
        teachers_schedules = []
        for teacher in all_teachers:
            teacher_lessons = crud.lessons_with_students_by_teacher(db, teacher.id)
            teacher_formatted_lessons = []
            for entry in teacher_lessons:
                lesson = entry["lesson"]
                weekday = weekday_map[lesson.lesson_date.weekday()] if hasattr(lesson.lesson_date, "weekday") else ""
                # Dinamik tarih hesapla (bugünden sonraki ilgili gün)
                current_lesson_date = calculate_next_lesson_date(lesson.lesson_date)
                teacher_formatted_lessons.append({
                    "weekday": weekday,
                    "lesson": lesson,
                    "current_lesson_date": current_lesson_date,  # Dinamik hesaplanan tarih
                    "students": entry["students"],
                })
            teachers_schedules.append({
                "teacher": teacher,
                "lessons": teacher_formatted_lessons
            })
        
        # Puantaj raporunu hesapla (sadece kendi öğretmeni için)
        attendance_report = []
        attendance_totals = None
        if current_teacher_id:
            attendance_report = crud.get_attendance_report_by_teacher(
                db,
                teacher_id=current_teacher_id,
                start_date=start_date_obj,
                end_date=end_date_obj
            )
            # Toplamları hesapla
            if attendance_report and len(attendance_report) > 0:
                teacher_report = attendance_report[0]
                if teacher_report.get("students"):
                    totals = {
                        "total_present": sum(s.get("present", 0) for s in teacher_report["students"]),
                        "total_excused_absent": sum(s.get("excused_absent", 0) for s in teacher_report["students"]),
                        "total_telafi": sum(s.get("telafi", 0) for s in teacher_report["students"]),
                        "total_unexcused_absent": sum(s.get("unexcused_absent", 0) for s in teacher_report["students"]),
                        "total_lessons": sum(s.get("total", 0) for s in teacher_report["students"])
                    }
                    attendance_totals = totals
        
        context = {
            "request": request,
            "lessons_with_students": formatted_lessons,
            "teacher_students": teacher_students,
            "teachers_schedules": teachers_schedules,
            "all_teachers": all_teachers,
            "selected_teacher_id": display_teacher_id,
            "current_teacher_id": current_teacher_id,
            "attendance_report": attendance_report,
            "attendance_totals": attendance_totals,
            "start_date": start_date or "",
            "end_date": end_date or "",
        }
        return templates.TemplateResponse("teacher_panel.html", context)
    except Exception as e:
        import logging
        logging.error(f"Teacher panel error: {e}")
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head><title>Hata - Piarte</title></head>
        <body>
            <h2>Öğretmen Paneli Hatası</h2>
            <p>Bir hata oluştu: {str(e)}</p>
            <a href="/logout">Çıkış Yap</a>
        </body>
        </html>
        """, status_code=500)


# UI: Students - create
@app.get("/students/new", response_class=HTMLResponse)
def student_form(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    redirect = redirect_teacher(request.session.get("user"))
    if redirect:
        return redirect
    return templates.TemplateResponse("student_new.html", {"request": request})


@app.post("/students/new")
def student_create(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    date_of_birth: str | None = Form(None),
    parent_name: str | None = Form(None),
    parent_phone: str | None = Form(None),
    address: str | None = Form(None),
    phone_primary: str | None = Form(None),
    phone_secondary: str | None = Form(None),
    db: Session = Depends(get_db),
):
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    redirect = redirect_teacher(request.session.get("user"))
    if redirect:
        return redirect
    dob = None
    if date_of_birth:
        try:
            from datetime import date
            y, m, d = map(int, date_of_birth.split("-"))
            dob = date(y, m, d)
        except Exception:
            dob = None
    payload = schemas.StudentCreate(
        first_name=first_name,
        last_name=last_name,
        date_of_birth=dob,
        parent_name=parent_name,
        parent_phone=parent_phone,
        address=address,
        phone_primary=phone_primary,
        phone_secondary=phone_secondary,
    )
    crud.create_student(db, payload)
    return RedirectResponse(url="/dashboard", status_code=302)


@app.post("/students/{student_id}/update")
def student_update(
    student_id: int,
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    date_of_birth: str | None = Form(None),
    parent_name: str | None = Form(None),
    parent_phone: str | None = Form(None),
    address: str | None = Form(None),
    phone_primary: str | None = Form(None),
    phone_secondary: str | None = Form(None),
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login/admin", status_code=302)
    dob = None
    if date_of_birth:
        try:
            from datetime import date
            y, m, d = map(int, date_of_birth.split("-"))
            dob = date(y, m, d)
        except Exception:
            dob = None
    payload = schemas.StudentUpdate(
        first_name=first_name,
        last_name=last_name,
        date_of_birth=dob,
        parent_name=parent_name or None,
        parent_phone=parent_phone or None,
        address=address or None,
        phone_primary=phone_primary or None,
        phone_secondary=phone_secondary or None,
    )
    crud.update_student(db, student_id, payload)
    return RedirectResponse(url=f"/ui/students/{student_id}", status_code=status.HTTP_303_SEE_OTHER)


# UI: Teachers - quick create via form
@app.post("/teachers/new")
def teacher_create_form(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone: str | None = Form(None),
    email: str | None = Form(None),
    db: Session = Depends(get_db),
):
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    redirect = redirect_teacher(request.session.get("user"))
    if redirect:
        return redirect
    payload = schemas.TeacherCreate(
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        email=email,
    )
    crud.create_teacher(db, payload)
    return RedirectResponse(url="/dashboard", status_code=302)


@app.post("/teachers/{teacher_id}/update")
def teacher_update_form(
    teacher_id: int,
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone: str | None = Form(None),
    email: str | None = Form(None),
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login/admin", status_code=302)
    payload = schemas.TeacherUpdate(
        first_name=first_name,
        last_name=last_name,
        phone=phone or None,
        email=email or None,
    )
    crud.update_teacher(db, teacher_id, payload)
    return RedirectResponse(url=f"/ui/teachers/{teacher_id}", status_code=status.HTTP_303_SEE_OTHER)


# UI: Payments - create
@app.get("/payments/new", response_class=HTMLResponse)
def payment_form(request: Request, db: Session = Depends(get_db), student_id: str | None = None):
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    redirect = redirect_teacher(request.session.get("user"))
    if redirect:
        return redirect
    students = crud.list_students(db)
    selected_student_id = None
    if student_id:
        try:
            selected_student_id = int(student_id)
        except (ValueError, TypeError):
            selected_student_id = None
    return templates.TemplateResponse("payment_new.html", {"request": request, "students": students, "selected_student_id": selected_student_id})


@app.post("/payments/new")
def payment_create(
    request: Request,
    student_id: int = Form(...),
    amount_try: float = Form(...),
    payment_date: str | None = Form(None),
    method: str | None = Form(None),
    note: str | None = Form(None),
    db: Session = Depends(get_db),
):
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    redirect = redirect_teacher(request.session.get("user"))
    if redirect:
        return redirect
    from datetime import date
    pd = None
    if payment_date:
        try:
            y, m, d = map(int, payment_date.split("-"))
            pd = date(y, m, d)
        except Exception:
            pd = None
    payload = schemas.PaymentCreate(
        student_id=student_id,
        amount_try=amount_try,
        payment_date=pd,
        method=method,
        note=note,
    )
    crud.create_payment(db, payload)
    return RedirectResponse(url="/dashboard", status_code=302)


# UI: Lessons - create and attendance
@app.get("/lessons/new", response_class=HTMLResponse)
def lesson_form(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    redirect = redirect_teacher(request.session.get("user"))
    if redirect:
        return redirect
    courses = crud.list_courses(db)
    teachers = crud.list_teachers(db)
    students = crud.list_students(db)
    return templates.TemplateResponse("lesson_new.html", {"request": request, "courses": courses, "teachers": teachers, "students": students})


# UI: Lessons - schedule list
@app.get("/ui/lessons", response_class=HTMLResponse)
def ui_lessons(
    request: Request,
    start: str | None = None,
    end: str | None = None,
    teacher_id: int | None = None,
    course_id: int | None = None,
    db: Session = Depends(get_db),
):
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    redirect = redirect_teacher(request.session.get("user"))
    if redirect:
        return redirect
    from datetime import date
    start_date = None
    end_date = None
    if start:
        try:
            y, m, d = map(int, start.split("-"))
            start_date = date(y, m, d)
        except Exception:
            start_date = None
    if end:
        try:
            y, m, d = map(int, end.split("-"))
            end_date = date(y, m, d)
        except Exception:
            end_date = None
    q = db.query(models.Lesson)
    if start_date:
        q = q.filter(models.Lesson.lesson_date >= start_date)
    if end_date:
        q = q.filter(models.Lesson.lesson_date <= end_date)
    if teacher_id:
        q = q.filter(models.Lesson.teacher_id == teacher_id)
    if course_id:
        q = q.filter(models.Lesson.course_id == course_id)
    lessons = q.order_by(models.Lesson.lesson_date.asc()).all()
    teachers = crud.list_teachers(db)
    courses = crud.list_courses(db)
    return templates.TemplateResponse(
        "lessons_list.html",
        {
            "request": request,
            "lessons": lessons,
            "teachers": teachers,
            "courses": courses,
            "start": start or "",
            "end": end or "",
            "teacher_id": teacher_id or "",
            "course_id": course_id or "",
        },
    )


@app.post("/lessons/new")
def lesson_create(
    request: Request,
    student_id: str = Form(...),
    first_name: str = Form(None),
    last_name: str = Form(None),
    course_id: int = Form(...),
    teacher_id: int = Form(...),
    lesson_date: str = Form(...),
    lesson_weekday: str | None = Form(None),
    start_time: str | None = Form(None),
    end_time: str | None = Form(None),
    description: str | None = Form(None),
    db: Session = Depends(get_db),
):
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    redirect = redirect_teacher(request.session.get("user"))
    if redirect:
        return redirect
    # Eğer yeni öğrenci eklenmişse...
    from datetime import date, time as t
    if not student_id:
        if not first_name or not last_name:
            return RedirectResponse(url="/lessons/new", status_code=302)
        student = schemas.StudentCreate(first_name=first_name, last_name=last_name)
        student_db = crud.create_student(db, student)
        student_id = student_db.id
    else:
        student_id = int(student_id)
    # Dersi oluştur
    y, m, d = map(int, lesson_date.split("-"))
    st = None
    et = None
    if start_time:
        hh, mm = map(int, start_time.split(":"))
        st = t(hh, mm)
    if end_time:
        hh, mm = map(int, end_time.split(":"))
        et = t(hh, mm)
    payload = schemas.LessonCreate(
        course_id=course_id,
        teacher_id=teacher_id,
        lesson_date=date(y, m, d),
        start_time=st,
        end_time=et,
        description=description
    )
    lesson = crud.create_lesson(db, payload)
    if lesson_weekday:
        try:
            requested_day = int(lesson_weekday)
            actual_day = lesson.lesson_date.weekday()
            if requested_day != actual_day:
                from datetime import timedelta
                delta = requested_day - actual_day
                lesson.lesson_date = lesson.lesson_date + timedelta(days=delta)
                db.commit()
                db.refresh(lesson)
        except Exception:
            pass
    # Tüm işlemleri tek bir transaction içinde yap
    try:
        # Öğrenciyi, oluşturulan dersin course'una kaydet (commit yapma)
        crud.enroll_student(db, student_id, course_id, commit=False)
        # Öğrenciyi öğretmene ata (eğer atanmamışsa)
        crud.assign_student_to_teacher(db, teacher_id, student_id)
        # Öğrenciyi bu derse özel olarak ata
        crud.assign_student_to_lesson(db, lesson.id, student_id)
        # Tüm değişiklikleri commit et
        db.commit()
    except Exception as e:
        db.rollback()
        # Eğer tablo yoksa, oluştur ve tekrar dene
        try:
            from .db import Base, engine
            Base.metadata.create_all(bind=engine)
            # Tekrar dene
            crud.enroll_student(db, student_id, course_id, commit=False)
            crud.assign_student_to_teacher(db, teacher_id, student_id)
            crud.assign_student_to_lesson(db, lesson.id, student_id)
            db.commit()
        except Exception as e2:
            # Hata mesajını logla
            import logging
            logging.error(f"Ders öğrenci atama hatası: {e2}")
            db.rollback()
            # Hata olsa bile derse yönlendir (ders oluşturuldu)
    
    # Ders oluşturuldu, dashboard'a yönlendir
    return RedirectResponse(url="/dashboard", status_code=302)


@app.get("/lessons/{lesson_id}/attendance/new", response_class=HTMLResponse)
def attendance_form(lesson_id: int, request: Request, db: Session = Depends(get_db), error: str | None = None):
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    from datetime import date as date_cls
    lesson = db.get(models.Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Ders bulunamadı")
    user = request.session.get("user")
    if user.get("role") == "teacher":
        if lesson.teacher_id != user.get("teacher_id"):
            return RedirectResponse(url="/ui/teacher", status_code=302)
        # Sadece bu derse atanmış öğrencileri getir
        students = crud.list_students_by_lesson(db, lesson_id)
    else:
        # Admin/staff için de sadece bu derse atanmış öğrencileri göster
        students = crud.list_students_by_lesson(db, lesson_id)
    
    # Bu ders için mevcut yoklamaları getir
    existing_attendances = crud.list_attendance_for_lesson(db, lesson_id)
    attendance_map = {att.student_id: att.status for att in existing_attendances}
    
    # Her öğrenci için ödeme durumunu ve mevcut yoklama durumunu kontrol et
    students_with_payment_status = []
    for student in students:
        needs_payment = crud.check_student_payment_status(db, student.id)
        current_status = attendance_map.get(student.id, "")
        students_with_payment_status.append({
            "student": student,
            "needs_payment": needs_payment,
            "current_status": current_status
        })
    
    # Öğretmen için bugünün tarihini, diğerleri için ders tarihini kullan
    if user.get("role") == "teacher":
        default_attendance_date = date_cls.today()
    else:
        default_attendance_date = lesson.lesson_date or date_cls.today()
    
    # Hata mesajını al
    error_message = None
    if error == "no_data" or request.session.get("attendance_errors"):
        error_message = request.session.get("attendance_errors", "Lütfen en az bir öğrenci için durum seçin.")
        request.session.pop("attendance_errors", None)
    
    return templates.TemplateResponse(
        "attendance_new.html",
        {
            "request": request,
            "lesson": lesson,
            "students_with_status": students_with_payment_status,
            "attendance_date": default_attendance_date.isoformat(),
            "error_message": error_message,
        },
    )


@app.post("/lessons/{lesson_id}/attendance/new")
async def attendance_create(lesson_id: int, request: Request, db: Session = Depends(get_db)):
    # #region agent log
    import json, os, time
    log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cursor", "debug.log")
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"id": f"log_{int(time.time())}_entry", "timestamp": int(time.time() * 1000), "location": "main.py:1009", "message": "attendance_create endpoint called", "data": {"lesson_id": lesson_id}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
    except Exception as e:
        import logging
        logging.error(f"Debug log error: {e}")
    # #endregion
    
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    user = request.session.get("user")
    lesson = db.get(models.Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Ders bulunamadı")
    allowed_student_ids = None
    if user.get("role") == "teacher":
        if lesson.teacher_id != user.get("teacher_id"):
            return RedirectResponse(url="/ui/teacher", status_code=302)
        # Sadece bu derse atanmış öğrencileri kontrol et
        lesson_students = crud.list_students_by_lesson(db, lesson_id)
        allowed_student_ids = {s.id for s in lesson_students}
    else:
        # Admin/staff için de sadece bu derse atanmış öğrencileri kontrol et
        lesson_students = crud.list_students_by_lesson(db, lesson_id)
        allowed_student_ids = {s.id for s in lesson_students}
    form = await request.form()
    import logging
    logging.warning(f"🔍 FORM DEBUG: Form alındı, toplam {len(form)} field var")
    logging.warning(f"🔍 FORM DEBUG: Form keys: {list(form.keys())}")
    
    attendance_date_raw = form.get("attendance_date")
    marked_at_dt = None
    from datetime import date as date_cls, datetime, time as time_cls
    
    # Öğretmen için tarih kontrolü
    if user.get("role") == "teacher":
        # Önce telafi durumu var mı kontrol et
        has_telafi = False
        for key, value in form.items():
            if key.startswith("status_") and value.strip().upper() == "TELAFI":
                has_telafi = True
                break
        
        # Telafi yoksa bugünün tarihini kullan
        if not has_telafi:
            today = date_cls.today()
            base_time = lesson.start_time or time_cls(hour=12, minute=0)
            if not isinstance(base_time, time_cls):
                base_time = time_cls(hour=12, minute=0)
            marked_at_dt = datetime.combine(today, base_time)
        else:
            # Telafi varsa seçilen tarihi kullan, yoksa bugünün tarihini kullan
            if attendance_date_raw and attendance_date_raw.strip():
                try:
                    year, month, day = map(int, attendance_date_raw.split("-"))
                    chosen_date = date_cls(year, month, day)
                    base_time = lesson.start_time or time_cls(hour=12, minute=0)
                    if not isinstance(base_time, time_cls):
                        base_time = time_cls(hour=12, minute=0)
                    marked_at_dt = datetime.combine(chosen_date, base_time)
                except Exception:
                    # Hata durumunda bugünün tarihini kullan
                    today = date_cls.today()
                    base_time = lesson.start_time or time_cls(hour=12, minute=0)
                    if not isinstance(base_time, time_cls):
                        base_time = time_cls(hour=12, minute=0)
                    marked_at_dt = datetime.combine(today, base_time)
            else:
                # Tarih gönderilmemişse (disabled input) bugünün tarihini kullan
                today = date_cls.today()
                base_time = lesson.start_time or time_cls(hour=12, minute=0)
                if not isinstance(base_time, time_cls):
                    base_time = time_cls(hour=12, minute=0)
                marked_at_dt = datetime.combine(today, base_time)
    elif attendance_date_raw:
        # Admin/staff için normal tarih seçimi
        try:
            year, month, day = map(int, attendance_date_raw.split("-"))
            chosen_date = date_cls(year, month, day)
            base_time = lesson.start_time or time_cls(hour=12, minute=0)
            if not isinstance(base_time, time_cls):
                base_time = time_cls(hour=12, minute=0)
            marked_at_dt = datetime.combine(chosen_date, base_time)
        except Exception:
            marked_at_dt = None
    
    # Expect fields like status_<student_id> = PRESENT|UNEXCUSED_ABSENT|EXCUSED_ABSENT|TELAFI
    # ÖNEMLİ: Her öğrenci için ayrı ayrı status değeri alınmalı
    to_create = []
    
    # Önce tüm form değerlerini logla
    logging.warning(f"🔍 FORM DEBUG: === FORM VERİLERİ ===")
    logging.warning(f"🔍 FORM DEBUG: Ders ID: {lesson_id}")
    logging.warning(f"🔍 FORM DEBUG: Allowed student IDs: {allowed_student_ids}")
    status_fields = []
    for key, value in form.items():
        if key.startswith("status_"):
            status_fields.append(f"{key}={value}")
            logging.warning(f"🔍 FORM DEBUG:   {key} = '{value}'")
    logging.warning(f"🔍 FORM DEBUG: Toplam {len(status_fields)} status field bulundu: {status_fields}")
    
    # Her öğrenci için status değerini al
    for key, value in form.items():
        if not key.startswith("status_"):
            continue
        try:
            sid = int(key.split("_", 1)[1])
        except Exception:
            logging.warning(f"Geçersiz status key: {key}")
            continue
        if allowed_student_ids is not None and sid not in allowed_student_ids:
            logging.warning(f"🔍 FORM DEBUG: Öğrenci {sid} bu derse atanmamış (allowed: {allowed_student_ids}), atlanıyor")
            continue
        
        # Form'dan gelen değeri al - DEĞİŞTİRME, OLDUĞU GİBİ KULLAN
        status_raw = (value or "").strip()
        
        # Boş değerleri atla
        if not status_raw:
            logging.warning(f"🔍 FORM DEBUG: Öğrenci {sid}: Boş değer, atlanıyor")
            continue
        
        # Status değerini büyük harfe çevir
        status = status_raw.upper()
        
        # Eski ABSENT değerlerini UNEXCUSED_ABSENT'e çevir (geriye dönük uyumluluk)
        if status == "ABSENT":
            status = "UNEXCUSED_ABSENT"
        
        # Eski LATE değerlerini TELAFI'ye çevir (geriye dönük uyumluluk)
        if status == "LATE":
            status = "TELAFI"
        
        # Geçerli status değerlerini kontrol et
        valid_statuses = {"PRESENT", "UNEXCUSED_ABSENT", "EXCUSED_ABSENT", "TELAFI"}
        if status not in valid_statuses:
            logging.error(f"❌ Öğrenci {sid}: Geçersiz durum '{status}' (ham: '{value}')")
            continue
        
        # Status değerini doğrulayarak ekle
        status_map = {
            "PRESENT": "Geldi",
            "EXCUSED_ABSENT": "Haberli Gelmedi",
            "TELAFI": "Telafi",
            "UNEXCUSED_ABSENT": "Habersiz Gelmedi"
        }
        import logging
        logging.warning(f"✅ YOKLAMA KAYDI: Öğrenci {sid}, Ders {lesson_id}, Durum: {status} ({status_map.get(status, 'Bilinmeyen')})")
        
        to_create.append(
            schemas.AttendanceCreate(
                lesson_id=lesson_id,
                student_id=sid,
                status=status,  # DOĞRUDAN status değerini kullan
                marked_at=marked_at_dt,
            )
        )
    success_count = 0
    error_count = 0
    errors = []
    
    # Debug: Gönderilen yoklama verilerini logla
    logging.info(f"=== YOKLAMA KAYIT İŞLEMİ ===")
    logging.info(f"Toplam {len(to_create)} kayıt işlenecek")
    for item in to_create:
        logging.info(f"  Öğrenci {item.student_id} -> Durum: {item.status}")
    
    # #region agent log - to_create listesi kontrolü
    import json, os, time
    log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cursor", "debug.log")
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"id": f"log_{int(time.time())}_to_create", "timestamp": int(time.time() * 1000), "location": "main.py:1195", "message": "to_create list before processing", "data": {"count": len(to_create), "items": [{"student_id": item.student_id, "lesson_id": item.lesson_id, "status": item.status} for item in to_create]}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
    except Exception as e:
        import logging
        logging.error(f"Debug log error: {e}")
    # #endregion
    
    # ÖNEMLİ: Her kaydı ayrı ayrı commit et - daha güvenli
    # Böylece bir kayıt başarısız olsa bile diğerleri kaydedilir
    import logging
    import traceback
    from sqlalchemy import select
    
    logging.info(f"=== YOKLAMA KAYIT İŞLEMİ BAŞLADI ===")
    logging.info(f"Toplam {len(to_create)} kayıt işlenecek")
    
    # Eğer to_create boşsa, hata ver
    if len(to_create) == 0:
        logging.error("❌ HATA: to_create listesi boş! Form verileri parse edilemedi!")
        logging.error(f"❌ HATA: Form'da {len(status_fields)} status field var ama hepsi boş!")
        logging.error(f"❌ HATA: Derse atanmış öğrenci sayısı: {len(lesson_students) if 'lesson_students' in locals() else 0}")
        # Eğer hiç öğrenci yoksa farklı mesaj göster
        if len(lesson_students) == 0:
            request.session["attendance_errors"] = "Bu derse henüz öğrenci atanmamış. Lütfen önce öğrenci atayın."
        else:
            request.session["attendance_errors"] = "Yoklama verisi bulunamadı. Lütfen en az bir öğrenci için durum seçin (Geldi, Haberli Gelmedi, Telafi, veya Habersiz Gelmedi)."
        # Hata mesajı ile birlikte form sayfasına geri dön
        return RedirectResponse(url=f"/lessons/{lesson_id}/attendance/new?error=no_data", status_code=302)
    
    for item in to_create:
        try:
            logging.info(f"[{item.student_id}] Kaydediliyor: Durum='{item.status}', Ders={item.lesson_id}")
            
            # #region agent log
            import json, os, time
            log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cursor", "debug.log")
            try:
                lesson_check = db.get(models.Lesson, item.lesson_id)
                student_check = db.get(models.Student, item.student_id)
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"id": f"log_{int(time.time())}_{item.student_id}_precheck", "timestamp": int(time.time() * 1000), "location": "main.py:1158", "message": "Pre-check before saving attendance", "data": {"student_id": item.student_id, "lesson_id": item.lesson_id, "lesson_exists": lesson_check is not None, "student_exists": student_check is not None}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "C"}) + "\n")
            except Exception as e:
                import logging
                logging.error(f"Debug log error: {e}")
            # #endregion
            
            # Her yoklama ayrı bir kayıt olarak oluşturulur - mevcut kayıt kontrolü yok
            from datetime import datetime
            import logging
            
            attendance = models.Attendance(
                lesson_id=item.lesson_id,
                student_id=item.student_id,
                status=str(item.status).strip().upper(),
                marked_at=item.marked_at or datetime.utcnow()
            )
            db.add(attendance)
            logging.warning(f"➕ [{item.student_id}] YENİ yoklama kaydı oluşturuluyor: Ders={item.lesson_id}, Durum='{attendance.status}'")
            
            # NOT: Yoklama alındığında LessonStudent ilişkisi oluşturulmaz
            # LessonStudent ilişkisi sadece öğrenci derse kayıt yapıldığında oluşturulur
            # Yoklama almak için öğrencinin derse kayıtlı olması gerekir
            
            # #region agent log
            import json, os, time
            log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cursor", "debug.log")
            try:
                os.makedirs(os.path.dirname(log_path), exist_ok=True)
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"id": f"log_{int(time.time())}_{item.student_id}_create", "timestamp": int(time.time() * 1000), "location": "main.py:attendance_create", "message": "New attendance record created", "data": {"student_id": item.student_id, "lesson_id": item.lesson_id, "status": attendance.status}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
            except Exception as e:
                logging.error(f"Debug log error: {e}")
            # #endregion
            
            # Hemen commit et - exception handling ile
            try:
                db.commit()
                # Refresh yap
                db.refresh(attendance)
                logging.info(f"[{item.student_id}] ✅ COMMIT BAŞARILI")
            except Exception as commit_error:
                db.rollback()
                error_count += 1
                errors.append(f"Commit hatası (öğrenci {item.student_id}): {commit_error}")
                logging.error(f"[{item.student_id}] ❌ COMMIT HATASI: {commit_error}")
                logging.error(traceback.format_exc())
                continue
            
            # #region agent log
            import json, os, time
            log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cursor", "debug.log")
            try:
                os.makedirs(os.path.dirname(log_path), exist_ok=True)
                attendance_id = attendance.id if 'attendance' in locals() else None
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"id": f"log_{int(time.time())}_{item.student_id}_commit", "timestamp": int(time.time() * 1000), "location": "main.py:1322", "message": "Attendance commit successful", "data": {"student_id": item.student_id, "lesson_id": item.lesson_id, "status": item.status, "attendance_id": attendance_id}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
            except Exception as e:
                import logging
                logging.error(f"Debug log error: {e}")
            # #endregion
            
            # Doğrula - YENİ SESSION ile (commit sonrası)
            db.flush()  # Önce flush yap
            saved = db.scalars(
                select(models.Attendance).where(
                    models.Attendance.lesson_id == item.lesson_id,
                    models.Attendance.student_id == item.student_id
                )
            ).first()
            
            # #region agent log
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"id": f"log_{int(time.time())}_{item.student_id}_verify", "timestamp": int(time.time() * 1000), "location": "main.py:1348", "message": "Attendance verification query", "data": {"student_id": item.student_id, "lesson_id": item.lesson_id, "found": saved is not None, "saved_id": saved.id if saved else None, "saved_status": saved.status if saved else None}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
            except Exception as e:
                import logging
                logging.error(f"Debug log error: {e}")
            # #endregion
            
            if saved:
                success_count += 1
                logging.info(f"[{item.student_id}] ✅ DOĞRULAMA BAŞARILI - ID: {saved.id}, Durum: {saved.status}")
            else:
                error_count += 1
                logging.error(f"[{item.student_id}] ❌ DOĞRULAMA BAŞARISIZ - VERİTABANINDA BULUNAMADI!")
                errors.append(f"Yoklama doğrulanamadı: {item.student_id}")
                
        except Exception as e:
            error_count += 1
            errors.append(f"Yoklama kayıt hatası (öğrenci {item.student_id}): {e}")
            logging.error(f"[{item.student_id}] ❌ HATA: {e}")
            logging.error(traceback.format_exc())
            try:
                db.rollback()
            except:
                pass
            continue
    
    logging.info(f"=== YOKLAMA KAYIT İŞLEMİ TAMAMLANDI ===")
    logging.info(f"Başarılı: {success_count}, Hatalı: {error_count}")
    
    # #region agent log - Final verification: Check all attendances in DB
    import json, os, time
    log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cursor", "debug.log")
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        # Final check: Get all attendances from DB to verify they were saved
        all_attendances_final = db.scalars(select(models.Attendance)).all()
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"id": f"log_{int(time.time())}_final_check", "timestamp": int(time.time() * 1000), "location": "main.py:1321", "message": "Final check - all attendances in DB after save", "data": {"total_count": len(all_attendances_final), "attendance_ids": [a.id for a in all_attendances_final], "lesson_ids": list(set([a.lesson_id for a in all_attendances_final])), "success_count": success_count, "error_count": error_count}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
    except Exception as e:
        import logging
        logging.error(f"Debug log error: {e}")
    # #endregion
    
    # Başarılı kayıt sayısını session'a kaydet (isteğe bağlı)
    if success_count > 0:
        request.session["attendance_success"] = success_count
    if error_count > 0:
        request.session["attendance_errors"] = error_count
    
    # Role'e göre yönlendir
    user = request.session.get("user")
    if user and user.get("role") == "teacher":
        return RedirectResponse(url="/ui/teacher", status_code=302)
    return RedirectResponse(url="/dashboard", status_code=302)


@app.post("/attendances/{attendance_id}/delete")
def delete_attendance_endpoint(
	attendance_id: int,
	request: Request,
	db: Session = Depends(get_db),
):
	"""Tek bir yoklama kaydını sil (sadece admin)"""
	if not request.session.get("user"):
		return RedirectResponse(url="/", status_code=302)
	user = request.session.get("user")
	if user.get("role") != "admin":
		raise HTTPException(status_code=403, detail="Sadece admin bu işlemi yapabilir")
	
	try:
		attendance = crud.delete_attendance(db, attendance_id)
		if attendance:
			import logging
			logging.warning(f"Yoklama kaydı silindi: ID={attendance_id}, Öğrenci={attendance.student_id}, Ders={attendance.lesson_id}")
			request.session["delete_attendance_success"] = "Yoklama kaydı başarıyla silindi"
		else:
			request.session["delete_attendance_error"] = "Yoklama kaydı bulunamadı"
	except Exception as e:
		import logging
		import traceback
		logging.error(f"Yoklama kaydı silinirken hata: {e}")
		logging.error(traceback.format_exc())
		request.session["delete_attendance_error"] = str(e)
	
	# Filtreleri koruyarak dashboard'a yönlendir
	from urllib.parse import urlencode
	params = {}
	if request.query_params.get("teacher_id"):
		params["teacher_id"] = request.query_params.get("teacher_id")
	if request.query_params.get("student_id"):
		params["student_id"] = request.query_params.get("student_id")
	if request.query_params.get("course_id"):
		params["course_id"] = request.query_params.get("course_id")
	if request.query_params.get("status"):
		params["status"] = request.query_params.get("status")
	if request.query_params.get("start_date"):
		params["start_date"] = request.query_params.get("start_date")
	if request.query_params.get("end_date"):
		params["end_date"] = request.query_params.get("end_date")
	if request.query_params.get("order_by"):
		params["order_by"] = request.query_params.get("order_by")
	
	redirect_url = "/dashboard"
	if params:
		redirect_url += "?" + urlencode(params)
	
	return RedirectResponse(url=redirect_url, status_code=302)


@app.get("/attendances/{attendance_id}/edit", response_class=HTMLResponse)
def edit_attendance_form(
	attendance_id: int,
	request: Request,
	db: Session = Depends(get_db),
):
	"""Yoklama düzenleme formu (staff için)"""
	user = request.session.get("user")
	if not user or user.get("role") not in ["admin", "staff"]:
		return RedirectResponse(url="/", status_code=302)
	
	attendance = db.get(models.Attendance, attendance_id)
	if not attendance:
		request.session["error"] = "Yoklama kaydı bulunamadı"
		return RedirectResponse(url="/ui/staff", status_code=302)
	
	lesson = db.get(models.Lesson, attendance.lesson_id)
	student = db.get(models.Student, attendance.student_id)
	teacher = db.get(models.Teacher, lesson.teacher_id) if lesson and lesson.teacher_id else None
	course = db.get(models.Course, lesson.course_id) if lesson and lesson.course_id else None
	
	return templates.TemplateResponse("attendance_edit.html", {
		"request": request,
		"attendance": attendance,
		"lesson": lesson,
		"student": student,
		"teacher": teacher,
		"course": course,
	})


@app.post("/attendances/{attendance_id}/edit")
def update_attendance_endpoint(
	attendance_id: int,
	request: Request,
	status: str = Form(...),
	marked_at_date: str = Form(...),
	marked_at_time: str | None = Form(None),
	note: str | None = Form(None),
	db: Session = Depends(get_db),
):
	"""Yoklama kaydını güncelle (staff için)"""
	user = request.session.get("user")
	if not user or user.get("role") not in ["admin", "staff"]:
		return RedirectResponse(url="/", status_code=302)
	
	try:
		from datetime import datetime
		
		# Tarih ve saat bilgisini birleştir
		marked_at_datetime = None
		if marked_at_time:
			try:
				hour, minute = map(int, marked_at_time.split(":"))
				marked_at_datetime = datetime.combine(
					datetime.strptime(marked_at_date, "%Y-%m-%d").date(),
					datetime.min.time().replace(hour=hour, minute=minute)
				)
			except (ValueError, AttributeError):
				marked_at_datetime = datetime.combine(
					datetime.strptime(marked_at_date, "%Y-%m-%d").date(),
					datetime.min.time()
				)
		else:
			marked_at_datetime = datetime.combine(
				datetime.strptime(marked_at_date, "%Y-%m-%d").date(),
				datetime.min.time()
			)
		
		# Yoklama kaydını güncelle
		updated_attendance = crud.update_attendance(
			db,
			attendance_id=attendance_id,
			status=status,
			marked_at=marked_at_datetime,
			note=note
		)
		
		if updated_attendance:
			request.session["success"] = "Yoklama kaydı başarıyla güncellendi"
		else:
			request.session["error"] = "Yoklama kaydı bulunamadı"
	except Exception as e:
		import logging
		import traceback
		logging.error(f"Yoklama güncellenirken hata: {e}")
		logging.error(traceback.format_exc())
		request.session["error"] = f"Yoklama güncellenirken hata oluştu: {str(e)}"
	
	return RedirectResponse(url="/ui/staff", status_code=302)


@app.get("/admin/clear-all-attendances")
@app.post("/admin/clear-all-attendances")
def clear_all_attendances(request: Request, db: Session = Depends(get_db)):
	"""Tüm yoklama kayıtlarını sil (sadece admin)"""
	if not request.session.get("user"):
		return RedirectResponse(url="/", status_code=302)
	user = request.session.get("user")
	if user.get("role") != "admin":
		raise HTTPException(status_code=403, detail="Sadece admin bu işlemi yapabilir")
	
	try:
		count = crud.delete_all_attendances(db)
		import logging
		logging.warning(f"Tüm yoklama kayıtları silindi: {count} kayıt")
		request.session["clear_attendances_success"] = f"{count} yoklama kaydı silindi"
		return RedirectResponse(url="/dashboard", status_code=302)
	except Exception as e:
		import logging
		import traceback
		logging.error(f"Yoklama kayıtları silinirken hata: {e}")
		logging.error(traceback.format_exc())
		request.session["clear_attendances_error"] = str(e)
		return RedirectResponse(url="/dashboard", status_code=302)


# UI: Enrollment - create
@app.get("/enrollments/new", response_class=HTMLResponse)
def enrollment_form(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    redirect = redirect_teacher(request.session.get("user"))
    if redirect:
        return redirect
    students = crud.list_students(db)
    courses = crud.list_courses(db)
    return templates.TemplateResponse("enrollment_new.html", {"request": request, "students": students, "courses": courses})


@app.post("/enrollments/new")
def enrollment_create(request: Request, student_id: int = Form(...), course_id: int = Form(...), db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    redirect = redirect_teacher(request.session.get("user"))
    if redirect:
        return redirect
    try:
        crud.enroll_student(db, student_id, course_id)
    except Exception:
        pass
    return RedirectResponse(url="/dashboard", status_code=302)


# Students
@app.post("/students", response_model=schemas.StudentOut)
def create_student(payload: schemas.StudentCreate, db: Session = Depends(get_db)):
	return crud.create_student(db, payload)


@app.get("/students", response_model=list[schemas.StudentOut])
def list_students(db: Session = Depends(get_db)):
	return crud.list_students(db)


@app.get("/api/students/search")
def search_students(q: str = None, db: Session = Depends(get_db)):
	"""Öğrenci arama API endpoint'i - autocomplete için"""
	if not q or len(q.strip()) < 3:
		return []
	search_term = f"%{q.strip()}%"
	students = db.query(models.Student).filter(
		(models.Student.first_name.ilike(search_term)) | 
		(models.Student.last_name.ilike(search_term))
	).limit(10).all()
	return [
		{
			"id": s.id,
			"first_name": s.first_name,
			"last_name": s.last_name,
			"full_name": f"{s.first_name} {s.last_name}",
			"phone": s.phone_primary or s.phone_secondary or None,
			"type": "student"
		}
		for s in students
	]


@app.get("/api/teachers/search")
def search_teachers(q: str = None, db: Session = Depends(get_db)):
	"""Öğretmen arama API endpoint'i - autocomplete için"""
	if not q or len(q.strip()) < 3:
		return []
	search_term = f"%{q.strip()}%"
	teachers = db.query(models.Teacher).filter(
		(models.Teacher.first_name.ilike(search_term)) | 
		(models.Teacher.last_name.ilike(search_term))
	).limit(10).all()
	return [
		{
			"id": t.id,
			"first_name": t.first_name,
			"last_name": t.last_name,
			"full_name": f"{t.first_name} {t.last_name}",
			"type": "teacher"
		}
		for t in teachers
	]


@app.get("/api/courses/search")
def search_courses(q: str = None, db: Session = Depends(get_db)):
	"""Kurs arama API endpoint'i - autocomplete için"""
	if not q or len(q.strip()) < 3:
		return []
	search_term = f"%{q.strip()}%"
	courses = db.query(models.Course).filter(
		models.Course.name.ilike(search_term)
	).limit(10).all()
	return [
		{
			"id": c.id,
			"name": c.name,
			"type": "course"
		}
		for c in courses
	]


@app.get("/api/search/all")
def search_all(q: str = None, db: Session = Depends(get_db)):
	"""Tüm türlerde arama API endpoint'i - autocomplete için (öğrenci, öğretmen, kurs)"""
	if not q or len(q.strip()) < 3:
		return []
	search_term = f"%{q.strip()}%"
	results = []
	
	# Öğrenciler
	students = db.query(models.Student).filter(
		(models.Student.first_name.ilike(search_term)) | 
		(models.Student.last_name.ilike(search_term))
	).limit(5).all()
	for s in students:
		results.append({
			"id": s.id,
			"name": f"{s.first_name} {s.last_name}",
			"type": "student",
			"url": f"/ui/students/{s.id}"
		})
	
	# Öğretmenler
	teachers = db.query(models.Teacher).filter(
		(models.Teacher.first_name.ilike(search_term)) | 
		(models.Teacher.last_name.ilike(search_term))
	).limit(5).all()
	for t in teachers:
		results.append({
			"id": t.id,
			"name": f"{t.first_name} {t.last_name}",
			"type": "teacher",
			"url": f"/ui/teachers/{t.id}"
		})
	
	# Kurslar
	courses = db.query(models.Course).filter(
		models.Course.name.ilike(search_term)
	).limit(5).all()
	for c in courses:
		results.append({
			"id": c.id,
			"name": c.name,
			"type": "course",
			"url": f"/ui/courses"
		})
	
	return results


@app.patch("/students/{student_id}", response_model=schemas.StudentOut)
def update_student(student_id: int, payload: schemas.StudentUpdate, db: Session = Depends(get_db)):
	student = crud.update_student(db, student_id, payload)
	if not student:
		raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")
	return student


# Teachers
@app.post("/teachers", response_model=schemas.TeacherOut)
def create_teacher(payload: schemas.TeacherCreate, db: Session = Depends(get_db)):
	return crud.create_teacher(db, payload)


@app.get("/teachers", response_model=list[schemas.TeacherOut])
def list_teachers(db: Session = Depends(get_db)):
	return crud.list_teachers(db)


# Courses
@app.get("/courses", response_model=list[schemas.CourseOut])
def list_courses(db: Session = Depends(get_db)):
	return crud.list_courses(db)


# UI: Courses - list
@app.get("/ui/courses", response_class=HTMLResponse)
def ui_courses(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    if request.session.get("user").get("role") == "teacher":
        return RedirectResponse(url="/ui/teacher", status_code=302)
    courses = crud.list_courses(db)
    return templates.TemplateResponse("courses_list.html", {"request": request, "courses": courses})


# UI: Courses - create form
@app.get("/courses/new", response_class=HTMLResponse)
def course_form(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    redirect = redirect_teacher(request.session.get("user"))
    if redirect:
        return redirect
    return templates.TemplateResponse("course_new.html", {"request": request})


# UI: Courses - create
@app.post("/courses/new")
def course_create(
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db),
):
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    redirect = redirect_teacher(request.session.get("user"))
    if redirect:
        return redirect
    payload = schemas.CourseCreate(name=name)
    try:
        crud.create_course_from_schema(db, payload)
    except Exception:
        # Kurs adı zaten varsa hata ver
        pass
    return RedirectResponse(url="/dashboard", status_code=302)


# UI: Courses - update form
@app.get("/courses/{course_id}/edit", response_class=HTMLResponse)
def course_edit_form(course_id: int, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    redirect = redirect_teacher(request.session.get("user"))
    if redirect:
        return redirect
    course = crud.get_course(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Kurs bulunamadı")
    return templates.TemplateResponse("course_edit.html", {"request": request, "course": course})


# UI: Courses - update
@app.post("/courses/{course_id}/update")
def course_update(
    course_id: int,
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login/admin", status_code=302)
    payload = schemas.CourseUpdate(name=name)
    crud.update_course(db, course_id, payload)
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


# UI: Courses - delete
@app.post("/courses/{course_id}/delete")
def course_delete(course_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login/admin", status_code=status.HTTP_303_SEE_OTHER)
    crud.delete_course(db, course_id)
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


# Enrollment
@app.post("/enrollments")
def enroll_student(payload: schemas.EnrollmentCreate, db: Session = Depends(get_db)):
	return crud.enroll_student(db, payload.student_id, payload.course_id)


# Lessons
@app.post("/lessons", response_model=schemas.LessonOut)
def create_lesson(payload: schemas.LessonCreate, db: Session = Depends(get_db)):
	return crud.create_lesson(db, payload)


@app.get("/teachers/{teacher_id}/lessons", response_model=list[schemas.LessonOut])
def lessons_by_teacher(teacher_id: int, db: Session = Depends(get_db)):
	return crud.list_lessons_by_teacher(db, teacher_id)


# UI: Lessons - edit form
@app.get("/lessons/{lesson_id}/edit", response_class=HTMLResponse)
def lesson_edit_form(lesson_id: int, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    user = request.session.get("user")
    if user.get("role") != "admin":
        return RedirectResponse(url="/login/admin", status_code=302)
    lesson = crud.get_lesson(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Ders bulunamadı")
    courses = crud.list_courses(db)
    teachers = crud.list_teachers(db)
    return templates.TemplateResponse("lesson_edit.html", {"request": request, "lesson": lesson, "courses": courses, "teachers": teachers})


# UI: Lessons - update
@app.post("/lessons/{lesson_id}/update")
def lesson_update(
    lesson_id: int,
    request: Request,
    course_id: int = Form(...),
    teacher_id: int = Form(...),
    lesson_date: str = Form(...),
    start_time: str | None = Form(None),
    end_time: str | None = Form(None),
    description: str | None = Form(None),
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login/admin", status_code=302)
    from datetime import date, time as t
    y, m, d = map(int, lesson_date.split("-"))
    st = None
    et = None
    if start_time:
        try:
            hh, mm = map(int, start_time.split(":"))
            st = t(hh, mm)
        except Exception:
            st = None
    if end_time:
        try:
            hh, mm = map(int, end_time.split(":"))
            et = t(hh, mm)
        except Exception:
            et = None
    payload = schemas.LessonUpdate(
        course_id=course_id,
        teacher_id=teacher_id,
        lesson_date=date(y, m, d),
        start_time=st,
        end_time=et,
        description=description
    )
    lesson = crud.update_lesson(db, lesson_id, payload)
    if not lesson:
        raise HTTPException(status_code=404, detail="Ders bulunamadı")
    # Öğretmen detay sayfasına yönlendir
    return RedirectResponse(url=f"/ui/teachers/{teacher_id}", status_code=status.HTTP_303_SEE_OTHER)


# UI: Lessons - add student form
@app.get("/lessons/{lesson_id}/add-student", response_class=HTMLResponse)
def lesson_add_student_form(lesson_id: int, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    user = request.session.get("user")
    if user.get("role") not in ["admin", "staff"]:
        return RedirectResponse(url="/login/admin", status_code=302)
    lesson = crud.get_lesson(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Ders bulunamadı")
    # Derse atanmamış öğrencileri getir (course'a kayıtlı ama derse atanmamış)
    enrolled_students = db.scalars(
        select(models.Student)
        .join(models.Enrollment, models.Enrollment.student_id == models.Student.id)
        .where(models.Enrollment.course_id == lesson.course_id)
    ).all()
    assigned_student_ids = {s.id for s in crud.list_students_by_lesson(db, lesson_id)}
    available_students = [s for s in enrolled_students if s.id not in assigned_student_ids]
    # Tüm öğrencileri de seçenek olarak ekle
    all_students = crud.list_students(db)
    return templates.TemplateResponse("lesson_add_student.html", {
        "request": request,
        "lesson": lesson,
        "available_students": available_students,
        "all_students": all_students
    })


# UI: Lessons - add student
@app.post("/lessons/{lesson_id}/add-student")
def lesson_add_student(lesson_id: int, request: Request, student_id: int = Form(...), db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user or user.get("role") not in ["admin", "staff"]:
        return RedirectResponse(url="/login/admin", status_code=302)
    lesson = crud.get_lesson(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Ders bulunamadı")
    # Öğrenciyi derse ata
    crud.assign_student_to_lesson(db, lesson_id, student_id)
    # Öğrenciyi course'a kaydet (eğer kayıtlı değilse)
    try:
        crud.enroll_student(db, student_id, lesson.course_id)
    except Exception:
        pass  # Zaten kayıtlı olabilir
    # Öğrenciyi öğretmene ata (eğer atanmamışsa)
    crud.assign_student_to_teacher(db, lesson.teacher_id, student_id)
    db.commit()
    return RedirectResponse(url=f"/ui/teachers/{lesson.teacher_id}", status_code=status.HTTP_303_SEE_OTHER)


# UI: Lessons - delete
@app.post("/lessons/{lesson_id}/delete")
def lesson_delete(lesson_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login/admin", status_code=status.HTTP_303_SEE_OTHER)
    lesson = crud.get_lesson(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Ders bulunamadı")
    teacher_id = lesson.teacher_id
    crud.delete_lesson(db, lesson_id)
    return RedirectResponse(url=f"/ui/teachers/{teacher_id}", status_code=status.HTTP_303_SEE_OTHER)


# Attendance
@app.post("/attendance", response_model=schemas.AttendanceOut)
def mark_attendance(payload: schemas.AttendanceCreate, db: Session = Depends(get_db)):
	return crud.mark_attendance(db, payload)


@app.get("/lessons/{lesson_id}/attendance", response_model=list[schemas.AttendanceOut])
def attendance_for_lesson(lesson_id: int, db: Session = Depends(get_db)):
	return crud.list_attendance_for_lesson(db, lesson_id)


# Payments
@app.post("/payments", response_model=schemas.PaymentOut)
def create_payment(payload: schemas.PaymentCreate, db: Session = Depends(get_db)):
	return crud.create_payment(db, payload)


@app.get("/students/{student_id}/payments", response_model=list[schemas.PaymentOut])
def payments_by_student(student_id: int, db: Session = Depends(get_db)):
	return crud.list_payments_by_student(db, student_id)


# UI: Students - list and detail
@app.get("/ui/students", response_class=HTMLResponse)
def ui_students(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    if request.session.get("user").get("role") == "teacher":
        return RedirectResponse(url="/ui/teacher", status_code=302)
    students = crud.list_students(db)
    return templates.TemplateResponse("students_list.html", {"request": request, "students": students})


@app.get("/ui/students/{student_id}", response_class=HTMLResponse)
def ui_student_detail(student_id: int, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    if request.session.get("user").get("role") == "teacher":
        return RedirectResponse(url="/ui/teacher", status_code=302)
    student = crud.get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")
    payments = crud.list_payments_by_student(db, student_id)
    # enrollments and courses
    enrollments = db.query(models.Enrollment).filter(models.Enrollment.student_id == student_id).all()
    
    # Öğrencinin yoklama kayıtlarını getir (detaylı bilgilerle)
    attendances_raw = crud.list_all_attendances(db, student_id=student_id, limit=1000, order_by="marked_at_desc")
    
    # Yoklama kayıtlarını detaylı bilgilerle formatla
    attendances_with_details = []
    for att in attendances_raw:
        lesson = db.get(models.Lesson, att.lesson_id) if att.lesson_id else None
        course = None
        teacher = None
        if lesson:
            course = db.get(models.Course, lesson.course_id) if lesson.course_id else None
            teacher = db.get(models.Teacher, lesson.teacher_id) if lesson.teacher_id else None
        
        attendances_with_details.append({
            "attendance": att,
            "lesson": lesson,
            "course": course,
            "teacher": teacher,
        })
    
    return templates.TemplateResponse("student_detail.html", {
        "request": request,
        "student": student,
        "payments": payments,
        "enrollments": enrollments,
        "attendances": attendances_with_details
    })


# UI: Teachers - list and detail
@app.get("/ui/teachers", response_class=HTMLResponse)
def ui_teachers(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    if request.session.get("user").get("role") == "teacher":
        return RedirectResponse(url="/ui/teacher", status_code=302)
    teachers = crud.list_teachers(db)
    return templates.TemplateResponse("teachers_list.html", {"request": request, "teachers": teachers})


@app.get("/ui/teachers/{teacher_id}", response_class=HTMLResponse)
def ui_teacher_detail(teacher_id: int, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    if request.session.get("user").get("role") == "teacher":
        return RedirectResponse(url="/ui/teacher", status_code=302)
    teacher = db.get(models.Teacher, teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="Öğretmen bulunamadı")
    lessons = crud.list_lessons_by_teacher(db, teacher_id)
    # Her ders için öğrencileri getir
    lessons_with_students = []
    for lesson in lessons:
        students = crud.list_students_by_lesson(db, lesson.id)
        lessons_with_students.append({"lesson": lesson, "students": students})
    teacher_students = crud.list_students_by_teacher(db, teacher_id)
    return templates.TemplateResponse("teacher_detail.html", {"request": request, "teacher": teacher, "lessons_with_students": lessons_with_students, "teacher_students": teacher_students})


# UI: Payment Reports
@app.get("/ui/reports/payments", response_class=HTMLResponse)
def payment_reports(request: Request, start: str | None = None, end: str | None = None, course_id: str | None = None, teacher_id: str | None = None, student_id: str | None = None, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    if request.session.get("user").get("role") == "teacher":
        return RedirectResponse(url="/ui/teacher", status_code=302)
    from datetime import date
    start_date = None
    end_date = None
    if start:
        try:
            y, m, d = map(int, start.split("-"))
            start_date = date(y, m, d)
        except Exception:
            start_date = None
    if end:
        try:
            y, m, d = map(int, end.split("-"))
            end_date = date(y, m, d)
        except Exception:
            end_date = None
    
    # Query parametrelerini integer'a çevir (boş string'leri None yap)
    course_id_int = None
    teacher_id_int = None
    student_id_int = None
    if course_id and course_id.strip():
        try:
            course_id_int = int(course_id)
        except (ValueError, TypeError):
            course_id_int = None
    if teacher_id and teacher_id.strip():
        try:
            teacher_id_int = int(teacher_id)
        except (ValueError, TypeError):
            teacher_id_int = None
    if student_id and student_id.strip():
        try:
            student_id_int = int(student_id)
        except (ValueError, TypeError):
            student_id_int = None
    
    # Get teacher's students if teacher filter is applied
    teacher_student_ids = None
    if teacher_id_int:
        teacher_students = crud.list_students_by_teacher(db, teacher_id_int)
        if teacher_students:
            teacher_student_ids = [s.id for s in teacher_students]
        else:
            # If teacher has no students, use impossible ID to return no results
            teacher_student_ids = [-1]
    
    # query payments with optional filters and total sum
    q = db.query(models.Payment).join(models.Student)
    # optional joins for filters
    # Filter by course or teacher through enrollments and lessons/payments if needed (basic: by course via enrollments)
    if course_id_int:
        q = q.join(models.Enrollment, models.Enrollment.student_id == models.Payment.student_id).filter(models.Enrollment.course_id == course_id_int)
    if teacher_student_ids is not None:
        # Filter payments by students assigned to the selected teacher
        q = q.filter(models.Payment.student_id.in_(teacher_student_ids))
    if student_id_int:
        # Filter payments by selected student
        q = q.filter(models.Payment.student_id == student_id_int)
    if start_date:
        q = q.filter(models.Payment.payment_date >= start_date)
    if end_date:
        q = q.filter(models.Payment.payment_date <= end_date)
    items = q.order_by(models.Payment.payment_date.desc()).all()
    sum_q = db.query(func.coalesce(func.sum(models.Payment.amount_try), 0)).join(models.Student)
    if course_id_int:
        sum_q = sum_q.join(models.Enrollment, models.Enrollment.student_id == models.Payment.student_id).filter(models.Enrollment.course_id == course_id_int)
    if teacher_student_ids is not None:
        # Filter sum by students assigned to the selected teacher
        sum_q = sum_q.filter(models.Payment.student_id.in_(teacher_student_ids))
    if student_id_int:
        # Filter sum by selected student
        sum_q = sum_q.filter(models.Payment.student_id == student_id_int)
    if start_date:
        sum_q = sum_q.filter(models.Payment.payment_date >= start_date)
    if end_date:
        sum_q = sum_q.filter(models.Payment.payment_date <= end_date)
    total = float(sum_q.scalar() or 0)
    courses = crud.list_courses(db)
    teachers = crud.list_teachers(db)
    # Get selected student info if student_id is provided
    selected_student = None
    if student_id_int:
        selected_student = db.get(models.Student, student_id_int)
    user = request.session.get("user")
    is_admin = user and user.get("role") == "admin"
    return templates.TemplateResponse("reports_payments.html", {"request": request, "items": items, "total": total, "start": start or "", "end": end or "", "courses": courses, "teachers": teachers, "course_id": course_id or "", "teacher_id": teacher_id or "", "student_id": student_id or "", "selected_student": selected_student, "is_admin": is_admin})


@app.get("/ui/reports/payments.csv")
def payment_reports_csv(request: Request, start: str | None = None, end: str | None = None, course_id: str | None = None, teacher_id: str | None = None, student_id: str | None = None, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    if request.session.get("user").get("role") == "teacher":
        return RedirectResponse(url="/ui/teacher", status_code=302)
    from datetime import date
    import csv
    from io import StringIO
    start_date = None
    end_date = None
    if start:
        try:
            y, m, d = map(int, start.split("-"))
            start_date = date(y, m, d)
        except Exception:
            start_date = None
    if end:
        try:
            y, m, d = map(int, end.split("-"))
            end_date = date(y, m, d)
        except Exception:
            end_date = None
    
    # Query parametrelerini integer'a çevir (boş string'leri None yap)
    course_id_int = None
    teacher_id_int = None
    student_id_int = None
    if course_id and course_id.strip():
        try:
            course_id_int = int(course_id)
        except (ValueError, TypeError):
            course_id_int = None
    if teacher_id and teacher_id.strip():
        try:
            teacher_id_int = int(teacher_id)
        except (ValueError, TypeError):
            teacher_id_int = None
    if student_id and student_id.strip():
        try:
            student_id_int = int(student_id)
        except (ValueError, TypeError):
            student_id_int = None
    
    # Get teacher's students if teacher filter is applied
    teacher_student_ids = None
    if teacher_id_int:
        teacher_students = crud.list_students_by_teacher(db, teacher_id_int)
        if teacher_students:
            teacher_student_ids = [s.id for s in teacher_students]
        else:
            # If teacher has no students, use impossible ID to return no results
            teacher_student_ids = [-1]
    
    q = db.query(models.Payment).join(models.Student)
    if course_id_int:
        q = q.join(models.Enrollment, models.Enrollment.student_id == models.Payment.student_id).filter(models.Enrollment.course_id == course_id_int)
    if teacher_student_ids is not None:
        # Filter payments by students assigned to the selected teacher
        q = q.filter(models.Payment.student_id.in_(teacher_student_ids))
    if student_id_int:
        # Filter payments by selected student
        q = q.filter(models.Payment.student_id == student_id_int)
    if start_date:
        q = q.filter(models.Payment.payment_date >= start_date)
    if end_date:
        q = q.filter(models.Payment.payment_date <= end_date)
    items = q.order_by(models.Payment.payment_date.desc()).all()
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Tarih", "Öğrenci", "Tutar", "Yöntem", "Not"])
    for p in items:
        writer.writerow([str(p.payment_date), f"{p.student.first_name} {p.student.last_name}", f"{p.amount_try}", p.method or "", p.note or ""]) 
    return Response(content=buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=odeme_raporu.csv"})


# UI: Admin - users
@app.get("/ui/admin/users", response_class=HTMLResponse)
def admin_users(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    users = crud.list_users(db)
    teachers = crud.list_teachers(db)
    return templates.TemplateResponse("admin_users.html", {"request": request, "users": users, "teachers": teachers})


@app.post("/ui/admin/users")
def admin_create_user(request: Request, username: str = Form(...), password: str = Form(...), full_name: str | None = Form(None), role: str | None = Form(None), teacher_id: str | None = Form(None), db: Session = Depends(get_db)):
    require_admin(request)
    try:
        tid = None
        if teacher_id and str(teacher_id).strip():
            try:
                tid = int(str(teacher_id).strip())
            except Exception:
                tid = None
        crud.create_user(db, schemas.UserCreate(username=username, password=password, full_name=full_name, role=role, teacher_id=tid))
    except Exception:
        pass
    return RedirectResponse(url="/ui/admin/users", status_code=302)


@app.post("/ui/admin/users/{user_id}/password")
def admin_change_password(user_id: int, request: Request, password: str = Form(...), db: Session = Depends(get_db)):
    require_admin(request)
    crud.update_user_password(db, user_id, password)
    return RedirectResponse(url="/ui/admin/users", status_code=302)


@app.post("/ui/admin/users/{user_id}/delete")
def admin_delete_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    user = db.get(models.User, user_id)
    if user and user.username != "admin":
        db.delete(user)
        db.commit()
    return RedirectResponse(url="/ui/admin/users", status_code=302)


@app.get("/login/admin", response_class=HTMLResponse)
def login_admin_form(request: Request):
    # Database'i ilk kullanımda başlat (bloklamadan)
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass
    
    # Kullanıcı zaten giriş yapmışsa dashboard'a yönlendir
    user = request.session.get("user")
    if user:
        if user.get("role") == "admin":
            return RedirectResponse(url="/dashboard", status_code=302)
        elif user.get("role") == "teacher":
            return RedirectResponse(url="/ui/teacher", status_code=302)
        elif user.get("role") == "staff":
            return RedirectResponse(url="/ui/staff", status_code=302)
    
    # Hata mesajını al
    login_error = request.session.get("login_error", "")
    if login_error:
        request.session.pop("login_error", None)
    
    # Direkt HTML döndür - template'e bağımlı olmadan
    error_html = f'<div style="padding:12px;background:#fee2e2;border:1px solid #ef4444;border-radius:6px;margin-bottom:16px;color:#dc2626;font-size:14px;">{login_error}</div>' if login_error else ""
    
    html_content = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Admin Giriş - Piarte</title>
    <style>
        body {{ font-family: ui-sans-serif, system-ui, 'Segoe UI', Roboto, sans-serif; padding: 24px; max-width: 420px; margin: auto; background: #f9fafb; }}
        .card {{ border: 1px solid #e5e7eb; border-radius: 8px; padding: 24px; margin-top: 48px; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        h2 {{ margin-top: 0; color: #111827; }}
        label {{ display: block; margin-top: 12px; margin-bottom: 4px; color: #374151; font-weight: 500; }}
        input {{ padding: 10px; margin: 6px 0; width: 100%; box-sizing: border-box; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; }}
        input:focus {{ outline: none; border-color: #0ea5e9; box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.1); }}
        button {{ padding: 12px 24px; margin-top: 16px; width: 100%; background: #111827; color: white; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer; }}
        button:hover {{ background: #1f2937; }}
        .info {{ color: #6b7280; font-size: 13px; margin-top: 16px; }}
    </style>
</head>
<body>
    <div class="card">
        <h2>Piarte - Admin Girişi</h2>
        {error_html}
        <form method="post" action="/login/admin">
            <label>Kullanıcı adı</label>
            <input type="text" name="username" required autocomplete="username" />
            <label>Şifre</label>
            <input type="password" name="password" required autocomplete="current-password" />
            <button type="submit">Giriş Yap</button>
        </form>
        <p class="info">Sadece yönetici girişi içindir.</p>
    </div>
</body>
</html>"""
    return HTMLResponse(content=html_content)

@app.post("/login/admin")
def login_admin(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    try:
        from passlib.hash import pbkdf2_sha256
        user = crud.get_user_by_username(db, username)
        
        # Kullanıcı yoksa
        if not user:
            request.session["login_error"] = "Kullanıcı adı veya şifre hatalı."
            return RedirectResponse(url="/login/admin", status_code=302)
        
        # Şifre kontrolü
        try:
            password_valid = pbkdf2_sha256.verify(password, user.password_hash)
        except Exception as e:
            # Şifre hash hatası
            import logging
            logging.error(f"Şifre doğrulama hatası: {e}")
            request.session["login_error"] = "Giriş hatası. Lütfen tekrar deneyin."
            return RedirectResponse(url="/login/admin", status_code=302)
        
        # Admin kontrolü: role None ise admin kabul et (geriye dönük uyumluluk)
        is_admin = (user.role is None) or (user.role == "admin")
        
        if not password_valid or not is_admin:
            request.session["login_error"] = "Kullanıcı adı veya şifre hatalı, ya da admin yetkisi yok."
            return RedirectResponse(url="/login/admin", status_code=302)
        
        # Session'a kullanıcı bilgilerini kaydet
        request.session["user"] = {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": "admin",
            "teacher_id": getattr(user, 'teacher_id', None),
        }
        # Hata mesajını temizle
        request.session.pop("login_error", None)
        return RedirectResponse(url="/dashboard", status_code=302)
    
    except Exception as e:
        # Genel hata yakalama
        import logging
        import traceback
        logging.error(f"Login hatası: {e}")
        logging.error(traceback.format_exc())
        request.session["login_error"] = f"Sunucu hatası: {str(e)}"
        return RedirectResponse(url="/login/admin", status_code=302)

# Öğretmen için giriş
@app.get("/login/teacher", response_class=HTMLResponse)
def login_teacher_form(request: Request):
    # Kullanıcı zaten giriş yapmışsa ilgili panele yönlendir
    user = request.session.get("user")
    if user:
        if user.get("role") == "teacher":
            return RedirectResponse(url="/ui/teacher", status_code=302)
        elif user.get("role") == "admin":
            return RedirectResponse(url="/dashboard", status_code=302)
        elif user.get("role") == "staff":
            return RedirectResponse(url="/ui/staff", status_code=302)
    
    html_content = """<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Öğretmen Giriş - Piarte</title>
    <style>
        body { font-family: ui-sans-serif, system-ui, 'Segoe UI', Roboto, sans-serif; padding: 24px; max-width: 420px; margin: auto; background: #f9fafb; }
        .card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 24px; margin-top: 48px; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        h2 { margin-top: 0; color: #111827; }
        label { display: block; margin-top: 12px; margin-bottom: 4px; color: #374151; font-weight: 500; }
        input { padding: 10px; margin: 6px 0; width: 100%; box-sizing: border-box; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; }
        input:focus { outline: none; border-color: #0ea5e9; box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.1); }
        button { padding: 12px 24px; margin-top: 16px; width: 100%; background: #111827; color: white; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer; }
        button:hover { background: #1f2937; }
        .info { color: #6b7280; font-size: 13px; margin-top: 16px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Piarte - Öğretmen Girişi</h2>
        <form method="post" action="/login/teacher">
            <label>Kullanıcı adı</label>
            <input type="text" name="username" required autocomplete="username" />
            <label>Şifre</label>
            <input type="password" name="password" required autocomplete="current-password" />
            <button type="submit">Giriş Yap</button>
        </form>
        <p class="info">Sadece öğretmen girişi içindir.</p>
    </div>
</body>
</html>"""
    return HTMLResponse(content=html_content)

@app.post("/login/teacher")
def login_teacher(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    from passlib.hash import pbkdf2_sha256
    user = crud.get_user_by_username(db, username)
    if not user or not pbkdf2_sha256.verify(password, user.password_hash) or user.role != "teacher":
        return RedirectResponse(url="/login/teacher", status_code=302)
    request.session["user"] = {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": "teacher",
        "teacher_id": getattr(user, 'teacher_id', None),
    }
    return RedirectResponse(url="/ui/teacher", status_code=302)

# Personel için giriş (örnek rol adı: staff)
@app.get("/login/staff", response_class=HTMLResponse)
def login_staff_form(request: Request):
    # Kullanıcı zaten giriş yapmışsa ilgili panele yönlendir
    user = request.session.get("user")
    if user:
        if user.get("role") == "staff":
            return RedirectResponse(url="/ui/staff", status_code=302)
        elif user.get("role") == "admin":
            return RedirectResponse(url="/dashboard", status_code=302)
        elif user.get("role") == "teacher":
            return RedirectResponse(url="/ui/teacher", status_code=302)
    
    html_content = """<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Personel Giriş - Piarte</title>
    <style>
        body { font-family: ui-sans-serif, system-ui, 'Segoe UI', Roboto, sans-serif; padding: 24px; max-width: 420px; margin: auto; background: #f9fafb; }
        .card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 24px; margin-top: 48px; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        h2 { margin-top: 0; color: #111827; }
        label { display: block; margin-top: 12px; margin-bottom: 4px; color: #374151; font-weight: 500; }
        input { padding: 10px; margin: 6px 0; width: 100%; box-sizing: border-box; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; }
        input:focus { outline: none; border-color: #0ea5e9; box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.1); }
        button { padding: 12px 24px; margin-top: 16px; width: 100%; background: #111827; color: white; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer; }
        button:hover { background: #1f2937; }
        .info { color: #6b7280; font-size: 13px; margin-top: 16px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Piarte - Personel Girişi</h2>
        <form method="post" action="/login/staff">
            <label>Kullanıcı adı</label>
            <input type="text" name="username" required autocomplete="username" />
            <label>Şifre</label>
            <input type="password" name="password" required autocomplete="current-password" />
            <button type="submit">Giriş Yap</button>
        </form>
        <p class="info">Sadece personel girişi içindir.</p>
    </div>
</body>
</html>"""
    return HTMLResponse(content=html_content)

@app.post("/login/staff")
def login_staff(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    from passlib.hash import pbkdf2_sha256
    user = crud.get_user_by_username(db, username)
    if not user or not pbkdf2_sha256.verify(password, user.password_hash) or user.role != "staff":
        return RedirectResponse(url="/login/staff", status_code=302)
    request.session["user"] = {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": "staff",
        "teacher_id": getattr(user, 'teacher_id', None),
    }
    return RedirectResponse(url="/ui/staff", status_code=302)

@app.get("/ui/staff", response_class=HTMLResponse)
def staff_panel(
	request: Request,
	search: str | None = None,
	student_id: str | None = None,
	teacher_id: str | None = None,
	selected_date: str | None = None,
	attendance_teacher_id: str | None = None,
	attendance_student_id: str | None = None,
	attendance_course_id: str | None = None,
	start_date: str | None = None,
	end_date: str | None = None,
	status: str | None = None,
	order_by: str = "marked_at_desc",
	edit_search: str | None = None,
	success: str | None = None,
	error: str | None = None,
	db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login/staff", status_code=302)
    if user.get("role") != "staff":
        # Staff harici biri geldi: kendi paneline yönlendir
        if user.get("role") == "admin":
            return RedirectResponse(url="/dashboard", status_code=302)
        elif user.get("role") == "teacher":
            return RedirectResponse(url="/ui/teacher", status_code=302)
        else:
            return RedirectResponse(url="/login/staff", status_code=302)
    try:
        from sqlalchemy import select
        
        # Query parametrelerini integer'a çevir (boş string'leri None yap)
        student_id_int = None
        teacher_id_int = None
        if student_id and student_id.strip():
            try:
                student_id_int = int(student_id)
            except (ValueError, TypeError):
                student_id_int = None
        if teacher_id and teacher_id.strip():
            try:
                teacher_id_int = int(teacher_id)
            except (ValueError, TypeError):
                teacher_id_int = None
        
        # Tüm öğretmenleri getir
        teachers = crud.list_teachers(db)
        
        # Her öğretmen için haftalık ders programını hazırla
        from datetime import datetime
        weekday_map = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        teachers_schedules = []
        
        for teacher in teachers:
            lessons_with_students = crud.lessons_with_students_by_teacher(db, teacher.id)
            formatted_lessons = []
            for entry in lessons_with_students:
                lesson = entry["lesson"]
                weekday = weekday_map[lesson.lesson_date.weekday()] if hasattr(lesson.lesson_date, "weekday") else ""
                # Dinamik tarih hesapla (bugünden sonraki ilgili gün)
                current_lesson_date = calculate_next_lesson_date(lesson.lesson_date)
                formatted_lessons.append({
                    "weekday": weekday,
                    "lesson": lesson,
                    "current_lesson_date": current_lesson_date,  # Dinamik hesaplanan tarih
                    "students": entry["students"],
                })
            teachers_schedules.append({
                "teacher": teacher,
                "lessons": formatted_lessons
            })
        
        # Öğrenci arama ve ders programı
        search_results = []
        selected_student = None
        student_lessons = []
        student_lessons_formatted = []
        selected_student_payments = []
        all_lesson_dates_sorted = []
        
        if search:
            # Öğrenci ara
            search_term = f"%{search.strip()}%"
            students_found = db.query(models.Student).filter(
                (models.Student.first_name.ilike(search_term)) | 
                (models.Student.last_name.ilike(search_term))
            ).limit(20).all()
            # Her öğrenci için ödeme durumunu kontrol et
            search_results = []
            for student in students_found:
                needs_payment = crud.check_student_payment_status(db, student.id)
                search_results.append({
                    "student": student,
                    "needs_payment": needs_payment
                })
        
        if student_id_int:
            # Seçilen öğrencinin bilgilerini ve derslerini getir
            selected_student = crud.get_student(db, student_id_int)
            if selected_student:
                student_lessons = crud.list_lessons_by_student(db, student_id_int)
                # Öğrencinin ödemelerini de getir
                selected_student_payments = crud.list_payments_by_student(db, student_id_int)
                
                # Öğrencinin tüm yoklamalarını tarihe göre sıralı getir (ders tarihleri için)
                student_attendances = db.scalars(
                    select(models.Attendance)
                    .where(models.Attendance.student_id == student_id_int)
                    .order_by(models.Attendance.marked_at.asc())
                ).all()
                
                # Dersleri haftalık formata çevir
                from datetime import time as time_type, date as date_type
                # Öğrencinin tüm derslerini birleştir (geçmiş + gelecek)
                # Geçmiş dersler: student_attendances'tan (yoklama alınmış)
                # Gelecek dersler: student_lessons'tan (atanmış)
                
                # Geçmiş derslerin tarihlerini al (yoklama tarihlerinden) - tekrarları kaldır
                past_lesson_dates = set()
                for att in student_attendances:
                    if att.marked_at:
                        past_lesson_dates.add(att.marked_at.date())
                
                # Tüm ders tarihlerini birleştir (geçmiş + gelecek)
                # ÖNEMLİ: Toplam ders sayısı için sadece yoklama alınmış dersleri say
                # Gelecek dersler (LessonStudent tablosundan) sadece program gösterimi için kullanılır
                all_lesson_dates = set()
                
                # Geçmiş dersler: Sadece yoklama alınmış dersler
                all_lesson_dates.update(past_lesson_dates)
                
                # Gelecek dersler: LessonStudent tablosundan (program gösterimi için)
                for lesson in student_lessons:
                    all_lesson_dates.add(lesson.lesson_date)
                
                # Tüm tarihleri sırala (program gösterimi için - hem geçmiş hem gelecek)
                all_lesson_dates_sorted = sorted(list(all_lesson_dates))
                
                # Sadece yoklama alınmış derslerin tarihlerini sırala (gösterim için)
                attendance_dates_sorted = sorted(list(past_lesson_dates))
                
                # Öğrencinin toplam ders sayısını hesapla
                # ÖNEMLİ: Sadece gerçekten yoklama alınmış dersleri say (kayıt yapılmış ama yoklama alınmamış dersler sayılmaz)
                total_lessons_count = len(past_lesson_dates)
                
                # Öğrencinin tüm derslerini tarihe göre sırala (gelecek dersler için)
                all_student_lessons_sorted = sorted(
                    student_lessons,
                    key=lambda x: (x.lesson_date, x.start_time if x.start_time else time_type.min)
                )
                
                for lesson in student_lessons:
                    weekday = weekday_map[lesson.lesson_date.weekday()] if hasattr(lesson.lesson_date, "weekday") else ""
                    # Dinamik tarih hesapla (bugünden sonraki ilgili gün)
                    current_lesson_date = calculate_next_lesson_date(lesson.lesson_date)
                    
                    # Öğrencinin bu derste toplam dersler içinde kaçıncı ders olduğunu bul
                    # Geçmiş dersler + gelecek dersler birlikte sayılıyor
                    lesson_number = None
                    try:
                        # Bu dersin tarihini bul
                        lesson_date = lesson.lesson_date
                        # Tüm tarihler içinde bu tarihin sırasını bul
                        lesson_index = all_lesson_dates_sorted.index(lesson_date)
                        lesson_number = lesson_index + 1
                    except ValueError:
                        lesson_number = None
                    
                    student_lessons_formatted.append({
                        "weekday": weekday,
                        "lesson": lesson,
                        "current_lesson_date": current_lesson_date,  # Dinamik hesaplanan tarih
                        "lesson_number": lesson_number,
                        "total_same_day": len(all_lesson_dates_sorted)  # Toplam ders sayısı (geçmiş + gelecek)
                    })
            else:
                total_lessons_count = 0
                student_attendances = []
                selected_student_payments = []
        else:
            total_lessons_count = 0
            student_attendances = []
            selected_student_payments = []
        
        # Ödeme durumu tablosu için tüm öğrencileri getir
        all_students = crud.list_students(db)
        payment_status_list = []
        from datetime import date
        today = date.today()
        
        for student in all_students:
            # Öğrencinin toplam ders sayısını hesapla (PRESENT veya TELAFI)
            total_lessons = db.scalars(
                select(func.count(models.Attendance.id))
                .where(
                    models.Attendance.student_id == student.id,
                    models.Attendance.status.in_(["PRESENT", "TELAFI", "LATE"])  # LATE eski kayıtlar için
                )
            ).first() or 0
            
            # Öğrencinin ödemelerini getir
            payments = crud.list_payments_by_student(db, student.id)
            total_paid_sets = len(payments)
            
            # Beklenen ödeme seti hesapla: Yapılan ödeme sayısı = Beklenen ödeme set sayısı
            # Yapılan her ödeme 1 set olarak sayılır
            # Örnek: 1 ödeme yapıldıysa beklenen = 1 set
            # Örnek: 2 ödeme yapıldıysa beklenen = 2 set
            # Örnek: 3 ödeme yapıldıysa beklenen = 3 set
            expected_paid_sets = total_paid_sets
            
            # En son ödeme tarihi
            last_payment_date = None
            if payments:
                last_payment_date = payments[0].payment_date  # Zaten tarihe göre sıralı (en yeni önce)
            
            # Ödeme durumu kontrolü - Yeni mantık:
            # Her set 4 derslik: 0. Set (0-3 ders), 1. Set (4-7 ders), 2. Set (8-11 ders)...
            # İlk ödeme yapıldığında (0-2 ders arası): "Ödeme yapıldı"
            # 3. ders: Ödeme yapılmamışsa "Ödeme bekleniyor"
            # 4. ders: Ödeme yapılmamışsa "Ödeme gerekli"
            # Her set için aynı mantık uygulanır
            payment_status = ""
            payment_status_class = ""
            needs_payment = False
            
            # Hiç ödeme yapılmadıysa, kaçıncı derste olursa olsun "Ödeme Gerekli"
            if total_paid_sets == 0:
                # Hiç ödeme yok, her durumda ödeme gerekli
                payment_status = "⚠️ Ödeme Gerekli"
                payment_status_class = "needs_payment"
                needs_payment = True
            elif total_lessons == 0:
                # 0 ders: Eğer ödeme yapıldıysa "Ödendi", yoksa "Ödeme Gerekli"
                if total_paid_sets > 0:
                    # 0 ders ama ödeme yapılmış
                    payment_status = "✅ Ödendi"
                    payment_status_class = "paid"
                    needs_payment = False
                else:
                    # 0 ders ve ödeme yok
                    payment_status = "⚠️ Ödeme Gerekli"
                    payment_status_class = "needs_payment"
                    needs_payment = True
            else:
                # Set numarası hesapla (0-based: 0. set = 0-3, 1. set = 4-7, 2. set = 8-11...)
                current_set = total_lessons // 4
                # Set içindeki pozisyon (0-3): 0=1. ders, 1=2. ders, 2=3. ders, 3=4. ders
                position_in_set = total_lessons % 4
                
                # Ödeme yapılan set sayısı (total_paid_sets) - ödeme tablosundan anlık olarak alınıyor
                # Her set 4 derslik periyot: 0. set (0-3), 1. set (4-7), 2. set (8-11)...
                if current_set < total_paid_sets:
                    # Bu set için ödeme yapılmış
                    if position_in_set == 0 or position_in_set == 1 or position_in_set == 2:
                        # Set içinde 0-2. pozisyon (0, 1, 2. dersler veya 4, 5, 6. dersler...): Ödeme Yapıldı
                        payment_status = "✅ Ödeme Yapıldı"
                        payment_status_class = "paid"
                        needs_payment = False
                    elif position_in_set == 3:
                        # Set içinde 3. pozisyon (3, 7, 11, 15... dersler)
                        # Bir sonraki set ödemesi yapılmadıysa "Ödeme Bekleniyor"
                        if (current_set + 1) < total_paid_sets:
                            # Bir sonraki set ödemesi yapılmış
                            payment_status = "✅ Ödeme Yapıldı"
                            payment_status_class = "paid"
                            needs_payment = False
                        else:
                            # Bir sonraki set ödemesi yapılmamış
                            payment_status = "⏳ Ödeme Bekleniyor"
                            payment_status_class = "waiting"
                            needs_payment = False
                elif current_set == total_paid_sets:
                    # Yeni set başladı, ödeme yapılmamış
                    if position_in_set == 0:
                        # Yeni set başladı (4, 8, 12... dersler): Ödeme Gerekli
                        payment_status = "⚠️ Ödeme Gerekli"
                        payment_status_class = "needs_payment"
                        needs_payment = True
                    elif position_in_set == 1 or position_in_set == 2:
                        # Set içinde 1-2. pozisyon (5-6, 9-10... dersler): Ödeme Yapıldı (ilk dersler)
                        payment_status = "✅ Ödeme Yapıldı"
                        payment_status_class = "paid"
                        needs_payment = False
                    elif position_in_set == 3:
                        # Set içinde 3. pozisyon (7, 11, 15... dersler): Ödeme Bekleniyor
                        payment_status = "⏳ Ödeme Bekleniyor"
                        payment_status_class = "waiting"
                        needs_payment = False
                else:
                    # Daha ileri bir set, ödeme yapılmamış
                    if position_in_set == 0:
                        # Yeni set başladı: Ödeme Gerekli
                        payment_status = "⚠️ Ödeme Gerekli"
                        payment_status_class = "needs_payment"
                        needs_payment = True
                    else:
                        # Set içinde diğer pozisyonlar: Ödeme Bekleniyor
                        payment_status = "⏳ Ödeme Bekleniyor"
                        payment_status_class = "waiting"
                        needs_payment = False
            
            payment_status_list.append({
                "student": student,
                "total_lessons": total_lessons,
                "expected_paid_sets": expected_paid_sets,
                "total_paid_sets": total_paid_sets,
                "last_payment_date": last_payment_date,
                "needs_payment": needs_payment,
                "payment_status": payment_status,
                "payment_status_class": payment_status_class
            })
        
        # Ödeme durumuna göre sırala (önce ödeme gerekli olanlar)
        payment_status_list.sort(key=lambda x: (not x["needs_payment"], x["student"].first_name, x["student"].last_name))
        
        # Geçmişe dönük yoklama için öğretmen ve tarih seçildiğinde öğrencileri getir
        selected_teacher = None
        selected_teacher_lessons = []
        if teacher_id_int and selected_date:
            try:
                import logging
                logging.info(f"🔍 Retrospective attendance: teacher_id={teacher_id_int}, selected_date={selected_date}")
                
                selected_teacher = crud.get_teacher(db, teacher_id_int)
                logging.info(f"✅ Teacher found: {selected_teacher.first_name if selected_teacher else 'None'}")
                
                # Seçilen tarihe ait dersleri getir
                from datetime import datetime
                selected_date_obj = datetime.strptime(selected_date, "%Y-%m-%d").date()
                selected_weekday = selected_date_obj.weekday()
                logging.info(f"📅 Selected date weekday: {selected_weekday} (0=Mon, 6=Sun)")
                
                # Öğretmene atanmış tüm öğrencileri getir
                teacher_students = db.scalars(
                    select(models.Student)
                    .join(models.TeacherStudent, models.TeacherStudent.student_id == models.Student.id)
                    .where(models.TeacherStudent.teacher_id == teacher_id_int)
                    .order_by(models.Student.first_name.asc(), models.Student.last_name.asc())
                ).all()
                logging.info(f"👥 Total students for teacher: {len(teacher_students)}")
                
                # Öğretmenin o gün hangi dersleri olduğunu bul (haftalık tekrar mantığına göre)
                from sqlalchemy.orm import joinedload
                all_lessons = db.query(models.Lesson).options(
                    joinedload(models.Lesson.course),
                    joinedload(models.Lesson.teacher)
                ).filter(models.Lesson.teacher_id == teacher_id_int).order_by(
                    models.Lesson.lesson_date.asc(),
                    models.Lesson.start_time.asc()
                ).all()
                logging.info(f"📚 Total lessons for teacher: {len(all_lessons)}")
                
                for lesson in all_lessons:
                    lesson_weekday = lesson.lesson_date.weekday()
                    logging.info(f"  - Lesson {lesson.id}: {lesson.course.name}, weekday={lesson_weekday}")
                    
                    # Dersin haftanın hangi günü olduğunu kontrol et
                    if lesson_weekday == selected_weekday:
                        logging.info(f"    ✅ MATCH! Adding lesson {lesson.id} with {len(teacher_students)} students")
                        # Aynı gün içindeki dersler için öğretmene atanmış TÜM öğrencileri ekle
                        selected_teacher_lessons.append({
                            "lesson": lesson,
                            "students": teacher_students  # Öğretmene atanmış tüm öğrenciler
                        })
                    else:
                        logging.info(f"    ❌ NO MATCH: {lesson_weekday} != {selected_weekday}")
                
                logging.info(f"📋 Final selected_teacher_lessons count: {len(selected_teacher_lessons)}")
            except Exception as e:
                import logging
                import traceback
                logging.error(f"❌ Error fetching teacher lessons for date: {e}")
                logging.error(traceback.format_exc())
        
        # Yoklama filtreleme için gerekli verileri hazırla
        students = crud.list_students(db)
        courses = crud.list_courses(db)
        
        # Query parametrelerini integer'a çevir (boş string'leri None yap)
        attendance_teacher_id_int = None
        attendance_student_id_int = None
        attendance_course_id_int = None
        if attendance_teacher_id and attendance_teacher_id.strip():
            try:
                attendance_teacher_id_int = int(attendance_teacher_id)
            except (ValueError, TypeError):
                attendance_teacher_id_int = None
        if attendance_student_id and attendance_student_id.strip():
            try:
                attendance_student_id_int = int(attendance_student_id)
            except (ValueError, TypeError):
                attendance_student_id_int = None
        if attendance_course_id and attendance_course_id.strip():
            try:
                attendance_course_id_int = int(attendance_course_id)
            except (ValueError, TypeError):
                attendance_course_id_int = None
        
        # Tarih filtrelerini parse et
        from datetime import date, datetime
        start_date_obj = None
        end_date_obj = None
        if start_date:
            try:
                y, m, d = map(int, start_date.split("-"))
                start_date_obj = date(y, m, d)
            except Exception:
                pass
        if end_date:
            try:
                y, m, d = map(int, end_date.split("-"))
                end_date_obj = date(y, m, d)
            except Exception:
                pass
        
        # Filtrelerin olup olmadığını kontrol et
        has_filters = any([
            attendance_teacher_id_int is not None,
            attendance_student_id_int is not None,
            attendance_course_id_int is not None,
            status is not None and status.strip(),
            start_date_obj is not None,
            end_date_obj is not None
        ])
        
        # Yoklama verilerini filtrele
        attendances = []
        if has_filters:
            # Direkt sorgu ile tüm yoklamaları al
            all_attendances_direct = db.scalars(select(models.Attendance)).all()
            
            # Filtreleri manuel uygula
            attendances = list(all_attendances_direct)
            
            # Teacher filter
            if attendance_teacher_id_int:
                filtered = []
                for att in attendances:
                    lesson = db.get(models.Lesson, att.lesson_id)
                    if lesson and lesson.teacher_id == attendance_teacher_id_int:
                        filtered.append(att)
                attendances = filtered
            
            # Student filter
            if attendance_student_id_int:
                attendances = [a for a in attendances if a.student_id == attendance_student_id_int]
            
            # Status filter
            if status:
                attendances = [a for a in attendances if a.status.upper() == status.upper()]
            
            # Course filter
            if attendance_course_id_int:
                filtered = []
                for att in attendances:
                    lesson = db.get(models.Lesson, att.lesson_id)
                    if lesson and lesson.course_id == attendance_course_id_int:
                        filtered.append(att)
                attendances = filtered
            
            # Date filters
            if start_date_obj:
                start_datetime = datetime.combine(start_date_obj, datetime.min.time())
                attendances = [a for a in attendances if a.marked_at and a.marked_at >= start_datetime]
            
            if end_date_obj:
                end_datetime = datetime.combine(end_date_obj, datetime.max.time())
                attendances = [a for a in attendances if a.marked_at and a.marked_at <= end_datetime]
            
            # Sort
            if order_by == "marked_at_desc" or order_by == "lesson_date_desc":
                attendances.sort(key=lambda x: x.marked_at if x.marked_at else datetime.min, reverse=True)
            elif order_by == "marked_at_asc" or order_by == "lesson_date_asc":
                attendances.sort(key=lambda x: x.marked_at if x.marked_at else datetime.min, reverse=False)
            
            # Limit
            attendances = attendances[:200]
        
        # Yoklamaları ders ve öğrenci bilgileriyle birlikte hazırla
        attendances_with_details = []
        for att in attendances:
            lesson = db.get(models.Lesson, att.lesson_id)
            student = db.get(models.Student, att.student_id)
            teacher = db.get(models.Teacher, lesson.teacher_id) if lesson and lesson.teacher_id else None
            course = db.get(models.Course, lesson.course_id) if lesson and lesson.course_id else None
            attendances_with_details.append({
                "attendance": att,
                "lesson": lesson,
                "student": student,
                "teacher": teacher,
                "course": course,
            })
        
        # Filtre dict'i oluştur
        filters = {
            "teacher_id": attendance_teacher_id_int,
            "student_id": attendance_student_id_int,
            "course_id": attendance_course_id_int,
            "status": status,
            "start_date": start_date,
            "end_date": end_date,
            "order_by": order_by
        }
        
        # Yoklama düzeltme için arama
        edit_attendances = []
        if edit_search and edit_search.strip():
            search_term = f"%{edit_search.strip()}%"
            # Öğrenci veya öğretmen ismi ile eşleşen yoklamaları bul
            all_attendances_for_edit = db.scalars(select(models.Attendance)).all()
            
            for att in all_attendances_for_edit:
                lesson = db.get(models.Lesson, att.lesson_id)
                student = db.get(models.Student, att.student_id)
                teacher = db.get(models.Teacher, lesson.teacher_id) if lesson and lesson.teacher_id else None
                
                # Öğrenci veya öğretmen ismi ile eşleşiyor mu kontrol et
                match = False
                if student:
                    if (search_term.replace('%', '').lower() in student.first_name.lower() or 
                        search_term.replace('%', '').lower() in student.last_name.lower() or
                        search_term.replace('%', '').lower() in f"{student.first_name} {student.last_name}".lower()):
                        match = True
                if teacher:
                    if (search_term.replace('%', '').lower() in teacher.first_name.lower() or 
                        search_term.replace('%', '').lower() in teacher.last_name.lower() or
                        search_term.replace('%', '').lower() in f"{teacher.first_name} {teacher.last_name}".lower()):
                        match = True
                
                if match:
                    course = db.get(models.Course, lesson.course_id) if lesson and lesson.course_id else None
                    edit_attendances.append({
                        "attendance": att,
                        "lesson": lesson,
                        "student": student,
                        "teacher": teacher,
                        "course": course,
                    })
            
            # Tarihe göre sırala (en yeni önce)
            edit_attendances.sort(key=lambda x: x["attendance"].marked_at if x["attendance"].marked_at else datetime.min, reverse=True)
            # Limit
            edit_attendances = edit_attendances[:100]
        
        return templates.TemplateResponse("staff_panel.html", {
            "request": request,
            "teachers": teachers,
            "teachers_schedules": teachers_schedules,
            "search": search or "",
            "search_results": search_results,
            "selected_student": selected_student,
            "student_lessons": student_lessons_formatted,
            "selected_student_payments": selected_student_payments,
            "total_lessons_count": total_lessons_count if 'total_lessons_count' in locals() else 0,
            "student_attendances": student_attendances if 'student_attendances' in locals() else [],
            "all_lesson_dates_sorted": all_lesson_dates_sorted if 'all_lesson_dates_sorted' in locals() else [],
            "attendance_dates_sorted": attendance_dates_sorted if 'attendance_dates_sorted' in locals() else [],
            "payment_status_list": payment_status_list,
            "today": today,
            "selected_teacher": selected_teacher,
            "selected_teacher_id": teacher_id_int,
            "selected_date": selected_date,
            "selected_teacher_lessons": selected_teacher_lessons,
            "success": success,
            "error": error,
            # Yoklama filtreleme için
            "students": students,
            "courses": courses,
            "filters": filters,
            "attendances": attendances_with_details,
            # Yoklama düzeltme için
            "edit_search": edit_search,
            "edit_attendances": edit_attendances
        })
    except Exception as e:
        import logging
        logging.error(f"Staff panel template error: {e}")
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head><title>Personel Paneli - Piarte</title></head>
        <body>
            <h2>Personel Paneli</h2>
            <p>Hoş geldiniz. Buradan temel işlemleri kolayca erişebilirsiniz:</p>
            <a href="/students/new"><button>Yeni Öğrenci Kaydı</button></a>
            <a href="/lessons/new"><button>Ders Seçimi / Kayıt</button></a>
            <a href="/payments/new"><button>Ödeme Al</button></a>
            <p>Hata: {str(e)}</p>
        </body>
        </html>
        """)

@app.post("/ui/staff/attendance/retrospective")
async def staff_retrospective_attendance(
    request: Request,
    teacher_id: int = Form(...),
    selected_date: str = Form(...),
    db: Session = Depends(get_db)
):
    """Geçmişe dönük yoklama kaydı oluştur"""
    user = request.session.get("user")
    if not user or user.get("role") != "staff":
        return RedirectResponse(url="/login/staff", status_code=302)
    
    try:
        from datetime import datetime
        
        # Form verilerini al
        form_data = await request.form()
        attendance_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
        
        # Yoklama kayıtlarını oluştur
        attendance_count = 0
        for key, value in form_data.items():
            if key.startswith("status_"):
                # Format: status_lessonId_studentId
                parts = key.split("_")
                if len(parts) == 3:
                    lesson_id = int(parts[1])
                    student_id = int(parts[2])
                    status_value = value.strip().upper()
                    
                    if status_value:  # Boş değilse
                        # Saat bilgisini al (time_lessonId_studentId formatında)
                        time_key = f"time_{lesson_id}_{student_id}"
                        time_value = form_data.get(time_key, "").strip()
                        
                        # Saat bilgisini parse et
                        marked_at_datetime = None
                        if time_value:
                            try:
                                # time input formatı: "HH:MM"
                                hour, minute = map(int, time_value.split(":"))
                                marked_at_datetime = datetime.combine(attendance_date, datetime.min.time().replace(hour=hour, minute=minute))
                            except (ValueError, AttributeError):
                                # Hata durumunda varsayılan olarak günün başlangıcını kullan
                                marked_at_datetime = datetime.combine(attendance_date, datetime.min.time())
                        else:
                            # Saat girilmemişse günün başlangıcını kullan
                            marked_at_datetime = datetime.combine(attendance_date, datetime.min.time())
                        
                        # Yoklama kaydı oluştur
                        attendance_data = schemas.AttendanceCreate(
                            lesson_id=lesson_id,
                            student_id=student_id,
                            status=status_value,
                            marked_at=marked_at_datetime,
                            note=f"Geçmişe dönük kayıt - {selected_date}"
                        )
                        crud.mark_attendance(db, attendance_data, commit=True)
                        attendance_count += 1
        
        if attendance_count > 0:
            return RedirectResponse(
                url=f"/ui/staff?teacher_id={teacher_id}&selected_date={selected_date}&success={attendance_count} yoklama kaydı başarıyla oluşturuldu",
                status_code=303
            )
        else:
            return RedirectResponse(
                url=f"/ui/staff?teacher_id={teacher_id}&selected_date={selected_date}&error=Hiçbir yoklama durumu seçilmedi",
                status_code=303
            )
    except Exception as e:
        import logging
        logging.error(f"Error creating retrospective attendance: {e}")
        return RedirectResponse(
            url=f"/ui/staff?teacher_id={teacher_id}&selected_date={selected_date}&error=Yoklama kaydı oluşturulurken hata: {str(e)}",
            status_code=303
        )

@app.post("/ui/staff/payment/retrospective")
async def staff_retrospective_payment(
    request: Request,
    student_id: int = Form(...),
    amount: float = Form(...),
    payment_date: str = Form(...),
    note: str = Form(None),
    db: Session = Depends(get_db)
):
    """Geçmişe dönük ödeme kaydı oluştur"""
    user = request.session.get("user")
    if not user or user.get("role") != "staff":
        return RedirectResponse(url="/login/staff", status_code=302)
    
    try:
        from datetime import datetime
        
        # Ödeme kaydı oluştur
        payment_date_obj = datetime.strptime(payment_date, "%Y-%m-%d").date()
        payment_data = schemas.PaymentCreate(
            student_id=student_id,
            amount=amount,
            payment_date=payment_date_obj,
            note=note or f"Geçmişe dönük ödeme - {payment_date}"
        )
        crud.create_payment(db, payment_data)
        
        return RedirectResponse(
            url=f"/ui/staff?success=Ödeme kaydı başarıyla oluşturuldu",
            status_code=303
        )
    except Exception as e:
        import logging
        logging.error(f"Error creating retrospective payment: {e}")
        return RedirectResponse(
            url=f"/ui/staff?error=Ödeme kaydı oluşturulurken hata: {str(e)}",
            status_code=303
        )

@app.post("/students/{student_id}/delete")
def delete_student(student_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login/admin", status_code=status.HTTP_303_SEE_OTHER)
    student = db.get(models.Student, student_id)
    if student:
        # Tüm bağlı teacher_student satırlarını sil (CASCADE çalışsa bile manuel silme daha güvenli)
        links = db.scalars(select(models.TeacherStudent).where(models.TeacherStudent.student_id == student.id)).all()
        for link in links:
            db.delete(link)
        # Öğrenciyi sil (CASCADE ile otomatik olarak enrollments, payments, attendances da silinir)
        db.delete(student)
        # Tüm değişiklikleri tek seferde commit et
        db.commit()
        # Değişikliklerin veritabanına yansıdığından emin olmak için refresh yap
        db.expire_all()
    return RedirectResponse(url="/ui/students", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/teachers/{teacher_id}/delete")
def delete_teacher(teacher_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login/admin", status_code=status.HTTP_303_SEE_OTHER)
    teacher = db.get(models.Teacher, teacher_id)
    if teacher:
        db.delete(teacher)
        db.commit()
    return RedirectResponse(url="/ui/teachers", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/payments/{payment_id}/edit", response_class=HTMLResponse)
def payment_edit_form(payment_id: int, request: Request, db: Session = Depends(get_db), start: str | None = None, end: str | None = None, course_id: str | None = None, teacher_id: str | None = None):
    """Ödeme düzenleme formu (sadece admin için)"""
    user = request.session.get("user")
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login/admin", status_code=status.HTTP_303_SEE_OTHER)
    
    payment = crud.get_payment(db, payment_id)
    if not payment:
        # Filtre parametrelerini koruyarak geri yönlendir
        params = []
        if start:
            params.append(f"start={start}")
        if end:
            params.append(f"end={end}")
        if course_id:
            params.append(f"course_id={course_id}")
        if teacher_id:
            params.append(f"teacher_id={teacher_id}")
        query_string = "&".join(params)
        redirect_url = f"/ui/reports/payments"
        if query_string:
            redirect_url += "?" + query_string
        request.session["delete_payment_error"] = "Ödeme kaydı bulunamadı."
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    
    students = crud.list_students(db)
    return templates.TemplateResponse("payment_edit.html", {
        "request": request,
        "payment": payment,
        "students": students,
        "start": start or "",
        "end": end or "",
        "course_id": course_id or "",
        "teacher_id": teacher_id or ""
    })


@app.post("/payments/{payment_id}/update")
def update_payment(
    payment_id: int,
    request: Request,
    student_id: int = Form(...),
    amount_try: float = Form(...),
    payment_date: str | None = Form(None),
    method: str | None = Form(None),
    note: str | None = Form(None),
    db: Session = Depends(get_db),
    start: str | None = None,
    end: str | None = None,
    course_id: str | None = None,
    teacher_id: str | None = None,
):
    """Ödeme kaydını günceller (sadece admin için)"""
    user = request.session.get("user")
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login/admin", status_code=status.HTTP_303_SEE_OTHER)
    
    from datetime import date
    pd = None
    if payment_date:
        try:
            y, m, d = map(int, payment_date.split("-"))
            pd = date(y, m, d)
        except Exception:
            pd = None
    
    payload = schemas.PaymentUpdate(
        student_id=student_id,
        amount_try=amount_try,
        payment_date=pd,
        method=method,
        note=note,
    )
    
    updated_payment = crud.update_payment(db, payment_id, payload)
    
    # Filtre parametrelerini koruyarak geri yönlendir
    params = []
    if start:
        params.append(f"start={start}")
    if end:
        params.append(f"end={end}")
    if course_id:
        params.append(f"course_id={course_id}")
    if teacher_id:
        params.append(f"teacher_id={teacher_id}")
    
    query_string = "&".join(params)
    redirect_url = f"/ui/reports/payments"
    if query_string:
        redirect_url += "?" + query_string
    
    # Başarı/hata mesajı için session kullan
    if updated_payment:
        request.session["delete_payment_success"] = "Ödeme kaydı başarıyla güncellendi."
    else:
        request.session["delete_payment_error"] = "Ödeme kaydı güncellenemedi."
    
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@app.post("/payments/{payment_id}/delete")
def delete_payment(payment_id: int, request: Request, db: Session = Depends(get_db), start: str | None = None, end: str | None = None, course_id: str | None = None, teacher_id: str | None = None):
    """Ödeme kaydını siler (sadece admin için)"""
    user = request.session.get("user")
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login/admin", status_code=status.HTTP_303_SEE_OTHER)
    
    # Ödemeyi sil
    success = crud.delete_payment(db, payment_id)
    
    # Filtre parametrelerini koruyarak geri yönlendir
    params = []
    if start:
        params.append(f"start={start}")
    if end:
        params.append(f"end={end}")
    if course_id:
        params.append(f"course_id={course_id}")
    if teacher_id:
        params.append(f"teacher_id={teacher_id}")
    
    query_string = "&".join(params)
    redirect_url = f"/ui/reports/payments"
    if query_string:
        redirect_url += "?" + query_string
    
    # Başarı/hata mesajı için session kullan
    if success:
        request.session["delete_payment_success"] = "Ödeme kaydı başarıyla silindi."
    else:
        request.session["delete_payment_error"] = "Ödeme kaydı silinemedi."
    
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)

