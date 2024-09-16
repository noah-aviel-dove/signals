from PyQt5 import (
    QtCore,
    QtGui,
    QtWidgets,
)


class StateSlider(QtWidgets.QWidget):
    scale = 10e6

    update = QtCore.pyqtSignal(bool, float)

    def __init__(self,
                 state_field: str,
                 min_: float = 0.0,
                 max_: float = 1.0,
                 val: float = 0.0,
                 parent=None):
        super().__init__(parent=parent)
        self.state_field = state_field
        self.max = QtWidgets.QLineEdit()
        self.min = QtWidgets.QLineEdit()
        self.val = QtWidgets.QLineEdit()
        self.slider = QtWidgets.QSlider()

        self.slider.setOrientation(QtCore.Qt.Orientation.Vertical)
        self.slider.setTickPosition(QtWidgets.QSlider.NoTicks)
        self.slider.setTracking(True)

        self.max.setValidator(QtGui.QDoubleValidator())
        self.val.setValidator(QtGui.QDoubleValidator())
        self.min.setValidator(QtGui.QDoubleValidator())

        self.slider.valueChanged.connect(self.value_slid)
        self.val.textEdited.connect(self.value_set)

        # FIXME connect signals from min and max

        self.max.setText(str(max_))
        self.val.setText(str(min_))
        self.min.setText(str(val))

        layout = QtWidgets.QGridLayout()

        layout.addWidget(self.max, column=1, row=1)
        layout.addWidget(self.val, column=1, row=2)
        layout.addWidget(self.min, column=1, row=3)
        layout.addWidget(self.slider, column=2, row=1, rowSpan=3)

        self.setLayout(layout)

    @property
    def fmin(self) -> float:
        return float(self.min.text())

    @property
    def fmax(self) -> float:
        return float(self.max.text())

    def _scale(self, slider_val: int) -> float:
        return slider_val * (self.fmax - self.fmin) / self.scale + self.fmin

    def _iscale(self, input_val: float) -> int:
        return round((input_val - self.fmin) * self.scale / (self.fmax - self.fmin))

    def value_set(self, value: str) -> None:
        value = float(value)
        self.slider.setValue(self._iscale(value))
        self.update.emit(False, value)

    def value_slid(self, value: int) -> None:
        value = self._scale(value)
        self.val.setText(str(value))
        self.update.emit(True, value)
