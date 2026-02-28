from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem


class FolderTree(QTreeWidget):
    week_selected = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("Katalog")
        self.itemClicked.connect(self._on_item_clicked)
        self._year_items = {}

    def populate(self, weeks):
        self.clear()
        self._year_items = {}
        for year, week in sorted(weeks):
            if year not in self._year_items:
                year_item = QTreeWidgetItem(self, [str(year)])
                self._year_items[year] = year_item
            week_item = QTreeWidgetItem(self._year_items[year], [f"Tydzień {week:02d}"])
            week_item.setData(0, 32, (year, week))
        self.expandAll()

    def _on_item_clicked(self, item, column):
        data = item.data(0, 32)
        if data:
            year, week = data
            self.week_selected.emit(year, week)
