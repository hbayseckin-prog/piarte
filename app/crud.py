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
def mark_attendance(db: Session, data: schemas.AttendanceCreate):
	"""
	Bir ders-öğrenci çifti için yoklama kaydını oluşturur veya günceller (upsert).
	Aynı (lesson_id, student_id) için birden fazla kayıt oluşmasını engeller.
	"""
	try:
		import logging
		# Önce mevcut bir kayıt var mı kontrol et
		existing = db.scalars(
			select(models.Attendance).where(
				models.Attendance.lesson_id == data.lesson_id,
				models.Attendance.student_id == data.student_id,
			)
		).first()
		if existing:
			# Güncelle
			logging.warning(f"MARK_ATTENDANCE: Yoklama güncelleniyor: lesson_id={data.lesson_id}, student_id={data.student_id}, eski_status={existing.status}, yeni_status={data.status}")
			existing.status = data.status
			if data.marked_at is not None:
				existing.marked_at = data.marked_at
			db.commit()
			db.refresh(existing)
			logging.warning(f"MARK_ATTENDANCE: Yoklama güncellendi: attendance_id={existing.id}")
			return existing
		# Yoksa yeni kayıt oluştur
		logging.warning(f"MARK_ATTENDANCE: Yeni yoklama kaydı oluşturuluyor: lesson_id={data.lesson_id}, student_id={data.student_id}, status={data.status}")
		attendance = models.Attendance(**data.model_dump())
		db.add(attendance)
		db.commit()
		db.refresh(attendance)
		logging.warning(f"MARK_ATTENDANCE: Yoklama kaydı başarıyla oluşturuldu: attendance_id={attendance.id}, lesson_id={attendance.lesson_id}, student_id={attendance.student_id}, status={attendance.status}")
		return attendance
	except Exception as e:
		# Hata durumunda rollback yap
		db.rollback()
		import logging
		import traceback
		logging.error(f"mark_attendance hatası: {e}, lesson_id={data.lesson_id}, student_id={data.student_id}")
		logging.error(traceback.format_exc())
		raise


def list_attendance_for_lesson(db: Session, lesson_id: int):
	stmt = select(models.Attendance).where(models.Attendance.lesson_id == lesson_id)
	return db.scalars(stmt).all()


def list_all_attendances(db: Session, limit: int = 100, teacher_id: int | None = None, student_id: int | None = None, course_id: int | None = None, status: str | None = None, start_date: date | None = None, end_date: date | None = None, order_by: str = "marked_at_desc"):
	# Tüm yoklamaları getir
	# Join gerekip gerekmediğini kontrol et
	needs_join = teacher_id is not None or course_id is not None or start_date is not None or end_date is not None or order_by.startswith("lesson_date")
	
	if needs_join:
		stmt = select(models.Attendance).join(models.Lesson, models.Attendance.lesson_id == models.Lesson.id)
	else:
		stmt = select(models.Attendance)
	
	# Filtreleme
	if teacher_id:
		stmt = stmt.where(models.Lesson.teacher_id == teacher_id)
	if student_id:
		stmt = stmt.where(models.Attendance.student_id == student_id)
	if course_id:
		stmt = stmt.where(models.Lesson.course_id == course_id)
	if status:
		stmt = stmt.where(models.Attendance.status == status.upper())
	if start_date:
		stmt = stmt.where(models.Lesson.lesson_date >= start_date)
	if end_date:
		stmt = stmt.where(models.Lesson.lesson_date <= end_date)
	
	# Sıralama
	if order_by == "marked_at_desc":
		stmt = stmt.order_by(models.Attendance.marked_at.desc())
	elif order_by == "marked_at_asc":
		stmt = stmt.order_by(models.Attendance.marked_at.asc())
	elif order_by == "lesson_date_desc":
		stmt = stmt.order_by(models.Lesson.lesson_date.desc(), models.Attendance.marked_at.desc())
	elif order_by == "lesson_date_asc":
		stmt = stmt.order_by(models.Lesson.lesson_date.asc(), models.Attendance.marked_at.asc())
	else:
		stmt = stmt.order_by(models.Attendance.marked_at.desc())
	
	stmt = stmt.limit(limit)
	return db.scalars(stmt).all()


def get_attendance_report_by_teacher(
	db: Session,
	teacher_id: int | None = None,
	start_date: date | None = None,
	end_date: date | None = None,
):
	"""
	Her öğretmen-altında her öğrenci için toplam yoklama sayısını döndürür.
	Sadece şu statüler sayılır:
	- PRESENT  -> geldi
	- UNEXCUSED_ABSENT -> habersiz gelmedi
	- LATE -> geç geldi
	EXCUSED_ABSENT (haberli gelmedi) sayılmaz, ama kaydı varsa satır yine görünür.
	"""
	# Tüm yoklamaları öğretmen, öğrenci ve derse join ederek al
	# Attendance tablosundan başlayarak join yapıyoruz
	q = db.query(
		models.Teacher.id.label("teacher_id"),
		models.Teacher.first_name.label("teacher_first_name"),
		models.Teacher.last_name.label("teacher_last_name"),
		models.Student.id.label("student_id"),
		models.Student.first_name.label("student_first_name"),
		models.Student.last_name.label("student_last_name"),
		models.Attendance.status,
	).select_from(
		models.Attendance
	).join(
		models.Lesson, models.Attendance.lesson_id == models.Lesson.id
	).join(
		models.Teacher, models.Lesson.teacher_id == models.Teacher.id
	).join(
		models.Student, models.Attendance.student_id == models.Student.id
	)

	# Opsiyonel filtreler (öğretmen ve tarih aralığı)
	if teacher_id:
		q = q.filter(models.Lesson.teacher_id == teacher_id)
	if start_date:
		q = q.filter(models.Lesson.lesson_date >= start_date)
	if end_date:
		q = q.filter(models.Lesson.lesson_date <= end_date)

	rows = q.all()
	
	# Debug: Toplam satır sayısını logla
	import logging
	logging.warning(f"PUANTAJ_DEBUG: Toplam {len(rows)} yoklama kaydı bulundu")

	report_map: dict[tuple[int, int], dict] = {}

	for r in rows:
		key = (r.teacher_id, r.student_id)
		if key not in report_map:
			report_map[key] = {
				"teacher_id": r.teacher_id,
				"teacher_first_name": r.teacher_first_name,
				"teacher_last_name": r.teacher_last_name,
				"student_id": r.student_id,
				"student_first_name": r.student_first_name,
				"student_last_name": r.student_last_name,
				"present": 0,
				"unexcused_absent": 0,
				"late": 0,
				"excused_absent": 0,
			}
		# Status'u kontrol et ve say
		if r.status == "PRESENT":
			report_map[key]["present"] += 1
		elif r.status == "UNEXCUSED_ABSENT":
			report_map[key]["unexcused_absent"] += 1
		elif r.status == "LATE":
			report_map[key]["late"] += 1
		elif r.status == "EXCUSED_ABSENT":
			report_map[key]["excused_absent"] += 1
		else:
			# Bilinmeyen status için log
			logging.warning(f"Bilinmeyen yoklama durumu: {r.status} (teacher_id={r.teacher_id}, student_id={r.student_id})")

	# Önce öğretmen-öğrenci bazlı liste
	report_list = list(report_map.values())
	# Öğretmen ve öğrenci adına göre sırala
	report_list.sort(
		key=lambda x: (
			x["teacher_last_name"],
			x["teacher_first_name"],
			x["student_last_name"],
			x["student_first_name"],
		)
	)

	# Daha sonra öğretmen bazında grupla; template'in beklediği yapı:
	# [
	#   {
	#     "teacher": {"first_name": "...", "last_name": "..."},
	#     "students": [
	#        {
	#          "student": {"first_name": "...", "last_name": "..."},
	#          "present": 3,
	#          "unexcused_absent": 1,
	#          "late": 0,
	#          "total": 4,
	#        },
	#        ...
	#     ],
	#   },
	#   ...
	# ]
	teachers_map: dict[int, dict] = {}
	for row in report_list:
		tid = row["teacher_id"]
		if tid not in teachers_map:
			teachers_map[tid] = {
				"teacher": {
					"first_name": row["teacher_first_name"],
					"last_name": row["teacher_last_name"],
				},
				"students": [],
			}
		# Toplam ders: daha önce konuştuğumuz gibi EXCUSED_ABSENT hariç
		total = row["present"] + row["unexcused_absent"] + row["late"]
		teachers_map[tid]["students"].append(
			{
				"student": {
					"first_name": row["student_first_name"],
					"last_name": row["student_last_name"],
				},
				"present": row["present"],
				"unexcused_absent": row["unexcused_absent"],
				"late": row["late"],
				"excused_absent": row["excused_absent"],
				"total": total,
			}
		)

	# Öğretmen adlarına göre sırala
	grouped_list = list(teachers_map.values())
	grouped_list.sort(
		key=lambda t: (
			t["teacher"]["last_name"],
			t["teacher"]["first_name"],
		)
	)
	return grouped_list


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


def check_student_payment_status(db: Session, student_id: int):
	"""
	Öğrencinin ödeme durumunu kontrol eder.
	Ödeme mantığı:
	- 0. derste (ilk kayıt) ödeme alınır (1. set)
	- 4. derse geldiğinde yeni ödeme alınır (2. set)
	- 8. derse geldiğinde yeni ödeme alınır (3. set)
	- 12, 16, 20... diye devam eder

	Beklenen ödeme seti = (toplam_ders // 4) + 1
	- 0 ders: 1 set (ilk kayıt)
	- 1-3 ders: 1 set (ilk kayıt)
	- 4-7 ders: 2 set (ilk kayıt + 4. ders)
	- 8-11 ders: 3 set (ilk kayıt + 4. ders + 8. ders)
	- 12-15 ders: 4 set
	- ...
	"""
	# Öğrencinin toplam ders sayısını hesapla (PRESENT veya LATE olan yoklamalar)
	total_lessons = db.scalars(
		select(func.count(models.Attendance.id)).where(
			models.Attendance.student_id == student_id,
			models.Attendance.status.in_(["PRESENT", "LATE"]),
		)
	).first() or 0

	# Öğrencinin ödemelerini getir
	payments = list_payments_by_student(db, student_id)
	total_paid_sets = len(payments)

	# Beklenen ödeme seti hesapla
	expected_paid_sets = (total_lessons // 4) + 1

	# Ödeme yetersizse True (kırmızı), yeterliyse False
	return total_paid_sets < expected_paid_sets


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


