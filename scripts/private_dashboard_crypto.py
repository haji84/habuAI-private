"""Authenticated encryption for private GPS/log source blobs at rest.

Only the configured private runtime gets the master key; Git, Pages static
assets, API replies, CI artifacts, and diagnostics must never include it.
Existing unencrypted databases need an offline controlled migration: this
module never silently treats them as encrypted or deletes originals.
"""
from __future__ import annotations
import base64
import binascii
import os
import re

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"HABU-PRIVATE-BLOB-V1:"
SHA = re.compile(r"[0-9a-f]{64}\Z")
LIMIT = 20 * 1024 * 1024


class CryptoError(ValueError):
    pass


def key_from_environment() -> bytes:
    raw = os.environ.get("HABU_PRIVATE_ENCRYPTION_KEY_B64", "")
    try:
        if not raw or len(raw) != 44:
            raise CryptoError("PRIVATE_ENCRYPTION_KEY_REQUIRED")
        key = base64.b64decode(raw, validate=True)
        if len(key) != 32:
            raise CryptoError("PRIVATE_ENCRYPTION_KEY_INVALID")
        return key
    except (binascii.Error, ValueError) as exc:
        raise CryptoError("PRIVATE_ENCRYPTION_KEY_INVALID") from exc


class SourceCipher:
    def __init__(self, key: bytes):
        if type(key) is not bytes or len(key) != 32:
            raise CryptoError("PRIVATE_ENCRYPTION_KEY_INVALID")
        self.aes = AESGCM(key)

    @staticmethod
    def aad(sha: str) -> bytes:
        if not isinstance(sha, str) or not SHA.fullmatch(sha):
            raise CryptoError("SOURCE_SHA_INVALID")
        return MAGIC + bytes.fromhex(sha)

    def seal(self, source: bytes, sha: str) -> bytes:
        if type(source) is not bytes or not 0 < len(source) <= LIMIT:
            raise CryptoError("PRIVATE_SOURCE_SIZE_INVALID")
        nonce = os.urandom(12)
        return MAGIC + nonce + self.aes.encrypt(nonce, source, self.aad(sha))

    def open(self, ciphertext: bytes, sha: str) -> bytes:
        if type(ciphertext) is not bytes or not ciphertext.startswith(MAGIC) or (
            len(ciphertext) < len(MAGIC) + 12 + 16
        ):
            raise CryptoError("UNENCRYPTED_OR_INVALID_SOURCE")
        at = len(MAGIC)
        nonce = ciphertext[at:at + 12]
        try:
            plain = self.aes.decrypt(nonce, ciphertext[at + 12:], self.aad(sha))
        except Exception as exc:
            raise CryptoError("PRIVATE_DECRYPTION_FAILED") from exc
        if not 0 < len(plain) <= LIMIT:
            raise CryptoError("PRIVATE_SOURCE_SIZE_INVALID")
        return plain
