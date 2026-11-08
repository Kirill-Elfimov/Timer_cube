import sys
from mimetypes import add_type
from time import monotonic

from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtSql import QSqlDatabase, QSqlQuery, QSqlTableModel

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
        self.model.setEditStrategy(QSqlTableModel.EditStrategy.OnManualSubmit)
        self.model.select()  # ← сначала загрузка
        self.model.setHeaderData(0, Qt.Orientation.Horizontal, "ID")
        self.model.setHeaderData(1, Qt.Orientation.Horizontal, "Время(мс)")



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
        self.timer_output.setFont(QFont("Consolas", 36, QFont.Weight.Bold))


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
            self.timer_output.setStyleSheet("")
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
        self.last_time_id = real_id
        self.last_time_ms = time_ms
        self.last_penalty = 0
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
        self.statusBar().showMessage(
            "Штраф DNF применён" if new_penalty else "Штраф DNF снят", 3000
        )
        print("DNF")




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