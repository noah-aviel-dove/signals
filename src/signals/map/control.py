import abc
import argparse
import cmd
import collections
import fnmatch
import functools
import pathlib
import shlex
import sys
import traceback
import typing

import attr
import more_itertools

import signals.chain.discovery
import signals.discovery
from signals.map import (
    BadName,
    ConnectionInfo,
    Coordinates,
    LinkedSigInfo,
    Map,
    MapLayerError,
    MappedSigInfo,
    SigState,
    SigStateItem,
    SlotInfo,
)


class NonExitingArgumentParser(argparse.ArgumentParser):

    # https://github.com/python/cpython/issues/85427
    def error(self, message: str) -> typing.NoReturn:
        raise argparse.ArgumentError(argument=None, message=message)


class Command(abc.ABC):

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
    def from_parsed_args(cls, args: argparse.Namespace) -> typing.Self:
        return cls()

    @classmethod
    def parse(cls, args: typing.Sequence[str]) -> typing.Self:
        return cls.from_parsed_args(cls.parser().parse_args(args))

    @abc.abstractmethod
    def affect(self, controller: 'Controller') -> None:
        raise NotImplementedError


S = typing.TypeVar(name='S')


@attr.s(auto_attribs=True, kw_only=True, frozen=True)
class LossyCommand(Command, typing.Generic[S], abc.ABC):
    _stash: list[S] = attr.ib(factory=list)

    @property
    def stash(self) -> S:
        return more_itertools.one(self._stash)

    def set_stash(self, stash_val: S):
        if self._stash:
            assert more_itertools.one(self._stash) == stash_val
        else:
            self._stash.append(stash_val)


class SerializingCommand(Command, abc.ABC):

    @abc.abstractmethod
    def serialize(self) -> str:
        raise NotImplementedError


class MapCommand(Command, abc.ABC):

    def affect(self, controller: 'Controller'):
        controller.command(self)

    @abc.abstractmethod
    def do(self, sip_map: Map) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def undo(self, sig_map: Map) -> None:
        raise NotImplementedError


@attr.s(auto_attribs=True, kw_only=True, frozen=True)
class FileCommand(Command, abc.ABC):
    path: pathlib.Path

    @classmethod
    @functools.lru_cache(1)
    def parser(cls) -> argparse.ArgumentParser:
        parser = super().parser()
        parser.add_argument('path', type=pathlib.Path)
        return parser

    @classmethod
    def from_parsed_args(cls, args: argparse.Namespace) -> typing.Self:
        return cls(path=args.path)


@attr.s(auto_attribs=True, kw_only=True, frozen=True)
class DeviceCommand(MapCommand, SerializingCommand, abc.ABC):
    at: Coordinates
    device_name: str

    @classmethod
    @functools.lru_cache(1)
    def parser(cls) -> argparse.ArgumentParser:
        parser = super().parser()
        parser.add_argument('at', type=Coordinates.parse)
        parser.add_argument('device_name')
        return parser

    @classmethod
    def from_parsed_args(cls, args: argparse.Namespace) -> typing.Self:
        return cls(at=args.at, device_name=args.device_name)

    def serialize(self) -> str:
        return ' '.join((
            self.name(),
            str(self.at),
            self.device_name
        ))

    def undo(self, sig_map: Map):
        sig_map.rm(self.at)


@attr.s(auto_attribs=True, kw_only=True, frozen=True)
class HistoryCommand(Command, abc.ABC):
    times: int

    @classmethod
    @functools.lru_cache(1)
    def parser(cls) -> argparse.ArgumentParser:
        parser = super().parser()
        parser.add_argument('times', type=int, nargs='?', default=1)
        return parser

    @classmethod
    def from_parsed_args(cls, args: argparse.Namespace) -> typing.Self:
        return cls(times=args.times)


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
        self._commands_by_alias = {}
        for cmd_cls in vars(cls).values():
            if signals.discovery.is_concrete_subclass(cmd_cls, Command):
                self._commands_by_alias[cmd_cls.name()] = cmd_cls
                symbol = cmd_cls.symbol()
                if symbol is not None:
                    self._commands_by_alias[symbol] = cmd_cls

    def parse(self, alias: str, args: typing.Sequence[str]) -> Command:
        try:
            cmd_cls = self._commands_by_alias[alias]
        except KeyError:
            raise BadCommand(alias, cmds=self._commands_by_alias)

        try:
            return cmd_cls.parse(args)
        except argparse.ArgumentError as e:
            raise BadCommandSyntax(e.message)

    @attr.s(auto_attribs=True, kw_only=True, frozen=True)
    class Add(MapCommand, SerializingCommand):
        """
        >>> c = CommandSet.Add.parse(['1a', 'signals.things.thing', 'foo=1', 'bar="baz"'])
        >>> c.signal
        MappedSigInfo(cls_name='signals.things.thing', state={'foo': 1, 'bar': 'baz'}, at=Coordinates(row=1, col=1))

        >>> c.serialize()
        '+ 1a signals.things.thing bar="baz" foo=1'
        """

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
            parser.add_argument('sig_state', type=SigStateItem.parse, nargs='*')
            return parser

        @classmethod
        def from_parsed_args(cls, args: argparse.Namespace) -> typing.Self:
            return cls(signal=MappedSigInfo(at=args.at,
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
    class Remove(MapCommand, LossyCommand[LinkedSigInfo]):
        """
        >>> c = CommandSet.Remove.parse(['1a'])
        >>> c.at
        Coordinates(row=1, col=1)
        """

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

        @classmethod
        def from_parsed_args(cls, args: argparse.Namespace) -> typing.Self:
            return cls(at=args.at)

        def do(self, sig_map: Map):
            sig_info = sig_map.rm(self.at)
            self.set_stash(sig_info)

        def undo(self, sig_map: Map):
            sig_map.add(self.stash)
            for connection in self.stash.links:
                sig_map.connect(connection)

    @attr.s(auto_attribs=True, kw_only=True, frozen=True)
    class Edit(MapCommand, LossyCommand[SigState]):
        """
        >>> c = CommandSet.Edit.parse(['1a', 'foo=1', 'bar="baz"'])
        >>> c.at
        Coordinates(row=1, col=1)
        >>> c.state
        {'foo': 1, 'bar': 'baz'}
        """

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
            parser.add_argument('sig_state', type=SigStateItem.parse, nargs='+', )
            return parser

        @classmethod
        def from_parsed_args(cls, args: argparse.Namespace) -> typing.Self:
            return cls(at=args.at,
                       state=SigState(args.sig_state))

        def do(self, sig_map: Map):
            old_state = sig_map.edit(at=self.at, state=self.state)
            self.set_stash(old_state)

        def undo(self, sig_map: Map):
            sig_map.edit(self.at, self.stash)

    @attr.s(auto_attribs=True, kw_only=True, frozen=True)
    class Move(MapCommand):
        """
        >>> c = CommandSet.Move.parse(['1a', '2b'])
        >>> c.at1
        Coordinates(row=1, col=1)
        >>> c.at2
        Coordinates(row=2, col=2)
        """

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

        @classmethod
        def from_parsed_args(cls, args: argparse.Namespace) -> typing.Self:
            return cls(at1=args.at1, at2=args.at2)

        def do(self, sig_map: Map):
            sig_map.mv(self.at1, self.at2)

        def undo(self, sig_map: Map):
            sig_map.mv(self.at2, self.at1)

    @attr.s(auto_attribs=True, kw_only=True, frozen=True)
    class Connect(MapCommand, SerializingCommand, LossyCommand[ConnectionInfo | None]):
        """
        >>> c = CommandSet.Connect.parse(['1a', '2b.foo'])
        >>> c.connection
        ConnectionInfo(input_at=Coordinates(row=1, col=1), output=SlotInfo(at=Coordinates(row=2, col=2), slot='foo'))

        >>> c.serialize()
        '> 1a 2b.foo'
        """

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
            parser.add_argument('output', type=SlotInfo.parse)
            return parser

        @classmethod
        def from_parsed_args(cls, args: argparse.Namespace) -> typing.Self:
            return cls(connection=ConnectionInfo(input_at=args.input_at,
                                                 output=args.output))

        def serialize(self) -> str:
            return ' '.join((
                self.symbol(),
                str(self.connection.input_at),
                str(self.connection.output)
            ))

        def do(self, sig_map: Map):
            old_input_at = sig_map.connect(self.connection)
            self.set_stash(None
                           if old_input_at is None else
                           ConnectionInfo(input_at=old_input_at,
                                          output=self.connection.output))

        def undo(self, sig_map: Map):
            sig_map.disconnect(self.connection.output)
            if self.stash is not None:
                sig_map.connect(self.stash)

    @attr.s(auto_attribs=True, kw_only=True, frozen=True)
    class Disconnect(MapCommand, LossyCommand[ConnectionInfo]):
        """
        >>> c = CommandSet.Disconnect.parse(['2b.foo'])
        >>> c.slot
        SlotInfo(at=Coordinates(row=2, col=2), slot='foo')
        """

        slot: SlotInfo

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
            parser.add_argument('slot', type=SlotInfo.parse)
            return parser

        @classmethod
        def from_parsed_args(cls, args: argparse.Namespace) -> typing.Self:
            return cls(slot=args.slot)

        def do(self, sig_map: Map):
            input_at = sig_map.disconnect(slot_info=self.slot)
            self.set_stash(ConnectionInfo(input_at=input_at, output=self.slot))

        def undo(self, sig_map: Map):
            sig_map.connect(self.stash)

    @attr.s(auto_attribs=True, kw_only=True, frozen=True)
    class Source(DeviceCommand):

        @classmethod
        def name(cls) -> str:
            return 'source'

        def do(self, sip_map: Map):
            pass

    @attr.s(auto_attribs=True, kw_only=True, frozen=True)
    class Sink(DeviceCommand):

        @classmethod
        def name(cls) -> str:
            return 'source'

        def do(self, sip_map: Map):
            pass

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
            # FIXME it would be interesting to make this undo-able
            controller.map = Map()
            old_stdin = controller.stdin
            with open(self.path) as f:
                controller.stdin = f
                try:
                    controller.cmdloop()
                finally:
                    controller.stdin = old_stdin
            controller.reset_history()

    class Show(Command):

        @classmethod
        def name(cls) -> str:
            return 'show'

        def affect(self, controller: 'Controller') -> None:
            for line in controller.dump():
                print(line, file=controller.stdout)

    class Exit(Command):

        @classmethod
        def name(cls) -> str:
            return 'exit'

        def affect(self, controller: 'Controller') -> None:
            controller.exit = True

    @attr.s(auto_attribs=True, kw_only=True, frozen=True)
    class Grep(Command):
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

        @classmethod
        def from_parsed_args(cls, args: argparse.Namespace) -> typing.Self:
            return cls(pattern=args.pattern)

        def affect(self, controller: 'Controller') -> None:
            for name in controller.grep(self.pattern):
                print(name, file=controller.stdout)


class Controller(cmd.Cmd):

    def __init__(self,
                 interactive: bool,
                 command_set: CommandSet = None,
                 map: Map = None,
                 paths: typing.Iterable[pathlib.Path] = (),
                 stdin=None,
                 stdout=None):
        super().__init__(stdin=stdin, stdout=stdout)
        self.use_rawinput = not interactive
        self.map = Map() if map is None else map
        self.command_set = CommandSet() if command_set is None else command_set
        self.library = signals.chain.discovery.Library(paths)
        self.library.scan()
        self.history = collections.deque[typing.Sequence[MapCommand]](maxlen=100)
        self.history_index = None
        self.exit = False

    @property
    def interactive(self) -> bool:
        return not self.use_rawinput

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
                cmd_ = self._parse_line(line)
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

    def command(self, cmd_: MapCommand) -> None:
        self.batch_command((cmd_,))

    def batch_command(self, batch: typing.Iterable[MapCommand]) -> None:
        batch = tuple(batch)
        self._process_batch(batch)
        if self.history_index is not None:
            while len(self.history) > self.history_index + 1:
                self.history.pop()
        self.history.append(batch)
        self.history_index = len(self.history) - 1

    def undo(self) -> None:
        if self.history_index is None:
            raise BadUndo
        else:
            batch = self.history[self.history_index]
            self._process_batch(batch, undo=True)
            self.history_index -= 1
            if self.history_index < 0:
                self.history_index = None

    def redo(self) -> None:
        target_index = 0 if self.history_index is None else self.history_index + 1
        if target_index >= len(self.history):
            raise BadRedo
        else:
            batch = self.history[target_index]
            self._process_batch(batch)
            self.history_index = target_index

    def reset_history(self):
        self.history.clear()
        self.history_index = None

    def dump(self) -> typing.Iterator[str]:
        for signal in self.map.iter_signals():
            yield self.command_set.Add(signal=signal).serialize()
        for connection in self.map.iter_connections():
            yield self.command_set.Connect(connection=connection).serialize()

    def grep(self, pattern: str) -> list[str]:
        return sorted(fnmatch.filter(self.library.names, pattern))

    def _process_batch(self, batch: typing.Sequence[MapCommand], undo: bool = False):
        # This is hopefully atomic, at least in the forward direction.
        if undo:
            batch = reversed(batch)
            for cmd in batch:
                # If any undo operation ever raises an exception, that indicates
                # something has gone terribly wrong, and the exception should
                # not be caught.
                cmd.undo(self.map)
        else:
            for i, cmd in enumerate(batch):
                try:
                    cmd.do(self.map)
                except Exception:
                    # If the batch fails partway through, roll back to previous
                    # state
                    self._process_batch(batch[:i], undo=True)
                    raise

    def _parse_line(self, line: str) -> Command:
        args = shlex.split(line)
        cmd_, *args = args
        return self.command_set.parse(cmd_, args)


if __name__ == '__main__':
    cmd_line = Controller(interactive=True,
                          command_set=CommandSet(),
                          map=Map(),
                          paths=map(pathlib.Path, sys.argv[1:]))
    cmd_line.cmdloop()
