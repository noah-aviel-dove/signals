from PyQt5 import (
    QtCore,
    QtWidgets,
)

import signals.ui.theme
import signals.ui.view


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        signals.ui.set_name(self)
        scene = signals.ui.view.Scene(self)
        view = QtWidgets.QGraphicsView(scene)
        view.setMouseTracking(True)
        self.setCentralWidget(view)
