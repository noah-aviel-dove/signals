import abc
import typing

from PyQt5 import (
    QtCore,
    QtGui,
    QtWidgets,
)
import numpy as np

import signals.graph
import signals.graph.files
import signals.layout
import signals.ui.theme


class NodePart(QtWidgets.QWidget):

    def __init__(self, node: signals.graph.Node, parent: QtWidgets.QWidget):
        super().__init__(parent=parent)
        signals.ui.set_name(self)
        self.gnode = node
        self.setContentsMargins(*[0] * 4)
        self.setFixedSize(self._size)

    @property
    @abc.abstractmethod
    def _size(self) -> QtCore.QSize:
        raise NotImplementedError

    @property
    def color(self) -> QtGui.QColor:
        theme = signals.ui.theme.current()
        return theme.on if self.gnode.enabled else theme.off

    def drawing_rect(self) -> QtCore.QRect:
        # FIXME this seems sus
        return self.rect() - QtCore.QMargins(0, 0, 1, 1)


N = typing.TypeVar(name='N', bound=NodePart)


class Node(QtWidgets.QWidget):
    spacing = 2

    def __init__(self,
                 gnode: signals.graph.Node,
                 lnode: signals.layout.Node,
                 parent):
        super().__init__(parent=parent)
        signals.ui.set_name(self)
        self.gnode = gnode
        self.lnode = lnode

        self._toggle: PowerToggle = self._create_part(PowerToggle)
        self._core: NodeCore = self._create_part(NodeCore)
        self._slots: list[Slot] = [
            self._create_part(Slot, slot=slot)
            for slot in self.gnode.slots()
        ]

        layout = QtWidgets.QHBoxLayout(self)
        center = QtCore.Qt.AlignCenter
        layout.setAlignment(center)
        layout.setSpacing(self.spacing)

        core_layout = QtWidgets.QVBoxLayout()
        core_layout.setAlignment(center)
        core_layout.setSpacing(self.spacing)

        slot_layout = QtWidgets.QHBoxLayout()
        slot_layout.setAlignment(center)
        slot_layout.setSpacing(self.spacing)
        slot_layout.addWidget(self._toggle)
        for slot in self._slots:
            slot_layout.addWidget(slot)

        core_layout.addLayout(slot_layout)
        core_layout.addWidget(self._core)
        if isinstance(self.gnode, signals.graph.files.BufferCachingNode):
            core_layout.addWidget(self._create_part(BufferCacheControl))

        # FIXME: add events
        if isinstance(gnode, signals.graph.Event):
            layout.addWidget(self._create_part(EventTrigger))
        layout.addLayout(core_layout)
        # FIXME: add visualisers
        if isinstance(gnode, signals.graph.Vis):
            layout.addWidget(self._create_part(Visualizer))
        # FIXME: add events
        if isinstance(gnode, signals.graph.Event):
            layout.addWidget(self._create_part(EventCaster))

        self.setLayout(layout)

    def connect(self, pane: 'signals.ui.view.GraphView') -> None:
        self._core.add_sink.connect(pane.edges.start_placing_edge)
        self._toggle.power_toggled.connect(pane.on_power_changed)
        for slot in self._slots:
            pane.edges.try_placing_edge.connect(slot.pull_mouse)
            slot.add_source.connect(pane.edges.stop_placing_edge)
            slot.rm_source.connect(pane.edges.start_moving_edge)

    def _create_part(self, part_cls: N, **args) -> N:
        return part_cls(node=self.gnode, parent=self, **args)


class NodeCore(NodePart, QtWidgets.QWidget):
    add_sink = QtCore.pyqtSignal(object)

    @property
    def _size(self) -> QtCore.QSize:
        return QtCore.QSize(40, 40)

    def _draw_circ(self, qp: QtGui.QPainter, s: float = 1) -> None:
        qp.drawEllipse(signals.ui.scale_rect(self.drawing_rect(), s))

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        with QtGui.QPainter(self) as qp:
            qp.setPen(self.color)
            qp.setBrush(QtCore.Qt.NoBrush)
            self._draw_circ(qp)

            node_type = self.gnode.type
            if node_type is signals.graph.NodeType.GENERATOR:
                qp.setBrush(self.color)
                self._draw_circ(qp, 2 / 3)
            elif node_type is signals.graph.NodeType.PLAYBACK:
                for s in np.linspace(1 / 5, 1, 4, endpoint=False):
                    self._draw_circ(qp, s)
            elif node_type is signals.graph.NodeType.VALUE:
                qp.setBrush(self.color)
                p = signals.ui.make_regular_polygon(n=4,
                                                    r=self.rect().width() / 3,
                                                    c=self.rect().center())
                qp.drawConvexPolygon(p)
            elif node_type is signals.graph.NodeType.OPERATOR:
                p = signals.ui.make_inset_chevron(a=-np.pi / 2,
                                                  r=self.rect().width(),
                                                  c=self.rect().center())
                qp.drawLines(*p)
            elif node_type is signals.graph.NodeType.TABLE:
                qp.setBrush(self.color)
                qp.drawRect(signals.ui.scale_rect(self.rect(), 2 / 3))
            else:
                assert False, node_type

    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent) -> None:
        a0.accept()
        self.add_sink.emit(self)


class Slot(NodePart):
    add_source = QtCore.pyqtSignal(object)
    rm_source = QtCore.pyqtSignal(object)

    def __init__(self, node: signals.graph.Node, parent, slot: str):
        super().__init__(node=node, parent=parent)
        self.slot = slot

    @property
    def _size(self) -> QtCore.QSize:
        return QtCore.QSize(11, 16)

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        with QtGui.QPainter(self) as qp:
            qp.setPen(self.color)
            qp.drawPolyline(self.rect().topLeft(),
                            self.rect().bottomLeft(),
                            self.rect().bottomRight(),
                            self.rect().topRight())
            qp.drawText(self.rect().left() + 2, self.rect().bottom() - 5, self.slot[0])

    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent) -> None:
        if a0.button() == QtCore.Qt.MouseButton.LeftButton:
            if getattr(self.gnode, self.slot) is None:
                self.add_source.emit(self)
            else:
                self.rm_source.emit(self)

    def pull_mouse(self, a0: QtGui.QMouseEvent, global_mouse_pos: QtCore.QPoint) -> None:
        if signals.ui.global_rect(self).contains(global_mouse_pos):
            self.mouseReleaseEvent(a0)


class PowerToggle(NodePart):
    power_toggled = QtCore.pyqtSignal(object)

    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent) -> None:
        a0.accept()
        self.gnode.enabled = not self.gnode.enabled
        self.power_toggled.emit(self.parent())

    @property
    def _size(self) -> QtCore.QSize:
        return QtCore.QSize(10, 10)

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        with QtGui.QPainter(self) as qp:
            qp.setPen(self.color)
            qp.setBrush(self.color)
            qp.drawEllipse(self.rect() - QtCore.QMargins(*[2] * 4))


class BufferCacheControl(NodePart):

    @property
    def _size(self) -> QtCore.QSize:
        return QtCore.QSize(40, 10)

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        with QtGui.QPainter(self) as qp:
            qp.setPen(self.color)
            qp.drawRect(self.rect())


class EventControl(NodePart):

    @property
    def _size(self) -> QtCore.QSize:
        return QtCore.QSize(5, 40)

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        with QtGui.QPainter(self) as qp:
            qp.setPen(self.color)
            c = self.rect().center().x()
            qp.drawLine(c, self.rect().top(), c, self.rect().bottom())


class EventTrigger(EventControl):
    pass


class EventCaster(EventControl):
    pass


class RateIndicator(NodePart):

    def _size(self) -> QtCore.QSize:
        return QtCore.QSize(10, 20)

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        rates = signals.graph.RequestRate
        rate = self.gnode.rate
        with QtGui.QPainter(self) as qp:
            # FIXME add rate indicators
            if rate is rates.FRAME:
                pass
            elif rate is rates.BLOCK:
                pass
            elif rate is rates.UNKNOWN:
                pass
            elif rate is rates.UNUSED_FRAME:
                pass


class Visualizer(NodePart):

    @property
    def _size(self) -> QtCore.QSize:
        return QtCore.QSize(0, 0)

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        with QtGui.QPainter(self) as qp:
            qp.setPen(signals.ui.theme.current().front)
            qp.drawRect(self.rect())
