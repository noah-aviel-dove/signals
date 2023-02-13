import abc
import operator
import typing

from PyQt5 import (
    QtCore,
    QtGui,
    QtWidgets,
)
import math

import signals.chain
import signals.chain.dev
import signals.layout
from signals.ui import dbgrect
import signals.ui.graph
import signals.ui.theme
import signals.ui.graph


class DeviceList(QtWidgets.QGraphicsWidget):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.graph = signals.layout.Subgraph()

    def set_devices(self, devices: list[signals.chain.dev.Device]):
        layout = QtWidgets.QGraphicsLinearLayout()
        for i, device in enumerate(devices):
            con = signals.ui.graph.NodeContainer(device)
            layout.addItem(con)
            layout.setAlignment(con, QtCore.Qt.AlignCenter)
            self.graph.add(signals.layout.Vertex(x=i,
                                                 y=0,
                                                 value=con.node))
        self.setLayout(layout)

    def paint(self,
              painter: QtGui.QPainter,
              option: QtWidgets.QStyleOptionGraphicsItem,
              widget: typing.Optional[QtWidgets.QWidget] = ...
              ) -> None:
        super().paint(painter, option, widget)
        if 1:
            dbgrect(self, painter, QtGui.QColorConstants.Green)


class UserSpace(QtWidgets.QGraphicsWidget):

    def __init__(self, stage: int, lane: int, parent=None):
        super().__init__(parent=parent)
        self.setMinimumSize(QtCore.QSizeF(100, 100))
        self.stage = stage
        self.lane = lane

        self.graph: signals.layout.Subgraph[
            signals.layout.Vertex[
                signals.ui.graph.Node
            ]
        ] = signals.layout.Subgraph()

        self._layout_lookup: dict[
            signals.ui.graph.Node,
            signals.layout.Vertex
        ] = {}

        self.setLayout(QtWidgets.QGraphicsGridLayout())

    def on_cable_placed(self, cable: signals.ui.graph.PlacedCable):
        input_node, output_slot = cable.input, cable.output
        input_node.on_input_changed(output_slot.slot, input_node.signal)

        output_node = output_slot.parentItem()
        input_vertex = self._layout_lookup[input_node]
        output_vertex = self._layout_lookup[output_node]

        input_vertex.outputs.append(output_vertex)
        slot_index = output_node.signal.slots().index(output_slot.slot)
        assert slot_index > 0
        output_vertex.inputs.insert(slot_index, input_vertex)

        self.organize_nodes()

    def on_cable_removed(self, cable: signals.ui.graph.PlacedCable):
        input_node, output_slot = cable.input, cable.output
        input_node.on_input_changed(output_slot.slot, None)

        output_node = output_slot.parentItem()
        input_vertex = self._layout_lookup[input_node]
        output_vertex = self._layout_lookup[output_node]

        input_vertex.outputs.remove(output_vertex)
        slot_index = output_node.signal.slots().index(output_slot.slot)
        assert slot_index > 0
        # This caused a ValueError once when the input wasn't found.
        assert output_vertex.inputs.pop(slot_index) is input_vertex

        self.organize_nodes()

    def link_external(self, graph: signals.layout.Subgraph):
        self._layout_lookup.update({vertex.value: vertex for vertex in graph})

    def organize_nodes(self) -> None:
        self.graph.layout()
        layout = QtWidgets.QGraphicsGridLayout()
        for vertex in self.graph:
            node: signals.ui.graph.Node = vertex.value
            con: signals.ui.graph.NodeContainer = typing.cast(signals.ui.graph.NodeContainer, node.parentItem())
            layout.addItem(
                con,
                vertex.y,  # fromRow
                vertex.x,  # fromColumn
                1,  # rowSpan
                math.ceil(vertex.w)  # columnSpan
            )
        self.setLayout(layout)

    def paint(self,
              painter: QtGui.QPainter,
              option: QtWidgets.QStyleOptionGraphicsItem,
              widget: typing.Optional[QtWidgets.QWidget] = ...
              ) -> None:
        super().paint(painter, option, widget)
        if 1:
            dbgrect(self, painter, QtGui.QColorConstants.Blue)


class Wrapper(QtWidgets.QGraphicsWidget):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        source_list = DeviceList(parent=self)
        sink_list = DeviceList(parent=self)
        user_space = UserSpace(1, 1, parent=self)

        source_list.set_devices(signals.chain.dev.SourceDevice.list())
        sink_list.set_devices(signals.chain.dev.SinkDevice.list())
        user_space.link_external(source_list.graph)
        user_space.link_external(sink_list.graph)

        layout = QtWidgets.QGraphicsLinearLayout(QtCore.Qt.Orientation.Vertical)

        for item in (source_list, user_space, sink_list):
            layout.addItem(item)
            layout.setAlignment(item, QtCore.Qt.AlignHCenter)

        self.setLayout(layout)

        source_list.setZValue(10)
        sink_list.setZValue(-10)

    def paint(self,
              painter: QtGui.QPainter,
              option: QtWidgets.QStyleOptionGraphicsItem,
              widget: typing.Optional[QtWidgets.QWidget] = ...
              ) -> None:
        super().paint(painter, option, widget)
        if 1:
            dbgrect(self, painter, QtGui.QColorConstants.Yellow)


class GraphEditor(QtWidgets.QGraphicsScene):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setBackgroundBrush(signals.ui.theme.current().palette.window())
        self.addItem(Wrapper())
        self.mouse_collider = QtWidgets.QGraphicsRectItem(0, 0, 1, 1)
        self.mouse_collider.setVisible(False)
        self.addItem(self.mouse_collider)

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        self.dispatch_mouse_event(event, operator.methodcaller('mouseReleaseEvent', event))

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        self.dispatch_mouse_event(event, operator.methodcaller('mousePressEvent', event))

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        self.dispatch_mouse_event(event, operator.methodcaller('mouseMoveEvent', event))

    def dispatch_mouse_event(self,
                             event: QtWidgets.QGraphicsSceneMouseEvent,
                             event_callback: typing.Callable[[QtWidgets.QGraphicsItem], typing.Any]):

        def attempt(item):
            if event.button() != QtCore.Qt.MouseButton.NoButton and not (event.button() & item.acceptedMouseButtons()):
                return False
            else:
                event_callback(item)
                return event.isAccepted()

        grabber = self.mouseGrabberItem()
        if grabber is not None and attempt(grabber):
            pass
        else:
            self.mouse_collider.setPos(event.scenePos())
            for item in self.collidingItems(self.mouse_collider):
                if attempt(item):
                    break
