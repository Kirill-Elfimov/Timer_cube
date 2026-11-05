import sys

from PyQt6.QtWidgets import QApplication, QMainWindow
from timer_ui import Ui_Form
from scrambles import scramble_333, scramble_222

disciplines = {
    "3x3": scramble_333,
    "2x2": scramble_222
}

# Наследуемся от виджета из PyQt6.QtWidgets и от класса с интерфейсом
class MyWidget(QMainWindow, Ui_Form):
    def __init__(self):
        super().__init__()
        # Вызываем метод для загрузки интерфейса из класса Ui_MainWindow,
        # остальное без изменений
        self.setupUi(self)

        # Кнопка дл перегенирации
        self.regeneration.clicked.connect(self.generation)

        # Комбобокс с выбором дисциплины
        self.choice_of_discipline.addItems(disciplines.keys())


        # Поле со скрамблом
        self.scramble_output.setEnabled(False)

    def generation(self):
        self.scramble_output.setText(disciplines[self.choice_of_discipline.currentText()]())




if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyWidget()
    ex.show()
    sys.exit(app.exec())