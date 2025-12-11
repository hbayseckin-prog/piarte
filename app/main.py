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
    import json, os, time
    log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cursor", "debug.log")
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        # Direct query to check all attendances in DB
        all_attendances_direct = db.scalars(select(models.Attendance)).all()
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"id": f"log_{int(time.time())}_dashboard_direct_query", "timestamp": int(time.time() * 1000), "location": "main.py:462", "message": "Direct DB query - all attendances", "data": {"total_count": len(all_attendances_direct), "attendance_ids": [a.id for a in all_attendances_direct], "lesson_ids": list(set([a.lesson_id for a in all_attendances_direct])), "student_ids": list(set([a.student_id for a in all_attendances_direct]))}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "D"}) + "\n")
    except Exception as e:
        import logging
        logging.error(f"Debug log error: {e}")
    # #endregion
    
    # DIRECT QUERY: list_all_attendances fonksiyonunu bypass et, direkt sorgu kullan
    # Bu, sorunun kaynağını bulmak için geçici bir çözüm
    import logging
    logging.warning("Dashboard: list_all_attendances bypass ediliyor, direkt sorgu kullanılıyor!")
    
    # Direkt sorgu ile tüm yoklamaları al
    if 'all_attendances_direct' not in locals():
        all_attendances_direct = db.scalars(select(models.Attendance)).all()
    
    # Filtreleri manuel uygula
    attendances = list(all_attendances_direct)
    
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
    
    # Date filters
    if start_date_obj:
        filtered = []
        for att in attendances:
            lesson = db.get(models.Lesson, att.lesson_id)
            if lesson and lesson.lesson_date and lesson.lesson_date >= start_date_obj:
                filtered.append(att)
        attendances = filtered
    
    if end_date_obj:
        filtered = []
        for att in attendances:
            lesson = db.get(models.Lesson, att.lesson_id)
            if lesson and lesson.lesson_date and lesson.lesson_date <= end_date_obj:
                filtered.append(att)
        attendances = filtered
    
    # Sort
    if order_by == "marked_at_desc":
        attendances.sort(key=lambda x: x.marked_at if x.marked_at else datetime.min, reverse=True)
    elif order_by == "marked_at_asc":
        attendances.sort(key=lambda x: x.marked_at if x.marked_at else datetime.min, reverse=False)
    elif order_by == "lesson_date_desc":
        attendances.sort(key=lambda x: (db.get(models.Lesson, x.lesson_id).lesson_date if db.get(models.Lesson, x.lesson_id) and db.get(models.Lesson, x.lesson_id).lesson_date else date.min, x.marked_at if x.marked_at else datetime.min), reverse=True)
    elif order_by == "lesson_date_asc":
        attendances.sort(key=lambda x: (db.get(models.Lesson, x.lesson_id).lesson_date if db.get(models.Lesson, x.lesson_id) and db.get(models.Lesson, x.lesson_id).lesson_date else date.min, x.marked_at if x.marked_at else datetime.min), reverse=False)
    
    # Limit
    attendances = attendances[:200]
    
    # #region agent log
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"id": f"log_{int(time.time())}_dashboard_direct", "timestamp": int(time.time() * 1000), "location": "main.py:476", "message": "Dashboard using DIRECT query (bypassing list_all_attendances)", "data": {"total_in_db": len(all_attendances_direct), "after_filters": len(attendances), "attendance_ids": [a.id for a in attendances], "filters": {"teacher_id": teacher_id_int, "student_id": student_id_int, "course_id": course_id_int, "status": status}}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "B"}) + "\n")
    except Exception as e:
        import logging
        logging.error(f"Debug log error: {e}")
    # #endregion
    
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
            logging.warning(f"Yoklama {att.id} için lesson {att.lesson_id} bulunamadı!")
        if not student:
            import logging
            logging.warning(f"Yoklama {att.id} için student {att.student_id} bulunamadı!")
        
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
    # Puantaj raporunu getir (sadece admin için)
    attendance_report = []
    if user.get("role") == "admin":
        attendance_report = crud.get_attendance_report_by_teacher(db)
        
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
    
    context = {
        "request": request,
        "courses": courses,
        "students": students,
        "teachers": teachers,
        "staff_users": staff_users,
        "attendances": attendances_with_details,
        "attendance_report": attendance_report,
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
def teacher_panel(request: Request, db: Session = Depends(get_db)):
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
    teacher_id = user.get("teacher_id")
    if not teacher_id:
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
        lessons_with_students = crud.lessons_with_students_by_teacher(db, teacher_id)
        from datetime import datetime
        weekday_map = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        formatted_lessons = []
        for entry in lessons_with_students:
            lesson = entry["lesson"]
            weekday = weekday_map[lesson.lesson_date.weekday()] if hasattr(lesson.lesson_date, "weekday") else ""
            formatted_lessons.append({
                "weekday": weekday,
                "lesson": lesson,
                "students": entry["students"],
            })
        # Öğretmene atanmış öğrencileri getir
        teacher_students = []
        if teacher_id:
            try:
                teacher_students = crud.list_students_by_teacher(db, teacher_id)
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
                                models.TeacherStudent.teacher_id == teacher_id
                            )
                        ).first()
                        if link:
                            teacher_students.append(student)
            except Exception as e:
                # Hata durumunda boş liste döndür
                import logging
                logging.error(f"Öğrenci listesi hatası: {e}")
                teacher_students = []
        context = {
            "request": request,
            "lessons_with_students": formatted_lessons,
            "teacher_students": teacher_students,
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
def payment_form(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    redirect = redirect_teacher(request.session.get("user"))
    if redirect:
        return redirect
    students = crud.list_students(db)
    return templates.TemplateResponse("payment_new.html", {"request": request, "students": students})


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
    
    # Dilersen derse yoklama otomatik açabilirsin...
    return RedirectResponse(url=f"/lessons/{lesson.id}/attendance/new", status_code=302)


@app.get("/lessons/{lesson_id}/attendance/new", response_class=HTMLResponse)
def attendance_form(lesson_id: int, request: Request, db: Session = Depends(get_db)):
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
    
    default_attendance_date = lesson.lesson_date or date_cls.today()
    return templates.TemplateResponse(
        "attendance_new.html",
        {
            "request": request,
            "lesson": lesson,
            "students_with_status": students_with_payment_status,
            "attendance_date": default_attendance_date.isoformat(),
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
    attendance_date_raw = form.get("attendance_date")
    marked_at_dt = None
    if attendance_date_raw:
        try:
            from datetime import date as date_cls, datetime, time as time_cls
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
    import logging
    
    # Önce tüm form değerlerini logla
    logging.info(f"=== FORM VERİLERİ ===")
    logging.info(f"Ders ID: {lesson_id}")
    for key, value in form.items():
        if key.startswith("status_"):
            logging.info(f"  {key} = '{value}'")
    
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
            logging.warning(f"Öğrenci {sid} bu derse atanmamış, atlanıyor")
            continue
        
        # Form'dan gelen değeri al - DEĞİŞTİRME, OLDUĞU GİBİ KULLAN
        status_raw = (value or "").strip()
        
        # Boş değerleri atla
        if not status_raw:
            logging.info(f"Öğrenci {sid}: Boş değer, atlanıyor")
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
        logging.info(f"✅ Öğrenci {sid}: {status} ({status_map.get(status, 'Bilinmeyen')})")
        
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
        request.session["attendance_errors"] = "Yoklama verisi bulunamadı. Lütfen öğrenci durumlarını seçin."
        user = request.session.get("user")
        if user and user.get("role") == "teacher":
            return RedirectResponse(url="/ui/teacher", status_code=302)
        return RedirectResponse(url="/dashboard", status_code=302)
    
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
            
            # Önce mevcut kaydı kontrol et
            existing = db.scalars(
                select(models.Attendance).where(
                    models.Attendance.lesson_id == item.lesson_id,
                    models.Attendance.student_id == item.student_id
                )
            ).first()
            
            if existing:
                # Mevcut kaydı güncelle
                existing.status = str(item.status).strip().upper()
                if item.marked_at:
                    existing.marked_at = item.marked_at
                logging.info(f"[{item.student_id}] Mevcut kayıt güncelleniyor: {existing.status}")
                
                # #region agent log
                import json, os, time
                log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cursor", "debug.log")
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"id": f"log_{int(time.time())}_{item.student_id}_update", "timestamp": int(time.time() * 1000), "location": "main.py:1183", "message": "Existing attendance record updated", "data": {"student_id": item.student_id, "lesson_id": item.lesson_id, "existing_id": existing.id, "old_status": existing.status, "new_status": str(item.status).strip().upper()}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
                except Exception as e:
                    import logging
                    logging.error(f"Debug log error: {e}")
                # #endregion
            else:
                # Yeni kayıt oluştur
                from datetime import datetime
                attendance = models.Attendance(
                    lesson_id=item.lesson_id,
                    student_id=item.student_id,
                    status=str(item.status).strip().upper(),
                    marked_at=item.marked_at or datetime.utcnow()
                )
                db.add(attendance)
                logging.info(f"[{item.student_id}] Yeni kayıt oluşturuluyor: {attendance.status}")
                
                # #region agent log
                import json, os, time
                log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cursor", "debug.log")
                try:
                    os.makedirs(os.path.dirname(log_path), exist_ok=True)
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"id": f"log_{int(time.time())}_{item.student_id}_create", "timestamp": int(time.time() * 1000), "location": "main.py:1218", "message": "New attendance record created", "data": {"student_id": item.student_id, "lesson_id": item.lesson_id, "status": attendance.status}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
                except Exception as e:
                    import logging
                    logging.error(f"Debug log error: {e}")
                # #endregion
            
            # Hemen commit et - exception handling ile
            try:
                db.commit()
                # Refresh yap
                if existing:
                    db.refresh(existing)
                else:
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
                attendance_id = existing.id if existing else (attendance.id if 'attendance' in locals() else None)
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
    return templates.TemplateResponse("student_detail.html", {"request": request, "student": student, "payments": payments, "enrollments": enrollments})


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
def payment_reports(request: Request, start: str | None = None, end: str | None = None, course_id: str | None = None, teacher_id: str | None = None, db: Session = Depends(get_db)):
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
    
    # query payments with optional filters and total sum
    q = db.query(models.Payment).join(models.Student)
    # optional joins for filters
    # Filter by course or teacher through enrollments and lessons/payments if needed (basic: by course via enrollments)
    if course_id_int:
        q = q.join(models.Enrollment, models.Enrollment.student_id == models.Payment.student_id).filter(models.Enrollment.course_id == course_id_int)
    if teacher_id_int:
        # teacher filter via lessons attendance isn't a direct relation to payment; skipping complex join; use lessons for date context only
        pass
    if start_date:
        q = q.filter(models.Payment.payment_date >= start_date)
    if end_date:
        q = q.filter(models.Payment.payment_date <= end_date)
    items = q.order_by(models.Payment.payment_date.desc()).all()
    sum_q = db.query(func.coalesce(func.sum(models.Payment.amount_try), 0)).join(models.Student)
    if course_id_int:
        sum_q = sum_q.join(models.Enrollment, models.Enrollment.student_id == models.Payment.student_id).filter(models.Enrollment.course_id == course_id_int)
    if start_date:
        sum_q = sum_q.filter(models.Payment.payment_date >= start_date)
    if end_date:
        sum_q = sum_q.filter(models.Payment.payment_date <= end_date)
    total = float(sum_q.scalar() or 0)
    courses = crud.list_courses(db)
    teachers = crud.list_teachers(db)
    return templates.TemplateResponse("reports_payments.html", {"request": request, "items": items, "total": total, "start": start or "", "end": end or "", "courses": courses, "teachers": teachers, "course_id": course_id or "", "teacher_id": teacher_id or ""})


@app.get("/ui/reports/payments.csv")
def payment_reports_csv(request: Request, start: str | None = None, end: str | None = None, course_id: str | None = None, teacher_id: str | None = None, db: Session = Depends(get_db)):
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
    
    q = db.query(models.Payment).join(models.Student)
    if course_id_int:
        q = q.join(models.Enrollment, models.Enrollment.student_id == models.Payment.student_id).filter(models.Enrollment.course_id == course_id_int)
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
def staff_panel(request: Request, search: str | None = None, student_id: int | None = None, db: Session = Depends(get_db)):
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
                formatted_lessons.append({
                    "weekday": weekday,
                    "lesson": lesson,
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
        
        if student_id:
            # Seçilen öğrencinin bilgilerini ve derslerini getir
            selected_student = crud.get_student(db, student_id)
            if selected_student:
                student_lessons = crud.list_lessons_by_student(db, student_id)
                # Dersleri haftalık formata çevir
                from datetime import time as time_type
                for lesson in student_lessons:
                    weekday = weekday_map[lesson.lesson_date.weekday()] if hasattr(lesson.lesson_date, "weekday") else ""
                    # Öğrencinin bu derste kaçıncı ders olduğunu bul (aynı gün içinde)
                    same_day_lessons = [l for l in student_lessons if l.lesson_date == lesson.lesson_date]
                    # Start time'a göre sırala
                    same_day_lessons.sort(key=lambda x: x.start_time if x.start_time else time_type.min)
                    lesson_number = same_day_lessons.index(lesson) + 1 if lesson in same_day_lessons else None
                    student_lessons_formatted.append({
                        "weekday": weekday,
                        "lesson": lesson,
                        "lesson_number": lesson_number,
                        "total_same_day": len(same_day_lessons)
                    })
        
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
            
            # Beklenen ödeme seti hesapla: (toplam_ders // 4) + 1
            # +1 çünkü ilk kayıt ödemesi (0. ders) her zaman bekleniyor
            # 0 ders: 1 set (ilk kayıt)
            # 1-3 ders: 1 set (ilk kayıt)
            # 4-7 ders: 2 set (ilk kayıt + 4. ders)
            # 8-11 ders: 3 set (ilk kayıt + 4. ders + 8. ders)
            # 12-15 ders: 4 set
            # ...
            expected_paid_sets = (total_lessons // 4) + 1
            
            # En son ödeme tarihi
            last_payment_date = None
            if payments:
                last_payment_date = payments[0].payment_date  # Zaten tarihe göre sıralı (en yeni önce)
            
            # Ödeme durumu kontrolü
            # Ödeme yetersizse kırmızı
            needs_payment = total_paid_sets < expected_paid_sets
            
            payment_status_list.append({
                "student": student,
                "total_lessons": total_lessons,
                "expected_paid_sets": expected_paid_sets,
                "total_paid_sets": total_paid_sets,
                "last_payment_date": last_payment_date,
                "needs_payment": needs_payment,
                "payment_status": "✅ Ödendi" if not needs_payment else "⚠️ Ödeme Gerekli"
            })
        
        # Ödeme durumuna göre sırala (önce ödeme gerekli olanlar)
        payment_status_list.sort(key=lambda x: (not x["needs_payment"], x["student"].first_name, x["student"].last_name))
        
        return templates.TemplateResponse("staff_panel.html", {
            "request": request,
            "teachers_schedules": teachers_schedules,
            "search": search or "",
            "search_results": search_results,
            "selected_student": selected_student,
            "student_lessons": student_lessons_formatted,
            "payment_status_list": payment_status_list,
            "today": today
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


