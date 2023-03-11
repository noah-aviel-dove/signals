import typing

from PyQt5 import (
    QtCore,
    QtGui,
)
import numpy as np

origin = QtCore.QPointF(0, 0)


def circ(a: float,
         r: float = 1,
         c: QtCore.QPointF = origin,
         ) -> QtCore.QPointF:
    return c + QtCore.QPointF(r * np.cos(a), r * np.sin(a))


def regular_polygon(n: int,
                    r: float = 1,
                    a0: float = 0,
                    c: QtCore.QPointF = origin,
                    ) -> QtGui.QPolygonF:
    poly = QtGui.QPolygonF()
    for a in np.linspace(a0, a0 + 2 * np.pi, n, endpoint=False):
        poly.append(circ(a, r, c))
    return poly


def inset_chevron(a: float = 0,
                  r: float = 1,
                  s: float = 0.5,
                  c: QtCore.QPointF = origin,
                  ) -> list[QtCore.QPointF]:
    return [
        circ(a + s * np.pi / 2, r, c),
        circ(-a, r * s, c),
        circ(a - s * np.pi / 2, r, c),
    ]


def tribar_polyline(s1: QtCore.QPointF, s2: QtCore.QPointF) -> list[QtCore.QPointF]:
    midx, midy = (s1.x() + s2.x()) // 2, (s1.y() + s2.y()) // 2
    delta = s2 - s1
    sy, sx = np.sign(delta.y()), np.sign(delta.x())
    if abs(delta.x()) < abs(delta.y()):
        leg1 = abs(midx - s1.x()) * sy
        leg2 = abs(midx - s2.x()) * sy
        c1 = QtCore.QPointF(s1.x(), midy - leg1)
        c2 = QtCore.QPointF(s2.x(), midy + leg2)
    else:
        leg1 = abs(midy - s1.y()) * sx
        leg2 = abs(midy - s2.y()) * sx
        c1 = QtCore.QPointF(s1.x() + leg1, midy)
        c2 = QtCore.QPointF(s2.x() - leg2, midy)
    return [s1, c1, c2, s2]


def tribar_polygon(s1: QtCore.QPointF, s2: QtCore.QPointF, radius: float) -> QtGui.QPolygonF:
    delta = s2 - s1
    sign = -np.sign(delta.x()) * np.sign(delta.y())
    if abs(delta.x()) < abs(delta.y()):
        offset_tips = QtCore.QPointF(radius, 0)
        a_bends = np.pi / 8 * sign
    else:
        offset_tips = QtCore.QPointF(radius, radius * sign) / np.sqrt(2)
        a_bends = np.pi * 3 / 8 * sign
    offset_bends = circ(a_bends, radius / np.cos(np.pi / 8))
    p1, p2, p3, p4 = tribar_polyline(s1, s2)
    return QtGui.QPolygonF([
        p1 + offset_tips, p2 + offset_bends, p3 + offset_bends, p4 + offset_tips,
        p4 - offset_tips, p3 - offset_bends, p2 - offset_bends, p1 - offset_tips
    ])


R = typing.TypeVar(name='R', bound=QtCore.QRect | QtCore.QRectF)


def scale_rect(rect: R, s: float) -> R:
    scaled = QtCore.QRectF(0.0, 0.0, rect.width() * s, rect.height() * s)
    scaled.moveCenter(rect.center())
    return scaled if isinstance(scaled, QtCore.QRectF) else scaled.toRect()


def rect_containing_points(*ps: QtCore.QPoint) -> QtCore.QRect:
    coords = np.array(list(zip(*[(p.x(), p.y()) for p in ps])))
    (minx, miny), (maxx, maxy) = coords.min(1), coords.max(1)
    return QtCore.QRect(minx, miny, maxx - minx + 1, maxy - miny + 1)


def clip_to_rect(p: QtCore.QPointF, r: QtCore.QRectF):
    p.setX(max(p.x(), r.left()))
    p.setX(min(p.x(), r.right()))
    p.setY(max(p.y(), r.top()))
    p.setY(min(p.y(), r.bottom()))
    assert r.contains(p)
