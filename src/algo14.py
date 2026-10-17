from PyQt5.QtWidgets import QMessageBox
from templates import TabTemplate
from Crypto.Hash import HMAC, SHA3_256

# ======================= LOGIKA ALGORYTMU =======================

CONFUSABLE_CHARS = {
    '-': ['-', '\u2010'],
    ';': [';', '\u037e'],
    'C': ['C', '\u216d'],
    'D': ['D', '\u216e'],
    'K': ['K', '\u212a'],
    'L': ['L', '\u216c'],
    'M': ['M', '\u216f'],
    'V': ['V', '\u2164'],
    'X': ['X', '\u2169'],
    'c': ['c', '\u217d'],
    'd': ['d', '\u217e'],
    'i': ['i', '\u2170'],
    'j': ['j', '\u0458'],
    'l': ['l', '\u217c'],
    'v': ['v', '\u2174'],
    'x': ['x', '\u2179']
}

CONFUSABLE_SPACES = [
    '\u0020',  # 000: Space
    '\u2000',  # 001: En Quad
    '\u2004',  # 010: Three-per-em Space
    '\u2005',  # 011: Four-per-em Space
    '\u2008',  # 100: Punctuation Space
    '\u2009',  # 101: Thin Space
    '\u202f',  # 110: Narrow No-break Space
    '\u205f'   # 111: Medium Mathematical Space
]

ORIGINALS = {val[0] for val in CONFUSABLE_CHARS.values()}
DUPLICATES = {val[1] for val in CONFUSABLE_CHARS.values()}
CHAR_TO_DUP = {val[0]: val[1] for val in CONFUSABLE_CHARS.values()}

SPACES = set(CONFUSABLE_SPACES)
SPACE_TO_BITS = {space_char: f"{idx:03b}" for idx, space_char in enumerate(CONFUSABLE_SPACES)}


def embed_watermark(text: str, watermark_bits: str) -> str:
    watermarked_text = []
    w_idx = 0
    w_len = len(watermark_bits)
    
    for c in text:
        if w_idx < w_len and (c in ORIGINALS or c in SPACES):
            if c in SPACES:
                bits = watermark_bits[w_idx:w_idx+3]
                w_idx += 3
                
                if len(bits) < 3:
                    bits = bits.ljust(3, '0')
                
                space_idx = int(bits, 2)
                watermarked_text.append(CONFUSABLE_SPACES[space_idx])
                
            elif c in ORIGINALS:
                bit = watermark_bits[w_idx]
                w_idx += 1
                
                if bit == '1':
                    watermarked_text.append(CHAR_TO_DUP[c])
                else:
                    watermarked_text.append(c)
        else:
            watermarked_text.append(c)
            
    return "".join(watermarked_text)


def extract_watermark(watermarked_text: str, payload_size: int = 64) -> str:
    extracted_bits = []
    
    for c in watermarked_text:
        if c in SPACES:
            extracted_bits.append(SPACE_TO_BITS[c])
        elif c in ORIGINALS:
            extracted_bits.append('0')
        elif c in DUPLICATES:
            extracted_bits.append('1')
            
        current_length = sum(len(b) for b in extracted_bits)
        if current_length >= payload_size:
            break
    
    result_string = "".join(extracted_bits)
    return result_string[:payload_size]


# ======================= KLASA ZAKŁADKI GUI =======================

class Algo14Tab(TabTemplate):
    def __init__(self):
        super().__init__()
        
        # 1. Użycie nowej funkcji customize_ui do zmiany tekstów dla tego algorytmu!
        help_text = (
            "HMAC Watermarking Algorithm\n\n"
            "EMBEDDING:\n"
            "1. Enter the base text in 'Cover Text'.\n"
            "2. Enter the message you want to sign in 'Message to Sign'.\n"
            "3. Enter your secret key.\n"
            "4. Click 'Embed Watermark'. The generated HMAC will be hidden in the text.\n\n"
            "EXTRACTION:\n"
            "1. Paste the watermarked text into the 'Cover Text' field.\n"
            "2. Click 'Extract Watermark' to retrieve the HMAC hex string."
        )

        self.customize_ui(
            cover_lbl="Cover Text",
            secret_lbl="Message to Sign",
            key_lbl="HMAC Key",
            embed_btn="Embed Watermark",
            extract_btn="Extract Watermark",
            output_grp="Watermark Output",
            tab_help_text=help_text
        )

        # 2. Podpięcie przycisków pod metody
        self.embed_button.clicked.connect(self.do_embed)
        self.extract_button.clicked.connect(self.do_extract)

    def do_embed(self):
        text = self.covertext_input.toPlainText()
        msg = self.secret_input.toPlainText().encode('utf-8')
        key = self.key_input.text().encode('utf-8')

        if not text or not msg or not key:
            QMessageBox.warning(self, "Error", "All fields (Text, Message, and Key) must be filled!")
            return

        try:
            # Generowanie HMAC SHA3_256
            hamak = HMAC.new(key, digestmod=SHA3_256)
            hamak.update(msg)
            mac_bytes = hamak.digest()
            
            # Zamiana na bity
            watermark_bits = "".join(f"{b:08b}" for b in mac_bytes)
            
            # Osadzanie
            text_with_watermark = embed_watermark(text, watermark_bits)
            
            # Informacja dla użytkownika w logu (opcjonalnie)
            original_hex = f"0x{mac_bytes.hex()}"
            result_display = f"--- Original HMAC (Hex) ---\n{original_hex}\n\n--- Watermarked Text ---\n{text_with_watermark}"
            
            self.result_output.setPlainText(result_display)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def do_extract(self):
        # Do ekstrakcji bierzemy tekst z pola covertext (zakładamy, że user tam wkleił oznaczony tekst)
        watermarked_text = self.covertext_input.toPlainText()
        
        if not watermarked_text:
            QMessageBox.warning(self, "Error", "Please paste the watermarked text into the 'Cover Text' field.")
            return

        try:
            # HMAC SHA3_256 daje zawsze 32 bajty = 256 bitów.
            payload_size_bits = 256 
            hex_chars_len = payload_size_bits // 4
            
            watermark_new_bits = extract_watermark(watermarked_text, payload_size=payload_size_bits)
            
            if len(watermark_new_bits) < payload_size_bits:
                QMessageBox.warning(self, "Warning", "Could not extract full 256 bits. The text might be too short or not watermarked properly.")

            # Jeśli udało się wyciągnąć jakiekolwiek bity
            if watermark_new_bits:
                watermark_hex = f"0x{int(watermark_new_bits, 2):0{hex_chars_len}x}"
            else:
                watermark_hex = "No watermark detected."
                
            result_display = f"--- Extracted Watermark (HMAC Hex) ---\n{watermark_hex}"
            self.result_output.setPlainText(result_display)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred during extraction: {str(e)}")