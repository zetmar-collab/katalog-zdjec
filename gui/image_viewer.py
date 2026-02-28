from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QScrollArea, QSizePolicy, QSplitter, QWidget,
    QMessageBox
)

from core.gps import open_on_map
from core.scanner import read_exif


class ImageViewer(QDialog):
    def __init__(self, photo, all_paths=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(photo.get('filename', 'Przeglądarka zdjęć'))
        self.resize(1000, 700)

        self._all_paths = all_paths or []
        self._current_path = photo.get('path', '')
        self._current_idx = self._find_index(self._current_path)
        self._photo = photo
        self._lat = None
        self._lon = None

        self._build_ui()
        self._load_photo(photo)

    def _find_index(self, path):
        try:
            return self._all_paths.index(path)
        except ValueError:
            return 0

    def _build_ui(self):
        layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Horizontal)

        # Image area
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        scroll = QScrollArea()
        scroll.setWidget(self._image_label)
        scroll.setWidgetResizable(True)
        splitter.addWidget(scroll)

        # Side panel
        side_widget = QWidget()
        side = QVBoxLayout(side_widget)

        self._exif_tree = QTreeWidget()
        self._exif_tree.setHeaderLabels(["Tag", "Wartość"])
        self._exif_tree.setColumnWidth(0, 150)
        side.addWidget(QLabel("Dane EXIF"))
        side.addWidget(self._exif_tree)

        self._map_btn = QPushButton("🗺 Wyszukaj lokalizację")
        self._map_btn.clicked.connect(self._show_on_map)
        side.addWidget(self._map_btn)

        side_widget.setMinimumWidth(250)
        side_widget.setMaximumWidth(350)
        splitter.addWidget(side_widget)
        splitter.setSizes([650, 350])

        layout.addWidget(splitter)

        # Navigation
        nav = QHBoxLayout()
        self._prev_btn = QPushButton("◀ Poprzednie")
        self._prev_btn.clicked.connect(self._go_prev)
        self._next_btn = QPushButton("Następne ▶")
        self._next_btn.clicked.connect(self._go_next)
        nav.addWidget(self._prev_btn)
        nav.addStretch()
        nav.addWidget(self._next_btn)
        layout.addLayout(nav)

        self._update_nav_buttons()

    def _load_photo(self, photo):
        path = photo.get('path', '')
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            screen = self.screen().availableGeometry()
            max_w = int(screen.width() * 0.65)
            max_h = int(screen.height() * 0.85)
            scaled = pixmap.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._image_label.setPixmap(scaled)

        self._load_exif(path, photo)
        self.setWindowTitle(photo.get('filename', 'Przeglądarka zdjęć'))

    def _load_exif(self, path, photo):
        self._exif_tree.clear()
        lat = photo.get('lat')
        lon = photo.get('lon')
        self._map_btn.setEnabled(True)
        self._lat = lat
        self._lon = lon

        basic = [
            ('Nazwa pliku', photo.get('filename', '')),
            ('Data wykonania', photo.get('date_taken', 'Nieznana')),
            ('Rok', str(photo.get('year', ''))),
            ('Tydzień', str(photo.get('week', ''))),
            ('Szerokość geogr.', str(lat) if lat is not None else ''),
            ('Długość geogr.', str(lon) if lon is not None else ''),
        ]
        for tag, val in basic:
            if val:
                QTreeWidgetItem(self._exif_tree, [tag, val])

        try:
            exif_data = read_exif(path)
            for tag, val in sorted(exif_data.get('exif', {}).items()):
                display_val = str(val)
                if len(display_val) > 100:
                    display_val = display_val[:100] + '…'
                QTreeWidgetItem(self._exif_tree, [str(tag), display_val])
        except Exception:
            pass

    def _show_on_map(self):
        if self._lat is not None and self._lon is not None:
            open_on_map(self._lat, self._lon)
        else:
            QMessageBox.information(
                self, "Brak lokalizacji",
                "Brak zapisanej lokalizacji w danych zdjęcia."
            )

    def _go_prev(self):
        if self._current_idx > 0:
            self._current_idx -= 1
            self._navigate_to(self._current_idx)

    def _go_next(self):
        if self._current_idx < len(self._all_paths) - 1:
            self._current_idx += 1
            self._navigate_to(self._current_idx)

    def _navigate_to(self, idx):
        path = self._all_paths[idx]
        photo = {'path': path, 'filename': Path(path).name}
        self._load_photo(photo)
        self._update_nav_buttons()

    def _update_nav_buttons(self):
        self._prev_btn.setEnabled(self._current_idx > 0)
        self._next_btn.setEnabled(self._current_idx < len(self._all_paths) - 1)
