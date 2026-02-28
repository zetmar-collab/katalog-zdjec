from pathlib import Path

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt5.QtWidgets import (
    QMainWindow, QSplitter, QWidget, QVBoxLayout, QPushButton,
    QFileDialog, QStatusBar, QAction, QMessageBox,
    QProgressBar, QLabel, QActionGroup
)

from core.database import init_db, get_all_weeks, get_photos_by_week, upsert_photo, get_photo_by_path
from core.scanner import scan_directory
from core.organizer import organize_photos
from gui.folder_tree import FolderTree
from gui.thumbnail_grid import ThumbnailGrid
from gui.image_viewer import ImageViewer
from gui.themes import apply_dark_theme, apply_light_theme


class ScanWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, root, db_path):
        super().__init__()
        self._root = root
        self._db_path = db_path

    def run(self):
        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            init_db(self._db_path)

            def callback(current, total, name):
                self.progress.emit(current, total, name)

            for photo in scan_directory(self._root, callback):
                upsert_photo(conn, photo)

            conn.close()
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Katalog Zdjęć")
        self.resize(1100, 700)

        self._settings = QSettings("PhotoCatalog", "PhotoCatalog")
        self._db_conn = None
        self._db_path = None
        self._catalog_root = None
        self._scan_worker = None

        self._build_ui()
        self._build_menu()
        self._apply_saved_theme()
        self._restore_or_prompt()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        # Left panel
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)

        self._folder_tree = FolderTree()
        self._folder_tree.week_selected.connect(self._on_week_selected)
        left_layout.addWidget(self._folder_tree)

        self._organize_btn = QPushButton("Porządkuj zdjęcia")
        self._organize_btn.clicked.connect(self._organize_photos)
        self._organize_btn.setEnabled(False)
        left_layout.addWidget(self._organize_btn)

        left.setMinimumWidth(180)
        left.setMaximumWidth(280)
        splitter.addWidget(left)

        # Right panel
        self._thumb_grid = ThumbnailGrid()
        self._thumb_grid.photo_selected.connect(self._open_viewer)
        splitter.addWidget(self._thumb_grid)

        splitter.setSizes([220, 880])
        root_layout.addWidget(splitter)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximumWidth(200)
        self._progress_bar.setVisible(False)
        self._status_bar.addPermanentWidget(self._progress_bar)
        self._status_label = QLabel("Gotowy")
        self._status_bar.addWidget(self._status_label)

    def _build_menu(self):
        menubar = self.menuBar()

        # --- Plik ---
        file_menu = menubar.addMenu("Plik")

        open_action = QAction("Otwórz katalog…", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_catalog_dir)
        file_menu.addAction(open_action)

        rescan_action = QAction("Skanuj ponownie", self)
        rescan_action.setShortcut("F5")
        rescan_action.triggered.connect(self._start_scan)
        file_menu.addAction(rescan_action)

        file_menu.addSeparator()

        import_action = QAction("Importuj z urządzenia…", self)
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self._open_import_dialog)
        file_menu.addAction(import_action)

        import_single_action = QAction("Importuj pojedyncze zdjęcie…", self)
        import_single_action.setShortcut("Ctrl+Shift+I")
        import_single_action.triggered.connect(self._import_single_photo)
        file_menu.addAction(import_single_action)

        file_menu.addSeparator()

        quit_action = QAction("Zakończ", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # --- Widok ---
        view_menu = menubar.addMenu("Widok")

        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)

        self._light_action = QAction("Jasny interfejs", self, checkable=True)
        self._dark_action = QAction("Ciemny interfejs", self, checkable=True)
        theme_group.addAction(self._light_action)
        theme_group.addAction(self._dark_action)
        self._light_action.triggered.connect(lambda: self._set_theme('light'))
        self._dark_action.triggered.connect(lambda: self._set_theme('dark'))
        view_menu.addAction(self._light_action)
        view_menu.addAction(self._dark_action)

        # --- Pomoc ---
        help_menu = menubar.addMenu("Pomoc")
        about_action = QAction("O aplikacji", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _apply_saved_theme(self):
        theme = self._settings.value("theme", "light")
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if theme == 'dark':
            apply_dark_theme(app)
            self._dark_action.setChecked(True)
        else:
            apply_light_theme(app)
            self._light_action.setChecked(True)

    def _set_theme(self, theme):
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if theme == 'dark':
            apply_dark_theme(app)
        else:
            apply_light_theme(app)
        self._settings.setValue("theme", theme)

    def _restore_or_prompt(self):
        last = self._settings.value("catalog_root", "")
        if last and Path(last).is_dir():
            self._open_catalog(last)
        else:
            self._open_catalog_dir()

    def _open_catalog_dir(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Wybierz folder katalogu", str(Path.home())
        )
        if directory:
            self._open_catalog(directory)

    def _open_catalog(self, directory):
        self._catalog_root = Path(directory)
        self._db_path = str(self._catalog_root / ".photo_catalog.db")
        self._settings.setValue("catalog_root", directory)

        self._db_conn = init_db(self._db_path)
        self.setWindowTitle(f"Katalog Zdjęć — {directory}")
        self._refresh_tree()
        self._start_scan()

    def _start_scan(self):
        if not self._catalog_root:
            return
        if self._scan_worker and self._scan_worker.isRunning():
            return

        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(0)
        self._status_label.setText("Skanowanie…")
        self._organize_btn.setEnabled(False)

        self._scan_worker = ScanWorker(str(self._catalog_root), self._db_path)
        self._scan_worker.progress.connect(self._on_scan_progress)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.error.connect(self._on_scan_error)
        self._scan_worker.start()

    def _on_scan_progress(self, current, total, name):
        if total > 0:
            self._progress_bar.setMaximum(total)
            self._progress_bar.setValue(current)
        self._status_label.setText(f"Skanowanie: {name} ({current}/{total})")

    def _on_scan_finished(self):
        self._progress_bar.setVisible(False)
        self._status_label.setText("Skanowanie zakończone")
        self._db_conn = init_db(self._db_path)
        self._refresh_tree()
        self._organize_btn.setEnabled(True)

    def _on_scan_error(self, msg):
        self._progress_bar.setVisible(False)
        self._status_label.setText(f"Błąd skanowania: {msg}")
        QMessageBox.warning(self, "Błąd skanowania", msg)

    def _refresh_tree(self):
        if self._db_conn:
            weeks = get_all_weeks(self._db_conn)
            self._folder_tree.populate(weeks)

    def _on_week_selected(self, year, week):
        if self._db_conn:
            photos = get_photos_by_week(self._db_conn, year, week)
            self._thumb_grid.load_week(photos)
            self._status_label.setText(f"{year} / Tydzień {week:02d} — {len(photos)} zdjęć")

    def _open_viewer(self, path):
        if not self._db_conn:
            return
        photo = get_photo_by_path(self._db_conn, path)
        if not photo:
            photo = {'path': path, 'filename': Path(path).name}
        all_paths = self._thumb_grid.get_all_paths()
        viewer = ImageViewer(photo, all_paths, self)
        viewer.exec_()

    def _organize_photos(self):
        if not self._catalog_root or not self._db_conn:
            return
        reply = QMessageBox.question(
            self, "Porządkowanie zdjęć",
            "Skopiować zdjęcia do podfolderów RRRR/Tydzień-nn?\n"
            "(Oryginały pozostają bez zmian)",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                moves = organize_photos(str(self._catalog_root), self._db_conn, mode='copy')
                QMessageBox.information(
                    self, "Gotowe",
                    f"Posegregowano {len(moves)} zdjęć do folderów rok/tydzień."
                )
            except Exception as e:
                QMessageBox.warning(self, "Błąd", str(e))

    def _open_import_dialog(self):
        if not self._catalog_root:
            QMessageBox.information(
                self, "Brak katalogu",
                "Najpierw otwórz lub wybierz folder katalogu."
            )
            return
        from gui.import_dialog import ImportDialog
        dlg = ImportDialog(str(self._catalog_root), self)
        dlg.import_completed.connect(self._on_import_completed)
        dlg.exec_()

    def _import_single_photo(self):
        if not self._catalog_root:
            QMessageBox.information(
                self, "Brak katalogu",
                "Najpierw otwórz lub wybierz folder katalogu."
            )
            return
        from core.scanner import SUPPORTED_EXTENSIONS
        import shutil
        from pathlib import Path as _Path
        ext_list = " ".join(f"*{e} *{e.upper()}" for e in sorted(SUPPORTED_EXTENSIONS))
        path, _ = QFileDialog.getOpenFileName(
            self, "Wybierz zdjęcie do importu", str(Path.home()),
            f"Zdjęcia ({ext_list})"
        )
        if not path:
            return
        src = _Path(path)
        dest = self._catalog_root / "Import"
        dest.mkdir(parents=True, exist_ok=True)
        dst = dest / src.name
        counter = 1
        while dst.exists():
            dst = dest / f"{src.stem}_{counter}{src.suffix}"
            counter += 1
        shutil.copy2(str(src), str(dst))
        self._status_label.setText(f"Zaimportowano: {src.name}. Skanowanie…")
        self._start_scan()

    def _on_import_completed(self, dest_folder):
        self._status_label.setText("Import zakończony. Skanowanie…")
        self._start_scan()

    def _show_about(self):
        QMessageBox.about(
            self, "O aplikacji — Katalog Zdjęć",
            "<b>Katalog Zdjęć</b><br><br>"
            "Autor: <b>Marek Zettel</b><br>"
            "<a href='https://zetmar.net.pl'>https://zetmar.net.pl</a><br><br>"
            "Automatycznie sortuje zdjęcia do folderów RRRR/Tydzień-nn<br>"
            "na podstawie danych EXIF.<br><br>"
            "Współrzędne GPS otwierane są w OpenStreetMap.<br>"
            "Import zdjęć z aparatu, telefonu, USB i kart SD."
        )

    def closeEvent(self, event):
        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.quit()
            self._scan_worker.wait(2000)
        if self._db_conn:
            self._db_conn.close()
        super().closeEvent(event)
