from sqlalchemy.orm import Session
from . import crud, schemas


DEFAULT_COURSES = ["Bateri", "Keman", "Resim"]


def seed_courses(db: Session):
	for name in DEFAULT_COURSES:
		if not crud.get_course_by_name(db, name):
			crud.create_course(db, name)


def seed_admin(db: Session):
	# Varsayılan admin: admin / admin123 (sonradan değiştirin)
	if not crud.get_user_by_username(db, "admin"):
		crud.create_user(db, schemas.UserCreate(username="admin", password="admin123", full_name="Yönetici"))


