import abc
import typing

from PyQt5 import (
    QtCore,
    QtGui,
    QtWidgets,
)
import attr

import signals.map
import signals.map.control
import signals.map.control

T = typing.TypeVar('T')


@attr.s(auto_attribs=True, frozen=True, kw_only=True, slots=True)
class Notification:
    at: signals.map.Coordinates

    @abc.abstractmethod
    def affect(self, controller: signals.map.control.Controller) -> None:
        raise NotImplementedError


@attr.s(auto_attribs=True, frozen=True, kw_only=True, slots=True)
class StateUpdate(Notification, typing.Generic[T]):
    field: str
    value: T
    continuous: bool

    def __attrs_post_init__(self):
        if self.continuous:
            assert isinstance(self.value, float), self

    def affect(self, controller: signals.map.control.Controller) -> None:
        cmds = controller.command_set
        cmd_cls = cmds.Track if self.continuous else cmds.Edit
        cmd = cmd_cls(at=self.at, state=signals.map.SigState({self.field: self.value}))
        cmd.affect(controller)


@attr.s(auto_attribs=True, frozen=True, kw_only=True, slots=True)
class Playback(Notification):
    state: signals.map.PlaybackState

    def affect(self, controller: signals.map.control.Controller) -> None:
        cmd = controller.command_set.PlaybackCommand(at=self.at,
                                                     target_state=self.state)
        cmd.affect(controller)


class Control(QtWidgets.QWidget, typing.Generic[T]):
    notify = QtCore.pyqtSignal(Notification)

    def __init__(self, at: signals.map.Coordinates, parent=None):
        super().__init__(parent=parent)
        self.at = at


class PlaybackButton(QtWidgets.QPushButton):
    play_chr = '\u23f5'
    pause_chr = '\u23f8'
    stop_chr = '\u23f9'

    def target_state(self) -> signals.map.PlaybackState:
        raise NotImplementedError


class PlayButton(PlaybackButton):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setCheckable(True)
        self.setChecked(False)
        self.setText(self.play_chr)
        self.pressed.connect(self._swap)

    def _swap(self) -> None:
        self.setText(self.pause_chr if self.isChecked() else self.play_chr)

    def target_state(self) -> signals.map.PlaybackState:
        states = signals.map.PlaybackCommandStates
        state = states.PAUSE if self.isChecked() else states.PLAY
        return state.value


class StopButton(PlaybackButton):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setText(self.stop_chr)

    def target_state(self) -> signals.map.PlaybackState:
        return signals.map.PlaybackCommandStates.STOP.value


class PlaybackControl(Control[signals.map.PlaybackState]):

    def __init__(self, at: signals.map.Coordinates, parent=None):
        super().__init__(at=at, parent=parent)

        layout = QtWidgets.QHBoxLayout()

        for button in (PlayButton(), StopButton()):
            # Closure badness
            def _callback(button=button):
                self.notify.emit(Playback(at=self.at, state=button.target_state()))

            button.pressed.connect(_callback)
            layout.addWidget(button)

        self.setLayout(layout)


class ValueControl(Control, typing.Generic[T]):

    def __init__(self,
                 *,
                 state_field: str,
                 at: signals.map.Coordinates,
                 parent=None):
        super().__init__(at=at, parent=parent)
        self.state_field = state_field


class IntControl(ValueControl[int]):

    def __init__(self,
                 *,
                 at: signals.map.Coordinates,
                 state_field: str,
                 val: int = 0,
                 parent=None):
        super().__init__(state_field=state_field, at=at, parent=parent)
        self.spinner = QtWidgets.QSpinBox()
        self.spinner.setValue(val)
        self.spinner.valueChanged.connect(lambda val: self.notify.emit(self.at, val))

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.spinner)

        self.setLayout(layout)


@attr.s(auto_attribs=True, frozen=True, kw_only=True, slots=True)
class FloatUpdate:
    value: float
    continuous: bool


class FloatControl(ValueControl[FloatUpdate]):
    scale = 10e6

    def __init__(self,
                 *,
                 state_field: str,
                 val: float = 0.0,
                 min_: float = -1.0,
                 max_: float = 1.0,
                 at: signals.map.Coordinates,
                 parent=None):
        super().__init__(state_field=state_field, at=at, parent=parent)
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
        self.notify.emit(StateUpdate(at=self.at,
                                     field=self.state_field,
                                     value=value,
                                     continuous=False))

    def value_slid(self, value: int) -> None:
        value = self._scale(value)
        self.val.setText(str(value))
        self.notify.emit(StateUpdate(at=self.at,
                                     field=self.state_field,
                                     value=value,
                                     continuous=True))
