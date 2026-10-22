"""
"A robust data hiding scheme using modular key mapping and AES encryption"
Naman Beri, Vibha Gaur, Ravneet Kaur (2026)
Journal of Discrete Mathematical Sciences & Cryptography
ISSN 0972-0529 (Print), ISSN 2169-0065 (Online)
Vol. 29 (2026), No. 6, pp. 2349–2363
http://dx.doi.org/10.47974/JDMSC-2610
The article is located at articles/9/a-robust-data-hiding-scheme-using-modular-key-mapping-and-ae.pdf
"""

import os
import struct
import hashlib
from typing import Optional, Dict, Any, Tuple
from collections import defaultdict
from Crypto.Cipher import AES
from Crypto.Util.number import bytes_to_long
from PyQt5.QtWidgets import QMessageBox, QLabel, QSplitter
from templates import TabTemplate

def create_main_array(covertext: str) -> Dict[str, list]:
    A = defaultdict(list)
    for idx, char in enumerate(covertext):
        A[char].append(idx)
    return A

def lcg(x: int, a: int, b: int, m: int) -> int:
    if m <= 0:
        return 0
    return (x * a + b) % m

#return a tuple containing the key, as well as the generation method
def derive_key(key_str: Optional[str]) -> Tuple[bytes, str]:
    """
    Derives a 32-byte AES key and returns (key_bytes, generation_method_description).
    1. If nothing is provided: os.urandom(32)
    2. If 64-character hex string: 64-length hex string from user
    3. If any other string: SHA256 of the input string
    """
    if not key_str or len(key_str.strip()) == 0:
        return os.urandom(32), "randomly generated cryptographically secure 32-byte key"
    key_str = key_str.strip()
    if len(key_str) == 64:
        try:
            return bytes.fromhex(key_str), "64-length hex string from user"
        except ValueError:
            pass
    return hashlib.sha256(key_str.encode('utf-8')).digest(), "SHA256 (derived from user key)"


def AES_encrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_CTR, nonce=iv)
    return cipher.encrypt(data)

def AES_decrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_CTR, nonce=iv)
    return cipher.decrypt(data)

def embed(covertext: str, secret: str, key_str: Optional[str] = None) -> Dict[str, Any]:
    if not covertext:
        raise ValueError("Cover text cannot be empty.")
    if not secret:
        raise ValueError("Secret message cannot be empty.")

    A = create_main_array(covertext)

    #check if every character in the secret message exists in the cover text
    missing = set(secret) - set(A.keys())
    if missing:
        #canonical representation helps with displaying whitespace characters
        missing_repr = ", ".join(repr(c) for c in sorted(list(missing)))
        raise ValueError(
            f"Cover text is missing required character(s): [{missing_repr}]. "
            "Every character of the secret message MUST appear in the cover text."
        )

    #pick parameters and the seed
    b = len(secret)
    a = 1
    x = bytes_to_long(os.urandom(8))

    #create the array B, which contains the indices of the characters that make up the secret message
    B = []
    for char in secret:
        m = len(A[char])
        x = lcg(x, a, b, m)
        #x is the chosen index of char in the covertext
        B.append(A[char][x])

    key_bytes, key_method = derive_key(key_str)
    iv = os.urandom(12)

    #uses a struct to pack B into bytes
    #> specifies Big-Endian, I means unsigned int (4 bytes), len(B) is the number of times to pack.
    #*B unpacks B into individual arguments for struct.pack
    raw_indices_bytes = struct.pack(f'>{len(B)}I', *B)
    ciphertext = AES_encrypt(raw_indices_bytes, key_bytes, iv)

    #IV isn't secret, so it can be included in the payload
    payload = iv + ciphertext

    return {
        'payload_hex': payload.hex(),
        'key_hex': key_bytes.hex(),
        'key_method': key_method,
        'iv_hex': iv.hex(),
        'ciphertext_hex': ciphertext.hex(),
        'indices': B,
        'secret_len': len(secret)
    }

def extract(covertext: str, payload_input: str, key_str: str) -> Tuple[str, list, str]:

    if not covertext:
        raise ValueError("Cover text cannot be empty.")
    if not payload_input:
        raise ValueError("Ciphertext / payload cannot be empty.")
    if not key_str:
        raise ValueError("AES key cannot be empty.")

    # Clean payload string to hex digits
    clean_hex = ''.join(c for c in payload_input.strip() if c in "0123456789abcdefABCDEF")
    if len(clean_hex) < 32:  # at least 12 bytes IV (24 hex) + 4 bytes index (8 hex)
        raise ValueError("The hex string is too short.")

    payload_bytes = bytes.fromhex(clean_hex)

    #separate the iv and the ciphertext
    iv = payload_bytes[:12]
    ciphertext = payload_bytes[12:]

    key_bytes, key_method = derive_key(key_str)
    raw_indices_bytes = AES_decrypt(ciphertext, key_bytes, iv)

    #each index is 4 bytes long
    if len(raw_indices_bytes) % 4 != 0:
        raise ValueError("Decryption failed: incorrect data length.")

    count = len(raw_indices_bytes) // 4
    B = list(struct.unpack(f'>{count}I', raw_indices_bytes))

    cover_len = len(covertext)
    secret_chars = []
    for idx in B:
        #check for out of bounds
        if idx >= cover_len:
            raise ValueError(
                f"Decrypted index {idx} exceeds cover text length ({cover_len}). "
                "Ensure you provided the exact matching cover text and AES key."
            )
        secret_chars.append(covertext[idx])

    return "".join(secret_chars), B, key_method

class Algo9Tab(TabTemplate):
    def __init__(self):
        super().__init__()

        #create a custom label under the output field
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            "color: #333; font-size: 14pt; padding: 6px; background: #f8f9fa; "
            "border: 1px solid #dee2e6; border-radius: 4px; margin-top: 6px;"
        )

        #add the status label to the right side of the splitter below result output
        splitter = self.findChild(QSplitter)
        if splitter and splitter.count() > 1:
            right_widget = splitter.widget(1)
            right_widget.layout().addWidget(self.status_label)

        help_text = (
            "Algorithm 9: Modular Key Mapping & AES Encryption\n\n"
            "EMBEDDING:\n"
            "1. Enter cover text in 'Cover Text' (must contain every character of the secret).\n"
            "2. Enter secret message in 'Secret Message'.\n"
            "3. Enter an AES key (passphrase or 64-char hex) or leave empty to auto-generate.\n"
            "4. Click 'Embed Secret Message'. The encrypted payload will appear in the result box, and metadata below.\n\n"
            "EXTRACTION:\n"
            "1. Enter/paste the cover text into 'Cover Text'.\n"
            "2. Paste the encrypted payload (hex) into 'Secret Message' field.\n"
            "3. Enter the AES key (passphrase or 64-char hex) into 'AES Key' field.\n"
            "4. Click 'Extract Secret Message' to decode the secret."
        )

        self.customize_ui(
            cover_lbl="Cover Text",
            secret_lbl="Secret Message",
            key_lbl="AES Key (32 bytes)",
            embed_btn="Embed Secret Message",
            extract_btn="Extract Secret Message",
            output_grp="Output (encrypted array of indices)",
            tab_help_text=help_text
        )

        self.embed_button.clicked.connect(self.do_embed)
        self.extract_button.clicked.connect(self.do_extract)

    def do_embed(self):
        cover = self.covertext_input.toPlainText()
        secret = self.secret_input.toPlainText()
        key = self.key_input.text().strip()

        if not cover.strip():
            QMessageBox.warning(self, "Error", "Cover text cannot be empty.")
            return
        if not secret:
            QMessageBox.warning(self, "Error", "Secret message cannot be empty.")
            return

        try:
            res = embed(cover, secret, key)

            # If key was not provided and instead generated automatically, put that key in the input field
            if not key:
                self.key_input.setText(res['key_hex'])

            self.result_output.setPlainText(res['payload_hex'])
            self.status_label.setText(
                f"<b>Embedding Successful!</b><br>"
                f"• <b>B array (indices):</b> <code>{res['indices']}</code><br>"
                f"• <b>AES Key:</b> {res['key_method']}<br>"
                f"• <b>Secret Length:</b> {res['secret_len']} chars | <b>Cover Length:</b> {len(cover)} chars"
            )

        except Exception as e:
            QMessageBox.critical(self, "Embedding Error", str(e))

    def do_extract(self):
        cover = self.covertext_input.toPlainText()
        payload = self.secret_input.toPlainText().strip()
        key = self.key_input.text().strip()

        if not cover.strip():
            QMessageBox.warning(self, "Error", "Please provide the cover text in the 'Cover Text' field.")
            return
        if not payload:
            QMessageBox.warning(self, "Error", "Please provide the encrypted payload (hex) in the 'Secret Message' field.")
            return
        if not key:
            QMessageBox.warning(self, "Error", "Please provide the AES key in the 'AES Key' field.")
            return

        try:
            secret, B, key_method = extract(cover, payload, key)
            #put the secret in the result field
            self.result_output.setPlainText(secret)
            self.status_label.setText(
                f"<b>Extraction Successful!</b><br>"
                f"• <b>B array:</b> <code>{B}</code><br>"
                f"• <b>AES Key:</b> {key_method}<br>"
                f"• <b>Extracted Secret Length:</b> {len(secret)} characters"
            )

        except Exception as e:
            QMessageBox.critical(self, "Extraction Error", str(e))

