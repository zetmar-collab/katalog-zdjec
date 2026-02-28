from datetime import date

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem


def _week_label(year, week):
    """Zwraca etykietę tygodnia z zakresem dat (pon–nd). Oznacza przełom roku."""
    monday = date.fromisocalendar(year, week, 1)
    sunday = date.fromisocalendar(year, week, 7)

    cross_year = monday.year != sunday.year

    if cross_year:
        date_range = f"{monday.strftime('%d.%m.%y')} – {sunday.strftime('%d.%m.%y')}"
        label = f"Tydzień {week:02d}   {date_range}  ⚑"
        tooltip = (
            f"Tydzień na przełomie roku:\n"
            f"{monday.strftime('%d.%m.%Y')} (pon) – {sunday.strftime('%d.%m.%Y')} (nd)"
        )
    else:
        date_range = f"{monday.strftime('%d.%m')} – {sunday.strftime('%d.%m')}"
        label = f"Tydzień {week:02d}   {date_range}"
        tooltip = f"{monday.strftime('%d.%m.%Y')} (pon) – {sunday.strftime('%d.%m.%Y')} (nd)"

    return label, tooltip


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
            label, tooltip = _week_label(year, week)
            week_item = QTreeWidgetItem(self._year_items[year], [label])
            week_item.setToolTip(0, tooltip)
            week_item.setData(0, 32, (year, week))
        self.expandAll()

    def _on_item_clicked(self, item, column):
        data = item.data(0, 32)
        if data:
            year, week = data
            self.week_selected.emit(year, week)
