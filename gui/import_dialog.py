import glob
import os
import shutil
from pathlib import Path

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QProgressBar, QFileDialog,
    QMessageBox, QGroupBox, QRadioButton, QButtonGroup
)

from core.scanner import SUPPORTED_EXTENSIONS


def find_removable_devices():
    devices = []

    # USB drives and SD cards mounted under /media and /run/media
    for base in ['/media', '/run/media']:
        if not os.path.exists(base):
            continue
        try:
            for entry in os.scandir(base):
                if entry.is_dir():
                    # Could be /media/LABEL or /media/user/LABEL
                    try:
                        for sub in os.scandir(entry.path):
                            if sub.is_dir():
                                devices.append({
                                    'name': sub.name,
                                    'path': sub.path,
                                    'type': 'USB / Karta SD',
                                })
                    except PermissionError:
                        pass
                    # Also treat the entry itself as a device
                    if entry.name not in ('lost+found',):
                        devices.append({
                            'name': entry.name,
                            'path': entry.path,
                            'type': 'USB / Karta SD',
                        })
        except PermissionError:
            pass

    # MTP devices (phones, some cameras) via GVFS
    for pattern in glob.glob('/run/user/*/gvfs/mtp:*'):
        if os.path.isdir(pattern):
            label = os.path.basename(pattern).replace('mtp:', '').replace('%2C', ',')
            devices.append({'name': label, 'path': pattern, 'type': 'MTP (telefon / aparat)'})

    # PTP cameras via GVFS
    for pattern in glob.glob('/run/user/*/gvfs/gphoto2:*'):
        if os.path.isdir(pattern):
            label = os.path.basename(pattern).replace('gphoto2:', '').replace('%2C', ',')
            devices.append({'name': label, 'path': pattern, 'type': 'PTP (aparat)'})

    # Deduplicate by path
    seen = set()
    unique = []
    for d in devices:
        if d['path'] not in seen:
            seen.add(d['path'])
            unique.append(d)
    return unique


def count_photos(path):
    count = 0
    for root, _, files in os.walk(path):
        for f in files:
            if Path(f).suffix.lower() in SUPPORTED_EXTENSIONS:
                count += 1
    return count


class ImportWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, source_path, dest_path):
        super().__init__()
        self._source = Path(source_path)
        self._dest = Path(dest_path)

    def run(self):
        try:
            files = [
                p for p in self._source.rglob('*')
                if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
            ]
            total = len(files)
            copied = 0
            self._dest.mkdir(parents=True, exist_ok=True)
            for i, src in enumerate(files):
                dst = self._dest / src.name
                counter = 1
                while dst.exists():
                    dst = self._dest / f"{src.stem}_{counter}{src.suffix}"
                    counter += 1
                shutil.copy2(str(src), str(dst))
                copied += 1
                self.progress.emit(i + 1, total, src.name)
            self.finished.emit(copied)
        except Exception as e:
            self.error.emit(str(e))


class ImportDialog(QDialog):
    import_completed = pyqtSignal(str)  # emits dest folder path

    def __init__(self, catalog_root, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Importuj zdjęcia z urządzenia")
        self.resize(560, 480)
        self._catalog_root = Path(catalog_root)
        self._selected_path = None
        self._worker = None
        self._build_ui()
        self._refresh_devices()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Device list
        device_group = QGroupBox("Wykryte urządzenia")
        dg_layout = QVBoxLayout(device_group)

        self._device_list = QListWidget()
        self._device_list.currentItemChanged.connect(self._on_device_selected)
        dg_layout.addWidget(self._device_list)

        btn_row = QHBoxLayout()
        self._refresh_btn = QPushButton("Odśwież")
        self._refresh_btn.clicked.connect(self._refresh_devices)
        self._browse_btn = QPushButton("Wskaż folder ręcznie…")
        self._browse_btn.clicked.connect(self._browse_manual)
        btn_row.addWidget(self._refresh_btn)
        btn_row.addWidget(self._browse_btn)
        dg_layout.addLayout(btn_row)
        layout.addWidget(device_group)

        # Single file import
        single_group = QGroupBox("Import pojedynczego zdjęcia")
        sg_layout = QHBoxLayout(single_group)
        self._single_btn = QPushButton("Wybierz jedno zdjęcie i importuj…")
        self._single_btn.clicked.connect(self._import_single_file)
        sg_layout.addWidget(self._single_btn)
        layout.addWidget(single_group)

        # Selected path info
        self._path_label = QLabel("Wybrane źródło: —")
        self._path_label.setWordWrap(True)
        layout.addWidget(self._path_label)

        self._photo_count_label = QLabel("")
        layout.addWidget(self._photo_count_label)

        # Destination subfolder
        dest_group = QGroupBox("Folder docelowy w katalogu")
        dg2 = QVBoxLayout(dest_group)
        self._dest_label = QLabel()
        self._update_dest_label("Import")
        dg2.addWidget(self._dest_label)
        layout.addWidget(dest_group)

        # Progress
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        self._status_label = QLabel("")
        layout.addWidget(self._status_label)

        # Buttons
        btn_row2 = QHBoxLayout()
        self._import_btn = QPushButton("Importuj zdjęcia")
        self._import_btn.setEnabled(False)
        self._import_btn.clicked.connect(self._start_import)
        self._close_btn = QPushButton("Zamknij")
        self._close_btn.clicked.connect(self.reject)
        btn_row2.addStretch()
        btn_row2.addWidget(self._import_btn)
        btn_row2.addWidget(self._close_btn)
        layout.addLayout(btn_row2)

    def _update_dest_label(self, subfolder):
        dest = self._catalog_root / subfolder
        self._dest_label.setText(str(dest))

    def _refresh_devices(self):
        self._device_list.clear()
        devices = find_removable_devices()
        if not devices:
            item = QListWidgetItem("Nie wykryto żadnych urządzeń")
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            self._device_list.addItem(item)
        for dev in devices:
            label = f"{dev['name']}  [{dev['type']}]\n  {dev['path']}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, dev['path'])
            self._device_list.addItem(item)

    def _on_device_selected(self, item):
        if item is None:
            return
        path = item.data(Qt.UserRole)
        if not path:
            return
        self._selected_path = path
        self._path_label.setText(f"Wybrane źródło: {path}")
        self._photo_count_label.setText("Zliczanie zdjęć…")
        self.repaint()
        count = count_photos(path)
        self._photo_count_label.setText(f"Znalezione zdjęcia: {count}")
        self._import_btn.setEnabled(count > 0)

    def _import_single_file(self):
        ext_list = " ".join(f"*{e} *{e.upper()}" for e in sorted(SUPPORTED_EXTENSIONS))
        path, _ = QFileDialog.getOpenFileName(
            self, "Wybierz zdjęcie do importu", str(Path.home()),
            f"Zdjęcia ({ext_list})"
        )
        if not path:
            return
        src = Path(path)
        dest = self._catalog_root / "Import"
        dest.mkdir(parents=True, exist_ok=True)
        dst = dest / src.name
        counter = 1
        while dst.exists():
            dst = dest / f"{src.stem}_{counter}{src.suffix}"
            counter += 1
        shutil.copy2(str(src), str(dst))
        self._status_label.setText(f"Zaimportowano: {src.name}")
        QMessageBox.information(
            self, "Import zakończony",
            f"Skopiowano zdjęcie:\n{src.name}\n\ndo folderu:\n{dest}"
        )
        self.import_completed.emit(str(dest))

    def _browse_manual(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Wybierz folder źródłowy", str(Path.home())
        )
        if directory:
            self._selected_path = directory
            self._path_label.setText(f"Wybrane źródło: {directory}")
            count = count_photos(directory)
            self._photo_count_label.setText(f"Znalezione zdjęcia: {count}")
            self._import_btn.setEnabled(count > 0)

    def _start_import(self):
        if not self._selected_path:
            return
        dest = self._catalog_root / "Import"
        self._import_btn.setEnabled(False)
        self._refresh_btn.setEnabled(False)
        self._browse_btn.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(0)
        self._status_label.setText("Importowanie…")

        self._worker = ImportWorker(self._selected_path, str(dest))
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, current, total, name):
        self._progress_bar.setMaximum(total)
        self._progress_bar.setValue(current)
        self._status_label.setText(f"Kopiowanie: {name} ({current}/{total})")

    def _on_finished(self, count):
        self._progress_bar.setVisible(False)
        self._status_label.setText(f"Zaimportowano {count} zdjęć.")
        dest = str(self._catalog_root / "Import")
        QMessageBox.information(
            self, "Import zakończony",
            f"Skopiowano {count} zdjęć do:\n{dest}"
        )
        self.import_completed.emit(dest)
        self._close_btn.setText("Zamknij")
        self._import_btn.setEnabled(True)
        self._refresh_btn.setEnabled(True)
        self._browse_btn.setEnabled(True)

    def _on_error(self, msg):
        self._progress_bar.setVisible(False)
        self._status_label.setText(f"Błąd: {msg}")
        QMessageBox.warning(self, "Błąd importu", msg)
        self._import_btn.setEnabled(True)
        self._refresh_btn.setEnabled(True)
        self._browse_btn.setEnabled(True)
