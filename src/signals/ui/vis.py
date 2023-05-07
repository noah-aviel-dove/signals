import typing

from PyQt5 import (
    QtGui,
    QtWidgets,
)
import matplotlib.pyplot as plt
import matplotlib.animation as plt_ani
import matplotlib.backends.backend_qtagg as plt_qtagg

import signals.map

import signals.ui.theme


class VisCanvas(plt_qtagg.FigureCanvas):
    interval = 30
    # FIXME make block size configurable and this be a multiple of it
    frames_per_interval = 1500

    # Hint for PyCharm since it can't find the base class
    figure: plt.Figure

    def __init__(self, map_: signals.map.Map, at: signals.map.Coordinates):
        fig, self.ax = plt.subplots()
        fig.tight_layout(pad=0)
        super().__init__(fig)
        self.at = at
        self.map = map_
        self.ani = None
        self.is_playing = False

    def setPalette(self, a0: QtGui.QPalette) -> None:
        super().setPalette(a0)
        self.ax.set_facecolor(a0.window().color().name())

    def start_or_stop(self):
        if self.ani is None:
            self.ani = plt_ani.FuncAnimation(self.figure, self._update, interval=self.interval, blit=True)
            self.is_playing = True
        elif self.is_playing:
            self.ani.pause()
            self.is_playing = False
        else:
            self.ani.resume()
            self.is_playing = True

    def _update(self, frame: int):
        try:
            return self.map.render(self.at, self.ax, self.frames_per_interval)
        except signals.map.BadVis as e:
            return [self.ax.text(0, 0, f'Error: {e}', c='red')]


class VisContainer(QtWidgets.QWidget):

    def __init__(self, vis: VisCanvas, parent=None):
        super().__init__(parent=parent)
        layout = QtWidgets.QVBoxLayout()
        button = FreezeButton()
        button.clicked.connect(vis.start_or_stop)
        layout.addWidget(button)
        layout.addWidget(vis)
        self.setLayout(layout)
        signals.ui.theme.register(self)


class VisRack(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)

    def add(self, vis: VisCanvas):
        self.layout().addWidget(VisContainer(vis))


class FreezeButton(QtWidgets.QPushButton):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
        self.setCheckable(True)
        self.setText('Start/Freeze')
