import markovify
import json
import random
import string
from fractions import Fraction
from markovify.chain import BEGIN, END
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt

# Make sure templates.py is in the same directory
from templates import TabTemplate


class MarkovStego:
    def __init__(self, text=None, state_size=1):
        self.state_size = state_size
        if text:
            self.text_model = markovify.Text(text, state_size=state_size)
            self.model = self.text_model.chain.model
        else:
            self.text_model = None
            self.model = {}

    def load_from_json(self, json_str):
        self.text_model = markovify.Text.from_json(json_str)
        self.state_size = self.text_model.state_size
        self.model = self.text_model.chain.model

    def to_json(self):
        if self.text_model:
            return self.text_model.to_json()
        return "{}"

    def get_sample_keys(self, limit=5):
        """Returns readable sample keys available in the current Markov model."""
        if not self.model:
            return []
        samples = []
        for state in self.model.keys():
            clean_words = [w for w in state if w != BEGIN]
            if clean_words:
                phrase = " ".join(clean_words)
                if phrase not in samples:
                    samples.append(phrase)
            if len(samples) >= limit:
                break
        return samples

    def resolve_key_state(self, stego_key, ignore_punct=True):
        """Resolves a user-provided key (1 or more words) into a valid state tuple in self.model."""
        if not stego_key or not stego_key.strip():
            return (BEGIN,) * self.state_size

        key_words = stego_key.strip().split()

        def match_word(w1, w2):
            if ignore_punct:
                # Ignorowanie interpunkcji i wielkości liter dla łatwego wyszukiwania klucza
                c1 = w1.translate(str.maketrans('', '', string.punctuation)).lower()
                c2 = w2.translate(str.maketrans('', '', string.punctuation)).lower()
                return c1 == c2
            return w1.lower() == w2.lower()

        def match_tuple(t1, t2):
            if len(t1) != len(t2): return False
            return all(match_word(w1, w2) for w1, w2 in zip(t1, t2))

        # 1. Dokładne dopasowanie długości[cite: 5, 11]
        if len(key_words) == self.state_size:
            for state in sorted(self.model.keys(), key=lambda x: str(x)):
                if match_tuple(state, tuple(key_words)):
                    return state

        # 2. Mniej słów niż rząd modelu[cite: 11]
        if len(key_words) < self.state_size:
            # Szukanie na początku zdania
            for state in sorted(self.model.keys(), key=lambda x: str(x)):
                if state[0] == BEGIN and match_tuple(state[self.state_size - len(key_words):], tuple(key_words)):
                    return state
            # Szukanie na końcu stanu
            for state in sorted(self.model.keys(), key=lambda x: str(x)):
                if match_tuple(state[-len(key_words):], tuple(key_words)):
                    return state

        # 3. Więcej słów -> bierzemy ogon o długości state_size[cite: 11]
        target_slice = tuple(key_words[-self.state_size:])
        for state in sorted(self.model.keys(), key=lambda x: str(x)):
            if match_tuple(state, target_slice):
                return state

        samples = self.get_sample_keys(limit=5)
        samples_str = ", ".join(f"'{s}'" for s in samples) if samples else "none"
        raise ValueError(
            f"Key '{stego_key}' was not found in the Order {self.state_size} Markov model.\n"
            f"Sample valid keys in this model: {samples_str}"
        )

    def encode(self, secret_message, L=3, stego_key="", ignore_punct=True):
        if not self.model:
            raise ValueError("Markov chain is not initialized!")

        msg_bytes = secret_message.encode('utf-8')
        prefix_bytes = f"{len(msg_bytes)}|".encode('utf-8')
        full_payload = prefix_bytes + msg_bytes

        binary = ''.join(f'{b:08b}' for b in full_payload)

        if len(binary) % L != 0:
            binary += '0' * (L - (len(binary) % L))
        blocks = [int(binary[i:i+L], 2) for i in range(0, len(binary), L)]

        state = self.resolve_key_state(stego_key, ignore_punct)
        generated_tokens = []

        # Phase 1: Kodowanie arytmetyczne[cite: 11]
        for m in blocks:
            low = Fraction(0)
            high = Fraction(2**L)
            target = Fraction(m) + Fraction(1, 2)

            iterations = 0
            while True:
                if low >= Fraction(m) and high <= Fraction(m + 1):
                    break

                iterations += 1
                if iterations > 1000:
                    raise ValueError("Markov model is stuck in an infinite loop. Please use a different input text.")

                if state not in self.model:
                    state = (BEGIN,) * self.state_size

                choices_dict = self.model.get(state, {END: 1})
                choices = sorted(choices_dict.items())
                total_weight = sum(w for _, w in choices)

                current_low = low
                length = high - low

                chosen_word = None
                for word, weight in choices:
                    prob = Fraction(weight, total_weight)
                    next_low = current_low + length * prob
                    if current_low <= target < next_low:
                        chosen_word = word
                        low = current_low
                        high = next_low
                        break
                    current_low = next_low

                if chosen_word is None:
                    chosen_word = choices[-1][0]

                generated_tokens.append(chosen_word)
                if chosen_word == END:
                    state = (BEGIN,) * self.state_size
                else:
                    state = tuple(list(state[1:]) + [chosen_word])

        random.seed(f"{stego_key}|{secret_message}")

        # Phase 2: Dokończenie zdania w celu kamuflażu[cite: 11]
        tail_word_count = 0
        while tail_word_count < 50:
            if state not in self.model:
                break
            choices_dict = self.model.get(state, {END: 1})
            if not choices_dict:
                break

            sorted_choices = sorted(choices_dict.items())
            words = [c[0] for c in sorted_choices]
            weights = [c[1] for c in sorted_choices]
            
            best_word = random.choices(words, weights=weights, k=1)[0]

            generated_tokens.append(best_word)
            if best_word == END:
                break

            state = tuple(list(state[1:]) + [best_word])
            tail_word_count += 1

        if tail_word_count >= 50 and generated_tokens[-1] != END:
            generated_tokens.append(END)

        random.seed()

        # Phase 3: Złożenie tekstu z bezbłędnym pozbyciem się "dziwnych kropek"[cite: 11]
        output_tokens = []
        for token in generated_tokens:
            if token == END:
                if output_tokens:
                    # Zamiast wstawiać samotną kropkę lub robić spację przed kropką,
                    # ZAWSZE dopisujemy ją do ostatniego wygenerowanego słowa na twardo.
                    output_tokens[-1] += "."
                else:
                    output_tokens.append(".")
            else:
                output_tokens.append(token)

        return " ".join(output_tokens)

    def decode(self, stego_text, L=3, stego_key="", ignore_punct=True):
        words_to_process = []
        for raw_word in stego_text.split():
            words_to_process.append(raw_word)

        state = self.resolve_key_state(stego_key, ignore_punct)

        binary_stream = ""
        extracted_bytes = bytearray()
        msg_byte_length = None
        prefix_size = 0

        low = Fraction(0)
        high = Fraction(2**L)

        word_idx = 0

        while word_idx < len(words_to_process):
            raw_word = words_to_process[word_idx]

            if state not in self.model:
                state = (BEGIN,) * self.state_size

            choices_dict = self.model.get(state, {END: 1})
            target_word = raw_word

            # Inteligentny dekoder: ściąga po jednej kropce z końca, by sprawdzić
            # czy ukryto tam znacznik END
            if raw_word == ".":
                target_word = END
            elif raw_word.endswith('.'):
                clean = raw_word[:-1]
                if raw_word not in choices_dict and clean in choices_dict:
                    target_word = clean
                    words_to_process.insert(word_idx + 1, END)

            choices = sorted(choices_dict.items())
            total_weight = sum(w for _, w in choices)

            current_low = low
            length = high - low

            found = False
            for w, weight in choices:
                prob = Fraction(weight, total_weight)
                next_low = current_low + length * prob
                if w == target_word:
                    low = current_low
                    high = next_low
                    found = True
                    break
                current_low = next_low

            if not found:
                raise ValueError(
                    f"Graph desynchronization. Incorrect key or wrong text.\n"
                    f"Looked for word: '{target_word}' for state: {state}\n"
                    f"Available words in this node are: {list(choices_dict.keys())[:5]}"
                )

            if target_word == END:
                state = (BEGIN,) * self.state_size
            else:
                state = tuple(list(state[1:]) + [target_word])

            word_idx += 1
            
            k = int(low)
            if high <= Fraction(k + 1):
                binary_stream += f'{k:0{L}b}'
                low = Fraction(0)
                high = Fraction(2**L)

                while len(binary_stream) >= 8:
                    extracted_bytes.append(int(binary_stream[:8], 2))
                    binary_stream = binary_stream[8:]

                    if msg_byte_length is None and b'|' in extracted_bytes:
                        parts = extracted_bytes.split(b'|', 1)
                        try:
                            msg_byte_length = int(parts[0].decode('ascii'))
                            prefix_size = len(parts[0]) + 1
                        except ValueError:
                            pass

                    if msg_byte_length is not None:
                        if len(extracted_bytes) >= prefix_size + msg_byte_length:
                            payload = extracted_bytes[prefix_size: prefix_size + msg_byte_length]
                            return payload.decode('utf-8', errors='replace')

        raise ValueError("End of steganogram reached before full message could be extracted (incomplete text or wrong key).")


class AlgoMarkovTab(TabTemplate):
    def __init__(self):
        super().__init__()

        self.result_output.setReadOnly(True)
        self.result_output.setPlaceholderText("Results will appear here...")

        self.customize_ui(
            cover_lbl="Markov Model Status",
            secret_lbl="Secret Msg (Hide) / Stegano Text (Decode)",
            key_lbl="Key (Starting Word(s) - Optional)",
            embed_btn="Generate Steganogram",
            extract_btn="Extract Data",
            tab_help_text=(
                "1. Select Markov Chain Order (1, 2, or 3).\n"
                "2. Load Markov chain from JSON or TXT file.\n"
                "3. (Optional) Enter 1 to N starting words as a Key (must exist in the model).\n"
                "4. TO HIDE: Enter secret message and click 'Generate Steganogram'.\n"
                "5. TO EXTRACT: Paste steganographic text, enter the SAME Key, and click 'Extract Data'."
            )
        )

        self.key_input.setEnabled(True)
        self.key_input.setPlaceholderText("e.g. 'The' (Order 1) or 'The capacity' (Order 2)")

        self.btn_gen_model = QPushButton("Generate from TXT")
        self.btn_use_model = QPushButton("Load from JSON")
        self.btn_save_model = QPushButton("Save to JSON")

        self.order_layout = QHBoxLayout()
        self.order_label = QLabel("Markov Order:")
        self.order_label.setStyleSheet("font-weight: bold;")
        
        self.order_combo = QComboBox()
        self.order_combo.addItems(["1", "2", "3"])
        self.order_combo.setToolTip("Order 1: High Capacity, Low Naturalness\nOrder 3: Low Capacity, High Naturalness")
        
        # Nowy CheckBox do ignorowania interpunkcji w słowach kluczowych
        self.ignore_punct_cb = QCheckBox("Ignore Punctuation in Key")
        self.ignore_punct_cb.setChecked(True)
        self.ignore_punct_cb.setToolTip("Matches 'John' with 'John:', '\"John', etc.")

        self.order_layout.addWidget(self.order_label)
        self.order_layout.addWidget(self.order_combo)
        self.order_layout.addWidget(self.ignore_punct_cb)

        old_layout = self.action_group.layout()
        if old_layout is not None:
            old_layout.removeWidget(self.embed_button)
            old_layout.removeWidget(self.extract_button)
            QWidget().setLayout(old_layout)

        new_action_layout = QVBoxLayout()

        row1 = QHBoxLayout()
        row1.addLayout(self.order_layout)
        row1.addWidget(self.btn_gen_model)
        row1.addWidget(self.btn_use_model)
        row1.addWidget(self.btn_save_model)

        row2 = QHBoxLayout()
        row2.addWidget(self.embed_button)
        row2.addWidget(self.extract_button)

        new_action_layout.addLayout(row1)
        new_action_layout.addLayout(row2)

        self.action_group.setLayout(new_action_layout)

        self.btn_gen_model.clicked.connect(self.generate_model_from_file)
        self.btn_save_model.clicked.connect(self.save_model_to_json)
        self.btn_use_model.clicked.connect(self.use_model_from_file)

        default_text = (
            "Digital steganography uses various hiding techniques. "
            "The capacity of hidden messages depends on text complexity. "
            "Methods using Markov chains are characterized by preserving the linguistic model. "
            "Text generated by the chain sounds relatively natural. "
        ) * 10

        self.covertext_input.setReadOnly(True)

        self.stego = MarkovStego(text=default_text, state_size=1)
        self.order_combo.setCurrentText("1")
        self.update_status_display("Default test dictionary")

        try:
            self.embed_button.clicked.disconnect()
            self.extract_button.clicked.disconnect()
        except TypeError:
            pass
        self.embed_button.clicked.connect(self.do_embed)
        self.extract_button.clicked.connect(self.do_extract)

    def update_status_display(self, source_name):
        samples = self.stego.get_sample_keys(limit=5)
        samples_str = ", ".join(f'"{s}"' for s in samples)
        self.covertext_input.setPlainText(
            f"<< Active Model: Order {self.stego.state_size} | States: {len(self.stego.model)} >>\n"
            f"Source: {source_name}\n"
            f"Sample valid keys: {samples_str}"
        )

    def generate_model_from_file(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Select text file (TXT)", "", "Text Files (*.txt);;All Files (*)", options=options)
        if file_name:
            self.covertext_input.setPlainText("Processing text... This may take a moment!")
            QApplication.processEvents()

            selected_order = int(self.order_combo.currentText())

            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    text = f.read()

                self.stego = MarkovStego(text=text, state_size=selected_order)
                self.update_status_display(file_name)
                QMessageBox.information(self, "Success", f"Order {selected_order} Markov chain compiled successfully!")
            except Exception as e:
                self.covertext_input.setPlainText(f"<< Error during model creation: {e} >>\nNote: Higher order chains require much more input text!")

    def save_model_to_json(self):
        if not self.stego.model:
            QMessageBox.warning(self, "Error", "No active model to save.")
            return

        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Save JSON model", "model.json", "JSON Files (*.json)", options=options)
        if file_name:
            json_str = self.stego.to_json()
            with open(file_name, 'w', encoding='utf-8') as f:
                f.write(json_str)
            QMessageBox.information(self, "Saved", f"Order {self.stego.state_size} Markov chain saved to disk.\nUsing JSON files frees up RAM.")

    def use_model_from_file(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Open prepared JSON model", "", "JSON Files (*.json);;All Files (*)", options=options)
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    json_str = f.read()

                self.stego.load_from_json(json_str)

                loaded_order = str(self.stego.state_size)
                index = self.order_combo.findText(loaded_order)
                if index >= 0:
                    self.order_combo.setCurrentIndex(index)

                self.update_status_display(file_name)
                QMessageBox.information(self, "Success", f"Order {loaded_order} Markov model successfully restored from JSON!")
            except Exception as e:
                self.covertext_input.setPlainText(f"<< Error loading model: {e} >>")

    def do_embed(self):
        secret = self.secret_input.toPlainText()
        key = self.key_input.text().strip()
        ignore_punct = self.ignore_punct_cb.isChecked()

        if not secret:
            QMessageBox.warning(self, "Error", "Please enter a message to hide in the 'Secret Msg' field.")
            return
        try:
            stego_text = self.stego.encode(secret, L=3, stego_key=key, ignore_punct=ignore_punct)
            self.result_output.setPlainText(stego_text)
        except Exception as e:
            QMessageBox.critical(self, "Generation Error", str(e))

    def do_extract(self):
        stego_text = self.secret_input.toPlainText()
        key = self.key_input.text().strip()
        ignore_punct = self.ignore_punct_cb.isChecked()

        if not stego_text:
            QMessageBox.warning(self, "Error", "Please paste the steganographic text into the 'Secret Msg / Stegano Text' field.")
            return

        if "--- EXTRACTED SECRET MESSAGE ---" in stego_text:
            QMessageBox.warning(self, "Warning", "Please paste the original steganogram, not the extracted message.")
            return

        try:
            secret = self.stego.decode(stego_text, L=3, stego_key=key, ignore_punct=ignore_punct)
            self.result_output.setPlainText(f"--- EXTRACTED SECRET MESSAGE ---\n\n{secret}")
        except Exception as e:
            QMessageBox.critical(self, "Extraction Error", str(e))