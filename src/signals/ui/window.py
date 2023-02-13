from PyQt5 import (
    QtWidgets,
)

import signals.ui.pane
import signals.ui.theme


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        signals.ui.set_name(self)
        self.setWindowTitle('signals : ' + signals.app().project.name)

        self.setAutoFillBackground(True)
        self.setStyleSheet(f'background-color: {signals.ui.theme.current().back.name()};')

        pane = signals.ui.pane.GraphView(self)
        self.setCentralWidget(pane)
