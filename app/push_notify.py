"""Web Push bildirimleri — nakit tahsilat → admin cihazları.

Ödeme kaydını bozmaz: gönderim hataları yutulur, abonelik 410 ise silinir.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import threading
from typing import Any

from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from . import models
from .db import SessionLocal, engine

logger = logging.getLogger(__name__)

_VAPID_CACHE: dict[str, str] | None = None


def _b64url(data: bytes) -> str:
	return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def ensure_push_subscriptions_table() -> None:
	try:
		from sqlalchemy import inspect

		inspector = inspect(engine)
		if "push_subscriptions" in set(inspector.get_table_names()):
			return
		print("push_subscriptions tablosu bulunamadi, olusturuluyor...")
		is_pg = "postgres" in str(engine.url).lower()
		ddl = """
			CREATE TABLE push_subscriptions (
				id SERIAL PRIMARY KEY,
				user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
				endpoint TEXT NOT NULL UNIQUE,
				p256dh TEXT NOT NULL,
				auth TEXT NOT NULL,
				user_agent VARCHAR(255),
				created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
				updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
			)
		""" if is_pg else """
			CREATE TABLE push_subscriptions (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
				endpoint TEXT NOT NULL UNIQUE,
				p256dh TEXT NOT NULL,
				auth TEXT NOT NULL,
				user_agent VARCHAR(255),
				created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
				updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
			)
		"""
		db = SessionLocal()
		try:
			db.execute(text(ddl))
			db.commit()
			print("push_subscriptions tablosu olusturuldu")
		except Exception as e:
			db.rollback()
			print(f"push_subscriptions tablo olusturma: {e}")
		finally:
			db.close()
	except Exception as e:
		print(f"push_subscriptions tablo kontrol hatasi: {e}")


def ensure_vapid_meta_table() -> None:
	"""VAPID anahtarları için TEXT değerli meta tablosu."""
	try:
		db = SessionLocal()
		try:
			db.execute(text("""
				CREATE TABLE IF NOT EXISTS push_vapid_keys (
					id INTEGER PRIMARY KEY,
					public_key TEXT NOT NULL,
					private_key TEXT NOT NULL,
					created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
				)
			"""))
			db.commit()
		except Exception as e:
			db.rollback()
			print(f"push_vapid_keys tablo: {e}")
		finally:
			db.close()
	except Exception as e:
		print(f"push_vapid_keys kontrol: {e}")


def _generate_vapid_keypair() -> tuple[str, str]:
	from cryptography.hazmat.backends import default_backend
	from cryptography.hazmat.primitives import serialization
	from cryptography.hazmat.primitives.asymmetric import ec

	private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
	private_pem = private_key.private_bytes(
		encoding=serialization.Encoding.PEM,
		format=serialization.PrivateFormat.PKCS8,
		encryption_algorithm=serialization.NoEncryption(),
	).decode("utf-8")
	nums = private_key.public_key().public_numbers()
	public_raw = b"\x04" + nums.x.to_bytes(32, "big") + nums.y.to_bytes(32, "big")
	return _b64url(public_raw), private_pem


def get_vapid_keys() -> tuple[str, str] | None:
	"""(public_key_b64url, private_pem). Yoksa None."""
	global _VAPID_CACHE
	if _VAPID_CACHE:
		return _VAPID_CACHE["public"], _VAPID_CACHE["private"]

	pub = (os.getenv("VAPID_PUBLIC_KEY") or "").strip()
	priv = (os.getenv("VAPID_PRIVATE_KEY") or "").strip()
	if pub and priv:
		_VAPID_CACHE = {"public": pub, "private": priv}
		return pub, priv

	ensure_vapid_meta_table()
	db = SessionLocal()
	try:
		row = db.execute(text("SELECT public_key, private_key FROM push_vapid_keys WHERE id = 1")).fetchone()
		if row and row[0] and row[1]:
			_VAPID_CACHE = {"public": row[0], "private": row[1]}
			return row[0], row[1]
		pub, priv = _generate_vapid_keypair()
		db.execute(
			text("INSERT INTO push_vapid_keys (id, public_key, private_key) VALUES (1, :p, :s)"),
			{"p": pub, "s": priv},
		)
		db.commit()
		_VAPID_CACHE = {"public": pub, "private": priv}
		logger.info("VAPID anahtarları oluşturuldu ve veritabanına kaydedildi")
		return pub, priv
	except Exception as e:
		db.rollback()
		logger.error("VAPID anahtarları alınamadı: %s", e)
		return None
	finally:
		db.close()


def get_vapid_public_key() -> str | None:
	keys = get_vapid_keys()
	return keys[0] if keys else None


def vapid_claims() -> dict[str, str]:
	"""Apple, @localhost / @*.local VAPID subject'lerini reddeder (403 BadJwtToken)."""
	configured = (os.getenv("VAPID_CLAIM_EMAIL") or os.getenv("VAPID_SUBJECT") or "").strip()
	if configured:
		if configured.startswith("mailto:") or configured.startswith("https://"):
			return {"sub": configured.rstrip("/")}
		if "@" in configured:
			return {"sub": f"mailto:{configured}"}
		return {"sub": f"https://{configured.rstrip('/')}"}

	domain = (
		os.getenv("PUBLIC_BASE_URL")
		or os.getenv("VAPID_SUBJECT_URL")
		or os.getenv("RAILWAY_PUBLIC_DOMAIN")
		or os.getenv("RAILWAY_STATIC_URL")
		or ""
	).strip()
	if domain:
		if domain.startswith("http://"):
			domain = "https://" + domain[len("http://") :]
		if domain.startswith("https://"):
			return {"sub": domain.rstrip("/")}
		return {"sub": f"https://{domain.rstrip('/')}"}

	return {"sub": "mailto:noreply@piarte.app"}


def upsert_subscription(
	db: Session,
	*,
	user_id: int,
	endpoint: str,
	p256dh: str,
	auth: str,
	user_agent: str | None = None,
) -> models.PushSubscription:
	existing = (
		db.query(models.PushSubscription)
		.filter(models.PushSubscription.endpoint == endpoint)
		.first()
	)
	if existing:
		existing.user_id = user_id
		existing.p256dh = p256dh
		existing.auth = auth
		if user_agent is not None:
			existing.user_agent = (user_agent or "")[:255] or None
		db.commit()
		db.refresh(existing)
		return existing
	row = models.PushSubscription(
		user_id=user_id,
		endpoint=endpoint,
		p256dh=p256dh,
		auth=auth,
		user_agent=(user_agent or "")[:255] or None,
	)
	db.add(row)
	db.commit()
	db.refresh(row)
	return row


def delete_subscription_by_endpoint(db: Session, endpoint: str) -> None:
	row = (
		db.query(models.PushSubscription)
		.filter(models.PushSubscription.endpoint == endpoint)
		.first()
	)
	if row:
		db.delete(row)
		db.commit()


def list_admin_subscriptions(db: Session) -> list[models.PushSubscription]:
	return (
		db.query(models.PushSubscription)
		.join(models.User, models.User.id == models.PushSubscription.user_id)
		.filter(
			or_(
				models.User.role == "admin",
				models.User.role.is_(None),
				models.User.role == "",
			)
		)
		.all()
	)


def count_admin_subscriptions(db: Session) -> int:
	return len(list_admin_subscriptions(db))


def is_nakit_method(method: str | None) -> bool:
	return (method or "").strip().casefold() == "nakit"


def _send_one(subscription: models.PushSubscription, payload: dict[str, Any], private_key: str) -> bool:
	"""True = ok veya geçici hata; False = abonelik silinmeli."""
	try:
		from pywebpush import webpush
	except ImportError:
		logger.error("pywebpush yüklü değil; push atlandı")
		print("PUSH_ERROR: pywebpush yüklü değil")
		return True

	try:
		claims = vapid_claims()
		webpush(
			subscription_info={
				"endpoint": subscription.endpoint,
				"keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
			},
			data=json.dumps(payload, ensure_ascii=False),
			vapid_private_key=private_key,
			vapid_claims=claims,
			ttl=86400,
		)
		print(f"PUSH_OK endpoint={subscription.endpoint[:48]}… sub={claims.get('sub')}")
		return True
	except Exception as e:
		status = getattr(getattr(e, "response", None), "status_code", None)
		body = ""
		try:
			resp = getattr(e, "response", None)
			if resp is not None and getattr(resp, "text", None):
				body = (resp.text or "")[:300]
		except Exception:
			pass
		print(f"PUSH_FAIL status={status} err={e} body={body}")
		logger.warning("Push gönderilemedi status=%s: %s %s", status, e, body)
		if status in (404, 410):
			return False
		return True


def notify_admins_staff_cash(
	*,
	student_name: str,
	amount_try: float,
	staff_name: str,
	payment_id: int | None = None,
) -> None:
	"""Admin aboneliklerine nakit tahsilat bildirimi."""
	keys = get_vapid_keys()
	if not keys:
		print("PUSH_SKIP: VAPID anahtarı yok")
		return
	_, private_key = keys
	payload = {
		"title": "Nakit tahsilat",
		"body": f"{staff_name}: {student_name} — {amount_try:.2f} ₺",
		"url": "/ui/finance/income",
		"tag": f"cash-{payment_id}" if payment_id else "cash-payment",
	}
	db = SessionLocal()
	try:
		subs = list_admin_subscriptions(db)
		print(f"PUSH_SEND count={len(subs)} student={student_name!r} by={staff_name!r}")
		if not subs:
			print("PUSH_SKIP: admin aboneliği yok")
			return
		stale_ids: list[int] = []
		for sub in subs:
			ok = _send_one(sub, payload, private_key)
			if not ok:
				stale_ids.append(sub.id)
		if stale_ids:
			db.query(models.PushSubscription).filter(
				models.PushSubscription.id.in_(stale_ids)
			).delete(synchronize_session=False)
			db.commit()
			print(f"PUSH_CLEANED stale={len(stale_ids)}")
	except Exception as e:
		logger.error("Admin push bildirimi hatası: %s", e)
		print(f"PUSH_ERROR: {e}")
		try:
			db.rollback()
		except Exception:
			pass
	finally:
		db.close()


def schedule_admin_cash_notify(
	*,
	student_name: str,
	amount_try: float,
	staff_name: str,
	payment_id: int | None = None,
) -> None:
	"""Ödeme yanıtından bağımsız thread."""
	threading.Thread(
		target=notify_admins_staff_cash,
		kwargs={
			"student_name": student_name,
			"amount_try": amount_try,
			"staff_name": staff_name,
			"payment_id": payment_id,
		},
		daemon=True,
	).start()
