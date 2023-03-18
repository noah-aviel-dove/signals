import importlib.util
import inspect
import pathlib
import types
import typing

_package_file = '__init__.py'
_main_file = '__main__.py'


def is_concrete_subclass(o: typing.Any, superclass: type, *, allow_abstract: bool = False) -> bool:
    return isinstance(o, type) and issubclass(o, superclass) and (allow_abstract or not inspect.isabstract(o))


def load_module(name: str, path: pathlib.Path) -> types.ModuleType:
    module = importlib.import_module(name)
    assert str(path) == module.__file__, (path, module.__file__)
    assert name == module.__name__, (name, module.__name__)
    return module


def iter_modules(path: pathlib.Path) -> typing.Iterator[types.ModuleType]:
    return _iter_modules(path, _parent_packages(path))


def _iter_modules(path: pathlib.Path, parents: typing.Sequence[str]) -> typing.Iterator[types.ModuleType]:
    if path.is_file():
        if path.name != _package_file:
            parents = (*parents, path.stem)
        yield load_module('.'.join(parents), path)
    elif path.is_dir():
        if (path / _package_file).exists():
            parents = (*parents, path.name)
            for sub_path in path.glob('*.py'):
                yield from _iter_modules(sub_path, parents)
    elif not path.exists():
        raise FileNotFoundError(path)
    else:
        raise RuntimeError(path)


def _parent_packages(path: pathlib.Path) -> list[str]:
    parents = []
    while True:
        path = path.parent
        if (path / _package_file).exists():
            parents.append(path.name)
        else:
            break
    parents.reverse()
    return parents


def iter_objects(module: types.ModuleType,
                 *,
                 include_private: bool = False
                 ) -> typing.Iterator[tuple[str, typing.Any]]:
    for k, v in vars(module).items():
        if include_private or not k.startswith('_'):
            yield k, v
