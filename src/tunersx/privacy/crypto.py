from __future__ import annotations

import base64


def xor_encrypt(plain: bytes, key: str) -> bytes:
    key_b = key.encode('utf-8')
    out = bytes([b ^ key_b[i % len(key_b)] for i, b in enumerate(plain)])
    return base64.b64encode(out)


def xor_decrypt(cipher: bytes, key: str) -> bytes:
    raw = base64.b64decode(cipher)
    key_b = key.encode('utf-8')
    return bytes([b ^ key_b[i % len(key_b)] for i, b in enumerate(raw)])
