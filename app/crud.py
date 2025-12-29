from sqlalchemy.orm import Session
from sqlalchemy import select, func, delete
from datetime import date
from . import models, schemas


# Users
def create_user(db: Session, data: schemas.UserCreate):
	from passlib.hash import pbkdf2_sha256
	password_hash = pbkdf2_sha256.hash(data.password)
	user = models.User(username=data.username, password_hash=password_hash, full_name=data.full_name, role=getattr(data, 'role', None), teacher_id=getattr(data, 'teacher_id', None))
	db.add(user)
	db.commit()
	db.refresh(user)
	return user


def get_user_by_username(db: Session, username: str):
	stmt = select(models.User).where(models.User.username == username)
	return db.scalars(stmt).first()


def list_users(db: Session):
	return db.scalars(select(models.User).order_by(models.User.created_at.desc())).all()


def update_user_password(db: Session, user_id: int, new_password: str):
	from passlib.hash import pbkdf2_sha256
	user = db.get(models.User, user_id)
	if not user:
		return None
	user.password_hash = pbkdf2_sha256.hash(new_password)
	db.commit()
	db.refresh(user)
	return user

# Students
def create_student(db: Session, data: schemas.StudentCreate) -> models.Student:
	student = models.Student(**data.model_dump())
	db.add(student)
	db.commit()
	db.refresh(student)
	return student


def list_students(db: Session):
	return db.scalars(select(models.Student).order_by(models.Student.created_at.desc())).all()


def find_student_by_name(db: Session, first_name: str, last_name: str):
	stmt = select(models.Student).where(
		func.lower(models.Student.first_name) == func.lower(first_name),
		func.lower(models.Student.last_name) == func.lower(last_name),
	)
	return db.scalars(stmt).first()


def get_student(db: Session, student_id: int):
	return db.get(models.Student, student_id)


def update_student(db: Session, student_id: int, data: schemas.StudentUpdate):
	student = db.get(models.Student, student_id)
	if not student:
		return None
	for k, v in data.model_dump(exclude_unset=True).items():
		setattr(student, k, v)
	db.commit()
	db.refresh(student)
	return student


# Teachers
def create_teacher(db: Session, data: schemas.TeacherCreate):
	teacher = models.Teacher(**data.model_dump())
	db.add(teacher)
	db.commit()
	db.refresh(teacher)
	return teacher


def update_teacher(db: Session, teacher_id: int, data: schemas.TeacherUpdate):
	teacher = db.get(models.Teacher, teacher_id)
	if not teacher:
		return None
	for k, v in data.model_dump(exclude_unset=True).items():
		setattr(teacher, k, v)
	db.commit()
	db.refresh(teacher)
	return teacher


def list_teachers(db: Session):
	return db.scalars(select(models.Teacher).order_by(models.Teacher.created_at.desc())).all()


def get_teacher(db: Session, teacher_id: int):
	return db.get(models.Teacher, teacher_id)


def find_teacher_by_name(db: Session, first_name: str, last_name: str):
	stmt = select(models.Teacher).where(
		func.lower(models.Teacher.first_name) == func.lower(first_name),
		func.lower(models.Teacher.last_name) == func.lower(last_name),
	)
	return db.scalars(stmt).first()


def get_or_create_teacher(db: Session, first_name: str, last_name: str):
	teacher = find_teacher_by_name(db, first_name, last_name)
	if teacher:
		return teacher, False
	payload = schemas.TeacherCreate(first_name=first_name, last_name=last_name)
	teacher = create_teacher(db, payload)
	return teacher, True


def assign_student_to_teacher(db: Session, teacher_id: int, student_id: int, commit: bool = False):
	link = db.scalars(select(models.TeacherStudent).where(models.TeacherStudent.student_id == student_id)).first()
	if link:
		if link.teacher_id != teacher_id:
			link.teacher_id = teacher_id
			if commit:
				db.commit()
				db.refresh(link)
		return link
	link = models.TeacherStudent(teacher_id=teacher_id, student_id=student_id)
	db.add(link)
	if commit:
		db.commit()
		db.refresh(link)
	return link


def list_students_by_teacher(db: Session, teacher_id: int):
	# Öğretmene atanmış öğrencileri getir
	try:
		stmt = (
			select(models.Student)
			.join(models.TeacherStudent, models.TeacherStudent.student_id == models.Student.id)
			.where(models.TeacherStudent.teacher_id == teacher_id)
			.order_by(models.Student.first_name.asc(), models.Student.last_name.asc())
		)
		students = db.scalars(stmt).all()
		return list(students) if students else []
	except Exception:
		# Hata durumunda boş liste döndür
		return []


def reset_teacher_student_links(db: Session):
	db.execute(delete(models.TeacherStudent))
	db.commit()


def delete_attendance(db: Session, attendance_id: int):
	"""Tek bir yoklama kaydını sil ve öğrenciyi dersten çıkar"""
	import logging
	import sys
	
	# Logları hem console'a hem de dosyaya yaz
	logging.basicConfig(
		level=logging.INFO,
		format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
		handlers=[
			logging.StreamHandler(sys.stdout),
			logging.FileHandler('attendance_deletion.log', encoding='utf-8')
		]
	)
	
	attendance = db.get(models.Attendance, attendance_id)
	if not attendance:
		logging.warning(f"❌ Yoklama kaydı bulunamadı: ID={attendance_id}")
		return None
	
	lesson_id = attendance.lesson_id
	student_id = attendance.student_id
	
	logging.info(f"🔍 Yoklama silme işlemi başlatıldı: ID={attendance_id}, Öğrenci={student_id}, Ders={lesson_id}")
	
	# SİLME ÖNCESİ DURUM KONTROLÜ
	lesson_student_before = db.scalars(
		select(models.LessonStudent)
		.where(models.LessonStudent.lesson_id == lesson_id, models.LessonStudent.student_id == student_id)
	).first()
	
	attendances_before = db.scalars(
		select(models.Attendance)
		.where(models.Attendance.lesson_id == lesson_id, models.Attendance.student_id == student_id)
	).all()
	
	logging.info(f"📊 SİLME ÖNCESİ DURUM:")
	logging.info(f"   - LessonStudent ilişkisi var mı: {lesson_student_before is not None}")
	logging.info(f"   - Toplam yoklama kaydı sayısı: {len(attendances_before)}")
	
	# Yoklama kaydını sil
	db.delete(attendance)
	logging.info(f"✅ Yoklama kaydı silindi: ID={attendance_id}")
	
	# Öğrenciyi o dersten çıkar (LessonStudent ilişkisini sil)
	lesson_student = db.scalars(
		select(models.LessonStudent)
		.where(models.LessonStudent.lesson_id == lesson_id, models.LessonStudent.student_id == student_id)
	).first()
	
	if lesson_student:
		logging.info(f"✅ LessonStudent ilişkisi bulundu ve siliniyor: Ders={lesson_id}, Öğrenci={student_id}")
		db.delete(lesson_student)
		logging.info(f"✅ LessonStudent ilişkisi silindi")
	else:
		logging.warning(f"⚠️ LessonStudent ilişkisi bulunamadı: Ders={lesson_id}, Öğrenci={student_id}")
	
	# Commit öncesi flush yap
	db.flush()
	logging.info(f"🔄 Flush yapıldı")
	
	# Commit yap
	db.commit()
	logging.info(f"💾 Commit yapıldı")
	
	# SİLME SONRASI DURUM KONTROLÜ (yeni session ile)
	from .db import SessionLocal
	check_db = SessionLocal()
	try:
		lesson_student_after = check_db.scalars(
			select(models.LessonStudent)
			.where(models.LessonStudent.lesson_id == lesson_id, models.LessonStudent.student_id == student_id)
		).first()
		
		attendances_after = check_db.scalars(
			select(models.Attendance)
			.where(models.Attendance.lesson_id == lesson_id, models.Attendance.student_id == student_id)
		).all()
		
		logging.info(f"📊 SİLME SONRASI DURUM:")
		logging.info(f"   - LessonStudent ilişkisi var mı: {lesson_student_after is not None}")
		logging.info(f"   - Toplam yoklama kaydı sayısı: {len(attendances_after)}")
		
		if lesson_student_after:
			logging.error(f"❌ HATA: LessonStudent ilişkisi hala var! ID={lesson_student_after.id}")
		else:
			logging.info(f"✅ BAŞARILI: LessonStudent ilişkisi silindi")
			
		if len(attendances_after) > 0:
			logging.warning(f"⚠️ UYARI: Hala {len(attendances_after)} yoklama kaydı var")
		else:
			logging.info(f"✅ BAŞARILI: Tüm yoklama kayıtları silindi")
	finally:
		check_db.close()
	
	logging.info(f"✅ Yoklama silme işlemi tamamlandı: ID={attendance_id}")
	return attendance


def delete_all_attendances(db: Session):
	"""Tüm yoklama kayıtlarını sil"""
	from sqlalchemy import delete
	import logging
	logging.warning("Tüm yoklama kayıtları siliniyor...")
	result = db.execute(delete(models.Attendance))
	count = result.rowcount
	db.commit()
	logging.warning(f"{count} yoklama kaydı silindi")
	return count


# Courses
def create_course(db: Session, name: str):
	course = models.Course(name=name)
	db.add(course)
	db.commit()
	db.refresh(course)
	return course


def create_course_from_schema(db: Session, data: schemas.CourseCreate):
	course = models.Course(**data.model_dump())
	db.add(course)
	db.commit()
	db.refresh(course)
	return course


def get_course(db: Session, course_id: int):
	return db.get(models.Course, course_id)


def get_course_by_name(db: Session, name: str):
	stmt = select(models.Course).where(models.Course.name == name)
	return db.scalars(stmt).first()


def update_course(db: Session, course_id: int, data: schemas.CourseUpdate):
	course = db.get(models.Course, course_id)
	if not course:
		return None
	for k, v in data.model_dump(exclude_unset=True).items():
		setattr(course, k, v)
	db.commit()
	db.refresh(course)
	return course


def delete_course(db: Session, course_id: int):
	course = db.get(models.Course, course_id)
	if not course:
		return False
	db.delete(course)
	db.commit()
	return True


def list_courses(db: Session):
	return db.scalars(select(models.Course).order_by(models.Course.name)).all()


# Enrollment
def enroll_student(db: Session, student_id: int, course_id: int, commit: bool = True):
	# Önce kontrol et, zaten kayıtlı mı?
	existing = db.scalars(
		select(models.Enrollment)
		.where(models.Enrollment.student_id == student_id, models.Enrollment.course_id == course_id)
	).first()
	if existing:
		return existing
	enrollment = models.Enrollment(student_id=student_id, course_id=course_id)
	db.add(enrollment)
	if commit:
		db.commit()
		db.refresh(enrollment)
	return enrollment


# Lesson Students
def assign_student_to_lesson(db: Session, lesson_id: int, student_id: int):
	# Öğrenci zaten bu derse atanmış mı kontrol et
	existing = db.scalars(
		select(models.LessonStudent)
		.where(models.LessonStudent.lesson_id == lesson_id, models.LessonStudent.student_id == student_id)
	).first()
	if existing:
		return existing
	link = models.LessonStudent(lesson_id=lesson_id, student_id=student_id)
	db.add(link)
	# commit yapma, çağıran fonksiyon commit yapacak
	return link


def list_students_by_lesson(db: Session, lesson_id: int):
	stmt = (
		select(models.Student)
		.join(models.LessonStudent, models.LessonStudent.student_id == models.Student.id)
		.where(models.LessonStudent.lesson_id == lesson_id)
		.order_by(models.Student.first_name.asc(), models.Student.last_name.asc())
	)
	return db.scalars(stmt).all()


# Lessons
def create_lesson(db: Session, data: schemas.LessonCreate):
	lesson = models.Lesson(**data.model_dump())
	db.add(lesson)
	db.commit()
	db.refresh(lesson)
	return lesson


def get_lesson(db: Session, lesson_id: int):
	return db.get(models.Lesson, lesson_id)


def update_lesson(db: Session, lesson_id: int, data: schemas.LessonUpdate):
	lesson = db.get(models.Lesson, lesson_id)
	if not lesson:
		return None
	for k, v in data.model_dump(exclude_unset=True).items():
		setattr(lesson, k, v)
	db.commit()
	db.refresh(lesson)
	return lesson


def delete_lesson(db: Session, lesson_id: int):
	lesson = db.get(models.Lesson, lesson_id)
	if not lesson:
		return False
	db.delete(lesson)
	db.commit()
	return True


def list_lessons_by_teacher(db: Session, teacher_id: int):
	stmt = select(models.Lesson).where(models.Lesson.teacher_id == teacher_id).order_by(models.Lesson.lesson_date.asc(), models.Lesson.start_time.asc())
	return db.scalars(stmt).all()


def list_lessons_by_student(db: Session, student_id: int):
	"""Öğrencinin atandığı dersleri getirir (LessonStudent tablosu üzerinden)"""
	stmt = (
		select(models.Lesson)
		.join(models.LessonStudent, models.LessonStudent.lesson_id == models.Lesson.id)
		.where(models.LessonStudent.student_id == student_id)
		.order_by(models.Lesson.lesson_date.asc(), models.Lesson.start_time.asc())
	)
	return db.scalars(stmt).all()


def lessons_with_students_by_teacher(db: Session, teacher_id: int):
	from sqlalchemy.orm import joinedload
	# Öğretmene ait tüm dersleri getir (tarih ve saat sırasına göre)
	lessons = db.query(models.Lesson).options(
		joinedload(models.Lesson.course),
		joinedload(models.Lesson.teacher)
	).filter(models.Lesson.teacher_id == teacher_id).order_by(
		models.Lesson.lesson_date.asc(),
		models.Lesson.start_time.asc()
	).all()
	
	out = []
	for lesson in lessons:
		# Her ders için, sadece o derse özel olarak atanmış öğrencileri getir
		lesson_students = list_students_by_lesson(db, lesson.id)
		out.append({"lesson": lesson, "students": lesson_students})
	return out


# Attendance
def mark_attendance(db: Session, data: schemas.AttendanceCreate, commit: bool = True):
	# Her yoklama ayrı bir kayıt olarak oluşturulur - mevcut kayıt kontrolü yok
	import logging
	from datetime import datetime
	
	attendance = models.Attendance(
		lesson_id=data.lesson_id,
		student_id=data.student_id,
		status=str(data.status).strip().upper(),
		marked_at=data.marked_at if hasattr(data, 'marked_at') and data.marked_at else datetime.utcnow(),
		note=data.note if hasattr(data, 'note') and data.note else None
	)
	db.add(attendance)
	
	if commit:
		db.commit()
		db.refresh(attendance)
		logging.info(f"Yeni yoklama kaydı oluşturuldu: Öğrenci {data.student_id}, Ders {data.lesson_id}, Durum: {attendance.status}")
	else:
		db.flush()
		logging.info(f"Yoklama session'a yazıldı (commit=False): Öğrenci {data.student_id}, Durum: {attendance.status}")
	
	return attendance


def list_attendance_for_lesson(db: Session, lesson_id: int):
	stmt = select(models.Attendance).where(models.Attendance.lesson_id == lesson_id)
	return db.scalars(stmt).all()


def list_all_attendances(db: Session, limit: int = 100, teacher_id: int | None = None, student_id: int | None = None, course_id: int | None = None, status: str | None = None, start_date: date | None = None, end_date: date | None = None, order_by: str = "marked_at_desc"):
	# #region agent log
	import json, os, time
	log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cursor", "debug.log")
	try:
		os.makedirs(os.path.dirname(log_path), exist_ok=True)
		with open(log_path, "a", encoding="utf-8") as f:
			f.write(json.dumps({"id": f"log_{int(time.time())}_list_entry", "timestamp": int(time.time() * 1000), "location": "crud.py:399", "message": "list_all_attendances called", "data": {"teacher_id": teacher_id, "student_id": student_id, "course_id": course_id, "status": status, "limit": limit}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "B"}) + "\n")
	except Exception as e:
		import logging
		logging.error(f"Debug log error: {e}")
	# #endregion
	
	# Tüm yoklamaları getir
	# Join gerekip gerekmediğini kontrol et (tarih filtreleri artık marked_at'e göre, lesson_date'e gerek yok)
	needs_join = teacher_id is not None or course_id is not None
	
	# Always use LEFT JOIN to ensure all attendances are included, even if lesson is missing
	# This prevents filtering out attendances with orphaned lesson references
	# IMPORTANT: Even if no filters need join, we still join to be able to access lesson data in dashboard
	if needs_join:
		stmt = select(models.Attendance).outerjoin(models.Lesson, models.Attendance.lesson_id == models.Lesson.id)
	else:
		# Even without filters, join to access lesson data (but use outerjoin to not filter out orphaned records)
		stmt = select(models.Attendance).outerjoin(models.Lesson, models.Attendance.lesson_id == models.Lesson.id)
	
	# Filtreleme
	if teacher_id:
		stmt = stmt.where(models.Lesson.teacher_id == teacher_id)
	if student_id:
		stmt = stmt.where(models.Attendance.student_id == student_id)
	if course_id:
		stmt = stmt.where(models.Lesson.course_id == course_id)
	if status:
		stmt = stmt.where(models.Attendance.status == status.upper())
	# Tarih filtreleri artık yoklama zamanına (marked_at) göre
	if start_date:
		from datetime import datetime
		start_datetime = datetime.combine(start_date, datetime.min.time())
		stmt = stmt.where(models.Attendance.marked_at >= start_datetime)
	if end_date:
		from datetime import datetime
		end_datetime = datetime.combine(end_date, datetime.max.time())
		stmt = stmt.where(models.Attendance.marked_at <= end_datetime)
	
	# Sıralama - artık sadece marked_at'e göre (lesson_date kaldırıldı)
	if order_by == "marked_at_desc" or order_by == "lesson_date_desc":
		stmt = stmt.order_by(models.Attendance.marked_at.desc())
	elif order_by == "marked_at_asc" or order_by == "lesson_date_asc":
		stmt = stmt.order_by(models.Attendance.marked_at.asc())
	else:
		stmt = stmt.order_by(models.Attendance.marked_at.desc())
	
	stmt = stmt.limit(limit)
	
	# #region agent log - Log the SQL query
	import json, os, time
	log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cursor", "debug.log")
	try:
		os.makedirs(os.path.dirname(log_path), exist_ok=True)
		with open(log_path, "a", encoding="utf-8") as f:
			f.write(json.dumps({"id": f"log_{int(time.time())}_list_query", "timestamp": int(time.time() * 1000), "location": "crud.py:447", "message": "list_all_attendances SQL query", "data": {"needs_join": needs_join, "has_teacher_filter": teacher_id is not None, "has_course_filter": course_id is not None, "has_date_filter": start_date is not None or end_date is not None, "limit": limit}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "B"}) + "\n")
	except Exception as e:
		import logging
		logging.error(f"Debug log error: {e}")
	# #endregion
	
	result = db.scalars(stmt).all()
	
	# #region agent log
	try:
		os.makedirs(os.path.dirname(log_path), exist_ok=True)
		with open(log_path, "a", encoding="utf-8") as f:
			f.write(json.dumps({"id": f"log_{int(time.time())}_list_result", "timestamp": int(time.time() * 1000), "location": "crud.py:456", "message": "list_all_attendances result", "data": {"count": len(result), "attendance_ids": [a.id for a in result], "lesson_ids": list(set([a.lesson_id for a in result])), "student_ids": list(set([a.student_id for a in result]))}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "B"}) + "\n")
	except Exception as e:
		import logging
		logging.error(f"Debug log error: {e}")
	# #endregion
	
	return result


# Payments
def create_payment(db: Session, data: schemas.PaymentCreate):
	payload = data.model_dump()
	if not payload.get("payment_date"):
		payload["payment_date"] = None  # default handled by model
	payment = models.Payment(**payload)
	db.add(payment)
	db.commit()
	db.refresh(payment)
	return payment


def list_payments_by_student(db: Session, student_id: int):
	stmt = select(models.Payment).where(models.Payment.student_id == student_id).order_by(models.Payment.payment_date.desc())
	return db.scalars(stmt).all()


def get_payment(db: Session, payment_id: int):
	"""Ödeme kaydını getirir"""
	return db.get(models.Payment, payment_id)


def update_payment(db: Session, payment_id: int, data: schemas.PaymentUpdate):
	"""Ödeme kaydını günceller"""
	payment = db.get(models.Payment, payment_id)
	if not payment:
		return None
	payload = data.model_dump()
	if not payload.get("payment_date"):
		payload["payment_date"] = None
	for key, value in payload.items():
		setattr(payment, key, value)
	db.commit()
	db.refresh(payment)
	return payment


def delete_payment(db: Session, payment_id: int):
	"""Ödeme kaydını siler"""
	payment = db.get(models.Payment, payment_id)
	if payment:
		db.delete(payment)
		db.commit()
		return True
	return False


def check_student_payment_status(db: Session, student_id: int):
	"""Öğrencinin ödeme durumunu kontrol eder - ödeme gerekip gerekmediğini döndürür"""
	from datetime import date
	today = date.today()
	
	# Öğrencinin toplam ders sayısını hesapla (PRESENT veya TELAFI)
	total_lessons = db.scalars(
		select(func.count(models.Attendance.id))
		.where(
			models.Attendance.student_id == student_id,
			models.Attendance.status.in_(["PRESENT", "TELAFI", "LATE"])  # LATE eski kayıtlar için
		)
	).first() or 0
	
	# Öğrencinin ödemelerini getir
	payments = list_payments_by_student(db, student_id)
	total_paid_sets = len(payments)
	
	# Beklenen ödeme seti hesapla: (toplam_ders // 4) + 1
	expected_paid_sets = (total_lessons // 4) + 1
	
	# Ödeme yetersizse True döndür
	return total_paid_sets < expected_paid_sets


def list_students_needing_payment(db: Session):
	"""Ödeme gerekli olan tüm öğrencileri listeler"""
	all_students = list_students(db)
	students_needing_payment = []
	
	for student in all_students:
		if check_student_payment_status(db, student.id):
			students_needing_payment.append(student)
	
	return students_needing_payment


# Invoices
def create_invoice(db: Session, data: schemas.InvoiceCreate):
    invoice = models.Invoice(**data.model_dump())
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


def list_invoices(db: Session, status: str | None = None):
    stmt = select(models.Invoice)
    if status:
        stmt = stmt.where(models.Invoice.status == status)
    return db.scalars(stmt.order_by(models.Invoice.due_date.asc())).all()


def list_invoices_by_student(db: Session, student_id: int):
    stmt = select(models.Invoice).where(models.Invoice.student_id == student_id).order_by(models.Invoice.due_date.asc())
    return db.scalars(stmt).all()


def mark_overdue_invoices(db: Session):
    from datetime import date
    # naive bulk update
    items = db.scalars(select(models.Invoice).where(models.Invoice.status == "PENDING", models.Invoice.due_date < date.today())).all()
    updated = 0
    for inv in items:
        inv.status = "OVERDUE"
        updated += 1
    if updated:
        db.commit()
    return updated


def get_attendance_report_by_teacher(db: Session, teacher_id: int | None = None, student_id: int | None = None, course_id: int | None = None, start_date: date | None = None, end_date: date | None = None):
    """Öğretmenlere göre yoklama raporu oluşturur. Filtreleme parametreleri ile çalışır."""
    # #region agent log
    import json, os, time
    log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cursor", "debug.log")
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"id": f"log_{int(time.time())}_report_entry", "timestamp": int(time.time() * 1000), "location": "crud.py:541", "message": "get_attendance_report_by_teacher called", "data": {}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "B"}) + "\n")
    except Exception as e:
        import logging
        logging.error(f"Debug log error: {e}")
    # #endregion
    
    # Öğretmen filtresi varsa sadece o öğretmeni al, yoksa tüm öğretmenleri al
    if teacher_id:
        teachers = [db.get(models.Teacher, teacher_id)] if db.get(models.Teacher, teacher_id) else []
    else:
        teachers = list_teachers(db)
    report = []
    
    for teacher in teachers:
        if not teacher:
            continue
        # Öğretmene ait tüm dersleri getir
        lessons = list_lessons_by_teacher(db, teacher.id)
        lesson_ids = [lesson.id for lesson in lessons]
        
        # #region agent log
        import json, os, time
        log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cursor", "debug.log")
        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"id": f"log_{int(time.time())}_report_teacher", "timestamp": int(time.time() * 1000), "location": "crud.py:557", "message": "Teacher lessons fetched", "data": {"teacher_id": teacher.id, "lesson_count": len(lessons), "lesson_ids": lesson_ids}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "C"}) + "\n")
        except Exception as e:
            import logging
            logging.error(f"Debug log error: {e}")
        # #endregion
        
        if not lesson_ids:
            continue
        
        # Bu derslere ait tüm yoklamaları getir
        # #region agent log - Before query
        import json, os, time
        log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cursor", "debug.log")
        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            # First check all attendances directly
            all_attendances_all_lessons = db.scalars(select(models.Attendance)).all()
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"id": f"log_{int(time.time())}_report_before_query", "timestamp": int(time.time() * 1000), "location": "crud.py:569", "message": "Before query - all attendances in DB", "data": {"teacher_id": teacher.id, "lesson_ids": lesson_ids, "total_attendances_in_db": len(all_attendances_all_lessons), "all_lesson_ids_in_db": list(set([a.lesson_id for a in all_attendances_all_lessons]))}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "D"}) + "\n")
        except Exception as e:
            import logging
            logging.error(f"Debug log error: {e}")
        # #endregion
        
        # Yoklamaları getir
        stmt = select(models.Attendance).where(
            models.Attendance.lesson_id.in_(lesson_ids)
        )
        
        # Öğrenci filtresi
        if student_id:
            stmt = stmt.where(models.Attendance.student_id == student_id)
        
        attendances = db.scalars(stmt).all()
        
        # Kurs ve tarih filtrelerini uygula (lesson bilgisi gerektiği için Python'da filtrele)
        if course_id or start_date or end_date:
            filtered_attendances = []
            for att in attendances:
                lesson = db.get(models.Lesson, att.lesson_id)
                if not lesson:
                    continue
                
                # Kurs filtresi
                if course_id and lesson.course_id != course_id:
                    continue
                
                # Tarih filtreleri - yoklama zamanına (marked_at) göre
                if start_date:
                    if att.marked_at:
                        attendance_date = att.marked_at.date() if hasattr(att.marked_at, 'date') else att.marked_at
                        if attendance_date < start_date:
                            continue
                    else:
                        continue  # marked_at yoksa atla
                if end_date:
                    if att.marked_at:
                        attendance_date = att.marked_at.date() if hasattr(att.marked_at, 'date') else att.marked_at
                        if attendance_date > end_date:
                            continue
                    else:
                        continue  # marked_at yoksa atla
                
                filtered_attendances.append(att)
            attendances = filtered_attendances
        
        # #region agent log
        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"id": f"log_{int(time.time())}_report_attendances", "timestamp": int(time.time() * 1000), "location": "crud.py:585", "message": "Attendances fetched for teacher", "data": {"teacher_id": teacher.id, "attendance_count": len(attendances), "attendance_ids": [a.id for a in attendances], "lesson_ids_in_attendances": list(set([a.lesson_id for a in attendances])), "expected_lesson_ids": lesson_ids}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "B"}) + "\n")
        except Exception as e:
            import logging
            logging.error(f"Debug log error: {e}")
        # #endregion
        
        # Resim kursu için özel hesaplama: Her yoklama kaydı için 1 ekleme yapılacak
        # Diğer kurslar için mevcut sistem aynı kalacak (her yoklama = 1 ders)
        
        # Öğrenci bazında grupla
        student_stats = {}
        for att in attendances:
            # Her yoklama için lesson bilgisini al
            lesson = db.get(models.Lesson, att.lesson_id)
            
            student_id = att.student_id
            if student_id not in student_stats:
                student = db.get(models.Student, student_id)
                if not student:
                    continue
                student_stats[student_id] = {
                    "student": student,
                    "present": 0,
                    "excused_absent": 0,
                    "telafi": 0,
                    "unexcused_absent": 0,
                    "total": 0,
                    "dates": []  # Yoklama tarihlerini saklamak için
                }
            
            # Yoklama zamanındaki tarihi kullan (marked_at)
            if att.marked_at:
                attendance_date = att.marked_at.date() if hasattr(att.marked_at, 'date') else att.marked_at
                date_str = attendance_date.strftime('%d.%m.%Y') if hasattr(attendance_date, 'strftime') else str(attendance_date)
            else:
                date_str = ''
            
            # Eski LATE değerlerini TELAFI olarak say (geriye dönük uyumluluk)
            # Eski ABSENT değerlerini UNEXCUSED_ABSENT olarak say (geriye dönük uyumluluk)
            status = att.status
            if status == "LATE":
                status = "TELAFI"
            elif status == "ABSENT":
                status = "UNEXCUSED_ABSENT"
            
            # Resim kursu kontrolü
            is_resim_course = lesson and lesson.course and lesson.course.name == "Resim"
            
            # Resim kursu için özel hesaplama:
            # - PRESENT, TELAFI -> öğretmen puantajına +1
            # - UNEXCUSED_ABSENT, EXCUSED_ABSENT -> öğretmen puantajına eklenmez (lesson_count = 0)
            # Diğer kurslar için: Her yoklama kaydı = 1 ders
            if is_resim_course:
                if status == "PRESENT" or status == "TELAFI":
                    lesson_count = 1  # Öğretmen puantajına eklenir
                else:
                    lesson_count = 0  # Öğretmen puantajına eklenmez
            else:
                lesson_count = 1  # Diğer kurslar için normal
            
            if status == "PRESENT":
                student_stats[student_id]["present"] += lesson_count
                student_stats[student_id]["total"] += lesson_count
                student_stats[student_id]["dates"].append(date_str)
            elif status == "EXCUSED_ABSENT":
                student_stats[student_id]["excused_absent"] += lesson_count
                student_stats[student_id]["dates"].append(date_str)
                # Haberli gelmedi durumunda toplam ders sayısına eklenmez
            elif status == "TELAFI":
                student_stats[student_id]["telafi"] += lesson_count
                student_stats[student_id]["total"] += lesson_count
                student_stats[student_id]["dates"].append(date_str)
            elif status == "UNEXCUSED_ABSENT":
                # Resim kursu için: Öğrenci puantajında görünür ama öğretmen puantajına eklenmez
                # Diğer kurslar için: Normal şekilde sayılır
                if is_resim_course:
                    # Öğrenci bazlı puantajda görünür (unexcused_absent artar)
                    student_stats[student_id]["unexcused_absent"] += 1
                    # Ama öğretmen puantajına eklenmez (lesson_count = 0, total'e eklenmez)
                    student_stats[student_id]["dates"].append(date_str)
                else:
                    # Diğer kurslar için normal
                    student_stats[student_id]["unexcused_absent"] += lesson_count
                    student_stats[student_id]["total"] += lesson_count
                    student_stats[student_id]["dates"].append(date_str)
        
        if student_stats:
            report.append({
                "teacher": teacher,
                "students": list(student_stats.values())
            })
    
    return report


