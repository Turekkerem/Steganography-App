import markovify
import json
import random
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

    def encode(self, secret_message, L=3):
        if not self.model:
            raise ValueError("Markov chain is not initialized!")
            
        # PEŁNE WSPARCIE UNICODE (UTF-8)
        msg_bytes = secret_message.encode('utf-8')
        prefix_bytes = f"{len(msg_bytes)}|".encode('utf-8')
        full_payload = prefix_bytes + msg_bytes
        
        binary = ''.join(f'{b:08b}' for b in full_payload)
        
        if len(binary) % L != 0:
            binary += '0' * (L - (len(binary) % L))
        blocks = [int(binary[i:i+L], 2) for i in range(0, len(binary), L)]

        state = (BEGIN,) * self.state_size
        generated_tokens = []

        # Phase 1: Arithmetic encoding
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

        random.seed(secret_message)

        # Phase 2: Naturally finish the sentence
        tail_word_count = 0
        while tail_word_count < 50:
            if state not in self.model:
                break
            choices_dict = self.model.get(state, {END: 1})
            if not choices_dict:
                break
            
            words = list(choices_dict.keys())
            weights = list(choices_dict.values())
            best_word = random.choices(words, weights=weights, k=1)[0]
            
            generated_tokens.append(best_word)
            if best_word == END:
                break
            
            state = tuple(list(state[1:]) + [best_word])
            tail_word_count += 1

        if tail_word_count >= 50 and generated_tokens[-1] != END:
            generated_tokens.append(END)
            
        random.seed() 

        # Phase 3: Format text
        output_tokens = []
        for token in generated_tokens:
            if token == END:
                if output_tokens and not output_tokens[-1].endswith('.'):
                    output_tokens[-1] += "."
                else:
                    output_tokens.append(".")
            else:
                output_tokens.append(token)
                
        return " ".join(output_tokens)

    def decode(self, stego_text, L=3):
        words_to_process = []
        for raw_word in stego_text.split():
            words_to_process.append(raw_word)

        state = (BEGIN,) * self.state_size
        
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
                    f"Graph desynchronization.\n"
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
                            payload = extracted_bytes[prefix_size : prefix_size + msg_byte_length]
                            return payload.decode('utf-8', errors='replace')


class AlgoMarkovTab(TabTemplate):
    def __init__(self):
        super().__init__()
        
        self.result_output.setReadOnly(True)
        self.result_output.setPlaceholderText("Results will appear here...")
        
        # Poprawione nazewnictwo interfejsu
        self.customize_ui(
            cover_lbl="Markov Model Status",
            secret_lbl="Secret Msg (Hide) / Stegano Text (Decode)",
            key_lbl="Key (N/A for this method)",
            embed_btn="Generate Steganogram",
            extract_btn="Extract Data",
            tab_help_text=(
                "1. Load Markov chain from JSON or TXT file.\n"
                "2. TO HIDE: Enter secret message in the middle text box and click 'Generate'.\n"
                "3. TO EXTRACT: Paste steganographic text into the middle text box and click 'Extract'."
            )
        )
        
        # Zablokowanie niepotrzebnego klucza w tym algorytmie
        self.key_input.setEnabled(False)
        self.key_input.setPlaceholderText("Not used in Markov Steganography")

        self.btn_gen_model = QPushButton("Generate markov chain from text file")
        self.btn_save_model = QPushButton("Save markov chain to JSON file")
        self.btn_use_model = QPushButton("Use markov chain from JSON file")
        
        action_layout = self.action_group.layout()
        action_layout.insertWidget(0, self.btn_gen_model)
        action_layout.insertWidget(1, self.btn_save_model)
        action_layout.insertWidget(2, self.btn_use_model)

        self.btn_gen_model.clicked.connect(self.generate_model_from_file)
        self.btn_save_model.clicked.connect(self.save_model_to_json)
        self.btn_use_model.clicked.connect(self.use_model_from_file)
        
        default_text = (
            "Digital steganography uses various hiding techniques. "
            "The capacity of hidden messages depends on text complexity. "
            "Methods using Markov chains are characterized by preserving the linguistic model. "
            "Text generated by the chain sounds relatively natural. "
        ) * 10 
        
        self.covertext_input.setPlainText("<< Default test dictionary initialized >>")
        self.covertext_input.setReadOnly(True)
        
        self.stego = MarkovStego(text=default_text, state_size=1)
        
        try:
            self.embed_button.clicked.disconnect()
            self.extract_button.clicked.disconnect()
        except TypeError:
            pass
        self.embed_button.clicked.connect(self.do_embed)
        self.extract_button.clicked.connect(self.do_extract)
        
    def generate_model_from_file(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Select text file (TXT)", "", "Text Files (*.txt);;All Files (*)", options=options)
        if file_name:
            self.covertext_input.setPlainText("Processing text... This may take a moment!")
            QApplication.processEvents() 
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    text = f.read()
                self.stego = MarkovStego(text=text, state_size=1)
                self.covertext_input.setPlainText(f"<< Successfully generated Markov model from file:\n{file_name} >>")
                QMessageBox.information(self, "Success", "Markov chain compiled successfully!")
            except Exception as e:
                self.covertext_input.setPlainText(f"<< Error during model creation: {e} >>")

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
            QMessageBox.information(self, "Saved", "Markov chain saved to disk.\nUsing JSON files frees up RAM.")

    def use_model_from_file(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Open prepared JSON model", "", "JSON Files (*.json);;All Files (*)", options=options)
        if file_name:
            with open(file_name, 'r', encoding='utf-8') as f:
                json_str = f.read()
            self.stego.load_from_json(json_str)
            self.covertext_input.setPlainText(f"<< Loaded Markov chain from disk from file:\n{file_name} >>")
            QMessageBox.information(self, "Success", "Markov model successfully restored from JSON!")

    def do_embed(self):
        # Pobieranie wpisanej tajnej wiadomości ze środkowego pola input
        secret = self.secret_input.toPlainText()
        if not secret:
            QMessageBox.warning(self, "Error", "Please enter a message to hide in the 'Secret Msg' field.")
            return
        try:
            stego_text = self.stego.encode(secret, L=3)
            # Wynik wypluwamy w polu z prawej strony (ReadOnly)
            self.result_output.setPlainText(stego_text)
        except Exception as e:
            QMessageBox.critical(self, "Generation Error", str(e))

    def do_extract(self):
        # Pobieranie steganogramu DO ODKODOWANIA z pola input (zamiast z pustego okna result)
        stego_text = self.secret_input.toPlainText()
        if not stego_text:
            QMessageBox.warning(self, "Error", "Please paste the steganographic text into the 'Secret Msg / Stegano Text' field.")
            return
            
        try:
            secret = self.stego.decode(stego_text, L=3)
            # Zdekodowany sekret wyrzucamy z prawej strony
            self.result_output.setPlainText(f"--- EXTRACTED SECRET MESSAGE ---\n\n{secret}")
        except Exception as e:
            QMessageBox.critical(self, "Extraction Error", str(e))