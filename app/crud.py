from sqlalchemy.orm import Session
from sqlalchemy import select, func, delete
from datetime import date, datetime
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


def list_students(db: Session, active_only: bool = False):
	stmt = select(models.Student)
	if active_only:
		stmt = stmt.where(models.Student.is_active == True)
	return db.scalars(stmt.order_by(models.Student.created_at.desc())).all()


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


def delete_student(db: Session, student_id: int) -> bool:
	"""Öğrenciyi ve ilişkili kayıtları (cascade) kalıcı olarak siler."""
	student = db.get(models.Student, student_id)
	if not student:
		return False
	db.delete(student)
	db.commit()
	return True


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


def list_teachers(db: Session, active_only: bool = True):
	stmt = select(models.Teacher).order_by(models.Teacher.created_at.desc())
	if active_only:
		stmt = stmt.where(models.Teacher.is_active == True)
	return db.scalars(stmt).all()


def delete_teacher(db: Session, teacher_id: int):
	"""Öğretmeni pasifleştirir; yoklama kayıtları korunur, öğrenci atamaları kaldırılır."""
	teacher = db.get(models.Teacher, teacher_id)
	if not teacher or not getattr(teacher, "is_active", True):
		return None

	# Öğrenci–öğretmen atamalarını kaldır (yeni öğretmene atanabilsinler)
	for link in db.scalars(
		select(models.TeacherStudent).where(models.TeacherStudent.teacher_id == teacher_id)
	).all():
		db.delete(link)

	# Öğretmen giriş hesaplarını sil
	for user in db.scalars(select(models.User).where(models.User.teacher_id == teacher_id)).all():
		db.delete(user)

	# Yoklaması olmayan ders programı slotlarını temizle; yoklamalı dersler kalır
	for lesson in list_lessons_by_teacher(db, teacher_id):
		attendance_count = db.scalar(
			select(func.count(models.Attendance.id)).where(models.Attendance.lesson_id == lesson.id)
		) or 0
		if int(attendance_count) == 0:
			db.delete(lesson)

	teacher.is_active = False
	db.commit()
	db.refresh(teacher)
	return teacher


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


def list_students_by_teacher(db: Session, teacher_id: int, active_only: bool = True):
	# Öğretmene atanmış öğrencileri getir
	try:
		stmt = (
			select(models.Student)
			.join(models.TeacherStudent, models.TeacherStudent.student_id == models.Student.id)
			.where(models.TeacherStudent.teacher_id == teacher_id)
		)
		if active_only:
			stmt = stmt.where(models.Student.is_active == True)
		stmt = stmt.order_by(models.Student.first_name.asc(), models.Student.last_name.asc())
		students = db.scalars(stmt).all()
		return list(students) if students else []
	except Exception:
		# Hata durumunda boş liste döndür
		return []


def reset_teacher_student_links(db: Session):
	db.execute(delete(models.TeacherStudent))
	db.commit()


def delete_attendance(db: Session, attendance_id: int):
	"""Tek bir yoklama kaydını sil (yalnızca ilgili attendance satırı)."""
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
	
	# KRİTİK: Yoklama silerken LessonStudent ilişkisine dokunma.
	# Aksi halde geçmiş/gelecek yoklama akışları beklenmedik şekilde etkilenebilir.
	lesson_student = db.scalars(
		select(models.LessonStudent)
		.where(models.LessonStudent.lesson_id == lesson_id, models.LessonStudent.student_id == student_id)
	).first()
	logging.info(
		f"ℹ️ LessonStudent ilişkisi korunuyor: Ders={lesson_id}, Öğrenci={student_id}, Var mı={lesson_student is not None}"
	)
	
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
			logging.info(f"✅ BAŞARILI: LessonStudent ilişkisi korundu. ID={lesson_student_after.id}")
		else:
			logging.warning(f"⚠️ UYARI: LessonStudent ilişkisi bulunmuyor")
			
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
def _enforce_single_student_slot_per_teacher_day(
	db: Session,
	teacher_id: int,
	student_id: int,
	target_lesson_id: int,
	target_weekday: int,
):
	"""
	Aynı öğretmen + aynı gün için öğrenciyi tek ders slotunda tutar.
	Hedef ders dışındaki LessonStudent kayıtlarını temizler.
	"""
	conflicting_links = db.scalars(
		select(models.LessonStudent)
		.join(models.Lesson, models.Lesson.id == models.LessonStudent.lesson_id)
		.where(
			models.LessonStudent.student_id == student_id,
			models.Lesson.teacher_id == teacher_id,
			models.Lesson.id != target_lesson_id,
		)
	).all()
	for link in conflicting_links:
		other_lesson = db.get(models.Lesson, link.lesson_id)
		if not other_lesson or not other_lesson.lesson_date:
			continue
		if other_lesson.lesson_date.weekday() == target_weekday:
			db.delete(link)


def assign_student_to_lesson(db: Session, lesson_id: int, student_id: int):
	lesson = db.get(models.Lesson, lesson_id)
	if lesson and lesson.lesson_date and lesson.teacher_id:
		_enforce_single_student_slot_per_teacher_day(
			db=db,
			teacher_id=lesson.teacher_id,
			student_id=student_id,
			target_lesson_id=lesson_id,
			target_weekday=lesson.lesson_date.weekday(),
		)
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


def remove_student_from_lesson(db: Session, lesson_id: int, student_id: int) -> bool:
	"""
	Öğrenciyi ders slotundan çıkarır (LessonStudent silinir).
	Geçmiş yoklama (Attendance), kurs kaydı ve öğretmen bağlantısına dokunulmaz.
	"""
	link = db.scalars(
		select(models.LessonStudent)
		.where(models.LessonStudent.lesson_id == lesson_id, models.LessonStudent.student_id == student_id)
	).first()
	if not link:
		return False
	db.delete(link)
	# commit yapma, çağıran fonksiyon commit yapacak
	return True


def list_students_by_lesson(db: Session, lesson_id: int, active_only: bool = True):
	stmt = (
		select(models.Student)
		.join(models.LessonStudent, models.LessonStudent.student_id == models.Student.id)
		.where(models.LessonStudent.lesson_id == lesson_id)
	)
	if active_only:
		stmt = stmt.where(models.Student.is_active == True)
	stmt = stmt.order_by(models.Student.first_name.asc(), models.Student.last_name.asc())
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

	# Ders günü/öğretmeni değiştiyse, derse bağlı öğrenciler için aynı gün tek slot kuralını uygula.
	if lesson.teacher_id and lesson.lesson_date:
		linked_students = db.scalars(
			select(models.LessonStudent).where(models.LessonStudent.lesson_id == lesson.id)
		).all()
		for ls in linked_students:
			_enforce_single_student_slot_per_teacher_day(
				db=db,
				teacher_id=lesson.teacher_id,
				student_id=ls.student_id,
				target_lesson_id=lesson.id,
				target_weekday=lesson.lesson_date.weekday(),
			)
	db.commit()
	db.refresh(lesson)
	return lesson


def delete_lesson(db: Session, lesson_id: int):
	"""Dersi siler. Bu derse ait yoklama kaydı varsa silmez (yoklamaların kendiliğinden silinmesini önler)."""
	lesson = db.get(models.Lesson, lesson_id)
	if not lesson:
		return None
	# Yoklama kaydı varsa dersi silme — CASCADE ile yoklamaların silinmesini engelle
	attendance_count = db.scalars(
		select(func.count(models.Attendance.id)).where(models.Attendance.lesson_id == lesson_id)
	).first() or 0
	if attendance_count and int(attendance_count) > 0:
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


def _lessons_with_students_from_lesson_rows(db: Session, lessons: list) -> list[dict]:
	if not lessons:
		return []

	lesson_ids = [lesson.id for lesson in lessons]
	lesson_student_rows = db.scalars(
		select(models.LessonStudent).where(models.LessonStudent.lesson_id.in_(lesson_ids))
	).all()
	student_ids = {row.student_id for row in lesson_student_rows}
	students_map = {
		s.id: s for s in db.scalars(
			select(models.Student).where(models.Student.id.in_(student_ids))
			.order_by(models.Student.first_name.asc(), models.Student.last_name.asc())
		).all()
	} if student_ids else {}
	students_by_lesson: dict[int, list] = {lesson_id: [] for lesson_id in lesson_ids}
	for row in lesson_student_rows:
		student = students_map.get(row.student_id)
		if student:
			students_by_lesson[row.lesson_id].append(student)

	# Program yalnızca LessonStudent atamalarını gösterir.
	# Eski yoklama fallback'i kaldırıldı: aksi halde dersten çıkarılan öğrenci
	# programda görünmeye devam eder, listede ise tek kayıt çıkar.
	out = []
	for lesson in lessons:
		out.append({"lesson": lesson, "students": students_by_lesson.get(lesson.id, [])})
	return out


def lessons_with_students_by_teacher(db: Session, teacher_id: int):
	from sqlalchemy.orm import joinedload
	lessons = db.query(models.Lesson).options(
		joinedload(models.Lesson.course),
		joinedload(models.Lesson.teacher)
	).filter(models.Lesson.teacher_id == teacher_id).order_by(
		models.Lesson.lesson_date.asc(),
		models.Lesson.start_time.asc()
	).all()
	return _lessons_with_students_from_lesson_rows(db, lessons)


def lessons_with_students_by_teacher_ids(db: Session, teacher_ids: list[int]) -> dict[int, list[dict]]:
	from sqlalchemy.orm import joinedload
	if not teacher_ids:
		return {}

	lessons = db.query(models.Lesson).options(
		joinedload(models.Lesson.course),
		joinedload(models.Lesson.teacher)
	).filter(models.Lesson.teacher_id.in_(teacher_ids)).order_by(
		models.Lesson.teacher_id.asc(),
		models.Lesson.lesson_date.asc(),
		models.Lesson.start_time.asc(),
	).all()

	lessons_by_teacher: dict[int, list] = {teacher_id: [] for teacher_id in teacher_ids}
	for lesson in lessons:
		lessons_by_teacher.setdefault(lesson.teacher_id, []).append(lesson)

	return {
		teacher_id: _lessons_with_students_from_lesson_rows(db, teacher_lessons)
		for teacher_id, teacher_lessons in lessons_by_teacher.items()
		if teacher_lessons
	}


# Attendance
def find_attendance_duplicate_student_ids(
	db: Session,
	*,
	lesson_id: int,
	student_ids: list[int],
	attendance_date,
) -> set[int]:
	if not student_ids:
		return set()
	from sqlalchemy import func
	rows = db.scalars(
		select(models.Attendance.student_id)
		.where(
			models.Attendance.lesson_id == lesson_id,
			models.Attendance.student_id.in_(student_ids),
			func.date(models.Attendance.marked_at) == attendance_date,
		)
	).all()
	return set(rows)


def create_attendances_bulk(db: Session, items: list[schemas.AttendanceCreate]) -> int:
	if not items:
		return 0
	from datetime import datetime
	for item in items:
		db.add(
			models.Attendance(
				lesson_id=item.lesson_id,
				student_id=item.student_id,
				status=str(item.status).strip().upper(),
				marked_at=item.marked_at or datetime.utcnow(),
				note=item.note if hasattr(item, "note") and item.note else None,
			)
		)
	db.commit()
	return len(items)


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


def update_attendance(db: Session, attendance_id: int, status: str | None = None, marked_at: datetime | None = None, note: str | None = None):
	"""Yoklama kaydını güncelle"""
	attendance = db.get(models.Attendance, attendance_id)
	if not attendance:
		return None
	
	if status is not None:
		attendance.status = str(status).strip().upper()
	if marked_at is not None:
		attendance.marked_at = marked_at
	if note is not None:
		attendance.note = note
	
	db.commit()
	db.refresh(attendance)
	return attendance


def student_name_matches_prefix(full_name: str, term: str) -> bool:
	"""Öğrenci adı filtresi: yazılan metnin ilk 3 harfi ad, soyad veya tam adla eşleşmeli."""
	term = (term or "").strip().lower()
	if len(term) < 3:
		return False
	prefix = term[:3]
	normalized = (full_name or "").strip().lower()
	parts = normalized.split()
	first = parts[0] if parts else ""
	last = parts[-1] if len(parts) > 1 else ""
	return first.startswith(prefix) or last.startswith(prefix) or normalized.startswith(prefix)


def attendance_status_filter(status: str):
	"""Yoklama durumu filtresi (TELAFI/LATE ve ABSENT/UNEXCUSED_ABSENT uyumluluğu)."""
	normalized = (status or "").strip().upper()
	if normalized == "TELAFI":
		return models.Attendance.status.in_(["TELAFI", "LATE"])
	if normalized == "UNEXCUSED_ABSENT":
		return models.Attendance.status.in_(["UNEXCUSED_ABSENT", "ABSENT"])
	return models.Attendance.status == normalized


def list_all_attendances(db: Session, limit: int = 100, teacher_id: int | None = None, student_id: int | None = None, course_id: int | None = None, status: str | None = None, start_date: date | None = None, end_date: date | None = None, order_by: str = "marked_at_desc"):
	needs_join = teacher_id is not None or course_id is not None

	if needs_join:
		stmt = select(models.Attendance).outerjoin(models.Lesson, models.Attendance.lesson_id == models.Lesson.id)
	else:
		stmt = select(models.Attendance).outerjoin(models.Lesson, models.Attendance.lesson_id == models.Lesson.id)
	
	# Filtreleme
	if teacher_id:
		stmt = stmt.where(models.Lesson.teacher_id == teacher_id)
	if student_id:
		stmt = stmt.where(models.Attendance.student_id == student_id)
	if course_id:
		stmt = stmt.where(models.Lesson.course_id == course_id)
	if status and status.strip():
		stmt = stmt.where(attendance_status_filter(status))
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
	return db.scalars(stmt).all()


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


# Expenses (Finans / Giderler)
EXPENSE_CATEGORIES = ["Kira", "Fatura", "Personel", "Malzeme", "Vergi", "Diğer"]


def create_expense(db: Session, data: schemas.ExpenseCreate):
	payload = data.model_dump()
	if not payload.get("expense_date"):
		payload["expense_date"] = date.today()
	if not payload.get("category"):
		payload["category"] = "Diğer"
	expense = models.Expense(**payload)
	db.add(expense)
	db.commit()
	db.refresh(expense)
	return expense


def get_expense(db: Session, expense_id: int):
	return db.get(models.Expense, expense_id)


def list_expenses(
	db: Session,
	*,
	start_date: date | None = None,
	end_date: date | None = None,
	category: str | None = None,
):
	stmt = select(models.Expense)
	if start_date:
		stmt = stmt.where(models.Expense.expense_date >= start_date)
	if end_date:
		stmt = stmt.where(models.Expense.expense_date <= end_date)
	if category and category.strip():
		stmt = stmt.where(models.Expense.category == category.strip())
	stmt = stmt.order_by(models.Expense.expense_date.desc(), models.Expense.id.desc())
	return db.scalars(stmt).all()


def update_expense(db: Session, expense_id: int, data: schemas.ExpenseUpdate):
	expense = db.get(models.Expense, expense_id)
	if not expense:
		return None
	payload = data.model_dump()
	if not payload.get("expense_date"):
		payload["expense_date"] = date.today()
	for key, value in payload.items():
		setattr(expense, key, value)
	db.commit()
	db.refresh(expense)
	return expense


def delete_expense(db: Session, expense_id: int) -> bool:
	expense = db.get(models.Expense, expense_id)
	if not expense:
		return False
	db.delete(expense)
	db.commit()
	return True


def sum_expenses(
	db: Session,
	*,
	start_date: date | None = None,
	end_date: date | None = None,
	category: str | None = None,
) -> float:
	q = db.query(func.coalesce(func.sum(models.Expense.amount_try), 0))
	if start_date:
		q = q.filter(models.Expense.expense_date >= start_date)
	if end_date:
		q = q.filter(models.Expense.expense_date <= end_date)
	if category and category.strip():
		q = q.filter(models.Expense.category == category.strip())
	return float(q.scalar() or 0)


def sum_payments_by_method(
	db: Session,
	*,
	start_date: date | None = None,
	end_date: date | None = None,
) -> dict[str, float]:
	"""Nakit / EFT(IBAN) / Kart toplamları."""
	q = db.query(models.Payment.method, func.coalesce(func.sum(models.Payment.amount_try), 0))
	if start_date:
		q = q.filter(models.Payment.payment_date >= start_date)
	if end_date:
		q = q.filter(models.Payment.payment_date <= end_date)
	q = q.group_by(models.Payment.method)
	result = {"Nakit": 0.0, "EFT": 0.0, "Kart": 0.0, "Diğer": 0.0}
	for method, total in q.all():
		key = (method or "").strip()
		amount = float(total or 0)
		if key in ("Nakit", "EFT", "Kart"):
			result[key] += amount
		else:
			result["Diğer"] += amount
	return result


def sum_payments_total(
	db: Session,
	*,
	start_date: date | None = None,
	end_date: date | None = None,
) -> float:
	q = db.query(func.coalesce(func.sum(models.Payment.amount_try), 0))
	if start_date:
		q = q.filter(models.Payment.payment_date >= start_date)
	if end_date:
		q = q.filter(models.Payment.payment_date <= end_date)
	return float(q.scalar() or 0)


def monthly_payment_totals(
	db: Session,
	*,
	start_date: date | None = None,
	end_date: date | None = None,
) -> list[dict]:
	"""Aylık tahsilat toplamları (grafik için)."""
	payments = db.query(models.Payment)
	if start_date:
		payments = payments.filter(models.Payment.payment_date >= start_date)
	if end_date:
		payments = payments.filter(models.Payment.payment_date <= end_date)
	buckets: dict[str, float] = {}
	for p in payments.all():
		if not p.payment_date:
			continue
		key = p.payment_date.strftime("%Y-%m")
		buckets[key] = buckets.get(key, 0.0) + float(p.amount_try or 0)
	return [{"month": k, "total": buckets[k]} for k in sorted(buckets.keys())]


def monthly_expense_totals(
	db: Session,
	*,
	start_date: date | None = None,
	end_date: date | None = None,
) -> list[dict]:
	expenses = list_expenses(db, start_date=start_date, end_date=end_date)
	buckets: dict[str, float] = {}
	for e in expenses:
		if not e.expense_date:
			continue
		key = e.expense_date.strftime("%Y-%m")
		buckets[key] = buckets.get(key, 0.0) + float(e.amount_try or 0)
	return [{"month": k, "total": buckets[k]} for k in sorted(buckets.keys())]


def expense_totals_by_category(
	db: Session,
	*,
	start_date: date | None = None,
	end_date: date | None = None,
) -> list[dict]:
	q = db.query(models.Expense.category, func.coalesce(func.sum(models.Expense.amount_try), 0))
	if start_date:
		q = q.filter(models.Expense.expense_date >= start_date)
	if end_date:
		q = q.filter(models.Expense.expense_date <= end_date)
	q = q.group_by(models.Expense.category)
	return [{"category": (cat or "Diğer"), "total": float(total or 0)} for cat, total in q.all()]


def check_student_payment_status(db: Session, student_id: int):
	"""Öğrencinin ödeme durumunu kontrol eder - ödeme gerekip gerekmediğini döndürür"""
	from datetime import date
	today = date.today()
	
	# Öğrencinin toplam ders sayısını hesapla (PRESENT veya TELAFI)
	total_lessons = db.scalars(
		select(func.count(models.Attendance.id))
		.where(
			models.Attendance.student_id == student_id,
			models.Attendance.status.in_(["PRESENT", "TELAFI", "UNEXCUSED_ABSENT"])  # Habersiz gelmedi de toplam derse dahil
		)
	).first() or 0
	
	# Öğrencinin ödemelerini getir
	payments = list_payments_by_student(db, student_id)
	total_paid_sets = len(payments)
	total_lessons = int(total_lessons or 0)
	
	# Ödeme gerekli sadece: hiç ödeme yok VEYA aldığı ders sayısı ödenen setlerin karşıladığı dersi geçti (12 derse gelmeden gerekli gösterme)
	# 3 set = 12 derse kadar; 8–9 ders alıp 3 set ödeyen öğrenci "gerekli" listesinde olmaz
	if total_paid_sets == 0:
		return True
	return total_lessons >= (total_paid_sets * 4)


def list_students_needing_payment(db: Session):
	"""Ödeme gerekli olan tüm öğrencileri listeler (sadece aktif öğrenciler)"""
	all_students = list_students(db, active_only=True)
	students_needing_payment = []
	
	for student in all_students:
		if check_student_payment_status(db, student.id):
			students_needing_payment.append(student)
	
	return students_needing_payment


ATTENDANCE_STATUS_LABELS = {
	"PRESENT": "Geldi",
	"UNEXCUSED_ABSENT": "Habersiz Gelmedi",
	"EXCUSED_ABSENT": "Haberli Gelmedi",
	"TELAFI": "Telafi",
}

ATTENDANCE_STATUS_SUMMARY_STYLES = {
	"PRESENT": {"bg": "#dcfce7", "color": "#15803d"},
	"UNEXCUSED_ABSENT": {"bg": "#fee2e2", "color": "#dc2626"},
	"EXCUSED_ABSENT": {"bg": "#ffedd5", "color": "#c2410c"},
	"TELAFI": {"bg": "#ede9fe", "color": "#6d28d9"},
}

ATTENDANCE_STATUS_DATE_BADGE_STYLES = {
	"PRESENT": {"bg": "#dcfce7", "color": "#15803d", "border": "#86efac"},
	"UNEXCUSED_ABSENT": {"bg": "#fee2e2", "color": "#dc2626", "border": "#fca5a5"},
	"EXCUSED_ABSENT": {"bg": "#ffedd5", "color": "#c2410c", "border": "#fdba74"},
	"TELAFI": {"bg": "#ede9fe", "color": "#6d28d9", "border": "#c4b5fd"},
}


def normalize_attendance_status(status: str | None) -> str:
	if not status:
		return ""
	if status == "LATE":
		return "TELAFI"
	if status == "ABSENT":
		return "UNEXCUSED_ABSENT"
	return status


def summarize_student_attendances(attendances) -> tuple[dict[str, int], list[dict]]:
	counts = {key: 0 for key in ATTENDANCE_STATUS_LABELS}
	entries: list[dict] = []
	for att in attendances:
		if not att.marked_at:
			continue
		status = normalize_attendance_status(att.status)
		if status in counts:
			counts[status] += 1
		badge_style = ATTENDANCE_STATUS_DATE_BADGE_STYLES.get(
			status,
			{"bg": "#e0e7ff", "color": "#4338ca", "border": "#c7d2fe"},
		)
		entries.append({
			"date": att.marked_at.date(),
			"status": status,
			"label": ATTENDANCE_STATUS_LABELS.get(status, status or "-"),
			"badge_bg": badge_style["bg"],
			"badge_color": badge_style["color"],
			"badge_border": badge_style["border"],
		})
	entries.sort(key=lambda item: item["date"])
	return counts, entries


WEEKDAY_MAP_TR = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
VALID_PAYMENT_STATUS_FILTERS = frozenset({"needs_payment", "waiting", "paid"})
_ATTENDANCE_STATUSES_FOR_PAYMENT = ("PRESENT", "TELAFI", "UNEXCUSED_ABSENT")


def classify_payment_status(total_lessons: int, total_paid_sets: int) -> dict:
	position_in_set = total_lessons % 4
	lessons_covered_by_payment = total_paid_sets * 4
	within_paid = total_paid_sets > 0 and total_lessons < lessons_covered_by_payment

	if total_paid_sets == 0:
		return {
			"payment_status": "⚠️ Ödeme Gerekli",
			"payment_status_class": "needs_payment",
			"needs_payment": True,
		}
	if total_lessons == 0:
		return {
			"payment_status": "✅ Ödendi",
			"payment_status_class": "paid",
			"needs_payment": False,
		}
	if within_paid:
		if position_in_set in (0, 1, 2):
			return {
				"payment_status": "✅ Ödeme Yapıldı",
				"payment_status_class": "paid",
				"needs_payment": False,
			}
		return {
			"payment_status": "⏳ Ödeme Bekleniyor",
			"payment_status_class": "waiting",
			"needs_payment": False,
		}
	return {
		"payment_status": "⚠️ Ödeme Gerekli",
		"payment_status_class": "needs_payment",
		"needs_payment": True,
	}


def _batch_attendance_counts(db: Session, student_ids: list[int]) -> dict[int, int]:
	if not student_ids:
		return {}
	rows = db.execute(
		select(models.Attendance.student_id, func.count(models.Attendance.id))
		.where(
			models.Attendance.student_id.in_(student_ids),
			models.Attendance.status.in_(_ATTENDANCE_STATUSES_FOR_PAYMENT),
		)
		.group_by(models.Attendance.student_id)
	).all()
	return {row[0]: int(row[1]) for row in rows}


def _batch_payment_counts(db: Session, student_ids: list[int]) -> dict[int, int]:
	if not student_ids:
		return {}
	rows = db.execute(
		select(models.Payment.student_id, func.count(models.Payment.id))
		.where(models.Payment.student_id.in_(student_ids))
		.group_by(models.Payment.student_id)
	).all()
	return {row[0]: int(row[1]) for row in rows}


def _batch_last_payment_dates(db: Session, student_ids: list[int]) -> dict[int, date]:
	if not student_ids:
		return {}
	rows = db.execute(
		select(models.Payment.student_id, func.max(models.Payment.payment_date))
		.where(models.Payment.student_id.in_(student_ids))
		.group_by(models.Payment.student_id)
	).all()
	return {row[0]: row[1] for row in rows}


def _load_lesson_days_courses_for_students(
	db: Session,
	student_ids: list[int],
	weekday_map: list[str] | None = None,
) -> tuple[dict[int, set], dict[int, set]]:
	if not student_ids:
		return {}, {}

	from sqlalchemy.orm import joinedload

	weekday_map = weekday_map or WEEKDAY_MAP_TR
	lesson_days_by_student: dict[int, set] = {sid: set() for sid in student_ids}
	lesson_courses_by_student: dict[int, set] = {sid: set() for sid in student_ids}

	lesson_student_rows = db.scalars(
		select(models.LessonStudent).where(models.LessonStudent.student_id.in_(student_ids))
	).all()
	linked_lesson_ids = {row.lesson_id for row in lesson_student_rows}
	lessons_by_id = {
		l.id: l for l in db.scalars(
			select(models.Lesson)
			.where(models.Lesson.id.in_(linked_lesson_ids))
			.options(joinedload(models.Lesson.course))
		).all()
	} if linked_lesson_ids else {}

	for row in lesson_student_rows:
		lesson = lessons_by_id.get(row.lesson_id)
		if not lesson:
			continue
		if getattr(lesson, "lesson_date", None):
			try:
				wd_idx = lesson.lesson_date.weekday()
				if 0 <= wd_idx < len(weekday_map):
					lesson_days_by_student[row.student_id].add(weekday_map[wd_idx])
			except Exception:
				pass
		if lesson.course and lesson.course.name:
			lesson_courses_by_student[row.student_id].add(lesson.course.name)

	return lesson_days_by_student, lesson_courses_by_student


def build_payment_status_list(
	db: Session,
	*,
	status_filter: str,
	payment_day: str | None = None,
	include_staff_fields: bool = False,
) -> tuple[list[dict], dict[int, dict]]:
	status_filter = (status_filter or "").strip().lower()
	if status_filter not in VALID_PAYMENT_STATUS_FILTERS:
		return [], {}

	all_students = list_students(db, active_only=True)
	if not all_students:
		return [], {}

	student_ids = [s.id for s in all_students]
	attendance_counts = _batch_attendance_counts(db, student_ids)
	payment_counts = _batch_payment_counts(db, student_ids)
	last_payment_by_student = _batch_last_payment_dates(db, student_ids) if include_staff_fields else {}

	candidates: list[dict] = []
	for student in all_students:
		total_lessons = attendance_counts.get(student.id, 0)
		total_paid_sets = payment_counts.get(student.id, 0)
		info = classify_payment_status(total_lessons, total_paid_sets)
		if info["payment_status_class"] != status_filter:
			continue

		item = {
			"student": student,
			"needs_payment": info["needs_payment"],
			"payment_status": info["payment_status"],
			"payment_status_class": info["payment_status_class"],
		}
		if include_staff_fields:
			item.update({
				"total_lessons": total_lessons,
				"expected_paid_sets": (total_lessons // 4) + 1,
				"total_paid_sets": total_paid_sets,
				"last_payment_date": last_payment_by_student.get(student.id),
			})
		candidates.append(item)

	if not candidates:
		return [], {}

	candidate_ids = [item["student"].id for item in candidates]
	lesson_days_by_student, lesson_courses_by_student = _load_lesson_days_courses_for_students(
		db, candidate_ids
	)

	payment_day_clean = (payment_day or "").strip()
	students_needing_payment_lessons: dict[int, dict] = {}
	payment_status_list: list[dict] = []

	for item in candidates:
		student = item["student"]
		lesson_days = lesson_days_by_student.get(student.id, set())
		lesson_courses = lesson_courses_by_student.get(student.id, set())

		if payment_day_clean and payment_day_clean not in lesson_days:
			continue

		lesson_days_str = ", ".join(sorted(lesson_days)) if lesson_days else "-"
		lesson_courses_str = ", ".join(sorted(lesson_courses)) if lesson_courses else "-"
		students_needing_payment_lessons[student.id] = {
			"lesson_days": lesson_days_str,
			"lesson_courses": lesson_courses_str,
			"lesson_days_set": lesson_days,
		}
		item["lesson_days"] = lesson_days_str
		item["lesson_days_set"] = lesson_days
		item["lesson_courses"] = lesson_courses_str
		payment_status_list.append(item)

	payment_status_list.sort(
		key=lambda x: (
			(x["student"].first_name or "").lower(),
			(x["student"].last_name or "").lower(),
		)
	)
	return payment_status_list, students_needing_payment_lessons


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


def get_attendance_report_by_teacher(
    db: Session,
    teacher_id: int | None = None,
    student_id: int | None = None,
    course_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    status: str | None = None,
    student_name: str | None = None,
):
    """Öğretmenlere göre yoklama raporu oluşturur. Filtreleme parametreleri ile çalışır."""
    from sqlalchemy.orm import joinedload

    if teacher_id:
        teachers = [db.get(models.Teacher, teacher_id)] if db.get(models.Teacher, teacher_id) else []
    else:
        teachers = list_teachers(db)
    report = []

    for teacher in teachers:
        if not teacher:
            continue
        lessons = list_lessons_by_teacher(db, teacher.id)
        lesson_ids = [lesson.id for lesson in lessons]

        attendances = []
        if lesson_ids:
            stmt = select(models.Attendance).where(
                models.Attendance.lesson_id.in_(lesson_ids)
            )
            if student_id:
                stmt = stmt.where(models.Attendance.student_id == student_id)
            if status and status.strip():
                stmt = stmt.where(attendance_status_filter(status))
            attendances = db.scalars(stmt).all()

            if course_id or start_date or end_date:
                lesson_map = {
                    l.id: l for l in db.scalars(
                        select(models.Lesson).where(models.Lesson.id.in_({a.lesson_id for a in attendances}))
                    ).all()
                } if attendances else {}
                filtered_attendances = []
                for att in attendances:
                    lesson = lesson_map.get(att.lesson_id)
                    if not lesson:
                        continue
                    if course_id and lesson.course_id != course_id:
                        continue
                    if start_date:
                        if not att.marked_at or att.marked_at.date() < start_date:
                            continue
                    if end_date:
                        if not att.marked_at or att.marked_at.date() > end_date:
                            continue
                    filtered_attendances.append(att)
                attendances = filtered_attendances

        lesson_map = {
            l.id: l for l in db.scalars(
                select(models.Lesson)
                .where(models.Lesson.id.in_({a.lesson_id for a in attendances}))
                .options(joinedload(models.Lesson.course))
            ).all()
        } if attendances else {}
        student_map = {
            s.id: s for s in db.scalars(
                select(models.Student).where(models.Student.id.in_({a.student_id for a in attendances}))
            ).all()
        } if attendances else {}

        if student_name and student_name.strip() and not student_id:
            attendances = [
                att for att in attendances
                if (stu := student_map.get(att.student_id))
                and student_name_matches_prefix(f"{stu.first_name} {stu.last_name}", student_name)
            ]

        student_stats = {}
        for att in attendances:
            lesson = lesson_map.get(att.lesson_id)
            att_student_id = att.student_id
            if att_student_id not in student_stats:
                student = student_map.get(att_student_id)
                if not student:
                    continue
                student_stats[att_student_id] = {
                    "student": student,
                    "present": 0,
                    "excused_absent": 0,
                    "telafi": 0,
                    "unexcused_absent": 0,
                    "total": 0,
                    "dates": []
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
                student_stats[att_student_id]["present"] += lesson_count
                student_stats[att_student_id]["total"] += lesson_count
                student_stats[att_student_id]["dates"].append(date_str)
            elif status == "EXCUSED_ABSENT":
                student_stats[att_student_id]["excused_absent"] += lesson_count
                student_stats[att_student_id]["dates"].append(date_str)
                # Haberli gelmedi durumunda toplam ders sayısına eklenmez
            elif status == "TELAFI":
                student_stats[att_student_id]["telafi"] += lesson_count
                student_stats[att_student_id]["total"] += lesson_count
                student_stats[att_student_id]["dates"].append(date_str)
            elif status == "UNEXCUSED_ABSENT":
                # Resim kursu için: Öğrenci puantajında görünür ama öğretmen puantajına eklenmez
                # Diğer kurslar için: Normal şekilde sayılır
                if is_resim_course:
                    # Öğrenci bazlı puantajda görünür (unexcused_absent artar)
                    student_stats[att_student_id]["unexcused_absent"] += 1
                    # Ama öğretmen puantajına eklenmez (lesson_count = 0, total'e eklenmez)
                    student_stats[att_student_id]["dates"].append(date_str)
                else:
                    # Diğer kurslar için normal
                    student_stats[att_student_id]["unexcused_absent"] += lesson_count
                    student_stats[att_student_id]["total"] += lesson_count
                    student_stats[att_student_id]["dates"].append(date_str)
        
        students_list = list(student_stats.values())
        if students_list or teacher_id:
            report.append({
                "teacher": teacher,
                "students": students_list
            })
    
    return report


