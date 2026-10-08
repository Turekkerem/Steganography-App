import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from algo1 import Algo1Tab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Steganography Project - Adam Bojek, Kerem Özdoğan")
        self.resize(900, 600)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.tab_home = QWidget()
        self.tab_help = QWidget()
        self.tab_algo1 = Algo1Tab()

        self.tabs.addTab(self.tab_home, "Home")
        self.tabs.addTab(self.tab_algo1, "Algorithm 1")

        self.init_home_tab()

    def init_home_tab(self):
        #todo, this is extremely basic
        layout = QVBoxLayout()
        label = QLabel("Welcome!!!\n This is our steganography app!")
        label.setStyleSheet("font-size: 32px; font-weight: bold;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        self.tab_home.setLayout(layout)

    def init_helf_tab(self):
        #todo
        pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
