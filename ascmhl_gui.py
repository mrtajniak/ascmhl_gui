import sys
import subprocess
import threading
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QFileDialog,
    QVBoxLayout, QHBoxLayout, QTextEdit, QComboBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class ASCMHLGui(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ASCMHL Creator GUI")
        self.resize(600, 400)
        self.init_ui()

        # Check if 'ascmhl' is available
        if not self.is_ascmhl_available():
            self.update_status("❌ ascmhl not found. Please ensure it is installed and added to your system PATH.", success=False)
        else:
            self.update_status("✅ ascmhl is available.", success=True)

    def init_ui(self):
        layout = QVBoxLayout()

        # ASC MHL version display
        self.version_label = QLabel("ASC MHL Version: Unknown")
        self.version_label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.version_label)

        # Folder selection
        self.folder_label = QLabel("No folder selected.")
        self.folder_btn = QPushButton("Select Media Folder")
        self.folder_btn.clicked.connect(self.select_folder)

        # Hash algorithm selection
        self.hash_combo = QComboBox()
        self.hash_combo.addItems(["md5", "sha1", "sha256", "xxh64", "xxh3", "c4"])
        self.hash_combo.setCurrentText("xxh64")

        # Run button
        self.run_btn = QPushButton("Create MHL generation")
        self.run_btn.clicked.connect(self.run_ascmhl)

        # Abort button
        self.abort_btn = QPushButton("Abort")
        self.abort_btn.setEnabled(False)
        self.abort_btn.clicked.connect(self.abort_ascmhl)

        # Exit button
        self.exit_btn = QPushButton("Exit")
        self.exit_btn.clicked.connect(self.close)
        self.exit_btn.setEnabled(True)

        # Log output
        self.log = QTextEdit()
        self.log.setReadOnly(True)

        # Status display
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.status_label.setStyleSheet("color: red;")
        self.status_label.setText("❌ ascmhl not found. Please ensure it is installed and added to your system PATH.")

        # Layout
        layout.addWidget(QLabel("Media Folder:"))
        layout.addWidget(self.folder_label)
        layout.addWidget(self.folder_btn)

        layout.addWidget(QLabel("Hash Algorithm:"))
        layout.addWidget(self.hash_combo)

        layout.addWidget(self.run_btn)
        layout.addWidget(self.abort_btn)  # Add Abort button to the layout
        layout.addWidget(QLabel("Output Log:"))
        layout.addWidget(self.log)

        layout.addWidget(QLabel("Status:"))
        layout.addWidget(self.status_label)
        layout.addWidget(self.exit_btn)

        self.setLayout(layout)

        # State
        self.media_folder = ""
        self.output_folder = ""
        self.process = None  # Track the running process

    def is_ascmhl_available(self):
        try:
            result = subprocess.run(["ascmhl", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
            version = result.stdout.strip()
            self.version_label.setText(f"{version}")
            return result.returncode == 0
        except (FileNotFoundError, subprocess.CalledProcessError):
            self.version_label.setText("ASCMHL Not Found")
            return False

    def update_status(self, message, success=None):
        self.status_label.setText(message)
        if success is True:  # Success
            self.status_label.setStyleSheet("color: green;")
        elif success is False:  # Error
            self.status_label.setStyleSheet("color: red;")
        elif success == "caution":  # Caution
            self.status_label.setStyleSheet("color: orange;")
        elif success is None:  # Info
            self.status_label.setStyleSheet("color: black;")

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Media Folder")
        if folder:
            self.media_folder = folder
            self.folder_label.setText(folder)

    def run_ascmhl(self):
        if not self.media_folder:
            self.log.append("⚠️ Please select a media folder.")
            self.update_status("⚠️ Please select a media folder.", success="caution")
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
        self.update_status("🔧 Running MHL creation...", success=None)
        self.exit_btn.setEnabled(False)
        self.abort_btn.setEnabled(True)  # Enable Abort button

        def run_command():
            try:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )

                for line in self.process.stdout:
                    self.log.append(line.strip())
                    self.log.moveCursor(self.log.textCursor().End)
                    self.log.ensureCursorVisible()
                    QApplication.processEvents()

                self.process.wait()
                if self.process.returncode == 0:
                    self.log.append("✅ MHL creation complete.")
                    self.update_status("✅ MHL creation complete.", success=True)
                else:
                    self.log.append("❌ MHL creation failed.")
                    self.update_status("❌ MHL creation failed.", success=False)

            except FileNotFoundError:
                self.log.append("❌ 'ascmhl' not found. Make sure it's installed and in your system PATH.")
                self.update_status("❌ 'ascmhl' not found. Please ensure it is installed and added to your system PATH.", success=False)
            except Exception as e:
                self.log.append(f"❌ Error: {str(e)}")
                self.update_status(f"❌ Error: {str(e)}", success=False)
            finally:
                self.process = None
                self.exit_btn.setEnabled(True)
                self.abort_btn.setEnabled(False)  # Disable Abort button

        # Run the command in a separate thread to keep the UI responsive
        threading.Thread(target=run_command, daemon=True).start()

        # Auto-scroll to the bottom of the log after appending new text
        self.log.moveCursor(self.log.textCursor().End)
        self.log.ensureCursorVisible()

        # Ensure the scroll bar follows the text in the output log
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def abort_ascmhl(self):
        if self.process and self.process.poll() is None:  # Check if the process is running
            self.process.terminate()
            self.log.append("⚠️ MHL creation aborted.")
            self.update_status("⚠️ MHL creation aborted.", success="caution")
            self.process = None
            self.abort_btn.setEnabled(False)  # Disable Abort button
            self.exit_btn.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = ASCMHLGui()
    gui.show()
    sys.exit(app.exec_())
