from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt

#use this class template when creating future tabs
class TabTemplate(QWidget):
    def __init__(self):
        super().__init__()

        main_layout = QHBoxLayout(self)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        self.covertext_input = QTextEdit()
        self.covertext_input.setPlaceholderText("Enter cover text here")

        self.secret_input = QTextEdit()
        self.secret_input.setPlaceholderText("Enter secret message here")

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Enter key (may not be necessary)")

        form_layout = QFormLayout()
        form_layout.addRow(QLabel("<b>Cover Text:</b>"), self.covertext_input)
        form_layout.addRow(QLabel("<b>Secret Message:</b>"), self.secret_input)
        form_layout.addRow(QLabel("<b>Key:</b>"), self.key_input)
        
        left_layout.addLayout(form_layout)

        self.embed_button = QPushButton("Embed Secret Message")
        self.extract_button = QPushButton("Extract Secret Message")
        left_layout.addWidget(self.embed_button)
        left_layout.addWidget(self.extract_button)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        right_layout.addWidget(QLabel("<b>Result:</b>"))
        self.result_output = QTextEdit()
        self.result_output.setReadOnly(True)
        right_layout.addWidget(self.result_output)

        #add both widgets to the splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        
        #horizontal proportions
        splitter.setSizes([400, 400])