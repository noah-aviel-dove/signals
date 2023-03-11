import abc
import pathlib
import pkgutil
import typing

import more_itertools
import sounddevice as sd

import signals.chain
import signals.chain.dev
import signals.discovery


class DiscoveryError(Exception):
    pass


class BadSignal(DiscoveryError, abc.ABC):
    pass


class BadSyntax(BadSignal):

    def __init__(self, cls_qualname: str):
        super().__init__(f'{cls_qualname!r} is not a valid signal name')


class BadPath(BadSignal):

    def __init__(self, cls_qualname: str, reason: str):
        super().__init__(f'Failed to load {cls_qualname!r}: {reason}')


class InvalidObject(BadSignal):

    def __init__(self, cls_qualname: str, o: object):
        super().__init__(f'Python object {cls_qualname}={o!r} is not a signal')


class BadDevice(DiscoveryError):
    pass


class BadDeviceName(BadDevice):

    def __init__(self, name):
        super().__init__(f'There is not device named {name!r}')


class BadDeviceChannels(BadDevice):
    pass


class NotASource(BadDeviceChannels):

    def __init__(self, name):
        super().__init__(f'Device {name!r} does not support input')


class NotASink(BadDeviceChannels):

    def __init__(self, name):
        super().__init__(f'Device {name!r} does not support output')


class Library:

    def __init__(self, paths: typing.Iterable[pathlib.Path]):
        self.paths = {pathlib.Path(signals.chain.__file__).parent}
        self.paths.update(paths)
        self.names = []

    def _filter(self, name: str, val: typing.Any) -> bool:
        # FIXME Might need to refactor the Signal hierarchy to make devices a stem group.
        return (
            signals.discovery.is_concrete_subclass(val, signals.chain.Signal)
            and not issubclass(val, signals.chain.dev.Device)
        )

    def scan(self) -> None:
        self.names[:] = [
            f'{module.__name__}.{k}'
            for path in self.paths
            for module in signals.discovery.iter_modules(path)
            for k, v in signals.discovery.iter_objects(module)
            if self._filter(k, v)
        ]


class Rack:

    def __init__(self):
        self.devices = []

    def scan(self):
        self.devices[:] = (signals.chain.dev.DeviceInfo(**info) for info in sd.query_devices())

    def get_device(self, name: str) -> signals.chain.dev.DeviceInfo:
        return more_itertools.one((device for device in self.devices if device.name == name),
                                  too_short=BadDevice(name))

    def get_source(self, name: str) -> signals.chain.dev.DeviceInfo:
        device = self.get_device(name)
        if device.is_source:
            return device
        else:
            raise NotASource(name)

    def get_sink(self, name: str) -> signals.chain.dev.DeviceInfo:
        device = self.get_device(name)
        if device.is_sink:
            return device
        else:
            raise NotASink(name)

    def sources(self) -> list[signals.chain.dev.DeviceInfo]:
        return sorted(filter(lambda dev: dev.is_source, self.devices))

    def sinks(self) -> list[signals.chain.dev.DeviceInfo]:
        return sorted(filter(lambda dev: dev.is_sink, self.devices))


def load_signal(qualname: str) -> type[signals.chain.Signal]:
    try:
        cls = pkgutil.resolve_name(qualname)
    except ValueError:
        raise BadSyntax(qualname)
    except (AttributeError, ImportError) as e:
        raise BadPath(qualname, e.args[0])

    if signals.discovery.is_concrete_subclass(cls, signals.chain.Signal):
        return cls
    else:
        raise InvalidObject(qualname, cls)
