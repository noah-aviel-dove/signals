import abc
import collections
import functools
import pathlib
import tempfile
import typing

import attr
import more_itertools
import numpy as np
import soundfile as sf

from signals.graph import (
    BlockLoc,
    Shape,
)


@attr.s(auto_attribs=True, frozen=True, kw_only=True)
class Request:
    sink: 'Node'
    loc: BlockLoc

    def resize(self, new_frames: int) -> typing.Self:
        return Request(sink=self.sink,
                       loc=BlockLoc(position=self.loc.position,
                                    shape=Shape(frames=new_frames, channels=self.loc.shape.channels)))


class _Slot(property):
    pass


class Node(abc.ABC):

    def __init__(self):
        self._sources = {}
        self._sinks = set()
        self.enabled = True

    @classmethod
    def slots(cls) -> list[str]:
        return [
            k
            for k in dir(cls)
            if isinstance(getattr(cls, k), _Slot)
        ]

    @property
    def sources(self) -> typing.Iterable['Node']:
        return map(self._sources.__getitem__, self.slots())

    @property
    def sinks(self) -> typing.Iterable['Node']:
        return self._sinks

    def upstream(self) -> typing.Sequence['Node']:
        return self._upstream(set())

    def _upstream(self, visited: set['Node']) -> collections.deque['Node']:
        result = collections.deque()
        for source in self.sources:
            if source not in visited:
                result.extend(source._upstream(visited))
                visited.update(result)
        assert self not in visited, 'Cycle detected'
        result.append(self)
        return result

    def request(self, source: 'Node', loc: BlockLoc) -> np.ndarray:
        block = source.respond(self._make_request(loc))
        assert block.shape <= loc.shape, (block.shape, loc.shape)
        return block

    def forward_request(self,
                        source: 'Node',
                        request: Request,
                        new_shape: typing.Optional[Shape] = None
                        ) -> np.ndarray:
        loc = request.loc if new_shape is None else BlockLoc(position=request.loc.position,
                                                             shape=new_shape)
        return self.request(source, loc)

    def forward_sample_request_to_block_request(self,
                                                source: 'Node',
                                                request: Request
                                                ) -> np.ndarray:
        return self.forward_request(source,
                                    request,
                                    Shape(channels=request.loc.shape.channels,
                                          frames=1))

    @functools.lru_cache(maxsize=2)
    def _make_request(self, loc: BlockLoc):
        return Request(sink=self, loc=loc)

    def respond(self, request: Request) -> np.ndarray:
        assert request.loc.shape
        return self._eval(request)

    def destroy(self) -> None:
        for slot in self.slots():
            delattr(self, slot)

    @abc.abstractmethod
    def _eval(self, request: Request) -> np.ndarray:
        raise NotImplementedError

    def _get_result(self, request: Request) -> np.ndarray:
        return self._eval(request)

    @property
    @abc.abstractmethod
    def channels(self) -> int:
        raise NotImplementedError


def slot(name: str) -> _Slot:
    def fget(self: Node) -> Node:
        return self._sources[name]

    def fdel(self: Node) -> None:
        old_source = self._sources.pop(name)
        old_source._sinks.remove(self)

    def fset(self: Node, source: Node) -> None:
        try:
            old_source = self._sources[name]
        except KeyError:
            pass
        else:
            old_source._sinks.remove(self)
        self._sources[name] = source
        source._sinks.add(self)

    return _Slot(fget=fget, fset=fset, fdel=fdel)


class PassThroughShape(Node, abc.ABC):

    @property
    def channels(self) -> int:
        input_shape = {source.channels for source in self.sources}
        if len(input_shape) > 1:
            input_shape.discard(1)
        return more_itertools.one(input_shape)


class NotCached(RuntimeError):
    pass


class BlockCachingNode(Node, abc.ABC):

    def __init__(self):
        super().__init__()
        self._block_cache = None
        self._block_cache_position = None
        self._block_cache_users = set()

    def _read_block_cache(self, request: Request) -> np.ndarray:
        if (
            self._block_cache is not None
            and self._block_cache_position == request.loc.position
            and self._block_cache.shape[0] >= request.loc.shape[0]
        ):
            return self._block_cache
        else:
            raise NotCached

    def _write_block_cache(self, block: np.ndarray, request: Request) -> None:
        sinks = list(self.sinks)
        if len(sinks) > 1:
            self._block_cache = block
            self._block_cache_position = request.loc.position
            self._block_cache_users = set(sinks)
            self._block_cache_users.remove(request.sink)

    def _use_block_cache(self, request: Request) -> None:
        self._block_cache_users.remove(request.sink)
        if not self._block_cache_users:
            self._block_cache = None

    def respond(self, request: Request) -> np.ndarray:
        try:
            result = self._read_block_cache(request)
        except NotCached:
            result = self._get_result(request)
            self._write_block_cache(result, request)
        else:
            self._use_block_cache(request)
        return result


class SoundFileBase(Node, abc.ABC):

    def __init__(self):
        super().__init__()
        self._buffer = None

    @property
    @abc.abstractmethod
    def _sample_path(self) -> pathlib.Path:
        raise NotImplementedError

    def _open(self, mode: str, position: int = 0) -> None:
        if self._buffer is None:
            self._buffer = sf.SoundFile(file=self._sample_path, mode=mode)
            self._open(mode, position)
        elif self._buffer.mode != mode:
            self._close()
            self._open(mode, position)
        else:
            assert self._buffer.mode == mode, self._buffer
            sought_postion = self._buffer.seek(position)
            assert position == sought_postion, (position, sought_postion)

    def _close(self) -> None:
        self._buffer.close()
        self._buffer = None

    def destroy(self) -> None:
        super().destroy()
        self._close()


class SoundFileReader(SoundFileBase, abc.ABC):

    def _read(self, request: Request) -> np.ndarray:
        self._open('r', request.loc.position)
        shape = request.loc.shape
        return self._buffer.read(frames=shape.frames)


class SoundFileWriter(SoundFileBase, abc.ABC):

    def _write(self, request: Request, block: np.ndarray) -> None:
        self._open('w', request.loc.position)
        self._buffer.write(block)


class BufferCachingNode(SoundFileReader, SoundFileWriter, BlockCachingNode, abc.ABC):

    def __init__(self):
        super().__init__()
        self.recording = False

    @functools.cached_property
    def _sample_path(self) -> pathlib.Path:
        return pathlib.Path(tempfile.mktemp(prefix='.'.join([
            'signals',
            'buffer_cache',
            type(self).__name__,
            id(self)
        ])))

    def _get_result(self, request: Request) -> np.ndarray:
        if self.recording:
            result = super()._get_result(request)
            self._write(request, result)
        else:
            result = self._read(request)
        return result
