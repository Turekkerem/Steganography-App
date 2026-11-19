import math
import re
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import PBKDF2
import nltk
from nltk.corpus import wordnet as wn
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from templates import TabTemplate

try:
    from dahuffman import HuffmanCodec
except ImportError as exc:
    raise ImportError("Please install dahuffman==0.4.2: pip install dahuffman==0.4.2") from exc


ENGLISH_CHAR_FREQS = {
    " ": 1800,
    "e": 1116,
    "t": 850,
    "a": 780,
    "o": 716,
    "i": 667,
    "n": 658,
    "s": 611,
    "h": 549,
    "r": 546,
    "d": 382,
    "l": 369,
    "u": 264,
    "c": 244,
    "m": 231,
    "f": 213,
    "w": 197,
    "y": 189,
    "p": 175,
    "g": 168,
    "b": 139,
    "v": 100,
    "k": 69,
    "x": 17,
    "j": 14,
    "q": 11,
    "z": 9,
    "E": 120,
    "T": 110,
    "A": 105,
    "I": 95,
    "S": 90,
    "O": 85,
    "H": 80,
    "W": 75,
    "M": 70,
    "C": 70,
    "B": 65,
    "P": 65,
    "F": 60,
    "D": 60,
    "N": 55,
    "R": 55,
    "L": 50,
    "G": 45,
    "U": 40,
    "Y": 35,
    "K": 25,
    "V": 20,
    "J": 15,
    "Q": 10,
    "X": 10,
    "Z": 10,
    ".": 140,
    ",": 120,
    "'": 50,
    '"': 40,
    "-": 35,
    "!": 25,
    "?": 25,
    ":": 20,
    ";": 20,
    "\n": 40,
    "0": 15,
    "1": 20,
    "2": 15,
    "3": 12,
    "4": 12,
    "5": 12,
    "6": 10,
    "7": 10,
    "8": 10,
    "9": 10,
    "\x00": 80,
}

KDF_SALT = b"stego_synonym_aes_ctr_kdf_v1"
KDF_ITERATIONS = 100_000
INITIAL_COUNTER_IV = 1


def _ensure_wordnet():
    try:
        wn.synsets("fast")
    except LookupError:
        nltk.download("wordnet", quiet=True)
        nltk.download("omw-1.4", quiet=True)


def _build_english_huffman_codec() -> HuffmanCodec:
    freqs = dict(ENGLISH_CHAR_FREQS)
    for code_point in range(0x20, 0x7F):
        ch = chr(code_point)
        if ch not in freqs:
            freqs[ch] = 1
    for code_point in range(0xA0, 0x100):
        ch = chr(code_point)
        if ch not in freqs:
            freqs[ch] = 1
    return HuffmanCodec.from_frequencies(freqs)


def _derive_aes_key(password: str) -> bytes:
    return PBKDF2(
        password.encode("utf-8"),
        KDF_SALT,
        dkLen=32,
        count=KDF_ITERATIONS,
        hmac_hash_module=SHA256,
    )


def _aes_ctr_encrypt(data: bytes, password: str) -> bytes:
    key = _derive_aes_key(password)
    cipher = AES.new(key, AES.MODE_CTR, initial_value=INITIAL_COUNTER_IV, nonce=b"")
    return cipher.encrypt(data)


def _aes_ctr_decrypt(ciphertext: bytes, password: str) -> bytes:
    key = _derive_aes_key(password)
    cipher = AES.new(key, AES.MODE_CTR, initial_value=INITIAL_COUNTER_IV, nonce=b"")
    return cipher.decrypt(ciphertext)


class SynonymStegoTab(TabTemplate):
    FILTER_KEYWORDS = {
        "obsolete": ("obsolete", "archaic", "dated"),
        "slang": ("slang", "colloquial", "informal", "vulgar"),
        "element": ("chemical element", "atomic number", "radioactive", "isotope", "symbol"),
        "abbreviation": ("abbreviation", "acronym", "initialism"),
        "medical": ("disease", "disorder", "syndrome", "anatomy", "pathology", "inflammation"),
        "legal": ("law", "legal", "statute", "jurisprudence", "offense", "offence"),
        "military": ("military", "weapon", "artillery", "warfare", "army", "naval"),
        "derogatory": ("derogatory", "offensive", "disparaging", "pejorative"),
    }

    def __init__(self):
        super().__init__()
        _ensure_wordnet()
        self.huffman_codec = _build_english_huffman_codec()

        self.customize_ui(
            key_lbl="Key (password -> KDF -> AES-CTR)",
            tab_help_text=(
                "WordNet Synonym Order Steganography:\n"
                "1. Enter English Cover Text (longer text = higher capacity).\n"
                "2. Enter Secret Message.\n"
                "3. Click 'Lexical Group Filters' to expand and customize WordNet domain/POS filters.\n"
                "4. Optionally toggle 'Use Huffman Coding (dahuffman)' and enter a password in 'Key' "
                "for PBKDF2 + AES-CTR (fixed IV=1 per block, no IV overhead).\n"
                "5. Click 'Embed Secret Message' or paste stego text into 'Cover Text' "
                "and click 'Extract Secret Message' using the exact same filters, Huffman toggle, and password."
            ),
        )
        self.key_input.setPlaceholderText("Enter password for KDF + AES-CTR (optional)")

        # === Rozsuwany panel filtrów ===
        self.toggle_filters_btn = QPushButton("▶ Lexical Group Filters (WordNet) [Expand]")
        self.toggle_filters_btn.setCheckable(True)
        self.toggle_filters_btn.setChecked(False)
        self.toggle_filters_btn.setStyleSheet("text-align: left; font-weight: bold; padding: 6px;")

        self.filter_panel = QFrame()
        self.filter_panel.setFrameShape(QFrame.StyledPanel)
        self.filter_panel.setVisible(False)

        filter_main_layout = QVBoxLayout(self.filter_panel)
        filter_grid = QGridLayout()

        # Filtry domenowe / rejestru
        self.filter_obsolete_cb = QCheckBox("Filter obsolete / archaic")
        self.filter_obsolete_cb.setChecked(True)

        self.filter_slang_cb = QCheckBox("Filter slang / colloquial")
        self.filter_slang_cb.setChecked(True)

        self.filter_element_cb = QCheckBox("Filter chemical element / symbol")
        self.filter_element_cb.setChecked(True)

        self.filter_abbrev_cb = QCheckBox("Filter abbreviation / acronym")
        self.filter_abbrev_cb.setChecked(True)

        self.filter_taxon_cb = QCheckBox("Filter genus / species nouns")
        self.filter_taxon_cb.setChecked(True)

        self.filter_medical_cb = QCheckBox("Filter medical / anatomy")
        self.filter_medical_cb.setChecked(True)

        self.filter_legal_cb = QCheckBox("Filter legal / law terms")
        self.filter_legal_cb.setChecked(False)

        self.filter_military_cb = QCheckBox("Filter military / weapons")
        self.filter_military_cb.setChecked(False)

        self.filter_derogatory_cb = QCheckBox("Filter derogatory / offensive")
        self.filter_derogatory_cb.setChecked(True)

        filter_grid.addWidget(self.filter_obsolete_cb, 0, 0)
        filter_grid.addWidget(self.filter_slang_cb, 0, 1)
        filter_grid.addWidget(self.filter_element_cb, 1, 0)
        filter_grid.addWidget(self.filter_abbrev_cb, 1, 1)
        filter_grid.addWidget(self.filter_taxon_cb, 2, 0)
        filter_grid.addWidget(self.filter_medical_cb, 2, 1)
        filter_grid.addWidget(self.filter_legal_cb, 3, 0)
        filter_grid.addWidget(self.filter_military_cb, 3, 1)
        filter_grid.addWidget(self.filter_derogatory_cb, 4, 0, 1, 2)

        filter_main_layout.addLayout(filter_grid)

        # Filtry części mowy (POS) + minimalna długość słowa
        pos_row = QHBoxLayout()
        pos_row.addWidget(QLabel("<b>Allowed POS:</b>"))

        self.pos_adj_cb = QCheckBox("Adjectives")
        self.pos_adj_cb.setChecked(True)

        self.pos_verb_cb = QCheckBox("Verbs")
        self.pos_verb_cb.setChecked(True)

        self.pos_noun_cb = QCheckBox("Nouns")
        self.pos_noun_cb.setChecked(True)

        self.pos_adv_cb = QCheckBox("Adverbs")
        self.pos_adv_cb.setChecked(False)

        pos_row.addWidget(self.pos_adj_cb)
        pos_row.addWidget(self.pos_verb_cb)
        pos_row.addWidget(self.pos_noun_cb)
        pos_row.addWidget(self.pos_adv_cb)
        pos_row.addStretch()

        pos_row.addWidget(QLabel("<b>Min word len:</b>"))
        self.min_len_combo = QComboBox()
        self.min_len_combo.addItems(["3", "4", "5"])
        self.min_len_combo.setCurrentText("3")
        pos_row.addWidget(self.min_len_combo)

        filter_main_layout.addLayout(pos_row)

        # Wpinamy przycisk i rozsuwany panel w lewej kolumnie przed sekcją Actions
        left_layout = self.input_group.parentWidget().layout()
        if left_layout is not None:
            idx = left_layout.indexOf(self.action_group)
            if idx >= 0:
                left_layout.insertWidget(idx, self.toggle_filters_btn)
                left_layout.insertWidget(idx + 1, self.filter_panel)
            else:
                left_layout.addWidget(self.toggle_filters_btn)
                left_layout.addWidget(self.filter_panel)

        # Przełącznik kodowania Huffmana
        self.use_huffman_cb = QCheckBox("Use Huffman Coding (English / dahuffman)")
        self.use_huffman_cb.setChecked(True)
        self.use_huffman_cb.setToolTip(
            "Encode English characters with HuffmanCodec (dahuffman==0.4.2) before bit embedding"
        )

        old_action_layout = self.action_group.layout()
        if old_action_layout is not None:
            old_action_layout.removeWidget(self.embed_button)
            old_action_layout.removeWidget(self.extract_button)
            QWidget().setLayout(old_action_layout)

        new_action_layout = QVBoxLayout()
        new_action_layout.addWidget(self.use_huffman_cb)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.embed_button)
        btn_row.addWidget(self.extract_button)
        new_action_layout.addLayout(btn_row)
        self.action_group.setLayout(new_action_layout)

        # Stały rozmiar okna Result Output, aby długi wynik nie zgniatał reszty interfejsu
        self.result_output.setFixedHeight(360)
        self.result_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.output_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        splitter = self.findChild(QSplitter)
        if splitter is not None:
            splitter.setCollapsible(0, False)
            splitter.setCollapsible(1, False)

        # Pasek statystyk + przyciski Copy / Save na dole sekcji Result Output
        output_layout = self.output_group.layout()
        self.stats_label = QLabel("Container stats: —")
        self.stats_label.setStyleSheet("font-size: 11pt; color: #555555;")
        self.stats_label.setWordWrap(True)

        output_btn_row = QHBoxLayout()
        self.btn_copy_result = QPushButton("Copy Result")
        self.btn_save_result = QPushButton("Save Result to TXT")
        output_btn_row.addWidget(self.btn_copy_result)
        output_btn_row.addWidget(self.btn_save_result)

        output_layout.addWidget(self.stats_label)
        output_layout.addLayout(output_btn_row)

        # Pierwsze zbudowanie grup synonimów
        self.raw_groups = self._extract_wordnet_groups()

        # Połączenia sygnałów
        self.toggle_filters_btn.toggled.connect(self.on_toggle_filters_panel)

        for cb in (
            self.filter_obsolete_cb,
            self.filter_slang_cb,
            self.filter_element_cb,
            self.filter_abbrev_cb,
            self.filter_taxon_cb,
            self.filter_medical_cb,
            self.filter_legal_cb,
            self.filter_military_cb,
            self.filter_derogatory_cb,
            self.pos_adj_cb,
            self.pos_verb_cb,
            self.pos_noun_cb,
            self.pos_adv_cb,
        ):
            cb.stateChanged.connect(self.on_filters_changed)

        self.min_len_combo.currentTextChanged.connect(self.on_filters_changed)

        self.embed_button.clicked.connect(self.handle_embed)
        self.extract_button.clicked.connect(self.handle_extract)
        self.btn_copy_result.clicked.connect(self.copy_result_to_clipboard)
        self.btn_save_result.clicked.connect(self.save_result_to_file)

    def on_toggle_filters_panel(self, checked: bool):
        self.filter_panel.setVisible(checked)
        if checked:
            self.toggle_filters_btn.setText("▼ Lexical Group Filters (WordNet) [Collapse]")
        else:
            self.toggle_filters_btn.setText("▶ Lexical Group Filters (WordNet) [Expand]")

    def _active_blocked_keywords(self) -> tuple[str, ...]:
        blocked = []
        mapping = (
            (self.filter_obsolete_cb, "obsolete"),
            (self.filter_slang_cb, "slang"),
            (self.filter_element_cb, "element"),
            (self.filter_abbrev_cb, "abbreviation"),
            (self.filter_medical_cb, "medical"),
            (self.filter_legal_cb, "legal"),
            (self.filter_military_cb, "military"),
            (self.filter_derogatory_cb, "derogatory"),
        )
        for checkbox, key in mapping:
            if checkbox.isChecked():
                blocked.extend(self.FILTER_KEYWORDS[key])
        return tuple(blocked)

    def _active_pos_set(self) -> set:
        pos_set = set()
        if self.pos_adj_cb.isChecked():
            pos_set.add(wn.ADJ)
        if self.pos_verb_cb.isChecked():
            pos_set.add(wn.VERB)
        if self.pos_noun_cb.isChecked():
            pos_set.add(wn.NOUN)
        if self.pos_adv_cb.isChecked():
            pos_set.add(wn.ADV)
        return pos_set

    def _extract_wordnet_groups(self):
        groups = []
        allowed_pos = self._active_pos_set()
        if not allowed_pos:
            return groups

        blocked_keywords = self._active_blocked_keywords()
        filter_taxon = self.filter_taxon_cb.isChecked()
        min_len = int(self.min_len_combo.currentText())

        for synset in wn.all_synsets():
            if synset.pos() not in allowed_pos:
                continue

            definition = synset.definition().lower()
            if blocked_keywords and any(bad in definition for bad in blocked_keywords):
                continue

            if filter_taxon and synset.pos() == wn.NOUN and (
                "genus" in definition or "species" in definition
            ):
                continue

            lemmas = [
                lemma.name().lower()
                for lemma in synset.lemmas()
                if lemma.name().isalpha()
                and "_" not in lemma.name()
                and len(lemma.name()) >= min_len
            ]
            unique_lemmas = sorted(set(lemmas))
            if len(unique_lemmas) >= 2:
                groups.append(unique_lemmas)

        return groups

    def on_filters_changed(self):
        QApplication.setOverrideCursor(self.cursor())
        try:
            self.raw_groups = self._extract_wordnet_groups()
        finally:
            QApplication.restoreOverrideCursor()

    def _build_word_to_group(self):
        min_len = int(self.min_len_combo.currentText())
        word_to_group = {}
        for group in self.raw_groups:
            cleaned = sorted({w.strip().lower() for w in group if w.isalpha() and len(w) >= min_len})
            if len(cleaned) < 2:
                continue

            power_of_two = 2 ** int(math.log2(len(cleaned)))
            valid_group = cleaned[:power_of_two]

            if not any(w in word_to_group for w in valid_group):
                for w in valid_group:
                    word_to_group[w] = valid_group

        return word_to_group

    def _max_embeddable_bits(self, text: str, word_to_group: dict) -> int:
        capacity = 0
        for token in re.split(r"(\W+)", text):
            lower_tok = token.lower()
            if lower_tok in word_to_group:
                capacity += int(math.log2(len(word_to_group[lower_tok])))
        return capacity

    def _encode_message_to_bytes(self, message: str, use_huffman: bool) -> bytes:
        if use_huffman:
            symbols = list(message) + ["\x00"]
            return self.huffman_codec.encode(symbols)
        return message.encode("utf-8") + b"\x00"

    def _decode_bytes_to_message(self, raw_bytes: bytes, use_huffman: bool) -> tuple[str, bool]:
        if use_huffman:
            try:
                symbols = self.huffman_codec.decode(raw_bytes)
            except Exception:
                return "[Huffman decode error: wrong password/key or truncated text]", False

            out_chars = []
            found_eof = False
            for sym in symbols:
                if sym == "\x00":
                    found_eof = True
                    break
                out_chars.append(str(sym))
            return "".join(out_chars), found_eof

        if b"\x00" in raw_bytes:
            before_null = raw_bytes.split(b"\x00", 1)[0]
            return before_null.decode("utf-8", errors="replace"), True
        return raw_bytes.decode("utf-8", errors="replace"), False

    def _prepare_bitstream(self, message: str, use_huffman: bool, password: str) -> tuple[str, int]:
        payload = self._encode_message_to_bytes(message, use_huffman)
        if password:
            payload = _aes_ctr_encrypt(payload, password)

        framed = len(payload).to_bytes(2, "big") + payload
        bits = "".join(f"{byte:08b}" for byte in framed)
        return bits, len(payload)

    def _recover_message_from_bits(self, bits: str, use_huffman: bool, password: str) -> tuple[str, bool]:
        total_bytes = len(bits) // 8
        if total_bytes < 2:
            return "", False

        all_bytes = bytes(int(bits[i : i + 8], 2) for i in range(0, total_bytes * 8, 8))
        expected_len = int.from_bytes(all_bytes[:2], "big")
        available = all_bytes[2:]

        is_complete = len(available) >= expected_len
        payload = available[:expected_len] if is_complete else available

        if password:
            try:
                payload = _aes_ctr_decrypt(payload, password)
            except Exception as exc:
                return f"[AES-CTR decryption error: {exc}]", False

        msg, decoded_eof = self._decode_bytes_to_message(payload, use_huffman)
        return msg, (is_complete and decoded_eof)

    @staticmethod
    def _match_case(word: str, template: str) -> str:
        if template.isupper():
            return word.upper()
        if template.istitle():
            return word.capitalize()
        return word

    def handle_embed(self):
        cover_text = self.covertext_input.toPlainText()
        secret_message = self.secret_input.toPlainText()
        password = self.key_input.text()
        use_huffman = self.use_huffman_cb.isChecked()

        if not cover_text.strip():
            QMessageBox.warning(self, "Missing Input", "Please enter a cover text.")
            return
        if not secret_message:
            QMessageBox.warning(self, "Missing Input", "Please enter a secret message.")
            return

        word_to_group = self._build_word_to_group()
        max_slot_bits = self._max_embeddable_bits(cover_text, word_to_group)

        bits, payload_bytes_len = self._prepare_bitstream(secret_message, use_huffman, password)
        total_bits = len(bits)
        bit_idx = 0

        tokens = re.split(r"(\W+)", cover_text)
        out_tokens = []
        used_slots = 0

        for token in tokens:
            lower_tok = token.lower()
            if bit_idx < total_bits and lower_tok in word_to_group:
                group = word_to_group[lower_tok]
                bits_per_slot = int(math.log2(len(group)))
                chunk = bits[bit_idx : bit_idx + bits_per_slot].ljust(bits_per_slot, "0")
                syn_idx = int(chunk, 2)
                chosen = self._match_case(group[syn_idx], token)
                out_tokens.append(chosen)
                bit_idx += bits_per_slot
                used_slots += 1
            else:
                out_tokens.append(token)

        stego_text = "".join(out_tokens)
        self.result_output.setPlainText(stego_text)

        cover_bits = len(cover_text.encode("utf-8")) * 8
        embedded_bits = min(bit_idx, total_bits)

        max_capacity_pct = (max_slot_bits / cover_bits * 100.0) if cover_bits > 0 else 0.0
        used_capacity_pct = (embedded_bits / cover_bits * 100.0) if cover_bits > 0 else 0.0
        slot_utilization_pct = (embedded_bits / max_slot_bits * 100.0) if max_slot_bits > 0 else 0.0

        huff_label = "Huffman" if use_huffman else "raw"
        aes_label = f"AES-CTR(IV={INITIAL_COUNTER_IV})" if password else "AES:off"
        warning_suffix = ""
        if bit_idx < total_bits:
            warning_suffix = " | WARNING: Cover text too short (message truncated)"

        self.stats_label.setText(
            f"Max Capacity: {max_capacity_pct:.2f}% ({max_slot_bits}/{cover_bits}b) | "
            f"Used Capacity: {used_capacity_pct:.2f}% ({embedded_bits}/{cover_bits}b, "
            f"{slot_utilization_pct:.1f}% of slots) | "
            f"Mode: {huff_label} + {aes_label} ({payload_bytes_len}B){warning_suffix}"
        )

    def handle_extract(self):
        stego_text = self.covertext_input.toPlainText()
        password = self.key_input.text()
        use_huffman = self.use_huffman_cb.isChecked()

        if not stego_text.strip():
            QMessageBox.warning(
                self,
                "Missing Input",
                "Paste the stego text into the 'Cover Text' field to extract the message.",
            )
            return

        word_to_group = self._build_word_to_group()
        max_slot_bits = self._max_embeddable_bits(stego_text, word_to_group)

        tokens = re.split(r"(\W+)", stego_text)
        extracted_bits = []
        matched_slots = 0

        for token in tokens:
            lower_tok = token.lower()
            if lower_tok in word_to_group:
                group = word_to_group[lower_tok]
                bits_per_slot = int(math.log2(len(group)))
                syn_idx = group.index(lower_tok)
                extracted_bits.append(f"{syn_idx:0{bits_per_slot}b}")
                matched_slots += 1

        raw_extracted_bits = "".join(extracted_bits)
        decoded_message, is_complete = self._recover_message_from_bits(
            raw_extracted_bits, use_huffman, password
        )
        self.result_output.setPlainText(decoded_message)

        stego_bits = len(stego_text.encode("utf-8")) * 8
        max_capacity_pct = (max_slot_bits / stego_bits * 100.0) if stego_bits > 0 else 0.0

        # Liczba bajtów odczytanych z nagłówka ramki
        total_bytes = len(raw_extracted_bits) // 8
        used_bits = 0
        if total_bytes >= 2:
            all_bytes = bytes(int(raw_extracted_bits[i : i + 8], 2) for i in range(0, total_bytes * 8, 8))
            expected_len = int.from_bytes(all_bytes[:2], "big")
            used_bits = min((2 + expected_len) * 8, len(raw_extracted_bits))
        used_capacity_pct = (used_bits / stego_bits * 100.0) if stego_bits > 0 else 0.0

        huff_label = "Huffman" if use_huffman else "raw"
        aes_label = f"AES-CTR(IV={INITIAL_COUNTER_IV})" if password else "AES:off"
        status_suffix = "" if is_complete else " | WARNING: Incomplete message or wrong filters/password"

        self.stats_label.setText(
            f"Max Capacity: {max_capacity_pct:.2f}% ({max_slot_bits}/{stego_bits}b) | "
            f"Used Capacity: {used_capacity_pct:.2f}% ({used_bits}/{stego_bits}b) | "
            f"Mode: {huff_label} + {aes_label} | Slots: {matched_slots}{status_suffix}"
        )

    def copy_result_to_clipboard(self):
        text = self.result_output.toPlainText()
        if not text:
            QMessageBox.warning(self, "Warning", "Nothing to copy.")
            return
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Copied", "Result copied to clipboard.")

    def save_result_to_file(self):
        text = self.result_output.toPlainText()
        if not text:
            QMessageBox.warning(self, "Warning", "Nothing to save.")
            return
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Result", "steganogram.txt", "Text Files (*.txt)", options=options
        )
        if file_name:
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(text)
            QMessageBox.information(self, "Saved", "Result saved to file.")