import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from algo1 import Algo1Tab
from algo8 import Algo8Tab
from algo14 import Algo14Tab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Steganography Project - Adam Bojek, Kerem Özdoğan")
        self.resize(1200, 800)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.tab_home = QWidget()
        self.tab_help = QWidget()
        self.tab_algo1 = Algo1Tab()
        self.tab_algo8 = Algo8Tab()
        self.tab_algo14 = Algo14Tab()

        self.tabs.addTab(self.tab_home, "Home")
        self.tabs.addTab(self.tab_algo1, "Algorithm 1")
        self.tabs.addTab(self.tab_algo8, "Algorithm 8")
        self.tabs.addTab(self.tab_algo14, "Algorithm 14")
        
        self.init_home_tab()

    def init_home_tab(self):
        # Główny layout dla zakładki Home
        layout = QVBoxLayout()
        layout.setContentsMargins(50, 50, 50, 50)  # Marginesy (lewo, góra, prawo, dół)
        layout.setSpacing(30)  # Odstępy między elementami

        # 1. Tytuł / Powitanie
        title_label = QLabel("Hi there! This is our steganography app!")
        title_label.setStyleSheet("font-size: 32px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)
        
        # 2. Instrukcja główna (używamy małego wsparcia HTML dla listy)
        instruction_text = (
            "<b>Instruction:</b> at the top of the window there are a few tabs - "
            "click on them to use different steganography methods (kiedyś damy im nazwy, ale na razie):<br>"
            "<ul>"
            "<li>Algo1</li>"
            "<li>Algo8</li>"
            "<li>Algo9</li>"
            "<li>Algo12 (?)</li>"
            "<li>Algo14</li>"
            "</ul>"
        )
        instruction_label = QLabel(instruction_text)
        instruction_label.setStyleSheet("font-size: 20px;")
        instruction_label.setWordWrap(True)  # Pozwala na zawijanie tekstu, jeśli okno będzie mniejsze

        # 3. Podpowiedź (Hint) na dole
        hint_label = QLabel("<i>Hint: on this page there are no instructions because each tab has its own help button.</i>")
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet("font-size: 16px; color: gray;")

        # Dodawanie elementów do layoutu
        layout.addWidget(title_label)
        layout.addWidget(instruction_label)
        
        # addStretch() działa jak "sprężyna" - wypycha powyższe elementy do góry, 
        # a poniższe na sam dół okna. Dzięki temu tekst nie zbija się na samym środku.
        layout.addStretch() 
        
        layout.addWidget(hint_label)

        # Ustawienie layoutu w zakładce Home
        self.tab_home.setLayout(layout)

    def init_help_tab(self):
        # todo
        pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet("QWidget { font-size: 14pt; }")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())