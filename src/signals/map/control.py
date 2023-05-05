import abc
import argparse
import cmd
import collections
import fnmatch
import functools
import hashlib
import itertools
import pathlib
import shlex
import sys
import traceback
import typing

import attr

import signals.chain.dev
import signals.chain.discovery
import signals.discovery
from signals.map import (
    BadName,
    ConnectionInfo,
    Coordinates,
    LinkedSigInfo,
    Map,
    MapLayerError,
    MappedDevInfo,
    MappedSigInfo,
    PlaybackState,
    PortInfo,
    SigState,
    SigStateItem,
)


class NonExitingArgumentParser(argparse.ArgumentParser):

    # https://github.com/python/cpython/issues/85427
    def error(self, message: str) -> typing.NoReturn:
        raise argparse.ArgumentError(argument=None, message=message)


class Command(abc.ABC):

    @abc.abstractmethod
    def affect(self, controller: 'Controller') -> None:
        raise NotImplementedError


class LineCommand(Command, abc.ABC):

    @classmethod
    def symbol(cls) -> str | None:
        return None

    @classmethod
    @abc.abstractmethod
    def name(cls) -> str:
        raise NotImplementedError

    @classmethod
    def parser(cls) -> argparse.ArgumentParser:
        return NonExitingArgumentParser()

    @classmethod
    def process_args(cls, args: argparse.Namespace) -> dict:
        return vars(args)


S = typing.TypeVar(name='S')


@attr.s(auto_attribs=True, kw_only=True, frozen=True)
class LossyCommand(Command, typing.Generic[S], abc.ABC):
    _stash: list[S] = attr.ib(factory=list)

    def pop_stash(self) -> S:
        return self._stash.pop()

    def push_stash(self, stash_val: S) -> None:
        self._stash.append(stash_val)


class SerializingCommand(Command, abc.ABC):

    @abc.abstractmethod
    def serialize(self) -> str:
        raise NotImplementedError


class MapCommand(Command, abc.ABC):

    def affect(self, controller: 'Controller'):
        controller.map_command(self)

    @abc.abstractmethod
    def do(self, sig_map: Map) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def undo(self, sig_map: Map) -> None:
        raise NotImplementedError


@attr.s(auto_attribs=True, kw_only=True, frozen=True)
class BatchMapCommand(MapCommand):
    cmds: typing.Sequence[MapCommand]
    label: str

    def undo(self, sig_map: Map) -> None:
        self._rollback(sig_map, self.cmds)

    def do(self, sig_map: Map) -> None:
        # This is hopefully atomic
        for i, cmd in enumerate(self.cmds):
            try:
                cmd.do(sig_map)
            except Exception:
                # If the batch fails partway through, roll back to previous
                # state
                self._rollback(sig_map, self.cmds[:i])
                raise

    def _rollback(self, sig_map: Map, cmds: typing.Reversible[MapCommand]):
        for cmd in reversed(self.cmds):
            # If any undo operation ever raises an exception, that indicates
            # something has gone terribly wrong, and the exception should
            # not be caught.
            cmd.undo(sig_map)


@attr.s(auto_attribs=True, kw_only=True, frozen=True)
class FileCommand(LineCommand, abc.ABC):
    path: pathlib.Path

    @classmethod
    @functools.lru_cache(1)
    def parser(cls) -> argparse.ArgumentParser:
        parser = super().parser()
        parser.add_argument('path', type=pathlib.Path)
        return parser


@attr.s(auto_attribs=True, kw_only=True, frozen=True)
class DeviceAssociationCommand(LineCommand, SerializingCommand, abc.ABC):
    at: Coordinates
    device_name: str

    @classmethod
    @functools.lru_cache(1)
    def parser(cls) -> argparse.ArgumentParser:
        parser = super().parser()
        parser.add_argument('at', type=Coordinates.parse)
        parser.add_argument('device_name')
        return parser

    def serialize(self) -> str:
        return ' '.join((
            self.name(),
            str(self.at),
            self.device_name
        ))

    def affect(self, controller: 'Controller') -> None:
        controller.map_command(CommandSet.Add(signal=self._get_device(controller)))

    @abc.abstractmethod
    def _get_device(self, controller: 'Controller') -> MappedDevInfo:
        raise NotImplementedError


@attr.s(auto_attribs=True, kw_only=True, frozen=True)
class DeviceListCommand(LineCommand, abc.ABC):

    @classmethod
    @functools.lru_cache(1)
    def parser(cls) -> argparse.ArgumentParser:
        parser = super().parser()
        return parser

    def affect(self, controller: 'Controller') -> None:
        for device in self._get_devices(controller.rack):
            print(str(device), file=controller.stdout)

    @abc.abstractmethod
    def _get_devices(self, rack: signals.chain.discovery.Rack) -> list[signals.chain.dev.DeviceInfo]:
        raise NotImplementedError


@attr.s(auto_attribs=True, kw_only=True, frozen=True)
class HistoryCommand(LineCommand, abc.ABC):
    times: int

    @classmethod
    @functools.lru_cache(1)
    def parser(cls) -> argparse.ArgumentParser:
        parser = super().parser()
        parser.add_argument('times', type=int, nargs='?', default=1)
        return parser


@attr.s(auto_attribs=True, kw_only=True, frozen=True)
class PlaybackCommand(LineCommand, abc.ABC):
    at: Coordinates

    @classmethod
    def parser(cls) -> argparse.ArgumentParser:
        parser = super().parser()
        parser.add_argument('at', type=Coordinates.parse)
        return parser

    @abc.abstractmethod
    def target_state(self) -> PlaybackState:
        raise NotImplementedError

    def affect(self, controller: 'Controller') -> None:
        controller.map.playback(self.at, self.target_state())


class CommandError(MapLayerError):
    pass


class BadCommandSyntax(CommandError):
    pass


class BadCommand(CommandError, BadName):

    def __init__(self, cmd_: str, cmds: typing.Iterable[str]):
        super().__init__(cmd_, options=cmds)


class BadHistory(CommandError, abc.ABC):
    pass


class BadUndo(BadHistory):

    def __init__(self):
        super().__init__('Cannot undo any further')


class BadRedo(BadHistory):

    def __init__(self):
        super().__init__('Cannot redo any further')


class CommandSet:

    def __init__(self):
        cls = type(self)
        self._commands_by_alias: dict[str, type[LineCommand]] = {}
        for cmd_cls in vars(cls).values():
            if signals.discovery.is_concrete_subclass(cmd_cls, LineCommand):
                self._commands_by_alias[cmd_cls.name()] = cmd_cls
                symbol = cmd_cls.symbol()
                if symbol is not None:
                    self._commands_by_alias[symbol] = cmd_cls

    def parse(self, alias: str, args: typing.Sequence[str]) -> LineCommand:
        try:
            cmd_cls = self._commands_by_alias[alias]
        except KeyError:
            raise BadCommand(alias, cmds=self._commands_by_alias)

        try:
            args = cmd_cls.process_args(cmd_cls.parser().parse_args(args))
        except argparse.ArgumentError as e:
            raise BadCommandSyntax(e.message)

        return self._create_cmd(cmd_cls, args)

    def _create_cmd(self, cmd_cls: type[LineCommand], cmd_args: dict) -> LineCommand:
        return cmd_cls(**cmd_args)

    @attr.s(auto_attribs=True, kw_only=True, frozen=True)
    class Add(LineCommand, MapCommand, SerializingCommand):
        signal: MappedSigInfo

        @classmethod
        def symbol(cls) -> str:
            return '+'

        @classmethod
        def name(cls) -> str:
            return 'add'

        @classmethod
        @functools.lru_cache(1)
        def parser(cls) -> argparse.ArgumentParser:
            parser = super().parser()
            parser.add_argument('at', type=Coordinates.parse)
            parser.add_argument('sig_cls', type=str)
            parser.add_argument('sig_state', type=SigStateItem.parse, nargs='*', )
            return parser

        @classmethod
        def process_args(cls, args: argparse.Namespace) -> dict:
            return dict(signal=MappedSigInfo(at=args.at,
                                             cls_name=args.sig_cls,
                                             state=SigState(args.sig_state)))

        def serialize(self) -> str:
            return ' '.join((
                self.symbol(),
                str(self.signal.at),
                self.signal.cls_name,
                str(self.signal.state)
            ))

        def do(self, sig_map: Map):
            sig_map.add(self.signal)

        def undo(self, sig_map: Map):
            sig_map.rm(self.signal.at)

    @attr.s(auto_attribs=True, kw_only=True, frozen=True)
    class Remove(LineCommand, MapCommand, LossyCommand[LinkedSigInfo]):
        at: Coordinates

        @classmethod
        def symbol(cls) -> str:
            return '-'

        @classmethod
        def name(cls) -> str:
            return 'rm'

        @classmethod
        @functools.lru_cache(1)
        def parser(cls) -> argparse.ArgumentParser:
            parser = super().parser()
            parser.add_argument('at', type=Coordinates.parse)
            return parser

        def do(self, sig_map: Map):
            sig_info = sig_map.rm(self.at)
            self.push_stash(sig_info)

        def undo(self, sig_map: Map):
            stash = self.pop_stash()
            sig_map.add(stash)
            for connection in stash.links:
                sig_map.connect(connection)

    @attr.s(auto_attribs=True, kw_only=True, frozen=True)
    class Edit(LineCommand, MapCommand, LossyCommand[SigState]):
        at: Coordinates
        state: SigState

        @classmethod
        def symbol(cls) -> str:
            return '*'

        @classmethod
        def name(cls) -> str:
            return 'ed'

        @classmethod
        @functools.lru_cache(1)
        def parser(cls) -> argparse.ArgumentParser:
            parser = super().parser()
            parser.add_argument('at', type=Coordinates.parse)
            parser.add_argument('sig_state', type=SigStateItem.parse, nargs='+')
            return parser

        @classmethod
        def process_args(cls, args: argparse.Namespace) -> dict:
            # Unfortunately, can't validate state keys without knowing the signal type
            return dict(at=args.at,
                        state=SigState(args.sig_state))

        def do(self, sig_map: Map):
            old_state = sig_map.edit(at=self.at, state=self.state)
            self.push_stash(old_state)

        def undo(self, sig_map: Map):
            sig_map.edit(self.at, self.pop_stash())

    @attr.s(auto_attribs=True, kw_only=True, frozen=True)
    class Move(LineCommand, MapCommand):
        at1: Coordinates
        at2: Coordinates

        @classmethod
        def symbol(cls) -> str:
            return '='

        @classmethod
        def name(cls) -> str:
            return 'mv'

        @classmethod
        @functools.lru_cache(1)
        def parser(cls) -> argparse.ArgumentParser:
            parser = super().parser()
            parser.add_argument('at1', type=Coordinates.parse)
            parser.add_argument('at2', type=Coordinates.parse)
            return parser

        def do(self, sig_map: Map):
            sig_map.mv(self.at1, self.at2)

        def undo(self, sig_map: Map):
            sig_map.mv(self.at2, self.at1)

    @attr.s(auto_attribs=True, kw_only=True, frozen=True)
    class Connect(LineCommand, MapCommand, SerializingCommand, LossyCommand[ConnectionInfo | None]):
        connection: ConnectionInfo

        @classmethod
        def symbol(cls) -> str:
            return '>'

        @classmethod
        def name(cls) -> str:
            return 'con'

        @classmethod
        @functools.lru_cache(1)
        def parser(cls) -> argparse.ArgumentParser:
            parser = super().parser()
            parser.add_argument('input_at', type=Coordinates.parse)
            parser.add_argument('output', type=PortInfo.parse)
            return parser

        @classmethod
        def process_args(cls, args: argparse.Namespace) -> dict:
            return dict(connection=ConnectionInfo(input_at=args.input_at,
                                                  output=args.output))

        def serialize(self) -> str:
            return ' '.join((
                self.symbol(),
                str(self.connection.input_at),
                str(self.connection.output)
            ))

        def do(self, sig_map: Map):
            old_input_at = sig_map.connect(self.connection)
            self.push_stash(None
                            if old_input_at is None else
                            ConnectionInfo(input_at=old_input_at,
                                           output=self.connection.output))

        def undo(self, sig_map: Map):
            sig_map.disconnect(self.connection.output)
            stash = self.pop_stash()
            if stash is not None:
                sig_map.connect(stash)

    @attr.s(auto_attribs=True, kw_only=True, frozen=True)
    class Disconnect(LineCommand, MapCommand, LossyCommand[ConnectionInfo]):
        port: PortInfo

        @classmethod
        def symbol(cls) -> str:
            return '>/'

        @classmethod
        def name(cls) -> str:
            return 'discon'

        @classmethod
        @functools.lru_cache(1)
        def parser(cls) -> argparse.ArgumentParser:
            parser = super().parser()
            parser.add_argument('port', type=PortInfo.parse)
            return parser

        def do(self, sig_map: Map):
            input_at = sig_map.disconnect(info=self.port)
            self.push_stash(ConnectionInfo(input_at=input_at, output=self.port))

        def undo(self, sig_map: Map):
            sig_map.connect(self.pop_stash())

    class Source(DeviceAssociationCommand):

        @classmethod
        def name(cls) -> str:
            return 'source'

        def _get_device(self, controller: 'Controller') -> MappedDevInfo:
            return MappedDevInfo.for_source(at=self.at,
                                            device=controller.rack.get_source(self.device_name))

    class Sink(DeviceAssociationCommand):

        @classmethod
        def name(cls) -> str:
            return 'sink'

        def _get_device(self, controller: 'Controller') -> MappedDevInfo:
            return MappedDevInfo.for_sink(at=self.at,
                                          device=controller.rack.get_sink(self.device_name))

    class Undo(HistoryCommand):

        @classmethod
        def symbol(cls) -> str:
            return '<<'

        @classmethod
        def name(cls) -> str:
            return 'undo'

        def affect(self, controller):
            for _ in range(self.times):
                controller.undo()

    class Redo(HistoryCommand):

        @classmethod
        def symbol(cls) -> str:
            return '>>'

        @classmethod
        def name(cls) -> str:
            return 'redo'

        def affect(self, controller):
            for _ in range(self.times):
                controller.redo()

    class Init(LineCommand):

        @classmethod
        def name(cls) -> str:
            return 'init'

        def affect(self, controller: 'Controller') -> None:
            controller.map_command(self.batch_clear(controller))

        @classmethod
        def batch_clear(cls, controller: 'Controller') -> BatchMapCommand:
            cmds = []
            sig_map = controller.map
            for connection in sig_map.iter_connections():
                cmds.append(CommandSet.Disconnect(port=connection.output))
            for signal in itertools.chain(sig_map.iter_sinks(),
                                          sig_map.iter_sources(),
                                          sig_map.iter_signals()):
                cmds.append(CommandSet.Remove(at=signal.at))
            return BatchMapCommand(cmds=cmds, label=cls.name())

    class Save(FileCommand):

        @classmethod
        def name(cls) -> str:
            return 'save'

        def affect(self, controller):
            with open(self.path, 'w') as f:
                for line in controller.dump():
                    f.write(line + '\n')

    class Load(FileCommand):

        @classmethod
        def name(cls) -> str:
            return 'load'

        def affect(self, controller: 'Controller') -> None:
            controller.map_command(self.batch_load(self.path, controller))

        @classmethod
        def batch_load(cls, path: pathlib.Path, controller: 'Controller') -> BatchMapCommand:
            clear = controller.command_set.Init.batch_clear(controller)
            cmds = list(clear.cmds)
            dump_cmds = {'add', 'con', 'source', 'sink'}
            with open(path) as f:
                for line in f:
                    cmd_ = controller.parse_line(line)
                    if isinstance(cmd_, MapCommand) and isinstance(cmd_, LineCommand) and cmd_.name() in dump_cmds:
                        cmds.append(cmd_)
                    else:
                        raise BadCommand(line, dump_cmds)
            return BatchMapCommand(cmds=cmds, label=cls.name())

    class Show(LineCommand):

        @classmethod
        def name(cls) -> str:
            return 'show'

        def affect(self, controller: 'Controller') -> None:
            for line in controller.dump():
                print(line, file=controller.stdout)

    class Hash(LineCommand):

        @classmethod
        def name(cls) -> str:
            return 'hash'

        def affect(self, controller: 'Controller') -> None:
            print(controller.hash(), file=controller.stdout)

    class Exit(LineCommand):

        @classmethod
        def name(cls) -> str:
            return 'exit'

        def affect(self, controller: 'Controller') -> None:
            controller.exit = True

    @attr.s(auto_attribs=True, kw_only=True, frozen=True)
    class Grep(LineCommand):
        pattern: str

        @classmethod
        def name(cls) -> str:
            return 'grep'

        @classmethod
        @functools.lru_cache(1)
        def parser(cls) -> argparse.ArgumentParser:
            parser = super().parser()
            parser.add_argument('pattern')
            return parser

        def affect(self, controller: 'Controller') -> None:
            for name in controller.grep(self.pattern):
                print(name, file=controller.stdout)

    class Sources(DeviceListCommand):

        @classmethod
        def name(cls) -> str:
            return 'sources'

        def _get_devices(self, rack: signals.chain.discovery.Rack) -> list[signals.chain.dev.DeviceInfo]:
            return rack.sources()

    class Sinks(DeviceListCommand):

        @classmethod
        def name(cls) -> str:
            return 'sinks'

        def _get_devices(self, rack: signals.chain.discovery.Rack) -> list[signals.chain.dev.DeviceInfo]:
            return rack.sinks()

    class PlayCommand(PlaybackCommand):

        @classmethod
        def name(cls) -> str:
            return 'play'

        def target_state(self) -> PlaybackState:
            return PlaybackState(position=None, active=True)

    class PauseCommand(PlaybackCommand):

        @classmethod
        def name(cls) -> str:
            return 'pause'

        def target_state(self) -> PlaybackState:
            return PlaybackState(position=None, active=False)

    class StopCommand(PlaybackCommand):

        @classmethod
        def name(cls) -> str:
            return 'stop'

        def target_state(self) -> PlaybackState:
            return PlaybackState(position=0, active=False)

        class SeekCommand(PlaybackCommand):
            position: int

            @classmethod
            def name(cls) -> str:
                return 'seek'

            @classmethod
            def parser(cls) -> argparse.ArgumentParser:
                parser = super().parser()
                parser.add_argument('position', type=int)
                return parser

            def target_state(self) -> PlaybackState:
                return PlaybackState(position=self.position, active=None)


class Controller(cmd.Cmd):

    def __init__(self,
                 *,
                 interactive: bool,
                 command_set: CommandSet = None,
                 map: Map = None,
                 paths: typing.Iterable[pathlib.Path] = (),
                 stdin=None,
                 stdout=None):
        super().__init__(stdin=stdin, stdout=stdout)
        self.use_rawinput = False
        self.modcount = 0
        self.interactive = interactive
        self.map = Map() if map is None else map
        self.command_set = CommandSet() if command_set is None else command_set
        self.library = signals.chain.discovery.Library(paths)
        self.library.scan()
        self.rack = signals.chain.discovery.Rack()
        self.rack.scan()
        self.history = collections.deque[MapCommand](maxlen=100)
        self.history_index = None
        self.exit = False

    @property
    def prompt(self) -> str:
        return 'signals: ' if self.interactive else ''

    def emptyline(self) -> bool:
        return False

    def default(self, line: str) -> bool:
        if line == 'EOF':
            self.exit = True
        else:
            try:
                cmd_ = self.parse_line(line)
                cmd_.affect(self)
            except MapLayerError as e:
                if self.interactive:
                    print(str(e), file=self.stdout)
                else:
                    raise
            except Exception:
                print('Unexpected error:', file=self.stdout)
                print(traceback.format_exc(), file=self.stdout)
                if not self.interactive:
                    raise

        return self.exit

    def confirm(self, msg: str, default: bool = True) -> bool:
        choices = '(Y/n)'
        if not default:
            choices = choices.swapcase()
        print(msg, choices, file=self.stdout)
        line = self.stdin.readline().rstrip('\r\n').casefold()
        if line == 'y':
            return True
        elif line == 'n':
            return False
        elif line == '':
            return default
        else:
            print('Invalid response', file=self.stdout)

    def map_command(self, cmd_: MapCommand) -> None:
        cmd_.do(self.map)
        self.modcount += 1
        if self.history_index is not None:
            while len(self.history) > self.history_index + 1:
                self.history.pop()
        self.history.append(cmd_)
        self.history_index = len(self.history) - 1

    def undo(self) -> None:
        if self.history_index is None:
            raise BadUndo
        else:
            cmd_ = self.history[self.history_index]
            cmd_.undo(self.map)
            self.modcount -= 1
            assert self.modcount >= 0
            self.history_index -= 1
            if self.history_index < 0:
                self.history_index = None

    def redo(self) -> None:
        target_index = 0 if self.history_index is None else self.history_index + 1
        if target_index >= len(self.history):
            raise BadRedo
        else:
            cmd_ = self.history[target_index]
            cmd_.do(self.map)
            self.modcount += 1
            self.history_index = target_index

    def reset_history(self):
        self.history.clear()
        self.history_index = None
        self.modcount = 0

    def dump(self) -> typing.Iterator[str]:
        sources = list(self.map.iter_sources())
        sources.sort()
        for source in sources:
            yield self.command_set.Source(at=source.at, device_name=source.device.name).serialize()
        sinks = list(self.map.iter_sinks())
        sinks.sort()
        for sink in sinks:
            yield self.command_set.Sink(at=sink.at, device_name=sink.device.name).serialize()
        signals = list(self.map.iter_signals())
        signals.sort()
        for signal in signals:
            yield self.command_set.Add(signal=signal).serialize()
        connections = list(self.map.iter_connections())
        connections.sort()
        for connection in connections:
            yield self.command_set.Connect(connection=connection).serialize()

    def grep(self, pattern: str) -> list[str]:
        return sorted(fnmatch.filter(self.library.names, pattern))

    def parse_line(self, line: str) -> Command:
        args = shlex.split(line)
        cmd_, *args = args
        return self.command_set.parse(cmd_, args)

    def hash(self) -> str:
        state_hash = hashlib.sha3_256()
        for line in self.dump():
            state_hash.update(line.encode())
        return state_hash.hexdigest()


if __name__ == '__main__':
    cmd_line = Controller(interactive=True,
                          command_set=CommandSet(),
                          map=Map(),
                          paths=map(pathlib.Path, sys.argv[1:]))
    cmd_line.cmdloop()
