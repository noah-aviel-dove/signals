# https://python-sounddevice.readthedocs.io/en/0.4.6/examples.html#plot-microphone-signal-s-in-real-time
import sys

from PyQt5 import (
    QtWidgets,
)
import matplotlib.animation as plt_ani
import matplotlib.backends.backend_qtagg as plt_qtagg
import matplotlib.pyplot as plt
import numpy as np

import signals.chain.dev
import signals.chain.discovery
import signals.chain.fixed
import signals.chain.osc
import signals.chain.vis


def setup_audio() -> signals.chain.vis.Vis:
    rack = signals.chain.discovery.Rack()
    rack.scan()

    hertz = signals.chain.fixed.Fixed()
    hertz.state.value = np.array([[330]])
    sound = signals.chain.osc.Sine()
    sound.hertz = hertz
    vis = signals.chain.vis.Wave()
    vis.input = sound
    sink = signals.chain.dev.SinkDevice(rack.get_sink('default'))
    sink.input = vis
    sink._stream.start()
    return vis


def setup_ani():
    vis = setup_audio()
    fig, ax = plt.subplots()
    fig.tight_layout(pad=0)
    interval = 30
    frames_per_cycle = 4608

    def _update(frame):
        return vis.render(ax, frames_per_cycle)

    canvas = plt_qtagg.FigureCanvas(fig)
    ani = plt_ani.FuncAnimation(fig,
                                _update,
                                interval=interval,
                                blit=True)

    return canvas, ani


class Container(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        layout = QtWidgets.QHBoxLayout()
        canvas, self.ani = setup_ani()
        layout.addWidget(canvas)
        self.setLayout(layout)


class Window(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.setCentralWidget(Container())


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec_())
