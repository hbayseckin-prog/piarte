"""
Almina Canpolat için Piyano dışındaki tüm yoklama kayıtlarını Piyano olarak düzeltir.
Çalıştırma (proje kökünden):
  python -m scripts.fix_almina_attendances_to_piano
  python -m scripts.fix_almina_attendances_to_piano 123   # öğrenci id ile
"""
import sys
import os
from collections import defaultdict

# Proje kökünü path'e ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func
from app.db import SessionLocal
from app import models
from app import crud
from app import schemas


def main():
    db = SessionLocal()
    try:
        # 1. Öğrenci: ID verilmişse onu kullan, yoksa "Almina Canpolat" ara
        student = None
        if len(sys.argv) > 1 and sys.argv[1].isdigit():
            student = db.get(models.Student, int(sys.argv[1]))
        if not student:
            all_students = db.query(models.Student).all()
            students = []
            for s in all_students:
                full = f"{s.first_name or ''} {s.last_name or ''}".lower()
                if "almina" in full and "canpolat" in full:
                    students.append(s)
            if students:
                student = students[0]
        if not student:
            print("Ogrenci bulunamadi: Almina Canpolat. Ogrenci ID ile deneyin: python -m scripts.fix_almina_attendances_to_piano <ogrenci_id>")
            return
        print(f"Öğrenci: {student.first_name} {student.last_name} (id={student.id})")

        # 2. Piyano kursu
        piano = crud.get_course_by_name(db, "Piyano")
        if not piano:
            # Alternatif isim
            courses = db.query(models.Course).all()
            piano = next((c for c in courses if "iyano" in c.name.lower() or "piano" in c.name.lower()), None)
        if not piano:
            print("Piyano kursu bulunamadı.")
            return
        print(f"Piyano kursu: {piano.name} (id={piano.id})")

        # 3. Bu öğrencinin tüm yoklamaları (Piyano dışı derslere ait olanlar)
        attendances = db.scalars(
            select(models.Attendance).where(models.Attendance.student_id == student.id)
        ).all()
        print(f"Toplam {len(attendances)} yoklama kaydı.")

        # Piyano dışı dersleri grupla (lesson_id'ye göre)
        by_lesson = defaultdict(list)
        for att in attendances:
            lesson = db.get(models.Lesson, att.lesson_id)
            if not lesson or lesson.course_id == piano.id:
                continue
            by_lesson[lesson.id].append((att, lesson))

        updated_lessons = 0
        created_lessons = 0
        moved_attendances = 0

        for lesson_id, att_lesson_list in by_lesson.items():
            lesson = att_lesson_list[0][1]  # aynı ders
            course_name = lesson.course.name if lesson.course else "?"
            almina_count = len(att_lesson_list)
            total_in_lesson = db.scalar(
                select(func.count(models.Attendance.id)).where(models.Attendance.lesson_id == lesson_id)
            )
            total_in_lesson = total_in_lesson or 0

            if total_in_lesson == almina_count:
                # Ders sadece Almina'ya ait; dersi Piyano yap
                crud.update_lesson(db, lesson.id, schemas.LessonUpdate(course_id=piano.id))
                updated_lessons += 1
                print(f"  Ders {lesson.id} ({course_name}) -> Piyano yapıldı ({almina_count} yoklama).")
            else:
                # Başka öğrencilerin de kaydı var; tek yeni Piyano dersi oluştur, Almina'nın hepsini taşı
                new_lesson = crud.create_lesson(db, schemas.LessonCreate(
                    course_id=piano.id,
                    teacher_id=lesson.teacher_id,
                    lesson_date=lesson.lesson_date,
                    start_time=lesson.start_time,
                    end_time=lesson.end_time,
                    description=lesson.description,
                ))
                for att, _ in att_lesson_list:
                    att.lesson_id = new_lesson.id
                    moved_attendances += 1
                db.commit()
                created_lessons += 1
                print(f"  Ders {lesson.id} ({course_name}): yeni Piyano dersi {new_lesson.id} oluşturuldu, {almina_count} yoklama taşındı.")

        print(f"\nÖzet: {updated_lessons} ders Piyano yapıldı, {created_lessons} yeni Piyano dersi oluşturuldu, {moved_attendances} yoklama taşındı.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
