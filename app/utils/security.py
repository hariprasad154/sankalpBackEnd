"""Base64 encode/decode for stored credentials (upgrade to bcrypt later)."""
import base64


def encode_value(value: str) -> str:
    if not value:
        return ""
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def decode_value(encoded: str) -> str:
    if not encoded:
        return ""
    return base64.b64decode(encoded.encode("ascii")).decode("utf-8")
