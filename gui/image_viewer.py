import io
from pathlib import Path

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QTransform
from PyQt5.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QScrollArea, QSizePolicy, QSplitter, QWidget,
    QMessageBox
)

from core.gps import open_on_map
from core.scanner import read_exif, RAW_EXTENSIONS, _extract_embedded_jpeg


def _load_pixmap(path):
    """Load a pixmap from any supported format including RAW files."""
    ext = Path(path).suffix.lower()

    # Standard formats: try QPixmap directly
    if ext not in RAW_EXTENSIONS:
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            return pixmap

    # RAW or fallback: try embedded JPEG first
    try:
        jpeg_data = _extract_embedded_jpeg(path)
        if jpeg_data:
            img = QImage()
            img.loadFromData(jpeg_data)
            if not img.isNull():
                return QPixmap.fromImage(img)
    except Exception:
        pass

    # Last resort: Pillow (handles DNG/TIFF-based RAW and more)
    try:
        from PIL import Image
        with Image.open(path) as img:
            img = img.convert('RGB')
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=85)
        qimg = QImage()
        qimg.loadFromData(buf.getvalue())
        if not qimg.isNull():
            return QPixmap.fromImage(qimg)
    except Exception:
        pass

    return None


class ImageViewer(QDialog):
    photo_deleted = pyqtSignal(str)       # path of deleted photo
    rotation_changed = pyqtSignal(str, int)  # path, new rotation

    def __init__(self, photo, all_paths=None, db_conn=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(photo.get('filename', 'Przeglądarka zdjęć'))
        self.resize(1000, 700)

        self._all_paths = all_paths or []
        self._current_path = photo.get('path', '')
        self._current_idx = self._find_index(self._current_path)
        self._photo = photo
        self._lat = None
        self._lon = None
        self._db_conn = db_conn
        self._rotation = 0
        self._base_pixmap = None

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

        # Navigation + rotate + delete
        nav = QHBoxLayout()
        self._prev_btn = QPushButton("◀ Poprzednie")
        self._prev_btn.clicked.connect(self._go_prev)
        self._next_btn = QPushButton("Następne ▶")
        self._next_btn.clicked.connect(self._go_next)
        self._rotate_left_btn = QPushButton("↺ Obróć lewo")
        self._rotate_left_btn.clicked.connect(self._rotate_left)
        self._rotate_right_btn = QPushButton("↻ Obróć prawo")
        self._rotate_right_btn.clicked.connect(self._rotate_right)
        self._delete_btn = QPushButton("🗑 Usuń zdjęcie…")
        self._delete_btn.clicked.connect(self._delete_current)

        nav.addWidget(self._prev_btn)
        nav.addStretch()
        nav.addWidget(self._rotate_left_btn)
        nav.addWidget(self._rotate_right_btn)
        nav.addStretch()
        nav.addWidget(self._delete_btn)
        nav.addStretch()
        nav.addWidget(self._next_btn)
        layout.addLayout(nav)

        self._update_nav_buttons()

    def _load_photo(self, photo):
        path = photo.get('path', '')
        self._rotation = int(photo.get('rotation') or 0)
        self._base_pixmap = _load_pixmap(path)
        self._display_photo()
        self._load_exif(path, photo)
        self.setWindowTitle(photo.get('filename', 'Przeglądarka zdjęć'))

    def _display_photo(self):
        if not self._base_pixmap:
            self._image_label.setText("Nie można załadować zdjęcia")
            return
        pixmap = self._base_pixmap
        if self._rotation:
            transform = QTransform().rotate(self._rotation)
            pixmap = pixmap.transformed(transform, Qt.SmoothTransformation)
        screen = self.screen().availableGeometry()
        max_w = int(screen.width() * 0.65)
        max_h = int(screen.height() * 0.85)
        scaled = pixmap.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._image_label.setPixmap(scaled)

    def _rotate_left(self):
        self._rotation = (self._rotation - 90) % 360
        self._display_photo()
        self._save_rotation()

    def _rotate_right(self):
        self._rotation = (self._rotation + 90) % 360
        self._display_photo()
        self._save_rotation()

    def _save_rotation(self):
        path = self._all_paths[self._current_idx] if self._all_paths else self._current_path
        if self._db_conn:
            from core.database import update_rotation
            update_rotation(self._db_conn, path, self._rotation)
        self.rotation_changed.emit(path, self._rotation)

    def _load_exif(self, path, photo):
        self._exif_tree.clear()

        try:
            exif_data = read_exif(path)
        except Exception:
            exif_data = {'lat': None, 'lon': None, 'exif': {}, 'date_taken': None}

        lat = photo.get('lat') if photo.get('lat') is not None else exif_data.get('lat')
        lon = photo.get('lon') if photo.get('lon') is not None else exif_data.get('lon')

        date_taken = photo.get('date_taken')
        if not date_taken:
            dt = exif_data.get('date_taken')
            date_taken = dt.strftime('%Y-%m-%d %H:%M:%S') if dt else 'Nieznana'

        self._lat = lat
        self._lon = lon

        basic = [
            ('Nazwa pliku', photo.get('filename', Path(path).name)),
            ('Data wykonania', date_taken),
            ('Rok', str(photo.get('year', ''))),
            ('Tydzień', str(photo.get('week', ''))),
            ('Obrót', f"{self._rotation}°"),
            ('Szerokość geogr.', f"{lat:.6f}" if lat is not None else ''),
            ('Długość geogr.', f"{lon:.6f}" if lon is not None else ''),
        ]
        for tag, val in basic:
            if val:
                QTreeWidgetItem(self._exif_tree, [tag, val])

        for tag, val in sorted(exif_data.get('exif', {}).items(), key=lambda x: str(x[0])):
            display_val = str(val)
            if len(display_val) > 100:
                display_val = display_val[:100] + '…'
            QTreeWidgetItem(self._exif_tree, [str(tag), display_val])

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
        if self._db_conn:
            from core.database import get_photo_by_path
            db_photo = get_photo_by_path(self._db_conn, path)
            if db_photo:
                photo = db_photo
        self._load_photo(photo)
        self._update_nav_buttons()

    def _delete_current(self):
        path = self._all_paths[self._current_idx] if self._all_paths else self._current_path
        fname = Path(path).name
        reply = QMessageBox.question(
            self, "Usuń zdjęcie",
            f"Na pewno usunąć zdjęcie?\n\n{fname}\n\nPlik zostanie trwale usunięty z dysku.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        self.photo_deleted.emit(path)
        self._all_paths.pop(self._current_idx)
        if not self._all_paths:
            self.accept()
            return
        if self._current_idx >= len(self._all_paths):
            self._current_idx = len(self._all_paths) - 1
        self._navigate_to(self._current_idx)

    def _update_nav_buttons(self):
        self._prev_btn.setEnabled(self._current_idx > 0)
        self._next_btn.setEnabled(self._current_idx < len(self._all_paths) - 1)
