"""
"Enhancing Imperceptibility: Zero-width Character-based Text Steganography for Preserving Message Privacy"
Saqib Ishtiaq, Naveed Ejaz, Muhammad Usman Hashmi, Syed Imran Hussain Shah (2025).
Acta Informatica Pragensia, 14(3), 445-459. https://doi.org/10.18267/j.aip.271
The article is located at articles/8/AIP_aip-202503-0009.pdf
"""

import math
from dahuffman import HuffmanCodec
from templates import TabTemplate
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QSplitter, QMessageBox

# Zero-Width Characters
# 1. U+200B: Zero width space
# 2. U+200C: Zero width non-joiner
# 3. U+200D: Zero width joiner
# 4. U+200E: Left-to-right mark
# 5. U+202A: Left-to-right embedding
# 6. U+202C: Pop directional formatting
# 7. U+202D: Left-to-right override
# 8. U+180E: Mongolian vowel separator
ZWC = [
    '\u200b',
    '\u200c',
    '\u200d',
    '\u200e',
    '\u202a',
    '\u202c',
    '\u202d',
    '\u180e',
]

def text_to_bits(text: str) -> str:
    #Converts a string to an 8-bit per character binary string
    return ''.join(format(ord(c), '08b') for c in text)

def bits_to_text(bits: str) -> str:
    chars = [bits[i:i+8] for i in range(0, len(bits), 8)]
    result = ''.join(chr(int(b, 2)) for b in chars if len(b) == 8)
    return result.rstrip('\x00') # strip padding

def compress_message(secret_message, key):
    """
    Compresses the secret message. Uses Huffman encoding if the key is provided. 
    Otherwise, standard 8-bit ASCII is used.
    """
    if key and len(key.strip()) > 0:
        missing = set(secret_message) - set(key)
        if missing:
            missing_chars = ", ".join(repr(x) for x in missing)
            raise ValueError(
                f"Secret message contains character(s) not present in key: [{missing_chars}]. "
                "The key text must contain all unique characters of the secret message to build the Huffman tree."
            )
        codec = HuffmanCodec.from_data(key)
        enc = codec.encode(secret_message)
        #mb - compressed binary secret
        #takes each byte of enc and converts it to 8-bit binary string
        mb = ''.join(f'{b:08b}' for b in enc)
        return mb, codec
    else:
        return text_to_bits(secret_message), None

def decompress_message(mb_bits, key):
    if key and len(key.strip()) > 0:
        try:
            codec = HuffmanCodec.from_data(key)
            byte_chunks = [mb_bits[i:i + 8] for i in range(0, len(mb_bits), 8) if len(mb_bits[i:i + 8]) == 8]
            raw_bytes = bytes(int(b, 2) for b in byte_chunks)
            return codec.decode(raw_bytes)
        except Exception as e:
            raise ValueError(f"Huffman decompression failed: {e}")
    else:
        return bits_to_text(mb_bits)

def compute_parameters(lc, lb, lz=8):
    """
    Calculates embedding parameters:
    Finds the minimum number of partitions n such that Cn >= Lb, where:
    m = floor(Lc / n)
    Cp = log2(m) + log2(Lz)
    Cn = Cp * n
    """
    n = 0
    log2_lz = int(math.log2(lz))
    while True:
        n += 1 #number of partitions
        m = lc // n #number of embedding locations in a partition
        if m <= 0:
            raise ValueError(f"Cover text is too short ({lc} characters) to hide {lb} bits of message. ")
        log2_m = int(math.log2(m)) if m >= 1 else 0
        cp = log2_m + log2_lz #partition capacity
        cn = cp * n #total capacity
        if cn >= lb: #if total capacity >= length of the binary secret, then ok
            return n, m, cp, cn, log2_m, log2_lz

def embed(cover_text, secret_message, key):
    """
    Hides secret_message in cover_text using ZWCs.
    """
    if not cover_text:
        raise ValueError("Cover text cannot be empty.")
    if not secret_message:
        raise ValueError("Secret message cannot be empty.")

    # Strip any ZWCs from cover text
    clean_tc = ''.join(c for c in cover_text if c not in ZWC)
    lc = len(clean_tc)
    lz = len(ZWC)

    mb, _ = compress_message(secret_message, key)
    lb = len(mb)

    n, m, cp, cn, log2_m, log2_lz = compute_parameters(lc, lb, lz)

    #Divide Tc into n partitions of size m
    tc_parts = [clean_tc[i * m:(i + 1) * m] for i in range(n)]
    #Remaining (unused) covertext
    rem_tc = clean_tc[n * m:]

    #Divide Mb into n partitions of size Cp (pad with 0s if Cn > Lb)
    mb_padded = mb.ljust(cn, '0')
    mb_parts = [mb_padded[i * cp:(i + 1) * cp] for i in range(n)]

    ts_parts = []
    for i in range(n):
        pi = tc_parts[i] #covertext chunks
        bi = mb_parts[i] #binary chunks (compressed secret)

        # log2(Lz) codes 3 bits of information. log2(m) codes the rest
        # log2(Lz) tells us which ZWC to pick
        # log2(m) tells us where to insert it
        #example: if the size of one binary chunk is 8 bits, there are 8 possible insertion locations
        #so floor(log2(8)) = 3, then bi[log2_lz:log2_lz + log2_m] codes 3 bits of information
        #which is enough to cover all insertion positions
        #importantly, an 8-bit chunk has 8 insertion locations, not 9
        zd = int(bi[:log2_lz], 2) #take three most significant (leftmost) bits
        if log2_m > 0:
            ld = int(bi[log2_lz:log2_lz + log2_m], 2)
        else:
            ld = 0

        #Insert Z[Zd] at Ld location
        new_pi = pi[:ld] + ZWC[zd] + pi[ld:]
        ts_parts.append(new_pi)

    stegotext = ''.join(ts_parts) + rem_tc
    ls = len(stegotext)

    info = {
        'n': n, #number of partitions
        'm': m, #Number of embedding locations in a partition
        'Cp': cp, #partition capacity
        'Cn': cn, #capacity of all n partitions
        'Lb': lb, #length of secret message in bits
        'Lc': lc, #length of cover text in characters
        'Ls': ls, #length of stegotext in characters
        'key_used': bool(key and len(key.strip()) > 0),
    }

    return stegotext, info

def extract(stegotext, key):
    if not stegotext:
        raise ValueError("Stegotext cannot be empty.")

    lz = len(ZWC)

    #Count ZWCs (number of modifications/insertions)
    n = sum(1 for c in stegotext if c in ZWC)
    if n == 0:
        raise ValueError("No ZWCs found in text.")
    ls = len(stegotext)
    lc = ls - n
    m = lc // n
    if m <= 0:
        raise ValueError("Partition length m can't be 0.")

    log2_m = int(math.log2(m)) if m >= 1 else 0
    log2_lz = int(math.log2(lz))

    #Divide Ts into n partitions of size m + 1
    part_size = m + 1 #this is the partition length AFTER embedding
    ts_parts = [stegotext[i * part_size:(i + 1) * part_size] for i in range(n)]

    #Extract bits from each partition
    #Iterate through each chunk of stegotext
    mb_parts = []
    for pi in ts_parts:
        found = False
        for idx, c in enumerate(pi):
            if c in ZWC:
                zd = ZWC.index(c) #first 3 bits of information
                ld = idx #the position of the ZWC tells us the remained of information
                found = True
                break
        if not found:
            raise ValueError("Each partition MUST have a ZWC.")

        zb = format(zd, f'0{log2_lz}b') #03b
        l_b = format(ld, f'0{log2_m}b') if log2_m > 0 else ''
        mb_parts.append(zb + l_b)

    mb = ''.join(mb_parts)
    return decompress_message(mb, key)

class Algo8Tab(TabTemplate):
    def __init__(self):
        super().__init__()

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            "color: #333; font-size: 14pt; padding: 6px; background: #f8f9fa; "
            "border: 1px solid #dee2e6; border-radius: 4px; margin-top: 6px;"
        )

        #add the new status label to the right side of the splitter
        splitter = self.findChild(QSplitter)
        if splitter and splitter.count() > 1:
            right_widget = splitter.widget(1)
            right_widget.layout().addWidget(self.status_label)

        # Connect button triggers
        self.embed_button.clicked.connect(self.handle_embed)
        self.extract_button.clicked.connect(self.handle_extract)

    def handle_embed(self):
        cover = self.covertext_input.toPlainText()
        secret = self.secret_input.toPlainText()
        key = self.key_input.text().strip() or None

        if not cover.strip():
            QMessageBox.warning(self, "Input Error", "No covertext provided")
            return
        if not secret:
            QMessageBox.warning(self, "Input Error", "No secret message provided")
            return

        try:
            stego, info = embed(cover, secret, key)
            self.result_output.setPlainText(stego)

            mode_str = "Huffman Compressed" if info['key_used'] else "Standard 8-bit ASCII"
            self.status_label.setText(
                f"<b>Embedding Successful!</b> ({mode_str})<br>"
                f"• <b>Partitions (n):</b> {info['n']} | <b>Partition size (m):</b> {info['m']} chars<br>"
                f"• <b>Bits/partition (Cp):</b> {info['Cp']} bits | <b>Total capacity (Cn):</b> {info['Cn']} bits (Secret: {info['Lb']} bits)<br>"
            )
        except Exception as e:
            QMessageBox.critical(self, "Embedding Error", str(e))

    def handle_extract(self):
        key = self.key_input.text().strip() or None
        text_to_extract = self.covertext_input.toPlainText()

        if not text_to_extract.strip():
            QMessageBox.warning(self, "Input Error", "No stegotext provided")
            return

        try:
            secret = extract(text_to_extract, key)
            self.result_output.setPlainText(secret)
            self.status_label.setText(
                f"<b>Extraction Successful!</b><br>"
                f"Extracted secret message length: {len(secret)} characters."
            )
        except Exception as e:
            QMessageBox.critical(self, "Extraction Error", str(e))

