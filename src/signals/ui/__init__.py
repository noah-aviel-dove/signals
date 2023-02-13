import typing

from PyQt5 import (
    QtCore,
    QtWidgets,
)
import numpy as np


def dbgrect(self, p, c):
    p.setPen(c)
    p.drawRect(self.rect())
    p.drawText(self.rect(), str(self.zValue()))


def set_name(w: QtCore.QObject):
    w.setObjectName(f'{w.__class__.__name__}-{id(w)}')


W = typing.TypeVar(name='W', bound=QtWidgets.QWidget)

R = typing.TypeVar(name='R', bound=QtCore.QRect | QtCore.QRectF)


def scale_rect(rect: R, s: float) -> R:
    scaled = QtCore.QRectF(0.0, 0.0, rect.width() * s, rect.height() * s)
    scaled.moveCenter(rect.center())
    return scaled if isinstance(scaled, QtCore.QRectF) else scaled.toRect()


def rect_containing_points(*ps: QtCore.QPoint) -> QtCore.QRect:
    coords = np.array(list(zip(*[(p.x(), p.y()) for p in ps])))
    (minx, miny), (maxx, maxy) = coords.min(1), coords.max(1)
    return QtCore.QRect(minx, miny, maxx - minx + 1, maxy - miny + 1)


def global_rect(w: QtWidgets.QWidget) -> QtCore.QRect:
    r = w.rect()
    return QtCore.QRect(w.mapToGlobal(r.topLeft()), r.size())
