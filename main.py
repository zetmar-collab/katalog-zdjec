import logging
import os
import sys

os.environ.setdefault('QT_LOGGING_RULES', 'qt.qpa.wayland=false')
logging.getLogger('exifread').setLevel(logging.CRITICAL)

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from gui.main_window import MainWindow


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Katalog Zdjęć")
    app.setOrganizationName("PhotoCatalog")

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
