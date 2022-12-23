import enum

from PyQt5 import QtGui
import attr

import signals


class ThemeType(enum.Enum):
    HIGH_CONTRAST = enum.auto()
    SOFT_DARK = enum.auto()
    SOFT_BRIGHT = enum.auto()


@attr.s(auto_attribs=True, frozen=True, kw_only=True)
class Theme:
    name: str
    type: ThemeType

    back: QtGui.QColor
    front: QtGui.QColor
    on: QtGui.QColor
    off: QtGui.QColor


RED = Theme(name='Vampire',
            type=ThemeType.HIGH_CONTRAST,
            back=QtGui.QColorConstants.Black,
            front=QtGui.QColorConstants.White,
            on=QtGui.QColorConstants.Red,
            off=QtGui.QColorConstants.DarkMagenta)

GREEN = Theme(name='Cyborg',
              type=ThemeType.HIGH_CONTRAST,
              back=QtGui.QColorConstants.Black,
              front=QtGui.QColorConstants.White,
              on=QtGui.QColorConstants.Green,
              off=QtGui.QColorConstants.DarkGreen)

WHITE = Theme(name='Bones',
              type=ThemeType.HIGH_CONTRAST,
              back=QtGui.QColorConstants.Black,
              front=QtGui.QColorConstants.White,
              on=QtGui.QColorConstants.White,
              off=QtGui.QColorConstants.DarkGray)


def current() -> Theme:
    return signals.app().project.config.theme
