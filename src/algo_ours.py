import hashlib
import math
import random
import re
import nltk
from nltk.corpus import wordnet as wn
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
)
from templates import TabTemplate


def _ensure_wordnet():
    try:
        wn.synsets("fast")
    except LookupError:
        nltk.download("wordnet", quiet=True)
        nltk.download("omw-1.4", quiet=True)


class SynonymStegoTab(TabTemplate):
    def __init__(self):
        super().__init__()
        _ensure_wordnet()
        self.raw_groups = self._extract_wordnet_groups()

        self.customize_ui(
            key_lbl="Key (seed)",
            tab_help_text=(
                "WordNet Synonym Order Steganography:\n"
                "1. Enter English Cover Text (longer text = higher capacity).\n"
                "2. Enter Secret Message.\n"
                "3. Optionally enter a Key to deterministically shuffle synonym bit-order.\n"
                "4. Click 'Embed Secret Message' to generate stego text.\n"
                "5. To extract, paste the stego text into 'Cover Text' and click 'Extract Secret Message'."
            ),
        )
        self.key_input.setPlaceholderText("Enter optional key for synonym ordering")

        # Pasek statystyk + przyciski Copy / Save na dole sekcji Result Output
        output_layout = self.output_group.layout()
        self.stats_label = QLabel("Container stats: —")
        self.stats_label.setStyleSheet("font-size: 11pt; color: #555555;")

        output_btn_row = QHBoxLayout()
        self.btn_copy_result = QPushButton("Copy Result")
        self.btn_save_result = QPushButton("Save Result to TXT")
        output_btn_row.addWidget(self.btn_copy_result)
        output_btn_row.addWidget(self.btn_save_result)

        output_layout.addWidget(self.stats_label)
        output_layout.addLayout(output_btn_row)

        self.embed_button.clicked.connect(self.handle_embed)
        self.extract_button.clicked.connect(self.handle_extract)
        self.btn_copy_result.clicked.connect(self.copy_result_to_clipboard)
        self.btn_save_result.clicked.connect(self.save_result_to_file)

    BLOCKED_DEF_KEYWORDS = (
        "chemical element",
        "atomic number",
        "radioactive",
        "symbol",
        "abbreviation",
        "archaic",
        "obsolete",
        "slang",
    )

    @classmethod
    def _extract_wordnet_groups(cls):
        """
        Buduje czystsze grupy synonimów z WordNet:
        - tylko słowa >= 3 litery (bez skrótów typu 'no', 'ra'),
        - głównie przymiotniki i czasowniki (oraz proste rzeczowniki bez terminów chemicznych/skrótów),
        - odfiltrowuje synsety z definicjami typu symbol/pierwiastek/slang.
        """
        groups = []
        allowed_pos = {wn.ADJ, wn.VERB, wn.NOUN}

        for synset in wn.all_synsets():
            if synset.pos() not in allowed_pos:
                continue

            definition = synset.definition().lower()
            if any(bad in definition for bad in cls.BLOCKED_DEF_KEYWORDS):
                continue

            # Rzeczowniki często mają specyficzne nazwy własne/pierwiastki — bierzemy tylko te z prostą definicją
            if synset.pos() == wn.NOUN and ("genus" in definition or "species" in definition):
                continue

            lemmas = [
                lemma.name().lower()
                for lemma in synset.lemmas()
                if lemma.name().isalpha()
                and "_" not in lemma.name()
                and len(lemma.name()) >= 3
            ]
            unique_lemmas = sorted(set(lemmas))
            if len(unique_lemmas) >= 2:
                groups.append(unique_lemmas)

        return groups

    def _build_word_to_group(self, key: str):
        rng = None
        if key:
            seed = int(hashlib.sha256(key.encode("utf-8")).hexdigest(), 16)
            rng = random.Random(seed)

        word_to_group = {}
        for idx, group in enumerate(self.raw_groups):
            cleaned = sorted({w.strip().lower() for w in group if w.isalpha()})
            if len(cleaned) < 2:
                continue

            power_of_two = 2 ** int(math.log2(len(cleaned)))
            if rng is not None:
                group_rng = random.Random(f"{rng.random()}:{idx}")
                shuffled = cleaned[:]
                group_rng.shuffle(shuffled)
                valid_group = shuffled[:power_of_two]
            else:
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

    @staticmethod
    def _text_to_bits(text: str) -> str:
        payload = text.encode("utf-8") + b"\x00"
        return "".join(f"{byte:08b}" for byte in payload)

    @staticmethod
    def _bits_to_text(bits: str) -> tuple[str, bool]:
        byte_values = bytearray()
        found_terminator = False

        for i in range(0, len(bits) - 7, 8):
            val = int(bits[i : i + 8], 2)
            if val == 0:
                found_terminator = True
                break
            byte_values.append(val)

        decoded = byte_values.decode("utf-8", errors="replace")
        return decoded, found_terminator

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
        key = self.key_input.text().strip()

        if not cover_text.strip():
            QMessageBox.warning(self, "Missing Input", "Please enter a cover text.")
            return
        if not secret_message:
            QMessageBox.warning(self, "Missing Input", "Please enter a secret message.")
            return

        word_to_group = self._build_word_to_group(key)
        max_slot_bits = self._max_embeddable_bits(cover_text, word_to_group)

        bits = self._text_to_bits(secret_message)
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

        # Statystyki: capacity = bity sekretu / bity covertextu
        secret_bits = len(secret_message.encode("utf-8")) * 8
        cover_bits = len(cover_text.encode("utf-8")) * 8
        capacity_ratio = (secret_bits / cover_bits) if cover_bits > 0 else 0.0
        capacity_pct = capacity_ratio * 100.0

        embedded_bits = min(bit_idx, total_bits)
        warning_suffix = ""
        if bit_idx < total_bits:
            warning_suffix = " | WARNING: Cover text too short (message truncated)"

        self.stats_label.setText(
            f"Capacity: {secret_bits}/{cover_bits} bits ({capacity_pct:.2f}%) | "
            f"Embedded (with EOF): {embedded_bits}/{total_bits} bits (max slots: {max_slot_bits} bits) | "
            f"Slots used: {used_slots}{warning_suffix}"
        )

    def handle_extract(self):
        stego_text = self.covertext_input.toPlainText()
        key = self.key_input.text().strip()

        if not stego_text.strip():
            QMessageBox.warning(
                self,
                "Missing Input",
                "Paste the stego text into the 'Cover Text' field to extract the message.",
            )
            return

        word_to_group = self._build_word_to_group(key)
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

        decoded_message, found_terminator = self._bits_to_text("".join(extracted_bits))
        self.result_output.setPlainText(decoded_message)

        secret_bits = len(decoded_message.encode("utf-8")) * 8
        stego_bits = len(stego_text.encode("utf-8")) * 8
        capacity_pct = (secret_bits / stego_bits * 100.0) if stego_bits > 0 else 0.0

        status_suffix = "" if found_terminator else " | WARNING: End marker '\\0' not found (incomplete)"
        self.stats_label.setText(
            f"Capacity: {secret_bits}/{stego_bits} bits ({capacity_pct:.2f}%) | "
            f"Extracted from {matched_slots} slot(s){status_suffix}"
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