import abc

from PyQt5 import (
    QtCore,
)


QObjectMeta = type(QtCore.QObject)


class QABCMeta(QObjectMeta, abc.ABCMeta):
    pass


class QABC(metaclass=QABCMeta):
    pass
