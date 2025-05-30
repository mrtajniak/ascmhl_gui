import sys
import subprocess
import threading
import json
import traceback
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QFileDialog,
    QVBoxLayout, QHBoxLayout, QTextEdit, QComboBox, QTabWidget, QLineEdit, QFormLayout, QCheckBox, QProgressBar, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont
import webbrowser
import site

# --- GLOBAL EXCEPTION HANDLER FOR STABILITY ---
def excepthook(type, value, tb):
    msg = "".join(traceback.format_exception(type, value, tb))
    QMessageBox.critical(None, "Unexpected Error", f"An unexpected error occurred:\n{msg}")
    sys.exit(1)
sys.excepthook = excepthook

# --- QTHREAD FOR RESPONSIVE LONG TASKS ---
class WorkerThread(QThread):
    output = pyqtSignal(str)
    finished = pyqtSignal(int)
    progress = pyqtSignal(int)  # New: for progress feedback

    def __init__(self, cmd):
        super().__init__()
        self.cmd = cmd
        self.process = None

    def run(self):
        try:
            self.process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            full_output = []
            for line in self.process.stdout:
                line = line.strip()
                full_output.append(line)
                self.output.emit(line)
                # Progress feedback: look for "Progress: XX%" in output
                if "progress" in line.lower():
                    import re
                    match = re.search(r'(\d{1,3})\s*%', line)
                    if match:
                        percent = int(match.group(1))
                        self.progress.emit(percent)
            self.process.wait()
            # Emit all output at the end if process failed
            if self.process.returncode != 0:
                self.output.emit("❌ Process failed. Full output below:")
                for l in full_output:
                    self.output.emit(l)
            self.finished.emit(self.process.returncode)
        except FileNotFoundError as e:
            self.output.emit("❌ ascmhl not found or not in PATH. Please check installation.")
            self.finished.emit(-1)
        except Exception as e:
            import traceback
            self.output.emit(f"❌ Error: {str(e)}\n{traceback.format_exc()}")
            self.finished.emit(-1)

class ASCMHLGui(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ASC MHL Creator GUI")
        self.resize(600, 380)
        self.init_ui()
        self.setFixedSize(self.size())
        self.setAcceptDrops(True)  # Enable drag & drop for the window
        self.show()
        threading.Thread(target=self.check_and_install_ascmhl, daemon=True).start()

    def init_ui(self):
        layout = QVBoxLayout()
        self.tabs = QTabWidget()

        self.main_tab = QWidget()
        self.init_main_tab()
        self.tabs.addTab(self.main_tab, "Create")

        self.info_tab = QWidget()
        self.init_info_tab()
        self.tabs.addTab(self.info_tab, "Info")

        self.log_tab = QWidget()
        self.init_log_tab()
        self.tabs.addTab(self.log_tab, "Logs")

        self.version_tab = QWidget()
        version_layout = QVBoxLayout()
        gui_version_label = QLabel("ASC MHL Creator GUI Version: 1.2.2")
        gui_version_label.setAlignment(Qt.AlignLeft)
        gui_version_label.setFont(QFont("Arial", 8))
        version_layout.addWidget(gui_version_label)
        self.mhl_version_label = QLabel("ASC MHL Version: Unknown")
        self.mhl_version_label.setAlignment(Qt.AlignLeft)
        self.mhl_version_label.setFont(QFont("Arial", 8))
        version_layout.addWidget(self.mhl_version_label)
        license_content = QTextEdit()
        license_content.setReadOnly(True)
        license_content.setText("""MIT License

Copyright (c) 2025 Krystian

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the \"Software\"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.""")
        version_layout.addWidget(license_content)
        self.update_ascmhl_btn = QPushButton("Update ASC MHL")
        self.update_ascmhl_btn.setVisible(False)
        self.update_ascmhl_btn.clicked.connect(self.update_ascmhl)
        version_layout.addWidget(self.update_ascmhl_btn)

        # Help/About button
        self.help_btn = QPushButton("Help / About")
        self.help_btn.clicked.connect(self.show_help_dialog)
        version_layout.addWidget(self.help_btn)

        self.version_tab.setLayout(version_layout)
        self.tabs.addTab(self.version_tab, "Version")

        layout.addWidget(self.tabs)
        self.status_bar = QProgressBar()
        self.status_bar.setRange(0, 0)
        self.status_bar.setAlignment(Qt.AlignCenter)
        self.status_bar.setVisible(False)
        layout.addWidget(self.status_bar)
        self.setLayout(layout)

        self.media_folder = ""
        self.output_folder = ""
        self.process = None

    def init_main_tab(self):
        layout = QVBoxLayout()

        # Folder selection
        folder_layout = QHBoxLayout()
        folder_label = QLabel("Media Folder:")
        folder_label.setAlignment(Qt.AlignLeft)
        folder_layout.addWidget(folder_label)
        self.folder_label = QLabel("No folder selected.")
        self.folder_label.setAcceptDrops(True)
        self.folder_label.setStyleSheet("background: #f0f0f0;")
        folder_layout.addWidget(self.folder_label)
        self.folder_btn = QPushButton("Select Folder")
        self.folder_btn.clicked.connect(self.select_folder)
        folder_layout.addWidget(self.folder_btn)
        layout.addLayout(folder_layout)

        # Drag & drop support for folder label
        self.folder_label.installEventFilter(self)

        # Hash algorithm selection
        hash_layout = QHBoxLayout()
        hash_label = QLabel("Hash Algorithm:")
        hash_label.setAlignment(Qt.AlignLeft)
        hash_layout.addWidget(hash_label)
        self.hash_combo = QComboBox()
        self.hash_combo.addItems(["md5", "sha1", "sha256", "xxh64", "xxh3", "c4"])
        self.hash_combo.setCurrentText("xxh64")
        hash_layout.addWidget(self.hash_combo)
        layout.addLayout(hash_layout)

        # Configuration section
        config_group = QVBoxLayout()
        config_label = QLabel("Configuration:")
        config_label.setAlignment(Qt.AlignLeft)
        config_group.addWidget(config_label)
        self.detect_renaming_checkbox = QCheckBox("Enable Detect Renaming (--detect_renaming)")
        self.detect_renaming_checkbox.setChecked(False)
        config_group.addWidget(self.detect_renaming_checkbox)
        self.no_directory_hashes_checkbox = QCheckBox("Skip Directory Hashes (--no_directory_hashes)")
        self.no_directory_hashes_checkbox.setChecked(False)
        self.no_directory_hashes_checkbox.stateChanged.connect(self.update_no_directory_hashes_label)
        config_group.addWidget(self.no_directory_hashes_checkbox)
        layout.addLayout(config_group)

        button_layout = QHBoxLayout()
        self.run_btn = QPushButton("Create MHL Generation")
        self.run_btn.clicked.connect(self.run_ascmhl)
        self.abort_btn = QPushButton("Abort")
        self.abort_btn.setEnabled(False)
        self.abort_btn.clicked.connect(self.abort_ascmhl)
        self.exit_btn = QPushButton("Exit")
        self.exit_btn.clicked.connect(self.close)
        button_layout.addWidget(self.run_btn)
        button_layout.addWidget(self.abort_btn)
        button_layout.addWidget(self.exit_btn)
        layout.addLayout(button_layout)

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.status_label.setStyleSheet("color: black;")
        self.status_label.setText("🔄 Checking ASC MHL availability...")
        layout.addWidget(self.status_label)

        self.main_tab.setLayout(layout)

    # Drag & drop event filter for folder label and main window
    def eventFilter(self, obj, event):
        if obj == self.folder_label:
            if event.type() == event.DragEnter:
                if event.mimeData().hasUrls():
                    event.accept()
                    return True
            elif event.type() == event.Drop:
                urls = event.mimeData().urls()
                if urls:
                    path = urls[0].toLocalFile()
                    if os.path.isdir(path):
                        self.media_folder = path
                        self.folder_label.setText(path)
                        return True
        return super().eventFilter(obj, event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isdir(path):
                self.media_folder = path
                self.folder_label.setText(path)

    def init_info_tab(self):
        layout = QFormLayout()
        self.location_input = QLineEdit()
        self.name_input = QLineEdit()
        self.email_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.role_input = QLineEdit()
        layout.addRow("Location:", self.location_input)
        layout.addRow("Name:", self.name_input)
        layout.addRow("Email:", self.email_input)
        layout.addRow("Phone:", self.phone_input)
        layout.addRow("Role:", self.role_input)

        self.export_info_btn = QPushButton("Export Info (XML)")
        self.export_info_btn.clicked.connect(self.export_user_data)
        layout.addRow(self.export_info_btn)

        self.import_info_btn = QPushButton("Import Info (XML)")
        self.import_info_btn.clicked.connect(self.import_user_data)
        layout.addRow(self.import_info_btn)

        # JSON export/import
        self.export_info_json_btn = QPushButton("Export Info (JSON)")
        self.export_info_json_btn.clicked.connect(self.export_user_data_json)
        layout.addRow(self.export_info_json_btn)

        self.import_info_json_btn = QPushButton("Import Info (JSON)")
        self.import_info_json_btn.clicked.connect(self.import_user_data_json)
        layout.addRow(self.import_info_json_btn)

        self.clear_info_btn = QPushButton("Clear Info")
        self.clear_info_btn.clicked.connect(self.clear_info_fields)
        layout.addRow(self.clear_info_btn)

        self.feedback_label = QLabel()
        self.feedback_label.setAlignment(Qt.AlignCenter)
        self.feedback_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.feedback_label.setStyleSheet("color: green;")
        layout.addRow(self.feedback_label)
        self.info_tab.setLayout(layout)

    def clear_info_fields(self):
        """Clear all Info tab input fields."""
        self.location_input.clear()
        self.name_input.clear()
        self.email_input.clear()
        self.phone_input.clear()
        self.role_input.clear()

    def export_user_data_json(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export User Data", "identity.json", "JSON Files (*.json)")
        if file_path:
            user_data = {
                'location': self.location_input.text(),
                'name': self.name_input.text(),
                'email': self.email_input.text(),
                'phone': self.phone_input.text(),
                'role': self.role_input.text()
            }
            with open(file_path, 'w') as file:
                json.dump(user_data, file, indent=4)
            self.clear_info_fields()
            self.feedback_label.setText("✅ User data exported to JSON.")

    def import_user_data_json(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import User Data", "", "JSON Files (*.json)")
        if file_path:
            with open(file_path, 'r') as file:
                user_data = json.load(file)
            self.location_input.setText(user_data.get('location', ''))
            self.name_input.setText(user_data.get('name', ''))
            self.email_input.setText(user_data.get('email', ''))
            self.phone_input.setText(user_data.get('phone', ''))
            self.role_input.setText(user_data.get('role', ''))
            self.feedback_label.setText("✅ User data imported from JSON.")

    def init_log_tab(self):
        layout = QVBoxLayout()

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

        self.clear_log_btn = QPushButton("Clear Logs")
        self.clear_log_btn.clicked.connect(self.clear_log)
        layout.addWidget(self.clear_log_btn)

        self.log_tab.setLayout(layout)

    def clear_log(self):
        self.log.clear()

    def check_and_install_ascmhl(self):
        try:
            result = subprocess.run(["ascmhl", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
            version = result.stdout.strip()
            self.mhl_version_label.setText(f"ASC MHL Version: {version}")
            self.update_status(f"✅ ASC MHL is available: {version}", success=True)
            self.log.append(f"✅ ASC MHL is available: {version}")
        except FileNotFoundError:
            self.mhl_version_label.setText("ASC MHL Version: Not Found")
            self.update_status("⚠️ ASC MHL not found. Attempting to install...", success="caution")
            self.log.append("⚠️ ASC MHL not found. Attempting to install...")
            self.install_or_update_ascmhl(upgrade=False)
            import shutil
            ascmhl_path = shutil.which("ascmhl")
            if not ascmhl_path:
                scripts_dirs = site.getusersitepackages(), site.getsitepackages()[0]
                scripts_hint = f"\n\nCommon Python Scripts directories:\n- {scripts_dirs[0]}\\Scripts\n- {scripts_dirs[1]}\\Scripts"
                self.update_status(
                    "❌ ASC MHL installed, but not found in PATH. Please add your Python Scripts directory to PATH and restart." + scripts_hint,
                    success=False
                )
                self.log.append(
                    "❌ ASC MHL installed, but not found in PATH. Please add your Python Scripts directory to PATH and restart." + scripts_hint
                )
                return
            try:
                result = subprocess.run(["ascmhl", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
                version = result.stdout.strip()
                self.mhl_version_label.setText(f"ASC MHL Version: {version}")
                self.update_status(f"✅ ASC MHL is available: {version}", success=True)
                self.log.append(f"✅ ASC MHL is available: {version}")
                installed_version = version.split('version')[-1].strip() if 'version' in version else version
            except Exception as e:
                self.update_status(f"❌ Failed to verify ASC MHL after install: {str(e)}", success=False)
                self.log.append(f"❌ Failed to verify ASC MHL after install: {str(e)}")
                installed_version = None
        else:
            installed_version = version.split('version')[-1].strip() if 'version' in version else version
        self.check_for_ascmhl_updates(installed_version=installed_version)

    def install_or_update_ascmhl(self, upgrade=False):
        try:
            command = "pip install --upgrade ascmhl" if upgrade else "pip install ascmhl"
            msg = (
                "Automatic installation/update of ASC MHL is not supported in this environment.\n\n"
                f"Please open a terminal and run:\n\n{command}\n\n"
                "You can also visit the ASC MHL PyPI page for more info."
            )
            app = QApplication.instance()
            from PyQt5.QtCore import QThread
            if app and QThread.currentThread() == app.thread():
                clipboard = app.clipboard()
                clipboard.setText(command)
                QMessageBox.information(self, "Manual ASC MHL Install/Update", msg)
            else:
                self.log.append("ℹ️ Please run this command manually: " + command)
            webbrowser.open("https://pypi.org/project/ascmhl/")
            self.log.append(f"ℹ️ User prompted to run: {command}")
            self.update_status("ℹ️ Please install/update ASC MHL manually. Command copied to clipboard.", success="caution")
        except Exception as e:
            self.log.append(f"❌ Failed to prompt for ASC MHL install/update: {str(e)}")
            self.update_status(f"❌ Failed to prompt for ASC MHL install/update: {str(e)}", success=False)

    def check_for_ascmhl_updates(self, installed_version=None):
        try:
            import pkg_resources
            import urllib.request
            import json as _json
            if installed_version is None:
                try:
                    installed_version = pkg_resources.get_distribution('ascmhl').version
                except Exception:
                    installed_version = None
            try:
                with urllib.request.urlopen('https://pypi.org/pypi/ascmhl/json') as response:
                    data = _json.load(response)
                    latest_version = data['info']['version']
            except Exception:
                latest_version = None
            if not installed_version:
                self.log.append("⚠️ Could not determine installed ASC MHL version. Is it installed?")
                self.update_status("⚠️ Could not determine installed ASC MHL version. Is it installed?", success="caution")
            elif not latest_version:
                self.log.append("⚠️ Could not reach PyPI to check for ASC MHL updates.")
                self.update_status("⚠️ Could not reach PyPI to check for ASC MHL updates.", success="caution")
            elif installed_version != latest_version:
                self.log.append(f"⚠️ Update available for ASC MHL: {installed_version} -> {latest_version}")
                self.update_status(f"⚠️ Update available for ASC MHL: {installed_version} -> {latest_version}", success="caution")
                self.update_ascmhl_btn.setVisible(True)
                return
            else:
                self.log.append("✅ ASC MHL is up to date.")
                self.update_status("✅ ASC MHL is up to date.", success=True)
        except Exception as e:
            self.log.append(f"❌ Failed to check for updates: {str(e)}")
            self.update_status(f"❌ Failed to check for updates: {str(e)}", success=False)

    def is_ascmhl_available(self):
        try:
            result = subprocess.run(["ascmhl", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
            version = result.stdout.strip()
            self.mhl_version_label.setText(f"ASC MHL Version: {version}")
            return result.returncode == 0
        except (FileNotFoundError, subprocess.CalledProcessError):
            self.mhl_version_label.setText("ASC MHL Version: Not Found")
            return False

    def update_status(self, message, success=None):
        if len(message) > 100:
            font_size = 10
        elif len(message) > 60:
            font_size = 13
        else:
            font_size = 16
        self.status_label.setText(message)
        self.status_label.setFont(QFont("Arial", font_size, QFont.Bold))
        if success is True:
            self.status_label.setStyleSheet("color: green;")
        elif success is False:
            self.status_label.setStyleSheet("color: red;")
        elif success == "caution":
            self.status_label.setStyleSheet("color: orange;")
        elif success is None:
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

        # Check if ascmhl is available before running
        try:
            result = subprocess.run(["ascmhl", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
        except Exception as e:
            self.log.append("❌ ascmhl not found or not working. Please check installation and PATH.")
            self.update_status("❌ ascmhl not found or not working. Please check installation and PATH.", success=False)
            return

        hash_alg = self.hash_combo.currentText()
        cmd = [
            "ascmhl",
            "create",
            self.media_folder,
            "--hash_format", hash_alg,
            "-v"
        ]

        if self.detect_renaming_checkbox.isChecked():
            cmd.append("--detect_renaming")
        if self.no_directory_hashes_checkbox.isChecked():
            cmd.append("--no_directory_hashes")

        def get_safe_input(input_field):
            return input_field.text().strip() if input_field.text().strip() else None

        location = get_safe_input(self.location_input)
        name = get_safe_input(self.name_input)
        email = get_safe_input(self.email_input)
        phone = get_safe_input(self.phone_input)
        role = get_safe_input(self.role_input)

        if location:
            cmd.extend(["--location", location])
        if name:
            cmd.extend(["--author_name", name])
        if email:
            cmd.extend(["--author_email", email])
        if phone:
            cmd.extend(["--author_phone", phone])
        if role:
            cmd.extend(["--author_role", role])

        self.log.append(f"\n🔧 Running: {' '.join(cmd)}\n")
        self.update_status("🔧 Running MHL creation...", success=None)

        self.exit_btn.setEnabled(False)
        self.abort_btn.setEnabled(True)
        self.run_btn.setEnabled(False)
        self.info_tab.setDisabled(True)
        self.detect_renaming_checkbox.setEnabled(False)
        self.no_directory_hashes_checkbox.setEnabled(False)
        self.hash_combo.setEnabled(False)
        self.folder_btn.setEnabled(False)
        self.status_bar.setVisible(True)
        self.status_bar.setRange(0, 0)

        def handle_output(line):
            self.log.append(line)
            self.log.moveCursor(self.log.textCursor().End)
            self.log.ensureCursorVisible()
            QApplication.processEvents()

        def handle_progress(percent):
            self.status_bar.setRange(0, 100)
            self.status_bar.setValue(percent)

        def handle_finished(returncode):
            self.status_bar.setRange(0, 0)
            self.status_bar.setVisible(False)
            if returncode == 0:
                self.log.append("✅ MHL creation complete.")
                self.update_status("✅ MHL creation complete.", success=True)
            elif returncode == -1:
                self.log.append("❌ Error occurred during MHL creation. See log above for details.")
                self.update_status("❌ Error occurred during MHL creation.", success=False)
            else:
                self.log.append(f"❌ MHL creation failed with exit code {returncode}. See log above for details.")
                self.update_status(f"❌ MHL creation failed (exit code {returncode}).", success=False)

            self.exit_btn.setEnabled(True)
            self.abort_btn.setEnabled(False)
            self.run_btn.setEnabled(True)
            self.info_tab.setDisabled(False)
            self.detect_renaming_checkbox.setEnabled(True)
            self.no_directory_hashes_checkbox.setEnabled(True)
            self.hash_combo.setEnabled(True)
            self.folder_btn.setEnabled(True)

            args_used = "<b>Arguments Used:</b><br>"
            args_used += f"<span style='color: blue;'>Media Folder:</span> {self.media_folder}<br>"
            args_used += f"<span style='color: green;'>Hash Algorithm:</span> {hash_alg}<br>"
            if self.detect_renaming_checkbox.isChecked():
                args_used += "<span style='color: orange;'>Detect Renaming:</span> Enabled<br>"
            if self.no_directory_hashes_checkbox.isChecked():
                args_used += "<span style='color: orange;'>Skip Directory Hashes:</span> Enabled<br>"
            if location:
                args_used += f"<span style='color: purple;'>Location:</span> {location}<br>"
            if name:
                args_used += f"<span style='color: purple;'>Name:</span> {name}<br>"
            if email:
                args_used += f"<span style='color: purple;'>Email:</span> {email}<br>"
            if phone:
                args_used += f"<span style='color: purple;'>Phone:</span> {phone}<br>"
            if role:
                args_used += f"<span style='color: purple;'>Role:</span> {role}<br>"

            self.log.append(args_used)

        self.worker_thread = WorkerThread(cmd)
        self.worker_thread.output.connect(handle_output)
        self.worker_thread.finished.connect(handle_finished)
        self.worker_thread.progress.connect(handle_progress)
        self.worker_thread.start()

    def abort_ascmhl(self):
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.terminate()
            self.log.append("⚠️ MHL creation aborted.")
            self.update_status("⚠️ MHL creation aborted.", success="caution")
            self.abort_btn.setEnabled(False)
            self.exit_btn.setEnabled(True)
            self.status_bar.setVisible(False)

    def update_no_directory_hashes_label(self):
        if self.no_directory_hashes_checkbox.isChecked():
            self.no_directory_hashes_checkbox.setStyleSheet("color: red;")
        else:
            self.no_directory_hashes_checkbox.setStyleSheet("color: black;")

    def export_user_data(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export User Data", "identity.xml", "XML Files (*.xml)")
        if file_path:
            user_data = {
                'location': self.location_input.text(),
                'name': self.name_input.text(),
                'email': self.email_input.text(),
                'phone': self.phone_input.text(),
                'role': self.role_input.text()
            }
            with open(file_path, 'w') as file:
                file.write("<userdata>\n")
                file.write("    <user>\n")
                for key, value in user_data.items():
                    file.write(f"        <{key}>{value}</{key}>\n")
                file.write("    </user>\n")
                file.write("</userdata>\n")
            user_data = None
            self.clear_info_fields()
            self.feedback_label.setText("✅ User data exported successfully.")

    def import_user_data(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import User Data", "", "XML Files (*.xml)")
        if file_path:
            try:
                from xml.etree import ElementTree as ET
                tree = ET.parse(file_path)
                root = tree.getroot()
                user = root.find('user')
                self.location_input.setText(user.find('location').text if user.find('location') is not None else "")
                self.name_input.setText(user.find('name').text if user.find('name') is not None else "")
                self.email_input.setText(user.find('email').text if user.find('email') is not None else "")
                self.phone_input.setText(user.find('phone').text if user.find('phone') is not None else "")
                self.role_input.setText(user.find('role').text if user.find('role') is not None else "")
                tree = None
                self.feedback_label.setText("✅ User data imported successfully.")
            except Exception as e:
                self.feedback_label.setStyleSheet("color: red;")
                self.feedback_label.setText(f"❌ Error importing user data: {str(e)}")

    def update_ascmhl(self):
        try:
            self.log.append("🔄 Updating ASC MHL...")
            self.update_status("🔄 Updating ASC MHL...", success=None)
            self.install_or_update_ascmhl(upgrade=True)
            result = subprocess.run(["ascmhl", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
            version = result.stdout.strip()
            self.mhl_version_label.setText(f"ASC MHL Version: {version}")
            self.update_ascmhl_btn.setVisible(False)
        except Exception as e:
            self.log.append(f"❌ Failed to update ASC MHL: {str(e)}")
            self.update_status(f"❌ Failed to update ASC MHL: {str(e)}", success=False)

    def show_help_dialog(self):
        QMessageBox.information(
            self,
            "Help / About",
            (
                "<b>ASC MHL Creator GUI</b><br><br>"
                "Version: 1.2.2<br>"
                "Author: Krystian<br><br>"
                "<b>Usage:</b><br>"
                "- Select or drag & drop a media folder.<br>"
                "- Choose hash algorithm and options.<br>"
                "- Fill in Info tab if needed.<br>"
                "- Click 'Create MHL Generation' to start.<br>"
                "- Progress will be shown below.<br><br>"
                "You can import/export user info as XML or JSON.<br><br>"
                "For more info, visit: <a href='https://pypi.org/project/ascmhl/'>ASC MHL PyPI</a>"
            )
        )

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    gui = ASCMHLGui()
    gui.show()
    sys.exit(app.exec_())
