from __future__ import annotations

import logging
import re
from typing import Tuple, Dict

from sqlalchemy.orm import Session

from . import crud, schemas, excel_loader

logger = logging.getLogger(__name__)


def sync_students_from_excel(db: Session):
    dataset = excel_loader.get_durum_dataset()
    if not dataset.rosters:
        crud.reset_teacher_student_links(db)
        return {"students_created": 0, "students_updated": 0, "skipped": 0, "assignments": 0, "teachers_created": 0}

    crud.reset_teacher_student_links(db)
    stats = {
        "students_created": 0,
        "students_updated": 0,
        "skipped": 0,
        "assignments": 0,
        "teachers_created": 0,
    }
    teacher_cache: Dict[str, int] = {}
    assigned_map: Dict[int, int] = {}

    for roster in dataset.rosters:
        teacher_first, teacher_last = _split_person_name(roster.teacher_display or roster.sheet_title)
        if not teacher_first:
            teacher_first = "Öğretmen"
        if not teacher_last:
            teacher_last = "Ekibimiz"
        teacher_key = f"{teacher_first.lower()}|{teacher_last.lower()}"
        teacher_id = teacher_cache.get(teacher_key)
        if teacher_id is None:
            teacher, created_flag = crud.get_or_create_teacher(db, teacher_first, teacher_last)
            teacher_id = teacher.id
            teacher_cache[teacher_key] = teacher_id
            if created_flag:
                stats["teachers_created"] += 1

        for row in roster.rows:
            first_name, last_name = _split_person_name(row.student)
            if not first_name or not last_name:
                stats["skipped"] += 1
                continue
            student = crud.find_student_by_name(db, first_name, last_name)
            parent_name = row.guardian
            phone = row.phone
            if student:
                changed = False
                if parent_name and not student.parent_name:
                    student.parent_name = parent_name
                    changed = True
                if phone:
                    if not student.parent_phone:
                        student.parent_phone = phone
                        changed = True
                    if not student.phone_primary:
                        student.phone_primary = phone
                        changed = True
                if changed:
                    stats["students_updated"] += 1
            else:
                payload = schemas.StudentCreate(
                    first_name=first_name,
                    last_name=last_name,
                    parent_name=parent_name,
                    parent_phone=phone,
                    phone_primary=phone,
                )
                student = crud.create_student(db, payload)
                stats["students_created"] += 1
            if student.id in assigned_map:
                # aynı öğrenciyi ikinci kez görürsek son görülen öğretmeni baz al
                if assigned_map[student.id] == teacher_id:
                    continue
            # Öğretmen öğrenci eşlemesi
            crud.assign_student_to_teacher(db, teacher_id, student.id)
            stats["assignments"] += 1
            assigned_map[student.id] = teacher_id

    db.commit()

    if stats["students_created"] or stats["students_updated"] or stats["assignments"]:
        logger.info(
            "Durum.xlsx senkronizasyonu tamamlandı: %s yeni öğrenci, %s güncelleme, %s atama, %s yeni öğretmen",
            stats["students_created"],
            stats["students_updated"],
            stats["assignments"],
            stats["teachers_created"],
        )

    return stats


def _split_person_name(full_name: str | None) -> Tuple[str | None, str | None]:
    if not full_name:
        return None, None
    cleaned = re.sub(r"[^A-Za-zÇÖÜĞŞİçöüğşıÂÊÎÔÛâêîôû\s']", " ", full_name)
    tokens = [token for token in cleaned.strip().split() if token]
    if not tokens:
        return None, None
    if len(tokens) == 1:
        return tokens[0].title(), "Belirtilmedi"
    first_name = tokens[0].title()
    last_name = " ".join(token.title() for token in tokens[1:]) or "Belirtilmedi"
    return first_name, last_name

