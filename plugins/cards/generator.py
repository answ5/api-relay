"""
Card-code generation — cryptographically secure random codes.

Format: XXXX-XXXX-XXXX-XXXX (16 chars, base-36 [0-9A-Z]).
"""

from __future__ import annotations

import hashlib
import secrets

_CARD_TEMPLATE = "{p1}-{p2}-{p3}-{p4}"
_CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def generate_card_code() -> str:
    """Generate a single 16-character card code.

    Uses ``secrets`` module (cryptographically secure).
    """
    parts = ["".join(secrets.choice(_CHARSET) for _ in range(4)) for _ in range(4)]
    return _CARD_TEMPLATE.format(p1=parts[0], p2=parts[1], p3=parts[2], p4=parts[3])


def hash_card_code(code: str) -> str:
    """SHA-256 hash for safe storage (never store raw codes)."""
    return hashlib.sha256(code.encode()).hexdigest()
