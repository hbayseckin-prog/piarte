from datetime import datetime, date, time
from sqlalchemy import Column, Integer, String, Date, DateTime, Time, ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .db import Base


class User(Base):
	__tablename__ = "users"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
	password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
	full_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
	role: Mapped[str | None] = mapped_column(String(30), nullable=True)  # admin, teacher
	teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id"), nullable=True)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Student(Base):
	__tablename__ = "students"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	first_name: Mapped[str] = mapped_column(String(100), nullable=False)
	last_name: Mapped[str] = mapped_column(String(100), nullable=False)
	date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
	parent_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
	parent_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
	address: Mapped[str | None] = mapped_column(Text, nullable=True)
	phone_primary: Mapped[str | None] = mapped_column(String(50), nullable=True)
	phone_secondary: Mapped[str | None] = mapped_column(String(50), nullable=True)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

	enrollments = relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")
	payments = relationship("Payment", back_populates="student", cascade="all, delete-orphan")
	teacher_link = relationship("TeacherStudent", back_populates="student", uselist=False, cascade="all, delete-orphan")


class Teacher(Base):
	__tablename__ = "teachers"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	first_name: Mapped[str] = mapped_column(String(100), nullable=False)
	last_name: Mapped[str] = mapped_column(String(100), nullable=False)
	phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
	email: Mapped[str | None] = mapped_column(String(120), nullable=True)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

	lessons = relationship("Lesson", back_populates="teacher")
	student_links = relationship("TeacherStudent", back_populates="teacher", cascade="all, delete-orphan")


class Course(Base):
	__tablename__ = "courses"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

	lessons = relationship("Lesson", back_populates="course")
	enrollments = relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")


class Enrollment(Base):
	__tablename__ = "enrollments"
	__table_args__ = (
		UniqueConstraint("student_id", "course_id", name="uq_student_course"),
	)

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
	course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
	joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

	student = relationship("Student", back_populates="enrollments")
	course = relationship("Course", back_populates="enrollments")


class Lesson(Base):
	__tablename__ = "lessons"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
	teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"), nullable=False)
	lesson_date: Mapped[date] = mapped_column(Date, nullable=False)
	start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
	end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

	course = relationship("Course", back_populates="lessons")
	teacher = relationship("Teacher", back_populates="lessons")
	attendances = relationship("Attendance", back_populates="lesson", cascade="all, delete-orphan")
	lesson_students = relationship("LessonStudent", back_populates="lesson", cascade="all, delete-orphan")


class Attendance(Base):
	__tablename__ = "attendances"
	__table_args__ = (
		# Attendance tablosundaki constraint adı, LessonStudent tablosundakinden
		# farklı olmalı (PostgreSQL'de constraint isimleri şema genelinde benzersizdir)
		UniqueConstraint("lesson_id", "student_id", name="uq_attendance_lesson_student"),
	)

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
	student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
	status: Mapped[str] = mapped_column(String(20), nullable=False)  # PRESENT, UNEXCUSED_ABSENT, EXCUSED_ABSENT, LATE
	note: Mapped[str | None] = mapped_column(Text, nullable=True)
	marked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

	lesson = relationship("Lesson", back_populates="attendances")


class Payment(Base):
	__tablename__ = "payments"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
	amount_try: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
	payment_date: Mapped[date] = mapped_column(Date, default=date.today)
	method: Mapped[str | None] = mapped_column(String(30), nullable=True)  # Nakit, Kart, EFT
	note: Mapped[str | None] = mapped_column(Text, nullable=True)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

	student = relationship("Student", back_populates="payments")


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    amount_try: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING, PAID, OVERDUE
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TeacherStudent(Base):
	__tablename__ = "teacher_students"
	__table_args__ = (
		UniqueConstraint("student_id", name="uq_teacher_student_student"),
	)

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)
	student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

	teacher = relationship("Teacher", back_populates="student_links")
	student = relationship("Student", back_populates="teacher_link")


class LessonStudent(Base):
	__tablename__ = "lesson_students"
	__table_args__ = (
		UniqueConstraint("lesson_id", "student_id", name="uq_lesson_student"),
	)

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
	student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

	lesson = relationship("Lesson", back_populates="lesson_students")
	student = relationship("Student")



