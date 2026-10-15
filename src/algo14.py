import os
from Crypto.Hash import HMAC,SHA3_224,SHA3_256




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
    """
    Algorithm 1: Watermark Embedding[cite: 6]
    Osadza ciąg bitów (np. 64-bitowy hash) w tekście za pomocą znaków konfuzyjnych.
    """
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
    """
    Algorithm 2: Watermark Extraction[cite: 7]
    Wydobywa ukryte bity z oznaczonego tekstu w sposób "ślepy" (bez udziału tekstu oryginalnego)[cite: 6, 7].
    """
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



if __name__=="__main__":
    key = b'Sixteen byte key'
    message = b'Wiadomosc do podpisania'
    long_text = """Tonight I would like to talk about Dolly Parton and her famous song like 9-5.
    It is very important to remember her songs bc she is one of the biggest POP stars whom were famous from making Country music.
    What else coule we talk about? I think XORs,XOR is very interesing operation on bytes/bits that allows us using stream ciphers on Counter/Galois-Counter Modes of operation in block ciphers.
    Moreover interesing mode is AES-XTS which uses xex(XOR-Encrypt-XOR) which is kinda interesting bc it manipulates bits in that way that some simple bit-flipping is harder to perform."""

    hamak = HMAC.new(key, digestmod=SHA3_256)
    hamak.update(message)

    mac_bytes = hamak.digest()
    payload_size_bits = len(mac_bytes) * 8
    hex_chars_len = len(mac_bytes) * 2

    print(f"0x{mac_bytes.hex()}")

    watermark_bits = "".join(f"{b:08b}" for b in mac_bytes)

    text_with_watermark = embed_watermark(long_text, watermark_bits)
    print(text_with_watermark)

    watermark_new = extract_watermark(text_with_watermark, payload_size=payload_size_bits)
    watermark_bits_new = f"0x{int(watermark_new, 2):0{hex_chars_len}x}"
    print(watermark_bits_new)