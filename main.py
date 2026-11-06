import sys
from time import monotonic

from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont

from timer_ui import Ui_Form
from scrambles import scramble_333, scramble_222

disciplines = {
    "3x3": scramble_333,
    "2x2": scramble_222
}


class MyWidget(QMainWindow, Ui_Form):
    def __init__(self):
        super().__init__()
        self.setupUi(self)



        # создание секундомера
        self.elapsed_ms = 0
        self.running = False
        self.last_tick = None

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


        # Поле со скрамблом
        self.scramble_output.setEnabled(False)

    def generation(self):
        self.scramble_output.setText(disciplines[self.choice_of_discipline.currentText()]())



    def keyPressEvent(self, event):
        key = event.key()

        # Пробел — старт / стоп (isAutoRepeat защищает от «дребезга»)
        if key == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._toggle_timer()
            event.accept()
            return

        super().keyPressEvent(event)


    def _toggle_timer(self):
        if self.running:
            self.pause()
        else:
            self.start()

    def start(self):
        if self.running:
            return
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







if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyWidget()
    ex.show()
    sys.exit(app.exec())