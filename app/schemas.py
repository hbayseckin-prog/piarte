from datetime import date, time, datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class StudentCreate(BaseModel):
	first_name: str
	last_name: str
	date_of_birth: Optional[date] = None
	parent_name: Optional[str] = None
	parent_phone: Optional[str] = None
	address: Optional[str] = None
	phone_primary: Optional[str] = None
	phone_secondary: Optional[str] = None


class StudentUpdate(StudentCreate):
	pass


class StudentOut(BaseModel):
	id: int
	first_name: str
	last_name: str
	date_of_birth: Optional[date] = None
	parent_name: Optional[str] = None
	parent_phone: Optional[str] = None
	address: Optional[str] = None
	phone_primary: Optional[str] = None
	phone_secondary: Optional[str] = None
	created_at: datetime

	class Config:
		from_attributes = True


class TeacherCreate(BaseModel):
	first_name: str
	last_name: str
	phone: Optional[str] = None
	email: Optional[str] = None


class TeacherUpdate(TeacherCreate):
	pass


class TeacherOut(BaseModel):
	id: int
	first_name: str
	last_name: str
	phone: Optional[str] = None
	email: Optional[str] = None
	created_at: datetime

	class Config:
		from_attributes = True


class CourseCreate(BaseModel):
	name: str


class CourseUpdate(BaseModel):
	name: str


class CourseOut(BaseModel):
	id: int
	name: str
	created_at: datetime

	class Config:
		from_attributes = True


class EnrollmentCreate(BaseModel):
	student_id: int
	course_id: int


class LessonCreate(BaseModel):
	course_id: int
	teacher_id: int
	lesson_date: date
	start_time: Optional[time] = None
	end_time: Optional[time] = None
	description: Optional[str] = None


class LessonUpdate(BaseModel):
	course_id: Optional[int] = None
	teacher_id: Optional[int] = None
	lesson_date: Optional[date] = None
	start_time: Optional[time] = None
	end_time: Optional[time] = None
	description: Optional[str] = None


class LessonOut(BaseModel):
	id: int
	course_id: int
	teacher_id: int
	lesson_date: date
	start_time: Optional[time] = None
	end_time: Optional[time] = None
	description: Optional[str] = None
	created_at: datetime

	class Config:
		from_attributes = True


class AttendanceCreate(BaseModel):
	lesson_id: int
	student_id: int
	status: str  # PRESENT, UNEXCUSED_ABSENT, EXCUSED_ABSENT, TELAFI
	note: Optional[str] = None
	marked_at: Optional[datetime] = None


class AttendanceOut(BaseModel):
	id: int
	lesson_id: int
	student_id: int
	status: str
	note: Optional[str]
	marked_at: datetime

	class Config:
		from_attributes = True


class PaymentCreate(BaseModel):
	student_id: int
	amount_try: float
	payment_date: Optional[date] = None
	method: Optional[str] = None
	note: Optional[str] = None


class PaymentUpdate(BaseModel):
	student_id: int
	amount_try: float
	payment_date: Optional[date] = None
	method: Optional[str] = None
	note: Optional[str] = None


class PaymentOut(BaseModel):
	id: int
	student_id: int
	amount_try: float
	payment_date: date
	method: Optional[str]
	note: Optional[str]
	created_at: datetime

	class Config:
		from_attributes = True


class InvoiceCreate(BaseModel):
	student_id: int
	amount_try: float
	due_date: date
	note: Optional[str] = None


class InvoiceOut(BaseModel):
	id: int
	student_id: int
	amount_try: float
	due_date: date
	status: str
	note: Optional[str]
	created_at: datetime

	class Config:
		from_attributes = True

class UserCreate(BaseModel):
	username: str
	password: str
	full_name: Optional[str] = None
	role: Optional[str] = None
	teacher_id: Optional[int] = None


class UserOut(BaseModel):
	id: int
	username: str
	full_name: Optional[str]
	role: Optional[str]
	teacher_id: Optional[int]
	created_at: datetime

	class Config:
		from_attributes = True


