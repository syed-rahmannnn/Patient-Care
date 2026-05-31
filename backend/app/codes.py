import secrets

# Unambiguous alphabet — no 0/O/1/I/L so a nurse can read a code off a screen
# and type it without confusion.
_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def new_join_code() -> str:
    """A short, human-typeable bed join code, e.g. "7K3-92A"."""
    raw = "".join(secrets.choice(_ALPHABET) for _ in range(6))
    return f"{raw[:3]}-{raw[3:]}"
