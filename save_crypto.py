"""AES-128-ECB encryption/decryption for Digimon Story: Time Stranger save files.

The game uses AES-128-ECB with a fixed key for all save files.
Save files are exactly 3,098,176 bytes (encrypted).
"""

from Crypto.Cipher import AES

_SAVE_AES_KEY = bytes.fromhex('33393632373736373534353535383833')

SAVE_FILE_SIZE = 3_098_176


def decrypt(data: bytes) -> bytes:
    """Decrypt a save file. Returns decrypted bytes."""
    if len(data) != SAVE_FILE_SIZE:
        raise ValueError(f"Invalid save file size: {len(data)} (expected {SAVE_FILE_SIZE})")
    cipher = AES.new(_SAVE_AES_KEY, AES.MODE_ECB)
    return cipher.decrypt(data)


def encrypt(data: bytes) -> bytes:
    """Encrypt save data back to game format. Returns encrypted bytes."""
    if len(data) != SAVE_FILE_SIZE:
        raise ValueError(f"Invalid data size: {len(data)} (expected {SAVE_FILE_SIZE})")
    cipher = AES.new(_SAVE_AES_KEY, AES.MODE_ECB)
    return cipher.encrypt(data)
