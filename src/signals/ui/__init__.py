import typing

from PyQt5 import (
    QtCore,
    QtGui,
    QtWidgets,
)
import numpy as np


def set_name(w: QtCore.QObject):
    w.setObjectName(f'{w.__class__.__name__}-{id(w)}')


W = typing.TypeVar(name='W', bound=QtWidgets.QWidget)

origin: QtCore.QPoint = QtCore.QPoint(0, 0)


def circ(a: float,
         r: float = 1,
         c: QtCore.QPoint = origin,
         ) -> QtCore.QPoint:
    return c + QtCore.QPoint(r * np.cos(a), r * np.sin(a))


def make_regular_polygon(n: int,
                         r: float = 1,
                         a0: float = 0,
                         c: QtCore.QPoint = origin,
                         ) -> QtGui.QPolygon:
    poly = QtGui.QPolygon()
    for a in np.linspace(a0, a0 + 2 * np.pi, n, endpoint=False):
        poly.append(circ(a, r, c))
    return poly


def make_inset_chevron(a: float = 0,
                       r: float = 1,
                       s: float = 0.5,
                       c: QtCore.QPoint = origin,
                       ) -> list[QtCore.QPoint]:
    return [
        circ(a + s * np.pi / 2, r, c),
        circ(-a, r * s, c),
        circ(a - s * np.pi / 2, r, c),
    ]


def scale_rect(rect: QtCore.QRect, s: float) -> QtCore.QRect:
    scaled = QtCore.QRect(0, 0, round(rect.width() * s), round(rect.height() * s))
    scaled.moveCenter(rect.center())
    return scaled


def rect_containing_points(*ps: QtCore.QPoint) -> QtCore.QRect:
    coords = np.array(list(zip(*[(p.x(), p.y()) for p in ps])))
    (minx, miny), (maxx, maxy) = coords.min(1), coords.max(1)
    return QtCore.QRect(minx, miny, maxx - minx + 1, maxy - miny + 1)


def global_rect(w: QtWidgets.QWidget) -> QtCore.QRect:
    r = w.rect()
    return QtCore.QRect(w.mapToGlobal(r.topLeft()), r.size())
