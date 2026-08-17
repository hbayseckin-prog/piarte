"""Generate VAPID keys for web push. Run: python scripts/generate_vapid_keys.py"""
from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid01


def main() -> None:
    vapid = Vapid01()
    vapid.generate_keys()
    private_pem = vapid.private_pem().decode()
    raw = vapid.public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    import base64

    public_key = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    print("Railway / .env icin asagidaki degiskenleri ekleyin:\n")
    print(f"VAPID_PUBLIC_KEY={public_key}")
    print(f"VAPID_PRIVATE_KEY={private_pem!r}")
    print("VAPID_CLAIMS_EMAIL=mailto:admin@piarte.app")


if __name__ == "__main__":
    main()
