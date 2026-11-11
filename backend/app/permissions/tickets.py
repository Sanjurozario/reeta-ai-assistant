import hashlib
import time
import uuid
from typing import Any, Dict, Optional, Tuple
from jose import jwt, JWTError
from app.config import settings


class TicketManager:
    """Manages ephemeral approval tickets and cryptographic tokens for Tier 2 actions."""

    ALGORITHM = "HS256"

    @staticmethod
    def hash_resource(resource: str) -> str:
        """Computes SHA-256 digest of target resource to prevent token reuse across different targets."""
        return hashlib.sha256((resource or "").strip().encode("utf-8")).hexdigest()

    @classmethod
    def create_ticket_id(cls) -> str:
        return f"ticket_{uuid.uuid4().hex[:12]}"

    @classmethod
    def issue_signed_token(
        cls,
        ticket_id: str,
        action: str,
        target_resource: str,
        ttl_seconds: Optional[int] = None,
    ) -> str:
        """
        Signs an ephemeral JWT containing target claims, expiration, and resource hash.
        """
        ttl = ttl_seconds or settings.APPROVAL_TICKET_TTL_SECONDS
        now = int(time.time())
        claims = {
            "jti": uuid.uuid4().hex,
            "ticket_id": ticket_id,
            "action": action.lower().strip(),
            "resource_hash": cls.hash_resource(target_resource),
            "iat": now,
            "exp": now + ttl,
        }
        return jwt.encode(claims, settings.SECRET_KEY, algorithm=cls.ALGORITHM)

    @classmethod
    def verify_token(
        cls,
        token: str,
        expected_action: str,
        expected_resource: str,
    ) -> Tuple[bool, str]:
        """
        Verifies signature, expiration, action match, and resource digest.
        Returns (is_valid, reason).
        """
        if not token:
            return False, "Approval token is missing."

        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[cls.ALGORITHM],
                options={"leeway": 0},
            )
        except jwt.ExpiredSignatureError:
            return False, "Approval token has expired."
        except JWTError as e:
            return False, f"Invalid token signature: {e}"

        # Explicit float wall-clock expiration check
        if payload.get("exp") and time.time() > payload["exp"]:
            return False, "Approval token has expired."

        # Verify action
        token_action = payload.get("action", "")
        if token_action != expected_action.lower().strip():
            return False, f"Token action '{token_action}' does not match requested action '{expected_action}'."

        # Verify resource hash
        expected_hash = cls.hash_resource(expected_resource)
        token_hash = payload.get("resource_hash", "")
        if token_hash != expected_hash:
            return False, "Token was issued for a different resource (hash mismatch)."

        return True, "Token verified successfully."
