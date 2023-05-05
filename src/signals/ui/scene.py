import abc
import operator
import typing

from PyQt5 import (
    QtCore,
    QtGui,
    QtWidgets,
)

import signals.chain
import signals.chain.dev
import signals.layout
import signals.ui.graph
import signals.ui.graph
import signals.ui.theme


class Scene(QtWidgets.QGraphicsScene):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        signals.ui.theme.register(self)
        self.mouse_collider = QtWidgets.QGraphicsRectItem(0, 0, 1, 1)
        self.mouse_collider.setVisible(False)
        self.addItem(self.mouse_collider)

    def setPalette(self, palette: QtGui.QPalette) -> None:
        super().setPalette(palette)
        self.setBackgroundBrush(palette.window())

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        self.dispatch_mouse_event(event, operator.methodcaller('mouseReleaseEvent', event))

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        self.dispatch_mouse_event(event, operator.methodcaller('mousePressEvent', event))

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        # Dispatch hover events, etc
        super().mouseMoveEvent(event)
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
                # For unknown reasons, a `QObject` sometimes included in the
                # list, causing an AttributeError. Additionally, while non-widget
                # graphics items do define mouse event methods, they are protected
                # and calling them raises a RuntimeError.
                if isinstance(item, QtWidgets.QGraphicsWidget) and attempt(item):
                    break
            # The scene appears to jump around when clicking, I think because
            # it's trying to keep this item on screen. This is an attempt tp
            # prevent that.
            self.mouse_collider.setPos(0, 0)
