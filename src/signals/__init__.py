import functools
import json
import pathlib
import typing

from PyQt5 import (
    QtWidgets,
)
import attr

import signals.ui.theme
import signals.chain


class _Env:

    @property
    def package_root(self) -> pathlib.Path:
        return pathlib.Path(__file__).parent

    @property
    def src_root(self) -> pathlib.Path:
        return self.package_root.parent

    @property
    def project_root(self) -> pathlib.Path:
        return self.src_root.parent


env = _Env()


@attr.s(auto_attribs=True, frozen=False, kw_only=True)
class Config:
    theme_: str

    @property
    def theme(self) -> signals.ui.theme.Theme:
        return getattr(signals.ui.theme, self.theme_)

    @classmethod
    def load(cls, path: pathlib.Path) -> typing.Self:
        with path.open('r') as f:
            return cls(**json.load(f))

    def save(self, path: pathlib.Path) -> None:
        with path.open('w') as f:
            json.dump(attr.asdict(self), f, indent=2)


@attr.s(auto_attribs=True, frozen=False, kw_only=True)
class Project:
    path: pathlib.Path

    @property
    def name(self) -> str:
        return self.path.stem

    @functools.cached_property
    def config(self) -> Config:
        return Config.load(self.path / 'config.json')

    @classmethod
    def default(cls) -> typing.Self:
        return cls(path=env.project_root / 'templates' / 'default')


class App(QtWidgets.QApplication):

    def __init__(self, argv: list[str]):
        super().__init__(argv)
        self.project = Project.default()

    @classmethod
    def instance(cls) -> typing.Optional[typing.Self]:
        return super().instance()

    def load(self, project: Project):
        self.project = project
        signals.ui.theme.controller.set_theme(project.config.theme)


def app() -> typing.Optional[App]:
    return App.instance()
