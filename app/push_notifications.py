import json
import logging
import os

from pywebpush import WebPushException, webpush
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "").strip()
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "").strip()
VAPID_CLAIMS_EMAIL = os.getenv("VAPID_CLAIMS_EMAIL", "mailto:admin@piarte.app").strip()


def push_enabled() -> bool:
    return bool(VAPID_PRIVATE_KEY and VAPID_PUBLIC_KEY)


def get_vapid_public_key() -> str:
    return VAPID_PUBLIC_KEY


def is_cash_payment(method: str | None) -> bool:
    return (method or "").strip().lower() in {"nakit", "cash"}


def _vapid_claims() -> dict:
    return {"sub": VAPID_CLAIMS_EMAIL}


def send_web_push(subscription_info: dict, payload: dict) -> str:
    """Returns: sent | stale | failed"""
    if not push_enabled():
        return "failed"
    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=_vapid_claims(),
        )
        return "sent"
    except WebPushException as exc:
        logger.warning("Web push gonderilemedi: %s", exc)
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status in (404, 410):
            return "stale"
        return "failed"
    except Exception as exc:
        logger.warning("Web push hatasi: %s", exc)
        return "failed"


def notify_admins_staff_cash_payment(
    db: Session,
    *,
    payment,
    staff_user: dict,
    student,
) -> int:
    from . import crud

    if not push_enabled():
        logger.info("VAPID anahtarlari yok; admin push bildirimi atlandi.")
        return 0

    student_name = "-"
    if student:
        student_name = f"{student.first_name or ''} {student.last_name or ''}".strip() or "-"

    staff_name = (staff_user.get("full_name") or staff_user.get("username") or "Staff").strip()
    amount_text = f"{float(payment.amount_try):.2f} TL"
    method_text = (payment.method or "Nakit").strip()

    payload = {
        "title": "Piarte - Nakit Odeme",
        "body": f"{staff_name}: {student_name} - {amount_text} TL ({method_text})",
        "url": "/ui/reports/payments",
    }

    sent = 0
    subscriptions = crud.list_push_subscriptions_for_admins(db)
    stale_ids: list[int] = []

    for sub in subscriptions:
        info = {
            "endpoint": sub.endpoint,
            "keys": {
                "p256dh": sub.p256dh_key,
                "auth": sub.auth_key,
            },
        }
        result = send_web_push(info, payload)
        if result == "sent":
            sent += 1
        elif result == "stale":
            stale_ids.append(sub.id)

    if stale_ids:
        crud.delete_push_subscriptions_by_ids(db, stale_ids)

    return sent


def maybe_notify_admins_for_staff_cash_payment(db: Session, payment, actor_user: dict | None) -> None:
    if not actor_user or actor_user.get("role") != "staff":
        return
    if not is_cash_payment(getattr(payment, "method", None)):
        return

    from . import crud

    student = crud.get_student(db, payment.student_id)
    try:
        notify_admins_staff_cash_payment(
            db,
            payment=payment,
            staff_user=actor_user,
            student=student,
        )
    except Exception as exc:
        logger.warning("Admin odeme bildirimi gonderilemedi: %s", exc)
