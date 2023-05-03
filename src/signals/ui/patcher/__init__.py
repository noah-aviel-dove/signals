import abc
import enum
import typing

from PyQt5 import (
    QtCore,
    QtGui,
    QtWidgets,
)

import signals.map
import signals.map.control
from signals.ui.graph import (
    NodeContainer,
)
import signals.ui.theme


class GridContext(enum.IntEnum):
    corner = 0
    row = 1
    column = 2
    body = row | column


class GridItem(QtWidgets.QGraphicsWidget):
    item_size = 100
    margin_size = 25

    def __init__(self, context: GridContext, parent: object = None):
        super().__init__(parent=parent)
        width = self.item_size if context & GridContext.row else self.margin_size
        height = self.item_size if context & GridContext.column else self.margin_size
        self.setPreferredSize(width, height)
        self.setSizePolicy(*[QtWidgets.QSizePolicy.Fixed] * 2)
        self.setFlags(self.ItemIsPanel)
        self.setActive(False)
        self.setZValue(0)
        signals.ui.theme.register(self)

    def paint(self,
              painter: QtGui.QPainter,
              option: QtWidgets.QStyleOptionGraphicsItem,
              widget: typing.Optional[QtWidgets.QWidget] = ...
              ) -> None:
        painter.setPen(self.palette().mid().color())
        r = self.rect()
        painter.drawPolyline(r.topRight(),
                             r.bottomRight(),
                             r.bottomLeft())


class Corner(GridItem):

    def __init__(self, parent=None):
        super().__init__(context=GridContext.corner, parent=parent)


class MarginLabel(GridItem):

    def __init__(self, context: GridContext, index: int, parent=None):
        super().__init__(context=context, parent=parent)
        self.index = index

    def paint(self,
              painter: QtGui.QPainter,
              option: QtWidgets.QStyleOptionGraphicsItem,
              widget: typing.Optional[QtWidgets.QWidget] = ...
              ) -> None:
        super().paint(painter, option, widget)
        painter.setOpacity(1)
        painter.setPen(self.palette().mid().color())
        painter.drawText(self.rect(),
                         QtCore.Qt.AlignCenter,
                         str(self.index))


class RowMargin(MarginLabel):

    def __init__(self, index: signals.map.CoordinateRow, parent=None):
        super().__init__(GridContext.column, index, parent)


class ColumnMargin(MarginLabel):

    def __init__(self, index: signals.map.CoordinateColumn, parent=None):
        super().__init__(GridContext.row, index, parent)


class Square(GridItem):

    def __init__(self, at: signals.map.Coordinates, parent=None):
        super().__init__(context=GridContext.body, parent=parent)
        self.at = at
        # FIXME add context menu
        self.setAcceptedMouseButtons(QtCore.Qt.MouseButton.RightButton)
        self.setAcceptHoverEvents(True)
        self.content: NodeContainer | None = None

    def hoverEnterEvent(self, event: QtWidgets.QGraphicsSceneHoverEvent) -> None:
        event.accept()
        self.setActive(True)
        self.update()

    def hoverLeaveEvent(self, event: QtWidgets.QGraphicsSceneHoverEvent) -> None:
        event.accept()
        self.setActive(False)
        self.update()

    def paint(self,
              painter: QtGui.QPainter,
              option: QtWidgets.QStyleOptionGraphicsItem,
              widget: typing.Optional[QtWidgets.QWidget] = ...
              ) -> None:
        super().paint(painter, option, widget)
        if self.isActive():
            painter.setOpacity(0.25)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(self.palette().dark())
            painter.drawRect(self.rect())

    def set_content(self, content: NodeContainer | None, rm: bool = False):
        if content is not self.content:
            if self.content is not None and rm:
                self.scene().removeItem(self.content)
            if content is not None:
                assert content.signal.at == self.at, content.signal
                content.setParentItem(self)
            self.content = content
            self.update()


class Patcher(QtWidgets.QGraphicsWidget):

    new_container = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._fill_grid(8, 8)

    def grid_layout(self) -> QtWidgets.QGraphicsGridLayout:
        layout = self.layout()
        assert isinstance(layout, QtWidgets.QGraphicsGridLayout)
        return layout

    def get_square(self, at: signals.map.Coordinates) -> Square:
        layout = self.grid_layout()
        item = layout.itemAt(at.row, at.col)
        assert isinstance(item, Square)
        return item

    def get_active_square(self) -> Square | None:
        panel = self.scene().activePanel()
        if isinstance(panel, Square):
            return panel
        else:
            return None

    def expand_grid_to(self, at: signals.map.Coordinates) -> None:
        layout = self.grid_layout()
        while at.row >= layout.rowCount():
            self._add_row(layout.columnCount())
        while at.col >= layout.columnCount():
            self._add_column(layout.rowCount())
        assert layout.rowCount() >= at.row
        assert layout.columnCount() >= at.col

    def _fill_grid(self, row_count: int, column_count: int) -> None:
        layout = QtWidgets.QGraphicsGridLayout()
        layout.setSpacing(0)

        layout.addItem(Corner(parent=self), 0, 0)
        self.setLayout(layout)

        for j in range(column_count):
            self._add_column(j + 1)

        for i in range(row_count):
            self._add_row(i + 1)

        assert layout.rowCount() == row_count + 1
        assert layout.columnCount() == column_count + 1

    def _add_row(self, row_index: int):
        row_index = signals.map.CoordinateRow(row_index)
        layout = self.grid_layout()
        layout.addItem(RowMargin(index=row_index, parent=self), row_index, 0)
        for j in range(1, layout.columnCount()):
            col_index = signals.map.CoordinateColumn(j)
            layout.addItem(Square(at=signals.map.Coordinates(row=row_index, col=col_index)), row_index, col_index)

    def _add_column(self, col_index: int):
        col_index = signals.map.CoordinateColumn(col_index)
        layout = self.grid_layout()
        layout.addItem(ColumnMargin(index=col_index, parent=self), 0, col_index)
        for i in range(1, layout.rowCount()):
            row_index = signals.map.CoordinateRow(i)
            layout.addItem(Square(at=signals.map.Coordinates(row=row_index, col=col_index)), row_index, col_index)

