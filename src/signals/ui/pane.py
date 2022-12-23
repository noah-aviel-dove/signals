import abc
import itertools
import string
import typing

from PyQt5 import (
    QtCore,
    QtGui,
    QtWidgets,
)
import more_itertools
import numpy as np

import signals.graph
import signals.graph.dev
import signals.ui.node
import signals.ui.theme


class GraphPane(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        signals.ui.set_name(self)

        # Needs to be initialized before device nodes can connect to it
        self.edges = Edges(self)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.source_list = DevList(self)
        self.source_list.set_devices(signals.graph.dev.SourceDevice.list())

        self.editor = GraphEditor(1, 1, self)

        self.sink_list = DevList(self)
        self.sink_list.set_devices(signals.graph.dev.SinkDevice.list())

        layout.addWidget(self.source_list)
        layout.addWidget(self.editor)
        layout.addWidget(self.sink_list)
        layout.setAlignment(self.source_list, QtCore.Qt.AlignHCenter)
        layout.setAlignment(self.sink_list, QtCore.Qt.AlignHCenter)

        # The `Edges` widget is transparent to mouse events.
        # This widget tracks the mouse for it.
        self.setMouseTracking(True)
        for child in self.children():
            if False and isinstance(child, QtWidgets.QWidget):
                child.setMouseTracking(True)
        self.edges.raise_()

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        self.edges.setGeometry(self.geometry())

    @classmethod
    def ancestor(cls, descendant: QtWidgets.QWidget) -> typing.Self:
        p = descendant
        while not isinstance(p, cls):
            p = p.parent()
            assert p is not None
        return p

    G = typing.TypeVar(name='G', bound='GraphPane')

    @classmethod
    def descendant(cls, decorated_cls: G) -> G:
        decorated_cls.pane = property(fget=cls.ancestor)
        return decorated_cls

    def on_power_changed(self, node: signals.ui.node.Node) -> None:
        node.repaint()
        self.edges.repaint()
        # FIXME propagate signal to do something to indicate when a source is
        # not being used because all sinks are disabled


@GraphPane.descendant
class SubPane(QtWidgets.QFrame):

    def __init__(self, parent: QtWidgets.QWidget):
        super().__init__(parent=parent)
        signals.ui.set_name(self)

        self.setStyleSheet(f'border: 1px solid {self.color.name()}')

    @property
    def color(self) -> QtGui.QColor:
        return signals.ui.theme.current().on


class DevList(SubPane):

    def __init__(self, parent: QtWidgets.QWidget):
        super().__init__(parent=parent)

        self.setSizePolicy(QtWidgets.QSizePolicy.Maximum,
                           QtWidgets.QSizePolicy.Maximum)

    def set_devices(self, devices: list[signals.graph.Node]) -> None:
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        for i, device in enumerate(devices):
            device = signals.ui.node.Node(device, self)
            layout.addWidget(device)
            device.connect(self.pane)


class GraphEditor(SubPane):

    def __init__(self, stage: int, lane: int, parent: QtWidgets.QWidget):
        super().__init__(parent=parent)
        self.stage = stage
        self.lane = lane
        self.setMinimumSize(100, 100)

        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum,
                           QtWidgets.QSizePolicy.Minimum)

        import signals.graph.osc
        self.add_node(signals.graph.osc.Sine())

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        super().paintEvent(a0)
        bl = self.rect().bottomLeft()
        with QtGui.QPainter(self) as qp:
            coords = f'{self.stage}{string.ascii_lowercase[self.lane - 1]}'
            qp.setPen(self.color)
            qp.drawText(bl.x() + 2, bl.y() - 2, coords)

    def add_node(self, node: signals.graph.Node) -> None:
        ui_node = signals.ui.node.Node(node=node, parent=self)
        ui_node.move(self.rect().center())
        ui_node.connect(self.pane)


@GraphPane.descendant
class Edges(QtWidgets.QWidget):
    try_placing_edge = QtCore.pyqtSignal(object, object)

    def __init__(self, parent: QtWidgets.QWidget):
        super().__init__(parent=parent)
        signals.ui.set_name(self)

        self.placed_edges: list[PlacedEdge] = []
        self.placing_edge: typing.Optional[PlacingEdge] = None

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def _start_using_mouse(self):
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, on=False)
        self.setMouseTracking(True)
        self.grabMouse()

    def _stop_using_mouse(self):
        self.releaseMouse()
        self.setMouseTracking(False)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def _movement_repaint(self, sink_pos: QtCore.QPoint) -> None:
        rect = self.placing_edge.move_sink(sink_pos)
        self.pane.repaint(rect)

    def start_placing_edge(self, source: signals.ui.node.NodeCore) -> None:
        if self.placing_edge is None:
            self.placing_edge = PlacingEdge(self.pane, source)
            self._start_using_mouse()

    def stop_placing_edge(self, slot: signals.ui.node.Slot) -> None:
        if self.placing_edge is not None:
            self._stop_using_mouse()
            placed = self.placing_edge.place(slot)
            self._movement_repaint(placed.sink_loc)
            self.placed_edges.append(placed)
            self.placing_edge = None

    def start_moving_edge(self, slot: signals.ui.node.Slot) -> None:
        try:
            changed = more_itertools.one(
                (e for e in self.placed_edges
                 if e.sink is slot),
                too_long=AssertionError
            )
        except ValueError:
            pass
        else:
            self.stop_placing_edge(slot)
            if self.placing_edge is None:
                self.placed_edges.remove(changed)
                self.placing_edge = changed.unplace()
                self._start_using_mouse()

    def cancel_placing_edge(self):
        if self.placing_edge is not None:
            self._stop_using_mouse()
            old = self.placing_edge
            self.placing_edge = None
            self.pane.repaint(old.rect())

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self.placing_edge is not None:
            self._movement_repaint(event.pos())

    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent) -> None:
        if a0.button() == QtCore.Qt.MouseButton.LeftButton:
            self.try_placing_edge.emit(a0, self.mapToGlobal(a0.pos()))
        elif a0.button() == QtCore.Qt.MouseButton.RightButton:
            a0.accept()
            self.cancel_placing_edge()
        else:
            pass

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        edges = (self.placed_edges
                 if self.placing_edge is None else
                 itertools.chain(self.placed_edges, [self.placing_edge]))
        with QtGui.QPainter(self) as qp:
            for edge in edges:
                if a0.rect().intersects(edge.rect()):
                    edge.paint(qp)


class Edge(abc.ABC):
    shadow = 3

    def __init__(self, pane: GraphPane, source: signals.ui.node.NodeCore):
        self.pane = pane
        self.source = source

    def _map(self, w: QtWidgets.QWidget, p: QtCore.QPoint) -> QtCore.QPoint:
        return w.mapTo(self.pane, p)

    @property
    def source_loc(self) -> QtCore.QPoint:
        r = self.source.rect()
        p = QtCore.QPoint(r.center().x(), r.bottom() + self.shadow + 1)
        return self._map(self.source, p)

    @property
    @abc.abstractmethod
    def sink_loc(self) -> QtCore.QPoint:
        raise NotImplementedError

    @property
    def points(self) -> list[QtCore.QPoint]:
        s1 = self.source_loc
        s2 = self.sink_loc
        midx, midy = (s1.x() + s2.x()) // 2, (s1.y() + s2.y()) // 2
        delta = s2 - s1
        sy, sx = np.sign(delta.y()), np.sign(delta.x())
        if abs(delta.x()) < abs(delta.y()):
            leg1 = abs(midx - s1.x()) * sy
            leg2 = abs(midx - s2.x()) * sy
            c1 = QtCore.QPoint(s1.x(), midy - leg1)
            c2 = QtCore.QPoint(s2.x(), midy + leg2)
        else:
            leg1 = abs(midy - s1.y()) * sx
            leg2 = abs(midy - s2.y()) * sx
            c1 = QtCore.QPoint(s1.x() + leg1, midy)
            c2 = QtCore.QPoint(s2.x() - leg2, midy)
        return [s1, c1, c2, s2]

    def paint(self, qp: QtGui.QPainter) -> None:
        t = signals.ui.theme.current()
        ps = self.points
        qp.setPen(QtGui.QPen(t.back, 1 + self.shadow * 2))
        qp.drawPolyline(*ps)
        qp.setPen(QtGui.QPen(t.on if self.source.gnode.enabled else t.off, 1))
        qp.drawPolyline(*ps)

    def _rect(self, *ps: QtCore.QPoint) -> QtCore.QRect:
        return signals.ui.rect_containing_points(*ps) + QtCore.QMargins(*[self.shadow + 1] * 4)

    def rect(self) -> QtCore.QRect:
        return self._rect(self.source_loc, self.sink_loc)

    def move_sink(self, pos: QtCore.QPoint) -> QtCore.QRect:
        old = QtCore.QPoint(self.sink_loc)
        self.sink_loc.setX(pos.x())
        self.sink_loc.setY(pos.y())
        return self._rect(old, self.source_loc, self.sink_loc)


class PlacingEdge(Edge):

    def __init__(self, pane: GraphPane, source: signals.ui.node.NodeCore):
        super().__init__(pane, source)
        self.tracking = QtCore.QPoint(0, 0)

    @property
    def sink_loc(self) -> QtCore.QPoint:
        return self.tracking

    def place(self, slot: signals.ui.node.Slot) -> 'PlacedEdge':
        return PlacedEdge(self.pane, self.source, slot)


class PlacedEdge(Edge):

    def __init__(self, pane: GraphPane, source: signals.ui.node.NodeCore, sink: signals.ui.node.Slot):
        super().__init__(pane, source)
        self.sink = sink
        setattr(self.sink.gnode, self.sink.slot, self.source.gnode)

    @property
    def sink_loc(self) -> QtCore.QPoint:
        r = self.sink.rect()
        p = QtCore.QPoint(r.center().x(), r.top() - self.shadow - 1)
        return self._map(self.sink, p)

    def unplace(self) -> PlacingEdge:
        delattr(self.sink.gnode, self.sink.slot)
        return PlacingEdge(self.pane, self.source)
