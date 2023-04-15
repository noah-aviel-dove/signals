import functools
import pathlib

from PyQt5 import (
    QtCore,
    QtGui,
    QtWidgets,
)

import PyQtCmd
import attr

import signals.map.control
import signals.ui.patcher
import signals.ui.patcher.map
import signals.ui.patcher.dialog
import signals.ui.theme
import signals.ui.scene
import signals.ui.graph


class Window(QtWidgets.QMainWindow):

    def __init__(self, path: pathlib.Path | None = None, parent=None):
        super().__init__(parent=parent)
        self.path = path
        self.saved_hash = None
        self.patcher = signals.ui.patcher.Patcher()
        self.controller = signals.map.control.Controller(
            interactive=True,
            map=signals.ui.patcher.map.PatcherMap(self.patcher)
        )

        self._set_title()
        self.patcher.new_container.connect(self._on_new_container)

        file = self.menuBar().addMenu(self.tr('&File'))
        file.addAction(self._create_action('New', 'Ctrl+N', self.new))
        file.addAction(self._create_action('New...', 'Ctrl+Shift+N', self.spawn))
        file.addAction(self._create_action('Open...', 'Ctrl+O', self.open))
        file.addAction(self._create_action('Revert', 'Ctrl+R', self.revert))
        file.addAction(self._create_action('Save', 'Ctrl+S', self.save))
        file.addAction(self._create_action('Save As...', 'Ctrl+Shift+S', self.save_as))
        file.addAction(self._create_action('Quit', 'Ctrl+Q', self.close))

        edit = self.menuBar().addMenu(self.tr('&Edit'))
        edit.addAction(self._create_action('Undo', 'Ctrl+Z', self._undo))
        edit.addAction(self._create_action('Redo', 'Ctrl+Shift+Z', self._redo))

        add_signal = self._create_action('Add signal', 'Alt+S', self.add_signal_at_active)
        self.addAction(add_signal)
        rm_signal = self._create_action('Delete signal', 'Alt+D', self.remove_at_active)
        self.addAction(rm_signal)
        add_sink = self._create_action('Add output device', 'Alt+O', self.add_sink_at_active)
        self.addAction(add_sink)
        add_source = self._create_action('Add input device', 'Alt+I', self.add_source_at_active)
        self.addAction(add_source)

        copy_signal = self._create_action('Copy signal', 'Ctrl+C', self.copy_at_active)
        self.addAction(copy_signal)
        paste_signal = self._create_action('Paste signal', 'Ctrl+V', self.paste_at_active)
        self.addAction(paste_signal)
        cut_signal = self._create_action('Cut signal', 'Ctrl+X', lambda: self.copy_at_active(cut=True))
        self.addAction(cut_signal)

        def interpreter(line: str) -> bool:
            self.controller.onecmd(line)
            return False

        console = PyQtCmd.QCmdConsole(interpreter=interpreter)
        console_dock = QtWidgets.QDockWidget()
        console_dock.setWidget(console)
        signals.ui.theme.register(console_dock)

        self.controller.stdout = console.stdout
        self.controller.stdin = None

        scene = signals.ui.scene.Scene(self)
        scene.addItem(self.patcher)
        view = QtWidgets.QGraphicsView(scene)
        self.setCentralWidget(view)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, console_dock)
        self.setStatusBar(QtWidgets.QStatusBar())

        signals.ui.theme.register(self.menuBar())
        if False:
            # FIXME the menus and status bars always appear as white/light gray even
            #  when the palette is set?
            signals.ui.theme.register(self.statusBar())

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self._discard_prompt():
            super().closeEvent(event)
        else:
            event.ignore()

    def _create_action(self,
                       text: str,
                       shortcut: str,
                       slot) -> QtWidgets.QAction:
        action = QtWidgets.QAction(text, self)
        action.setShortcut(shortcut)
        action.triggered.connect(slot)
        return action

    def _set_title(self):
        if self.path is None:
            s = '*'
        else:
            s = str(self.path)
            if self.is_dirty():
                s = '* ' + s
        self.setWindowTitle(f'signals: patcher: {s}')

    def add_signal_at_active(self) -> None:
        sq = self._active_square(empty=True)
        if sq:
            dialog = signals.ui.patcher.dialog.AddSignal(filterer=self.controller.grep,
                                                         at=sq.at)
            dialog.accepted.connect(lambda: self._add_signal(dialog.info()))
            dialog.open()

    def add_device_at_active(self, is_source: bool) -> None:
        sq = self._active_square(empty=True)
        if sq:
            dialog = signals.ui.patcher.dialog.AddDevice(at=sq.at,
                                                         sources_not_sinks=is_source,
                                                         sources=self.controller.rack.sources(),
                                                         sinks=self.controller.rack.sinks())
            dialog.accepted.connect(lambda: self._add_signal(dialog.info()))
            dialog.open()

    def remove_at_active(self) -> None:
        sq = self._active_square(empty=False)
        if sq:
            self._remove_signal(sq.at)

    def add_source_at_active(self) -> None:
        self.add_device_at_active(is_source=True)

    def add_sink_at_active(self) -> None:
        self.add_device_at_active(is_source=False)

    def edit_at_active(self) -> None:
        sq = self._active_square(empty=False)
        if sq:
            dialog = signals.ui.patcher.dialog.EditSignal(sq.content.signal)
            dialog.accepted.connect(lambda: self._edit_signal(dialog.info()))
            dialog.open()

    _signal_mime_type = 'application/prs.signals.signal'

    def copy_at_active(self, cut: bool = False) -> None:
        sq = self._active_square(empty=False)
        if sq is not None:
            add_cmd = self.controller.command_set.Add(signal=sq.content.signal)
            data = QtCore.QMimeData()
            data.setData(self._signal_mime_type, add_cmd.serialize().encode())
            QtGui.QGuiApplication.clipboard().setMimeData(data)
            if cut:
                self.controller.push(self.controller.command_set.Remove(at=sq.at))

    def paste_at_active(self) -> None:
        sq = self._active_square(empty=True)
        data = QtGui.QGuiApplication.clipboard().mimeData()
        if sq is not None and data.hasFormat(self._signal_mime_type):
            add_cmd = self.controller.parse_line(data.data(self._signal_mime_type).data().decode())
            assert isinstance(add_cmd, self.controller.command_set.Add), add_cmd
            add_cmd = attr.evolve(add_cmd, signal=attr.evolve(add_cmd.signal, at=sq.at))
            self.controller.push(add_cmd)

    def new(self):
        if self._discard_prompt():
            self._clear()
            self.path = None

    def spawn(self):
        # FIXME create new empty window
        raise NotImplementedError

    def save(self):
        if self.path is None:
            self.path = self.save_as()
        else:
            self._save(self.path)

    def save_as(self) -> pathlib.Path | None:
        path, _ = QtWidgets.QFileDialog().getSaveFileName(parent=self,
                                                          caption='Save as...')
        if path:
            path = pathlib.Path(path)
            self._save(path)
            return path
        else:
            return None

    def open(self):
        if self._discard_prompt():
            path, _ = QtWidgets.QFileDialog.getOpenFileName(parent=self,
                                                            caption='Open...')
            if path:
                path = pathlib.Path(path)
                self._load(path)

    def revert(self):
        if self._discard_prompt():
            if self.path is None:
                self._clear()
            else:
                self._load(self.path)

    def is_dirty(self) -> bool:
        return (
            self.controller.modcount > 0
            and
            (
                self.path is None
                or not
                (
                    self.saved_modcount == self.controller.modcount
                    and
                    self.saved_hash == self.controller.hash()
                )
            )
        )

    def _discard_prompt(self) -> bool:
        if self.is_dirty():
            dialog = QtWidgets.QMessageBox()
            dialog.setText('Discard unsaved changes?')
            dialog.setStandardButtons(dialog.Discard | dialog.Cancel)
            return dialog.exec() == dialog.Discard
        else:
            return True

    def _save(self, path: pathlib.Path):
        self.controller.command_set.Save(path=path).affect(self.controller)
        self.statusBar().showMessage(f'Saved as {path}')
        self._set_clean_state()

    def _load(self, path: pathlib.Path):
        try:
            self.controller.command_set.Load(path=path).affect(self.controller)
        except signals.map.MapLayerError as e:
            QtWidgets.QErrorMessage(parent=self).showMessage(f'Failed to load from {path}: {e}')
        else:
            self.statusBar().showMessage(f'Loaded from {path}')
            self.path = path
            self._set_clean_state()

    def _clear(self) -> None:
        self.controller.command_set.Init().affect(self.controller)

    def _active_square(self,
                       *,
                       empty: bool | None = None
                       ) -> signals.ui.patcher.Square | None:
        sq = self.patcher.get_active_square()
        if sq is None or (empty is not None and ((sq.content is None) != empty)):
            return None
        else:
            return sq

    def _add_signal(self, signal: signals.map.MappedSigInfo):
        self.controller.push(self.controller.command_set.Add(signal=signal))

    def _remove_signal(self, at: signals.map.Coordinates):
        self.controller.push(self.controller.command_set.Remove(at=at))

    def _edit_signal(self, signal: signals.map.MappedSigInfo):
        self.controller.push(self.controller.command_set.Edit(at=signal.at, state=signal.state))

    def _undo(self):
        try:
            self.controller.undo()
        except signals.map.control.BadUndo as e:
            self.statusBar().showMessage(e.args[0])

    def _redo(self):
        try:
            self.controller.redo()
        except signals.map.control.BadRedo as e:
            self.statusBar().showMessage(e.args[0])

    def _set_clean_state(self):
        self.saved_modcount = self.controller.modcount
        self.saved_hash = self.controller.hash()

    def _on_new_container(self, new_container: signals.ui.graph.NodeContainer) -> None:
        # FIXME connect power toggle
        for port in new_container.ports.values():
            port.input_changed.connect(self.on_port_changed)

    def on_port_changed(self,
                        port: signals.ui.graph.Port,
                        new_input: signals.ui.graph.PlacingCable | None,
                        event: QtWidgets.QGraphicsSceneMouseEvent
                        ) -> None:
        old_input = port.input
        old_input_container = None if old_input is None else old_input.container
        output = signals.map.PortInfo(port=port.name, at=port.container.signal.at)
        command_set = self.controller.command_set
        if new_input is None:
            cmd_ = command_set.Disconnect(port=output)
        else:
            input = new_input.container.signal
            cmd_ = command_set.Connect(connection=signals.map.ConnectionInfo(input_at=input.at, output=output))

        self.controller.push(cmd_)

        if new_input is not None:
            new_input.remove()

        if old_input_container is not None:
            signals.ui.graph.PlacingCable(old_input_container, event.scenePos())
