import itertools
import typing

from PyQt5 import (
    QtCore,
    QtGui,
    QtWidgets,
)

import signals.chain
import signals.chain.dev
import signals.chain.files
import signals.layout
import signals.map
import signals.ui
import signals.ui.geometry
import signals.ui.theme


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


# FIXME perhaps decorators could be replaced with mixins using the approach
#  demonstrated [here](https://stackoverflow.com/a/66376066/1530508) to avoid
#  metaclass conflicts
def palette_client(*,
                   pen: str | None = None,
                   brush: str | None = None,
                   pen_off: str | None = None,
                   brush_off: str | None = None
                   ):
    def decorator(cls):
        def setPalette(self, palette: QtGui.QPalette) -> None:
            # FIXME
            on = True
            nonlocal brush_off
            nonlocal pen_off
            if pen_off is None:
                pen_off = pen
            if brush_off is None:
                brush_off = brush
            if pen is not None:
                self.setPen(getattr(palette, pen if on else pen_off)().color())
            if brush is not None:
                self.setBrush(getattr(palette, brush if on else brush_off)())

        cls.setPalette = setPalette
        return cls

    return decorator


@palette_client(pen='mid', pen_off='dark')
class NodePartRect(QtWidgets.QGraphicsRectItem):
    pass


@palette_client(brush='mid', pen_off='dark')
class NodePartText(QtWidgets.QGraphicsSimpleTextItem):
    pass


@palette_client(pen='mid', pen_off='dark')
class NodePartEllipse(QtWidgets.QGraphicsEllipseItem):
    pass


@contained
class NodePartWidget(QtWidgets.QGraphicsWidget):

    def __init__(self,
                 *delegates: QtWidgets.QAbstractGraphicsShapeItem,
                 parent: QtWidgets.QGraphicsItem = None):
        super().__init__(parent=parent)
        self.delegates = delegates
        for delegate in self.delegates:
            delegate.setParentItem(self)
        self.setPreferredSize(self.delegates[0].boundingRect().size())
        self.setSizePolicy(*[QtWidgets.QSizePolicy.Fixed] * 2)
        signals.ui.theme.register(self)

    def setPalette(self, palette: QtGui.QPalette) -> None:
        super().setPalette(palette)
        for delegate in self.delegates:
            delegate.setPalette(palette)


class Node(NodePartWidget):

    def __init__(self, parent=None):
        super().__init__(
            NodePartEllipse(0, 0, 40, 40),
            parent=parent
        )
        # FIXME this should be split into a new class hierarchy for different signal interfaces
        if isinstance(self.container, signals.chain.dev.SinkDevice):
            self.setAcceptedMouseButtons(QtCore.Qt.MouseButton.NoButton)
        else:
            self.setAcceptedMouseButtons(QtCore.Qt.MouseButton.LeftButton)

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        cable = self.scene().mouseGrabberItem()
        if isinstance(cable, PlacingCable):
            if cable.container is self.container:
                cable.remove()
            else:
                event.ignore()
        else:
            PlacingCable(self.container, event.scenePos())


class PowerToggle(NodePartWidget):

    def __init__(self, parent=None):
        super().__init__(
            NodePartEllipse(0, 0, 10, 10),
            parent=parent
        )
        self.powered = None
        self.set_powered(self.container.signal.state['enabled'])
        self.setAcceptedMouseButtons(QtCore.Qt.MouseButton.LeftButton)

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        event.accept()

    def set_powered(self, powered: bool):
        self.powered = powered


class Slot(NodePartWidget):
    input_changed = QtCore.pyqtSignal(object, object, object)

    def __init__(self, slot: str, parent=None):
        label = NodePartText(slot[0])
        super().__init__(
            NodePartRect(0, 0, 10, 20),
            label,
            parent=parent
        )
        self.slot = slot
        self.input: PlacedCable | None = None
        self.setToolTip(self.slot)
        self.setAcceptedMouseButtons(QtCore.Qt.MouseButton.LeftButton)

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        item = self.scene().mouseGrabberItem()
        new_input = item if isinstance(item, PlacingCable) else None

        if (
            new_input is None
            and self.input is None
        ) or (
            new_input is not None
            and self.input is not None
            and new_input.container is self.input.container
        ):
            event.ignore()
        else:
            event.accept()
            self.input_changed.emit(self, new_input, event)


class NodeContainer(QtWidgets.QGraphicsWidget):
    spacing = 5

    power_toggled = QtCore.pyqtSignal(object)

    def __init__(self,
                 signal: signals.map.MappedSigInfo,
                 parent: typing.Optional[QtWidgets.QGraphicsItem] = None):
        super().__init__(parent=parent)
        self.signal = signal

        self.power_toggle = PowerToggle(self)
        self.node = Node(self)
        self.slots = {}
        self.cables = []
        self.placing_cable: PlacingCable | None = None

        self.set_signal(signal)
        self.setZValue(-1)

    def set_signal(self, signal: signals.map.MappedSigInfo):
        self.signal = signal
        self.slots = {slot: Slot(slot=slot) for slot in signal.slot_names()}
        slot_layout = hlayout()
        slot_layout.setSpacing(self.spacing)
        slot_layout.addItem(self.power_toggle)
        slot_layout.setAlignment(self.power_toggle, QtCore.Qt.AlignBottom)
        for slot in self.slots.values():
            slot_layout.addItem(slot)

        core_layout = vlayout()
        core_layout.setSpacing(self.spacing)
        core_layout.addItem(slot_layout)
        core_layout.addItem(self.node)

        self.setLayout(core_layout)

    def toggle_power(self) -> None:
        self.power_toggled.emit()
        # FIXME update UI, connect signal in patcher


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


class Visualizer(QtWidgets.QGraphicsRectItem):
    pass


@contained
@palette_client(pen='window', brush='mid')
class Cable(QtWidgets.QGraphicsPolygonItem):
    width = 3
    shadow_radius = 3

    def __init__(self, parent: NodeContainer):
        super().__init__(parent=parent)
        # FIXME appears underneath items to the bottom-right of origin
        #  regardless of z-value?
        self.setZValue(-2)
        signals.ui.theme.register(self)

    def setPen(self, pen: typing.Union[QtGui.QPen, QtGui.QColor, QtCore.Qt.GlobalColor, QtGui.QGradient]) -> None:
        if not isinstance(pen, QtGui.QPen):
            pen = QtGui.QPen(pen)
        pen.setWidth(self.shadow_radius)
        pen.setJoinStyle(QtCore.Qt.PenJoinStyle.MiterJoin)
        super().setPen(pen)

    def input_pos(self) -> QtCore.QPointF:
        node = self.container.node
        r = node.rect()
        return self.mapFromItem(node, QtCore.QPointF(r.center().x(), r.bottom()))

    def target_pos(self) -> QtCore.QPointF:
        raise NotImplementedError

    def remove(self) -> None:
        self.scene().removeItem(self)

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
        parent.cables.append(self)
        self.target = target
        self._update_points()

    def target_pos(self) -> QtCore.QPointF:
        r = self.target.rect()
        return self.mapFromItem(self.target, QtCore.QPointF(r.center().x(), r.top()))

    def remove(self) -> None:
        self.container.cables.remove(self)
        super().remove()

    def unplace(self, mouse_scenepos: QtCore.QPointF) -> 'PlacingCable':
        placing = PlacingCable(self.container, mouse_scenepos)
        self.remove()
        return placing


class PlacingCable(Cable):

    def __init__(self, parent: NodeContainer, mouse_scenepos: QtCore.QPointF):
        super().__init__(parent=parent)
        assert parent.placing_cable is None, parent
        parent.placing_cable = self
        self.mouse_tracking = self.mapFromScene(mouse_scenepos)
        self.setAcceptedMouseButtons(QtCore.Qt.MouseButton.LeftButton | QtCore.Qt.MouseButton.RightButton)
        self.grabMouse()
        self._update_points()

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        scene_pos = event.scenePos()
        scene_rect = self.scene().sceneRect() - QtCore.QMarginsF(*[self.width + self.shadow_radius] * 4)
        signals.ui.geometry.clip_to_rect(scene_pos, scene_rect)
        self.mouse_tracking = self.mapFromScene(scene_pos)
        self._update_points()

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            self.remove()
        else:
            event.ignore()
            # Defer left-click to widget underneath.
            # FIXME this will defer to *any* widget beneath us
            #       How about when the cable is created, emit signal to disable
            #       mouse input for all widgets besides slots?

    def target_pos(self) -> QtCore.QPointF:
        return self.mouse_tracking

    def remove(self):
        assert self.container.placing_cable is self
        self.container.placing_cable = None
        self.ungrabMouse()
        super().remove()

    def place(self, target: Slot) -> PlacedCable:
        placed = PlacedCable(self.container, target)
        self.remove()
        return placed
