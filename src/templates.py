from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt

# use this class template when creating future tabs
class TabTemplate(QWidget):
    def __init__(self):
        super().__init__()

        # Główny layout (z dodanymi marginesami)
        main_layout = QHBoxLayout(self)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # ==================== LEWA STRONA ====================
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0) # Lepszy margines przed splitterem

        # 1. Przyciski Pomocy (Help) na górze
        help_layout = QHBoxLayout()
        self.general_help_btn = QPushButton("ℹ️ General Help")
        self.tab_help_btn = QPushButton("❓ Algorithm Help")
        help_layout.addWidget(self.general_help_btn)
        help_layout.addWidget(self.tab_help_btn)
        left_layout.addLayout(help_layout)

        # 2. Grupa wejściowa (Input Data) - ładnie oprawiona w ramkę QGroupBox
        self.input_group = QGroupBox("Input Data")
        form_layout = QFormLayout()

        # Zachowane dokładne nazwy zmiennych dla kompatybilności wstecznej!
        self.cover_label = QLabel("<b>Cover Text:</b>")
        self.covertext_input = QTextEdit()
        self.covertext_input.setPlaceholderText("Enter cover text here")

        self.secret_label = QLabel("<b>Secret Message:</b>")
        self.secret_input = QTextEdit()
        self.secret_input.setPlaceholderText("Enter secret message here")

        self.key_label = QLabel("<b>Key:</b>")
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Enter key (may not be necessary)")

        form_layout.addRow(self.cover_label, self.covertext_input)
        form_layout.addRow(self.secret_label, self.secret_input)
        form_layout.addRow(self.key_label, self.key_input)
        
        self.input_group.setLayout(form_layout)
        left_layout.addWidget(self.input_group)

        # 3. Grupa z przyciskami (Actions) - również w ramce
        self.action_group = QGroupBox("Actions")
        action_layout = QHBoxLayout()
        
        self.embed_button = QPushButton("Embed Secret Message")
        self.extract_button = QPushButton("Extract Secret Message")
        
        action_layout.addWidget(self.embed_button)
        action_layout.addWidget(self.extract_button)
        
        self.action_group.setLayout(action_layout)
        left_layout.addWidget(self.action_group)

        # ==================== PRAWA STRONA ====================
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)

        self.output_group = QGroupBox("Result Output")
        output_layout = QVBoxLayout()
        
        self.result_output = QTextEdit()
        self.result_output.setReadOnly(True)
        self.result_output.setPlaceholderText("Operation results will appear here...")
        output_layout.addWidget(self.result_output)
        
        self.output_group.setLayout(output_layout)
        right_layout.addWidget(self.output_group)

        # ==================== DODANIE DO SPLITTERA ====================
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([450, 450])

        # Domyślne teksty dla przycisków "Help"
        self.general_help_text = (
            "Welcome to the Steganography App!\n\n"
            "This application allows you to hide secret data inside standard text "
            "or apply watermarks. Choose an algorithm tab at the top to begin."
        )
        self.tab_help_text = "Standard Steganography:\n1. Input cover text.\n2. Input secret message.\n3. Click 'Embed'."

        # Podłączenie przycisków "Help" do ich akcji
        self.general_help_btn.clicked.connect(self.show_general_help)
        self.tab_help_btn.clicked.connect(self.show_tab_help)

    # --- METODY DO WYŚWIETLANIA POMOCY ---
    def show_general_help(self):
        QMessageBox.information(self, "General Help", self.general_help_text)

    def show_tab_help(self):
        QMessageBox.information(self, "Algorithm Help", self.tab_help_text)

    # --- METODA DO SZYBKIEJ ZMIANY NAZW (np. dla Watermarking'u) ---
    def customize_ui(self, cover_lbl=None, secret_lbl=None, key_lbl=None, 
                     embed_btn=None, extract_btn=None, output_grp=None,
                     tab_help_text=None, general_help_text=None):
        """
        Metoda służy do podmiany etykiet i tekstów przycisków w klasach dziedziczących,
        jeśli algorytm wymaga innego nazewnictwa (np. 'Watermark' zamiast 'Secret Message').
        """
        if cover_lbl:
            self.cover_label.setText(f"<b>{cover_lbl}:</b>")
            self.covertext_input.setPlaceholderText(f"Enter {cover_lbl.lower()} here")
        if secret_lbl:
            self.secret_label.setText(f"<b>{secret_lbl}:</b>")
            self.secret_input.setPlaceholderText(f"Enter {secret_lbl.lower()} here")
        if key_lbl:
            self.key_label.setText(f"<b>{key_lbl}:</b>")
            self.key_input.setPlaceholderText(f"Enter {key_lbl.lower()} here")
        if embed_btn:
            self.embed_button.setText(embed_btn)
        if extract_btn:
            self.extract_button.setText(extract_btn)
        if output_grp:
            self.output_group.setTitle(output_grp)
        if tab_help_text:
            self.tab_help_text = tab_help_text
        if general_help_text:
            self.general_help_text = general_help_text