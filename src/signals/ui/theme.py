import enum
import typing

from PyQt5 import (
    QtCore,
    QtGui,
    QtWidgets,
)
import attr


@attr.s(auto_attribs=True, frozen=True, kw_only=True)
class SimplePalette:
    back: QtGui.QColor
    dark: QtGui.QColor
    mid: QtGui.QColor
    light: QtGui.QColor

    _mapping = {
        'back': ('base', 'window', 'button'),
        'dark': ('dark',),
        'mid': ('mid', 'text', 'windowText'),
        'light': ('light', 'bright_text'),
    }

    _palette_params = [
        'windowText',
        'button',
        'light',
        'dark',
        'mid',
        'text',
        'bright_text',
        'base',
        'window'
    ]

    assert sorted(sum(_mapping.values(), start=())) == sorted(_palette_params)

    def to_qpalette(self) -> QtGui.QPalette:
        args = {
            arg: getattr(self, attrib)
            for attrib, args in self._mapping.items()
            for arg in args
        }
        return QtGui.QPalette(*[args[param] for param in self._palette_params])


@attr.s(auto_attribs=True, frozen=True, kw_only=True)
class PartialSimplePalette:
    back: QtGui.QColor | None = attr.ib(default=None)
    dark: QtGui.QColor | None = attr.ib(default=None)
    mid: QtGui.QColor | None = attr.ib(default=None)
    light: QtGui.QColor | None = attr.ib(default=None)

    def __or__(self, other: typing.Self) -> typing.Self | SimplePalette:
        fields = attr.asdict(self)
        merged = {}
        for attrib, value in fields.items():
            other_value = getattr(other, attrib)
            if value is not None and other_value is not None:
                raise ValueError(value, other_value)
            elif other_value is None:
                merged[attrib] = value
            else:
                merged[attrib] = other_value

        if None in merged.values():
            return PartialSimplePalette(**merged)
        else:
            return SimplePalette(**merged)


class ThemeType(enum.Enum):
    HIGH_CONTRAST = PartialSimplePalette(back=QtGui.QColorConstants.Black, light=QtGui.QColorConstants.White)
    SOFT_DARK = PartialSimplePalette()
    SOFT_BRIGHT = PartialSimplePalette()


@attr.s(auto_attribs=True, frozen=True, kw_only=True)
class Theme:
    name: str
    type: ThemeType
    palette: QtGui.QPalette

    @classmethod
    def create(cls,
               name: str,
               type: ThemeType,
               palette: PartialSimplePalette
               ):
        palette |= type.value
        if isinstance(palette, SimplePalette):
            return cls(name=name,
                       type=type,
                       palette=palette.to_qpalette())
        else:
            raise ValueError(palette)


RED = Theme.create('Vampire', ThemeType.HIGH_CONTRAST, PartialSimplePalette(
    dark=QtGui.QColorConstants.DarkMagenta,
    mid=QtGui.QColorConstants.Red
))

GREEN = Theme.create('Cyborg', ThemeType.HIGH_CONTRAST, PartialSimplePalette(
    dark=QtGui.QColorConstants.DarkGreen,
    mid=QtGui.QColorConstants.Green
))

WHITE = Theme.create('Bones', ThemeType.HIGH_CONTRAST, PartialSimplePalette(
    dark=QtGui.QColorConstants.DarkGray,
    mid=QtGui.QColorConstants.LightGray,
))


class ThemeController(QtCore.QObject):
    theme_set = QtCore.pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.theme = None

    def set_theme(self, theme: Theme):
        self.theme = theme
        self.theme_set.emit(theme.palette)


controller = ThemeController()


def register(user: QtWidgets.QWidget | QtWidgets.QGraphicsWidget | QtWidgets.QGraphicsScene) -> None:
    user.setPalette(controller.theme.palette)
    controller.theme_set.connect(user.setPalette)
