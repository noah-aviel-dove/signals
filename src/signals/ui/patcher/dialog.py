import typing

from PyQt5 import (
    QtCore,
    QtWidgets,
)

import signals.map
import signals.ui.theme


class SignalDialog(QtWidgets.QDialog):

    def __init__(self,
                 *,
                 at: signals.map.Coordinates,
                 parent=None,
                 flags=QtCore.Qt.WindowFlags()
                 ):
        super().__init__(parent=parent, flags=flags)
        self.at = at
        self.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        signals.ui.theme.register(self)

        # FIXME this can be fleshed out with more consolidation of behavior


class AddSignal(SignalDialog):

    def __init__(self,
                 *,
                 filterer: typing.Callable[[str], list[str]],
                 at: signals.map.Coordinates,
                 parent=None,
                 flags=QtCore.Qt.WindowFlags()):
        super().__init__(at=at, parent=parent, flags=flags)
        self.setWindowTitle('Add signal')

        self.cls_name = None
        self.state = signals.map.SigState()
        self.at = at

        layout = QtWidgets.QVBoxLayout()
        editor = QtWidgets.QLineEdit()
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

        def enable_button():
            buttons.button(buttons.Ok).setEnabled(chooser.currentItem() is not None)

        editor.textChanged.connect(filter)
        chooser.currentItemChanged.connect(lambda curr, prev: chooser.setCurrentItem(curr))
        chooser.itemSelectionChanged.connect(enable_button)
        chooser.itemActivated.connect(choose)
        buttons.accepted.connect(lambda: choose(chooser.currentItem()))
        buttons.rejected.connect(self.reject)

        layout.addWidget(editor)
        layout.addWidget(chooser)
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
        super().__init__(at=at, parent=parent, flags=flags)
        self.setWindowTitle('Add device')

        self.sources_not_sinks = sources_not_sinks
        self.devices = []
        self.device = None

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
