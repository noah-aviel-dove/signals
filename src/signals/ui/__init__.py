import abc

from PyQt5 import (
    QtCore,
)


def dbgrect(self, p, c):
    p.setPen(c)
    p.drawRect(self.rect())
    p.drawText(self.rect(), str(self.zValue()))


QObjectMeta = type(QtCore.QObject)


class QABCMeta(QObjectMeta, abc.ABCMeta):
    pass


class QABC(metaclass=QABCMeta):
    pass
