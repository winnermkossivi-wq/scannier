"""
Verification de signature HMAC pour webhooks.

Format : X-Webhook-Signature: sha256=<hex_digest>
Le secret est partage entre l'emetteur et Scannier (WEBHOOK_SECRET_KEY).
"""
import hmac
import hashlib
import time
from django.conf import settings


def verify_webhook_signature(request, max_age_seconds=300):
    """
    Verifie la signature HMAC-SHA256 d'un webhook entrant.

    Headers requis :
    - X-Webhook-Signature: sha256=<hex_digest>
    - X-Webhook-Timestamp: unix timestamp (optionnel, pour anti-replay)

    Returns: (bool, error_message)
    """
    secret = getattr(settings, "WEBHOOK_SECRET_KEY", "")
    if not secret:
        return False, "Webhook secret non configure"

    signature_header = request.headers.get("X-Webhook-Signature", "")
    if not signature_header.startswith("sha256="):
        return False, "Header X-Webhook-Signature manquant ou invalide"

    provided_sig = signature_header[7:]  # enleve "sha256="

    # Recupere le corps brut de la requete
    body = request.body
    if not body:
        return False, "Corps de requete vide"

    # Calcul de la signature attendue
    expected_sig = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()

    # Comparaison en temps constant
    if not hmac.compare_digest(provided_sig, expected_sig):
        return False, "Signature invalide"

    # Verification timestamp anti-replay (optionnel)
    timestamp_header = request.headers.get("X-Webhook-Timestamp")
    if timestamp_header:
        try:
            ts = int(timestamp_header)
            now = int(time.time())
            if abs(now - ts) > 300:  # 5 minutes
                return False, "Timestamp trop ancien (replay possible)"
        except ValueError:
            return False, "Timestamp invalide"

    return True, None


def sign_webhook_payload(payload: bytes, secret: str = None) -> str:
    """
    Signe un payload pour l'envoi de webhook sortant.
    Returns: "sha256=<hex_digest>"
    """
    secret = secret or getattr(settings, "WEBHOOK_SECRET_KEY", "")
    if not secret:
        raise ValueError("WEBHOOK_SECRET_KEY non configure")

    sig = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()
    return f"sha256={sig}"