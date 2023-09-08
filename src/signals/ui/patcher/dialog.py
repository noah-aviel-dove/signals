import copy
import typing

from PyQt5 import (
    QtCore,
    QtGui,
    QtWidgets,
)
import attr
import numpy as np

import signals.map
import signals.ui.theme


class SignalDialog(QtWidgets.QDialog):

    def __init__(self,
                 *,
                 parent=None,
                 flags=QtCore.Qt.WindowFlags()
                 ):
        super().__init__(parent=parent, flags=flags)
        self.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        signals.ui.theme.register(self)

        # FIXME this can be fleshed out with more consolidation of behavior


class SigStateValidator(QtGui.QValidator):

    def __init__(self, init_value: signals.SigStateValue, parent=None):
        super().__init__(parent=parent)
        self.init_value = init_value

    def convert(self, input: str) -> signals.SigStateValue:
        if isinstance(self.init_value, str):
            result = input
        else:
            result = signals.map.SigStateItem.parse_value(input)
            if isinstance(self.init_value, (float, bool)) and isinstance(result, int):
                result = type(self.init_value)(result)
            elif (
                isinstance(self.init_value, np.ndarray)
                and self.init_value.size == 1
                and isinstance(result, (int, float))
            ):
                result = np.array([result])

        if not isinstance(result, type(self.init_value)):
            raise ValueError

        if isinstance(result, np.ndarray):
            if result.ndim > self.init_value.ndim:
                raise ValueError
            else:
                result.reshape(self.init_value.shape)
            result = result.astype(self.init_value.dtype)

        return result

    def validate(self, input: str, pos: int) -> tuple[QtGui.QValidator.State, str, int]:
        try:
            self.convert(input)
        except ValueError:
            state = self.State.Intermediate
        else:
            state = self.State.Acceptable
        return state, input, pos


class SigStateEditor(QtWidgets.QWidget):

    state_changed = QtCore.pyqtSignal(str)

    def __init__(self, state: signals.map.SigState, parent=None):
        super().__init__(parent=parent)
        self.init_state = signals.map.SigState(state)
        self.state = state

        layout = QtWidgets.QFormLayout()

        self.labels = {}
        self.editors = {}

        for item in self.state.items():
            item: signals.map.SigStateItem

            label = QtWidgets.QLabel()
            self.labels[item.k] = label

            editor = QtWidgets.QLineEdit()
            validator = SigStateValidator(item.v)
            editor.setValidator(validator)

            # Force variable to be bound when the function is defined rather than called
            def changed(ed=editor, it=item, v=validator):
                val = v.convert(ed.text())
                self._set_value(signals.map.SigStateItem(k=it.k, v=val))

            editor.editingFinished.connect(changed)
            self.editors[item.k] = editor

            self._set_value(item)
            layout.addRow(label, editor)

        self.setLayout(layout)

    def reset_changes(self):
        for item in self.init_state.items():
            item: signals.map.SigStateItem
            self._set_value(item)

    def _set_value(self, item: signals.map.SigStateItem):
        init = item.v == self.init_state[item.k]
        current = item.v == self.state[item.k]

        self.state[item.k] = item.v
        value_str = signals.map.SigStateItem.dump_value(item.v)
        self.editors[item.k].setText(value_str)

        if isinstance(init, np.ndarray):
            init = init.all()
        if isinstance(current, np.ndarray):
            current = current.all()
        self.labels[item.k].setText(item.k + ('' if init else '*'))
        if not current:
            self.state_changed.emit(item.k)

    def has_valid_state(self) -> bool:
        return all(ed.hasAcceptableInput() for ed in self.editors.values())


class AddSignal(SignalDialog):

    def __init__(self,
                 *,
                 filterer: typing.Callable[[str], list[str]],
                 at: signals.map.Coordinates,
                 parent=None,
                 flags=QtCore.Qt.WindowFlags()):
        super().__init__(parent=parent, flags=flags)
        self.setWindowTitle('Add signal')

        self.cls_name = None
        self.state = signals.map.SigState()
        self.state_edit = None
        self.at = at

        layout = QtWidgets.QVBoxLayout()
        cls_name_editor = QtWidgets.QLineEdit()
        chooser = QtWidgets.QListWidget()
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.button(buttons.Ok).setEnabled(False)

        def filter(text: str):
            items = filterer(f'*{text}*')
            chooser.clear()
            chooser.addItems(items)

        def choose(item: QtWidgets.QListWidgetItem):
            self.cls_name = item.text()
            self.accept()

        state_edit_wrapper = QtWidgets.QWidget()
        state_edit_wrapper.setLayout(QtWidgets.QHBoxLayout())

        def on_selection_changed():
            if self.state_edit is not None:
                state_edit_wrapper.layout().removeWidget(self.state_edit)
                self.state_edit.setParent(None)
            if chooser.currentItem() is None:
                buttons.button(buttons.Ok).setEnabled(False)
                self.cls_name = None
                self.state_edit = None
            else:
                buttons.button(buttons.Ok).setEnabled(True)
                self.cls_name = chooser.currentItem().text()
                # Reset to empty, then fill in default state
                self.state = signals.map.SigState()
                self.state = self.info().state
                self.state_edit = SigStateEditor(self.state)
                state_edit_wrapper.layout().addWidget(self.state_edit)

        cls_name_editor.textChanged.connect(filter)
        chooser.currentItemChanged.connect(lambda curr, prev: chooser.setCurrentItem(curr))
        chooser.itemSelectionChanged.connect(on_selection_changed)
        chooser.itemActivated.connect(choose)
        buttons.accepted.connect(lambda: choose(chooser.currentItem()))
        buttons.rejected.connect(self.reject)

        layout.addWidget(cls_name_editor)
        layout.addWidget(chooser)
        layout.addWidget(state_edit_wrapper)
        layout.addWidget(buttons)

        self.setLayout(layout)
        signals.ui.theme.register(self)

    def info(self) -> signals.map.MappedSigInfo:
        assert self.cls_name is not None
        return signals.map.MappedSigInfo(cls_name=self.cls_name,
                                         state=self.state,
                                         at=self.at)


class AddDevice(SignalDialog):

    def __init__(self,
                 at: signals.map.Coordinates,
                 *,
                 sources_not_sinks: bool,
                 sources: list,
                 sinks: list,
                 parent=None,
                 flags=QtCore.Qt.WindowFlags()):
        super().__init__(parent=parent, flags=flags)
        self.setWindowTitle('Add device')

        self.sources_not_sinks = sources_not_sinks
        self.devices = []
        self.device = None
        self.at = at

        devices_by_name = {
            device.name: device
            for device in sources + sinks
        }

        layout = QtWidgets.QVBoxLayout()
        selection_layout = QtWidgets.QHBoxLayout()
        input_layout = QtWidgets.QVBoxLayout()
        type_chooser_layout = QtWidgets.QVBoxLayout()

        type_chooser = QtWidgets.QGroupBox()
        source_button = QtWidgets.QRadioButton()
        sink_button = QtWidgets.QRadioButton()
        device_chooser = QtWidgets.QListWidget()
        label = QtWidgets.QLabel()
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)

        buttons.button(buttons.Ok).setEnabled(False)
        source_button.setChecked(sources_not_sinks)
        sink_button.setChecked(not sources_not_sinks)
        source_button.setText('Sources')
        sink_button.setText('Sinks')

        def choose_type(source_not_sinks):
            self.sources_not_sinks = source_not_sinks
            self.devices = sources if self.sources_not_sinks else sinks
            device_chooser.clear()
            device_chooser.addItems([device.name for device in self.devices])

        choose_type(self.sources_not_sinks)

        def change_device(curr: QtWidgets.QListWidgetItem, prev: QtWidgets.QListWidgetItem):
            if curr is None:
                self.device = None
                label.setText('')
            else:
                self.device = devices_by_name[curr.text()]
                label.setText(str(self.device))

        def choose_device(item: QtWidgets.QListWidgetItem):
            self.device = devices_by_name[item.text()]
            self.accept()

        def enable_button():
            buttons.button(buttons.Ok).setEnabled(device_chooser.currentItem() is not None)

        source_button.toggled.connect(choose_type)
        sink_button.clicked.connect(lambda checked: choose_type(not checked))

        device_chooser.currentItemChanged.connect(change_device)
        device_chooser.itemSelectionChanged.connect(enable_button)
        device_chooser.itemActivated.connect(choose_device)

        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)

        type_chooser_layout.addWidget(source_button)
        type_chooser_layout.addWidget(sink_button)
        type_chooser.setLayout(type_chooser_layout)

        input_layout.addWidget(type_chooser)
        input_layout.addWidget(device_chooser)
        selection_layout.addLayout(input_layout)
        selection_layout.addWidget(label)

        layout.addLayout(selection_layout)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def info(self) -> signals.map.MappedDevInfo:
        assert self.device is not None
        if self.sources_not_sinks:
            return signals.map.MappedDevInfo.for_source(at=self.at,
                                                        device=self.device)
        else:
            return signals.map.MappedDevInfo.for_sink(at=self.at,
                                                      device=self.device)


class EditSignal(SignalDialog):

    def __init__(self,
                 signal: signals.map.MappedSigInfo,
                 *,
                 parent=None,
                 flags=QtCore.Qt.WindowFlags()
                 ):
        super().__init__(parent=parent, flags=flags)
        self.setWindowTitle(f'Edit {signal.cls_name} at {signal.at}')

        self.signal = signal
        self.state_edit = SigStateEditor(state=signals.map.SigState(signal.state))

        self.state_edit.state_changed.connect(self._on_change)

        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok
            | QtWidgets.QDialogButtonBox.Cancel
            | QtWidgets.QDialogButtonBox.Reset
        )
        self.buttons.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(self.accept)
        self.buttons.button(QtWidgets.QDialogButtonBox.Cancel).clicked.connect(self.reject)
        self.buttons.button(QtWidgets.QDialogButtonBox.Reset).clicked.connect(self._reset)

        self._reset()

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.state_edit)
        layout.addWidget(self.buttons)
        self.setLayout(layout)

    def _on_change(self, key: str):
        self.buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        self.buttons.button(QtWidgets.QDialogButtonBox.Reset).setEnabled(True)

    def info(self) -> signals.map.MappedSigInfo:
        return attr.evolve(self.signal, state=self.state_edit.state)

    def _reset(self):
        self.state_edit.reset_changes()
        self.buttons.button(QtWidgets.QDialogButtonBox.Reset).setEnabled(False)


