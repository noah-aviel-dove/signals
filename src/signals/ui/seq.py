import math
import typing

from PyQt5 import (
    QtCore,
    QtWidgets,
)

import signals.map


class Event(QtWidgets.QGraphicsWidget):
    # TODO: extract superclass from this and `NodeContainer`

    def __init__(self,
                 at: signals.map.Coordinates,
                 parent: typing.Optional[QtWidgets.QGraphicsItem] = None
                 ):
        super().__init__(parent=parent)
        self.at = at
        self.duration = 1
        self.velocity = 1

        self.setAcceptedMouseButtons(self.acceptedMouseButtons() | QtCore.Qt.MouseButton.LeftButton)

    @property
    def key(self) -> int:
        return self.

    def mouseReleaseEvent(self,
                          event: QtWidgets.QGraphicsSceneMouseEvent
                          ) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.duration += 1
        elif event.button() == QtCore.Qt.MouseButton.RightButton:
            self.duration -= 1
            if self.duration == 0:
                self.scene().removeItem(self)


    def mouseDoubleClickEvent(self,
                              event: QtWidgets.QGraphicsSceneMouseEvent
                              ) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.velocity = int(math.ceil(self.duration))
            self.duration = 1
        elif event.button() == QtCore.Qt.MouseButton.RightButton:
            self.scene().removeItem(self)