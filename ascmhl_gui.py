import sys
import subprocess
import threading
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QFileDialog,
    QVBoxLayout, QHBoxLayout, QTextEdit, QComboBox
)
from PyQt5.QtCore import Qt

class ASCMHLGui(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ASC MHL Creator GUI")
        self.resize(600, 400)
        self.init_ui()

        # Check if 'ascmhl' is available
        if not self.is_ascmhl_available():
            self.log.append("❌ 'ascmhl' not found. Please ensure it is installed and added to your system PATH.")

    def init_ui(self):
        layout = QVBoxLayout()

        # Folder selection
        self.folder_label = QLabel("No folder selected.")
        self.folder_btn = QPushButton("Select Media Folder")
        self.folder_btn.clicked.connect(self.select_folder)

        # Hash algorithm selection
        self.hash_combo = QComboBox()
        self.hash_combo.addItems(["md5", "sha1", "sha256", "xxh64", "xxh3", "c4"])
        self.hash_combo.setCurrentText("xxh64")

        # Run button
        self.run_btn = QPushButton("Create ASC MHL")
        self.run_btn.clicked.connect(self.run_ascmhl)

        # Log output
        self.log = QTextEdit()
        self.log.setReadOnly(True)

        # Layout
        layout.addWidget(QLabel("Media Folder:"))
        layout.addWidget(self.folder_label)
        layout.addWidget(self.folder_btn)

        layout.addWidget(QLabel("Hash Algorithm:"))
        layout.addWidget(self.hash_combo)

        layout.addWidget(self.run_btn)
        layout.addWidget(QLabel("Output Log:"))
        layout.addWidget(self.log)

        self.setLayout(layout)

        # State
        self.media_folder = ""
        self.output_folder = ""

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Media Folder")
        if folder:
            self.media_folder = folder
            self.folder_label.setText(folder)

    def is_ascmhl_available(self):
        try:
            subprocess.run(["ascmhl", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

    def run_ascmhl(self):
        if not self.media_folder:
            self.log.append("⚠️ Please select a media folder.")
            return

        hash_alg = self.hash_combo.currentText()
        cmd = [
            "ascmhl",
            "create",
            self.media_folder,
            "--hash_format", hash_alg,
            "-v"
        ]

        self.log.append(f"\n🔧 Running: {' '.join(cmd)}\n")

        def run_command():
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )

                for line in process.stdout:
                    # Append new log entries to display from top to bottom
                    self.log.append(line.strip())
                    self.log.moveCursor(self.log.textCursor().End)
                    self.log.ensureCursorVisible()
                    QApplication.processEvents()

                process.wait()
                if process.returncode == 0:
                    self.log.append("✅ MHL creation complete.")
                else:
                    self.log.append("❌ MHL creation failed.")

            except FileNotFoundError:
                self.log.append("❌ 'ascmhl' not found. Make sure it's installed and in your system PATH.")
            except Exception as e:
                self.log.append(f"❌ Error: {str(e)}")

        # Run the command in a separate thread to keep the UI responsive
        threading.Thread(target=run_command, daemon=True).start()

        # Auto-scroll to the bottom of the log after appending new text
        self.log.moveCursor(self.log.textCursor().End)
        self.log.ensureCursorVisible()

        # Ensure the scroll bar follows the text in the output log
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = ASCMHLGui()
    gui.show()
    sys.exit(app.exec_())
