from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QPixmap, QImage, QTransform
from PyQt5.QtWidgets import (
    QListWidget, QListWidgetItem, QAbstractItemView, QMenu, QAction
)

from core.gps import open_on_map

THUMB_SIZE = 150


def _blob_to_pixmap(blob):
    if not blob:
        return None
    img = QImage()
    img.loadFromData(blob)
    return QPixmap.fromImage(img)


class ThumbnailGrid(QListWidget):
    photo_selected = pyqtSignal(str)
    photo_delete_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.IconMode)
        self.setIconSize(QSize(THUMB_SIZE, THUMB_SIZE))
        self.setGridSize(QSize(THUMB_SIZE + 20, THUMB_SIZE + 30))
        self.setResizeMode(QListWidget.Adjust)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.itemDoubleClicked.connect(self._on_double_click)
        self._photos = []
        self._sort_field = 'date_taken'   # 'date_taken' | 'filename'
        self._sort_asc = True

    def load_week(self, photos):
        self._photos = list(photos)
        self._apply_sort()

    def set_sort(self, field, ascending):
        self._sort_field = field
        self._sort_asc = ascending
        self._apply_sort()

    def _apply_sort(self):
        def key(p):
            val = p.get(self._sort_field) or ''
            return val.lower() if isinstance(val, str) else val

        self._photos.sort(key=key, reverse=not self._sort_asc)
        self.clear()
        for photo in self._photos:
            item = QListWidgetItem(photo.get('filename', ''))
            pixmap = _blob_to_pixmap(photo.get('thumbnail_blob'))
            if pixmap:
                rotation = int(photo.get('rotation') or 0)
                if rotation:
                    transform = QTransform().rotate(rotation)
                    pixmap = pixmap.transformed(transform, Qt.SmoothTransformation)
                item.setIcon(QIcon(pixmap))
            item.setData(Qt.UserRole, photo)
            item.setToolTip(photo.get('filename', ''))
            self.addItem(item)

    def _current_photo(self, pos=None):
        if pos is not None:
            item = self.itemAt(pos)
        else:
            items = self.selectedItems()
            item = items[0] if items else None
        return item.data(Qt.UserRole) if item else None

    def _on_double_click(self, item):
        photo = item.data(Qt.UserRole)
        if photo:
            self.photo_selected.emit(photo['path'])

    def _show_context_menu(self, pos):
        photo = self._current_photo(pos)
        if not photo:
            return

        menu = QMenu(self)

        open_action = QAction("Otwórz", self)
        open_action.triggered.connect(lambda: self.photo_selected.emit(photo['path']))
        menu.addAction(open_action)

        map_action = QAction("Pokaż na mapie", self)
        has_gps = photo.get('lat') is not None and photo.get('lon') is not None
        map_action.setEnabled(has_gps)
        if has_gps:
            map_action.triggered.connect(lambda: open_on_map(photo['lat'], photo['lon']))
        menu.addAction(map_action)

        exif_action = QAction("Pokaż EXIF", self)
        exif_action.triggered.connect(lambda: self.photo_selected.emit(photo['path']))
        menu.addAction(exif_action)

        menu.addSeparator()
        delete_action = QAction("Usuń zdjęcie…", self)
        delete_action.triggered.connect(lambda: self.photo_delete_requested.emit(photo['path']))
        menu.addAction(delete_action)

        menu.exec_(self.mapToGlobal(pos))

    def get_all_paths(self):
        return [p['path'] for p in self._photos]
