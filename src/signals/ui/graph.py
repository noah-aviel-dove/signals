import itertools
import typing

from PyQt5 import (
    QtCore,
    QtGui,
    QtWidgets,
)

import signals.chain
import signals.chain.files
import signals.chain.dev
import signals.layout
import signals.ui
import signals.ui.theme
import signals.ui.geometry


def hlayout() -> QtWidgets.QGraphicsLinearLayout:
    return QtWidgets.QGraphicsLinearLayout(QtCore.Qt.Orientation.Horizontal)


def vlayout() -> QtWidgets.QGraphicsLinearLayout:
    return QtWidgets.QGraphicsLinearLayout(QtCore.Qt.Orientation.Vertical)


def contained(cls):
    def _get_container_parent(self) -> 'NodeContainer':
        p = self.parentItem()
        assert isinstance(p, NodeContainer), p
        return p

    cls.container = property(fget=_get_container_parent)
    return cls


@contained
class NodePart(QtWidgets.QGraphicsWidget):

    def __init__(self,
                 *delegates: (QtWidgets.QGraphicsEllipseItem
                              | QtWidgets.QGraphicsRectItem
                              | QtWidgets.QGraphicsSimpleTextItem),
                 parent: QtWidgets.QGraphicsItem = None):
        super().__init__(parent=parent)
        self.delegates = delegates
        for delegate in self.delegates:
            delegate.setParentItem(self)
        self.setPreferredSize(self.delegates[0].rect().size())
        self.setSizePolicy(*[QtWidgets.QSizePolicy.Fixed] * 2)

    def set_color(self, pen):
        for delegate in self.delegates:
            delegate.setPen(pen)


class Node(NodePart):

    def __init__(self, parent=None):
        super().__init__(
            QtWidgets.QGraphicsEllipseItem(0, 0, 40, 40),
            parent=parent
        )
        if isinstance(self.container.signal, signals.chain.dev.SinkDevice):
            self.setAcceptedMouseButtons(QtCore.Qt.MouseButton.NoButton)
        else:
            self.setAcceptedMouseButtons(QtCore.Qt.MouseButton.LeftButton)

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        event.accept()
        self.container.add_cable()


class PowerToggle(NodePart):

    def __init__(self, parent=None):
        super().__init__(
            QtWidgets.QGraphicsEllipseItem(0, 0, 10, 10),
            parent=parent
        )
        self.setAcceptedMouseButtons(QtCore.Qt.MouseButton.LeftButton)

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        event.accept()
        self.container.on_power_toggled()


class Slot(NodePart):

    def __init__(self, slot: str, parent=None):
        label = QtWidgets.QGraphicsSimpleTextItem(slot[0])
        super().__init__(
            QtWidgets.QGraphicsRectItem(0, 0, 10, 20),
            label,
            parent=parent
        )
        self.slot = slot
        self.setToolTip(self.slot)
        # self.size() is controlled by layout, still zero in initializer
        label.setX(self.preferredSize().width() / 2)

        self.setAcceptedMouseButtons(QtCore.Qt.MouseButton.LeftButton)


class NodeContainer(QtWidgets.QGraphicsWidget):
    spacing = 5

    def __init__(self,
                 signal: signals.chain.Signal,
                 parent: typing.Optional[QtWidgets.QGraphicsItem] = None):
        super().__init__(parent=parent)

        self.signal = signal

        self.power_toggle = PowerToggle()
        self.node = Node(self)
        self.slots = [Slot(slot=slot) for slot in signal.slots()]
        self.cables = []

        slot_layout = hlayout()
        slot_layout.setSpacing(self.spacing)
        slot_layout.addItem(self.power_toggle)
        slot_layout.setAlignment(self.power_toggle, QtCore.Qt.AlignBottom)
        for slot in self.slots:
            slot_layout.addItem(slot)

        core_layout = vlayout()
        core_layout.setSpacing(self.spacing)
        core_layout.addItem(slot_layout)
        core_layout.addItem(self.node)

        self.setLayout(core_layout)

        self.set_theme(signals.ui.theme.current())
        self.set_appearance()

    def on_power_toggled(self):
        self.signal.enabled = not self.signal.enabled
        self.set_appearance()

    def add_cable(self):
        cable = PlacingCable(self)
        self.cables.append(cable)
        self.set_appearance()

    def remove_cable(self, cable: 'Cable'):
        self.cables.remove(cable)
        self.scene().removeItem(cable)

    def on_input_changed(self, source: Slot) -> None:
        if source in self.slots:
            # FIXME this is obviously fucked
            setattr(self.signal, source.slot, input_signal)

    def set_theme(self, theme: signals.ui.theme):
        self.setPalette(theme.palette)

    def set_appearance(self):
        pen = self.palette().mid() if self.signal.enabled else self.palette().dark()
        color = pen.color()
        for item in (self.node, self.power_toggle, *self.slots):
            item.set_color(color)
        for cable in self.cables:
            cable.pen().setColor(self.palette().window().color())
            cable.setBrush(color)


class RateIndicator(QtWidgets.QGraphicsRectItem):

    def __init__(self, pos: QtCore.QPointF, parent: Node):
        super().__init__(parent=parent, x=pos.x(), y=pos.y(), w=20, h=10)

    def paint(self,
              painter: QtGui.QPainter,
              option: QtWidgets.QStyleOptionGraphicsItem,
              widget: typing.Optional[QtWidgets.QWidget] = ...
              ) -> None:
        rates = signals.chain.RequestRate
        rate = typing.cast(Node, self.parentItem()).signal.rate
        # FIXME add rate indicators
        if rate is rates.FRAME:
            pass
        elif rate is rates.BLOCK:
            super().paint(painter, option, widget)
        elif rate is rates.UNKNOWN:
            pass
        elif rate is rates.UNUSED_FRAME:
            pass


class BufferCacheControl(QtWidgets.QGraphicsRectItem):
    pass


class EventControl(QtWidgets.QGraphicsLineItem):
    pass


class EventTrigger(EventControl):
    pass


class EventCaster(EventControl):
    pass


class Visualizer(QtWidgets.QGraphicsRectItem):
    pass


@contained
class Cable(QtWidgets.QGraphicsPolygonItem):
    width = 3
    shadow_radius = 3

    def __init__(self, parent: NodeContainer):
        super().__init__(parent=parent)
        self.pen().setWidth(self.shadow_radius)
        self.pen().setJoinStyle(QtCore.Qt.PenJoinStyle.MiterJoin)

    def input_pos(self) -> QtCore.QPointF:
        node = self.container.node
        r = node.rect()
        return self.mapFromItem(node, QtCore.QPointF(r.center().x(), r.bottom()))

    def target_pos(self) -> QtCore.QPointF:
        raise NotImplementedError

    def _update_points(self):
        self.setPolygon(
            signals.ui.geometry.tribar_polygon(
                self.input_pos(),
                self.target_pos(),
                self.width
            )
        )


class PlacedCable(Cable):

    def __init__(self, parent: NodeContainer, target: Slot):
        super().__init__(parent=parent)
        self.target = target
        self._update_points()

    def target_pos(self) -> QtCore.QPointF:
        r = self.target.rect()
        return QtCore.QPointF(r.center().x(), r.top())

    def unplace(self) -> 'PlacingCable':
        return PlacingCable(self.container)


class PlacingCable(Cable):

    def __init__(self, parent: NodeContainer):
        super().__init__(parent=parent)
        self.mouse_tracking = QtCore.QPointF()
        self.setAcceptedMouseButtons(QtCore.Qt.MouseButton.LeftButton | QtCore.Qt.MouseButton.RightButton)
        self.grabMouse()

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        self.mouse_tracking = self.mapFromScene(event.scenePos())
        self._update_points()

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            self.container.remove_cable(self)
        else:
            pass
            # Defer left-click to widget underneath.
            # FIXME this will defer to *any* widget beneath us
            #       How about when the cable is created, emit signal to disable
            #       mouse input for all widgets besides slots?

    def target_pos(self) -> QtCore.QPointF:
        return self.mouse_tracking

    def place(self, target: Slot) -> PlacedCable:
        self.ungrabMouse()
        return PlacedCable(self.container, target)
