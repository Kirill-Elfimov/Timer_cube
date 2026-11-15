import sys
from mimetypes import add_type
from time import monotonic
import sqlite3
from contextlib import closing

from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox, QStyledItemDelegate
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtSql import QSqlDatabase, QSqlQuery, QSqlTableModel, QSqlTableModel

from PyQt6.QtWidgets import QColorDialog  # если ещё нет

from timer_ui import Ui_Form
from scrambles import scramble_333, scramble_222

disciplines = {
    "3x3": scramble_333,
    "2x2": scramble_222
}

# Подключение БД
def create_connection():
    db = QSqlDatabase.addDatabase("QSQLITE")

    db.setDatabaseName("my_assemblies")

    # Пытаемся открыть подключение
    if not db.open():
        # Если не получилось — сообщаем пользователю
        QMessageBox.critical(
            None,
            "Ошибка!",
            f"Не удалось подключиться к базе данных!\n"
            f"Ошибка: {db.lastError().text()}\n"
            f"Попробуйте перезагрузить компьютер."
        )
        return False
    return True


# Создание таблицы
def create_tables():
    query = QSqlQuery()

    query.exec("""
        CREATE TABLE IF NOT EXISTS times (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discipline TEXT NOT NULL DEFAULT '3x3',
            time_ms INTEGER NOT NULL,
            penalty INTEGER NOT NULL DEFAULT 0
        )
    """)




class MyWidget(QMainWindow, Ui_Form):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.model = QSqlTableModel(self)
        self.model.setTable("times")
        self.model.setSort(0, Qt.SortOrder.DescendingOrder)
        self.model.setEditStrategy(QSqlTableModel.EditStrategy.OnManualSubmit)
        self.model.select()


        # Твблица с прошлыми сборками

        self.model.setTable("times")  # Указываем таблицу

        # Устанавливаем красивые заголовки столбцов
        # (потому что «id» и «completed» — не самые понятные названия)
        self.model.setHeaderData(0, Qt.Orientation.Horizontal, "ID")
        self.model.setHeaderData(1, Qt.Orientation.Horizontal, "Дисциплина")
        self.model.setHeaderData(2, Qt.Orientation.Horizontal, "Время (мс)")
        self.model.setHeaderData(3, Qt.Orientation.Horizontal, "Штраф")

        # Загружаем данные из базы — без этого вызова таблица будет пустая!
        self.model.select()


        self.tableView_times.setModel(self.model)

        # Немного косметики
        self.tableView_times.resizeColumnsToContents()  # Подгоняем ширину столбцов
        self.tableView_times.setAlternatingRowColors(True)  # Чередуем цвета строк
        self.tableView_times.setItemDelegateForColumn(2, TimeDelegate(self.tableView_times))
        self.tableView_times.setItemDelegateForColumn(3, PenaltyDelegate(self.tableView_times))



        # создание секундомера
        self.elapsed_ms = 0
        self.running = False
        self.last_tick = None
        self.flag = True # Остановлен таймер или нет
        self.last_time_id = None
        self.last_penalty = 0

        self.timer = QTimer(self)
        self.timer.setInterval(10)  # обновление каждые 10 мс
        self.timer.timeout.connect(self._update_time)

        self.timer_output.setText("00:00.00")
        self.timer_output.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_output.setFont(QFont("Consolas", 42, QFont.Weight.Bold))


        # Фокус окна для роботы пробела
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)


        # Кнопка для перегенирации
        self.regeneration.clicked.connect(self.generation)

        # Комбобокс с выбором дисциплины
        self.choice_of_discipline.addItems(disciplines.keys())
        self.generation()
        self.choice_of_discipline.currentTextChanged.connect(self.generation)

        self.delete_button.clicked.connect(self.delete_time)
        self.p2_button.clicked.connect(self.toggle_p2)
        self.dnf_button.clicked.connect(self.toggle_DNF)


        # Поле со скрамблом
        self.scramble_output.setEnabled(False)

        self.ao5_l = None
        self.ao12_l = None
        self.ao100_l = None
        self.ao1000_l = None
        self.general_l = None
        self.best_l = None

        self.sr_ao5()
        self.sr_ao12()
        self.sr_ao100()
        self.sr_ao1000()
        self.sr_general()
        self.sr_best()
        self.change_in_statistics()

        self.bg_color = "#ffffff"
        self.buttons_color = "#f0f0f0"
        self.font_color = "#000000"

        self.apply_background_color(QColor(self.bg_color))
        self.apply_buttons_color(QColor(self.buttons_color))
        self.apply_font_color(QColor(self.font_color))
        self.apply_all_styles()

        self.bg_color_button.clicked.connect(lambda: self.pick_color("background"))
        self.buttons_color_button.clicked.connect(lambda: self.pick_color("buttons"))
        self.font_color_button.clicked.connect(lambda: self.pick_color("font"))

    def generation(self):
        self.scramble_output.setText(disciplines[self.choice_of_discipline.currentText()]())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.timer_output.setStyleSheet("color: green;")
            if self.running:
                self.pause()
                self.flag = False
            event.accept()
            return
        super().keyPressEvent(event)


    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.timer_output.setStyleSheet(f"color: {self.font_color};")
            if not self.running and self.flag:
                self.start()
            self.flag = True
            event.accept()
            return
        super().keyReleaseEvent(event)



    def start(self):
        if self.running:
            return
        self.elapsed_ms = 0
        self.running = True
        self.last_tick = monotonic()
        self.timer.start()


    def pause(self):
        if not self.running:
            return
        self.running = False
        self.timer.stop()
        # Досчитываем «хвост» после последнего тика
        if self.last_tick is not None:
            self.elapsed_ms += int((monotonic() - self.last_tick) * 1000)
            self.last_tick = None
        self._render_time()

        if self.elapsed_ms > 0:
            self.add_time(self.elapsed_ms)


    def _update_time(self):
        now = monotonic()
        if self.last_tick is not None:
            self.elapsed_ms += int((now - self.last_tick) * 1000)
        self.last_tick = now
        self._render_time()

    # Вывод времени на экран
    def _render_time(self):
        ms = self.elapsed_ms
        minutes = ms // 60000
        seconds = (ms % 60000) // 1000
        hundredths = (ms % 1000) // 10
        self.timer_output.setText(f"{minutes:02d}:{seconds:02d}.{hundredths:02d}")




    # Добавление сборки в БД
    def add_time(self, time_ms):
        record = self.model.record()
        record.setValue("discipline", self.choice_of_discipline.currentText())
        record.setValue("time_ms", time_ms)
        record.setValue("penalty", 0)
        if not self.model.insertRecord(-1, record):
            print("insertRecord:", self.model.lastError().text())
            return False
        if not self.model.submitAll():
            print("submitAll:",
                  self.model.lastError().text(),
                  QSqlDatabase.database().lastError().text())
            self.model.revertAll()
            return False
        q = QSqlQuery()
        q.exec("SELECT last_insert_rowid()")
        real_id = int(q.value(0)) if q.next() else None
        print(f"Сборка {time_ms} мс добавлена, id={real_id}")
        self.sr_ao5()
        self.sr_ao12()
        self.sr_ao100()
        self.sr_ao1000()
        self.sr_general()
        self.sr_best()
        self.change_in_statistics()
        self.last_time_id = real_id
        self.last_time_ms = time_ms
        self.last_penalty = 0
        self.model.select()
        return True




    # Удаление сборки из БД
    def delete_time(self):
        if self.last_time_id is None:
            return
        if self.running:
            return

        reply = QMessageBox.question(
            self, "Подтверждение удаления",
            f"Удалить последнюю сборку?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        for row in range(self.model.rowCount()):
            if self.model.data(self.model.index(row, 0)) == self.last_time_id:
                self.model.removeRow(row)
                if self.model.submitAll():
                    self.model.select()
                    print("Сборка удалена", self.last_time_id)
                    self.last_time_id = None
                    self.statusBar().showMessage("Сборка удалена", 3000)
                    self.sr_ao5()
                    self.sr_ao12()
                    self.sr_ao100()
                    self.sr_ao1000()
                    self.sr_general()
                    self.sr_best()
                    self.change_in_statistics()
                else:
                    self.model.revertAll()
                return
        self.last_time_id = None
        self.last_time_ms = None
        self.last_penalty = 0



    def toggle_p2(self):
        if self.last_time_id is None:
            return
        if self.running:
            return
        if self.last_penalty == 2000:
            new_penalty = 0
        else:
            new_penalty = 2000

        q = QSqlQuery()
        q.prepare("UPDATE times SET penalty = ? WHERE id = ?")
        q.addBindValue(new_penalty)
        q.addBindValue(self.last_time_id)
        if not q.exec():
            return

        self.last_penalty = new_penalty
        self.model.select()
        self.sr_ao5()
        self.sr_ao12()
        self.sr_ao100()
        self.sr_ao1000()
        self.sr_general()
        self.sr_best()
        self.change_in_statistics()
        self.statusBar().showMessage(
            "Штраф +2 применён" if new_penalty else "Штраф +2 снят", 3000
        )
        print("+2")


    def toggle_DNF(self):
        if self.last_time_id is None:
            return
        if self.running:
            return
        if self.last_penalty == -1:
            new_penalty = 0
        else:
            new_penalty = -1

        q = QSqlQuery()
        q.prepare("UPDATE times SET penalty = ? WHERE id = ?")
        q.addBindValue(new_penalty)
        q.addBindValue(self.last_time_id)
        if not q.exec():
            return

        self.last_penalty = new_penalty
        self.model.select()
        self.sr_ao5()
        self.sr_ao12()
        self.sr_ao100()
        self.sr_ao1000()
        self.sr_general()
        self.sr_best()
        self.change_in_statistics()
        self.statusBar().showMessage(
            "Штраф DNF применён" if new_penalty else "Штраф DNF снят", 3000
        )
        print("DNF")

    def sr_best(self):
        discipline = self.choice_of_discipline.currentText()

        sql = ("SELECT time_ms, penalty FROM times "
               "WHERE discipline = ? AND penalty != -1 "
               "ORDER BY time_ms + penalty ASC LIMIT 1")
        params = (discipline,)

        try:
            with closing(sqlite3.connect("my_assemblies")) as con:
                con.row_factory = sqlite3.Row
                rows = con.execute(sql, params).fetchall()

            if len(rows) == 0:
                self.best_l = None
                return

            best_ms = rows[0]["time_ms"] + rows[0]["penalty"]
            self.best_l = round(best_ms / 1000, 2)
            print(f"Лучшее ({discipline}) = {self.best_l} с")
        except sqlite3.Error as e:
            print("SQLite error:", e)



    def sr_ao5(self):
        discipline = self.choice_of_discipline.currentText()


        sql = ("SELECT time_ms, penalty FROM times "
                "WHERE discipline = ? AND penalty != -1 "
                "ORDER BY id DESC LIMIT 5")
        params = (discipline,)

        try:
            with closing(sqlite3.connect("my_assemblies")) as con:
                con.row_factory = sqlite3.Row
                rows = con.execute(sql, params).fetchall()

            if len(rows) < 5:
                print(f"Для ao5 нужно 5 сборок, есть {len(rows)}")
                self.ao5_l = None
                return

            totals = sorted(r["time_ms"] + r["penalty"] for r in rows)
            ao5_ms = sum(totals[1:-1]) / 3
            self.ao5_l = round(ao5_ms / 1000, 2)
            print(f"ao5 ({discipline}) = {self.ao5_l} с")
        except sqlite3.Error as e:
            print("SQLite error:", e)



    def sr_ao12(self):
        discipline = self.choice_of_discipline.currentText()


        sql = ("SELECT time_ms, penalty FROM times "
                "WHERE discipline = ? AND penalty != -1 "
                "ORDER BY id DESC LIMIT 12")
        params = (discipline,)

        try:
            with closing(sqlite3.connect("my_assemblies")) as con:
                con.row_factory = sqlite3.Row
                rows = con.execute(sql, params).fetchall()

            if len(rows) < 12:
                print(f"Для ao12 нужно 12 сборок, есть {len(rows)}")
                self.ao12_l = None
                return

            totals = sorted(r["time_ms"] + r["penalty"] for r in rows)
            ao12_ms = sum(totals[1:-1]) / 10
            self.ao12_l = round(ao12_ms / 1000, 2)
            print(f"ao12 ({discipline}) = {self.ao12_l} с")

        except sqlite3.Error as e:
            print("SQLite error:", e)



    def sr_ao100(self):
        discipline = self.choice_of_discipline.currentText()


        sql = ("SELECT time_ms, penalty FROM times "
                "WHERE discipline = ? AND penalty != -1 "
                "ORDER BY id DESC LIMIT 100")
        params = (discipline,)

        try:
            with closing(sqlite3.connect("my_assemblies")) as con:
                con.row_factory = sqlite3.Row
                rows = con.execute(sql, params).fetchall()

            if len(rows) < 100:
                print(f"Для ao100 нужно 100 сборок, есть {len(rows)}")
                self.ao100_l = None
                return

            totals = sorted(r["time_ms"] + r["penalty"] for r in rows)
            ao100_ms = sum(totals[1:-1]) / 90
            self.ao100_l = round(ao100_ms / 1000, 2)
            print(f"ao100 ({discipline}) = {self.ao100_l} с")

        except sqlite3.Error as e:
            print("SQLite error:", e)



    def sr_ao1000(self):
        discipline = self.choice_of_discipline.currentText()


        sql = ("SELECT time_ms, penalty FROM times "
                "WHERE discipline = ? AND penalty != -1 "
                "ORDER BY id DESC LIMIT 1000")
        params = (discipline,)

        try:
            with closing(sqlite3.connect("my_assemblies")) as con:
                con.row_factory = sqlite3.Row
                rows = con.execute(sql, params).fetchall()

            if len(rows) < 1000:
                print(f"Для ao1000 нужно 1000 сборок, есть {len(rows)}")
                self.ao1000_l = None
                return

            totals = sorted(r["time_ms"] + r["penalty"] for r in rows)
            ao1000_ms = sum(totals[1:-1]) / 950
            self.ao1000_l = round(ao1000_ms / 1000, 2)
            print(f"ao1000 ({discipline}) = {self.ao1000_l} с")

        except sqlite3.Error as e:
            print("SQLite error:", e)


    def sr_general(self):
        discipline = self.choice_of_discipline.currentText()


        sql = ("SELECT time_ms, penalty FROM times "
                "WHERE discipline = ? AND penalty != -1 ")
        params = (discipline,)

        try:
            with closing(sqlite3.connect("my_assemblies")) as con:
                con.row_factory = sqlite3.Row
                rows = con.execute(sql, params).fetchall()

            if len(rows) < 1:
                self.general_l = None
                return

            totals = sorted(r["time_ms"] + r["penalty"] for r in rows)
            general_ms = sum(totals[1:-1]) / len(totals[1:-1])
            self.general_l = round(general_ms / 1000, 2)
            print(f"Среднее ({discipline}) = {self.general_l} с")
        except sqlite3.Error as e:
            print("SQLite error:", e)


    def change_in_statistics(self):
        self.statistics_label.setText(f"Лучшее = {self.best_l}\nao5 = {self.ao5_l}\nao12 = {self.ao12_l}\nao100 = {self.ao100_l}")
        self.statistics_label.setFont(QFont("Consolas", 18, QFont.Weight.Bold))
        self.statistics_label_2.setText(f"Лучшее = {self.best_l}\nao5 = {self.ao5_l}\nao12 = {self.ao12_l}\nao100 = {self.ao100_l}\n"
                                        f"ao1000 = {self.ao1000_l}\nСреднее = {self.general_l}")
        self.statistics_label_2.setFont(QFont("Consolas", 18, QFont.Weight.Bold))



    def pick_color(self, target):
        color = QColorDialog.getColor()
        if not color.isValid():
            return

        if target == "background":
            self.apply_background_color(color)
        elif target == "buttons":
            self.apply_buttons_color(color)
        elif target == "font":
            self.apply_font_color(color)

    def apply_background_color(self, color):
        self.bg_color = color.name()
        self.apply_all_styles()
        print(f"Фон: {self.bg_color}")

    def apply_buttons_color(self, color):
        self.buttons_color = color.name()
        self.apply_all_styles()
        print(f"Кнопки: {self.buttons_color}")

    def apply_font_color(self, color):
        self.font_color = color.name()
        self.apply_all_styles()
        print(f"Шрифт: {self.font_color}")

    def apply_all_styles(self):
        bg = self.bg_color
        btn = self.buttons_color
        fnt = self.font_color

        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {bg}; }}
            QTabWidget::pane {{ background-color: {bg}; border: none; }}
            QTabWidget > QWidget {{ background-color: {bg}; }}
            QTabBar::tab {{ background-color: {bg}; padding: 6px 12px; }}
            QTabBar::tab:selected {{ background-color: {bg}; font-weight: bold; }}
            QPushButton {{ background-color: {btn}; }}
            QTableView {{
    background-color: {bg};
    alternate-background-color: {bg};
    gridline-color: {bg};
    color: {fnt};
    selection-background-color: {bg};
    selection-color: {fnt};
}}
QHeaderView::section {{
    background-color: {bg};
    color: {fnt};
    border: 1px solid {bg};
    padding: 4px;
}}
QTableView::item {{
    background-color: {bg};
}}
        """)

        self.timer_output.setStyleSheet(f"color: {fnt};")
        self.statistics_label.setStyleSheet(f"color: {fnt};")
        self.statistics_label_2.setStyleSheet(f"color: {fnt};")
        self.scramble_output.setStyleSheet(f"color: {fnt};")



class TimeDelegate(QStyledItemDelegate):
    def displayText(self, value, locale):
        try:
            ms = int(value)
        except (TypeError, ValueError):
            return super().displayText(value, locale)
        minutes = ms // 60000
        seconds = (ms % 60000) // 1000
        hundredths = (ms % 1000) // 10
        return f"{minutes:02d}:{seconds:02d}.{hundredths:02d}"

class PenaltyDelegate(QStyledItemDelegate):
    def displayText(self, value, locale):
        try:
            pen = int(value)
        except (TypeError, ValueError):
            return super().displayText(value, locale)
        if pen == 2000:
            return "+2"
        elif pen == -1:
            return "DNF"





if __name__ == '__main__':
    app = QApplication(sys.argv)
    if not create_connection():
        sys.exit(1)
    create_tables()
    print("Подключение установлено! 🎉")
    print(f"Имя базы: {QSqlDatabase.database().databaseName()}")
    print(f"Драйвер: {QSqlDatabase.database().driver()}")
    ex = MyWidget()
    ex.show()
    sys.exit(app.exec())