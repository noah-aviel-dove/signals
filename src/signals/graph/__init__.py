import typing

import attr
import numpy as np


class Shape(typing.NamedTuple):
    """
    >>> s = Shape(frames=10, channels=2)
    >>> s
    Shape(frames=10, channels=2)
    >>> t = tuple(s)
    >>> t
    (10, 2)
    >>> s == t
    True
    >>> s <= t
    True
    >>> s >= t
    True
    >>> s == (1, 1)
    False
    >>> (1, 1) <= Shape(frames=s.frames, channels=1) <= s
    True
    >>> (1, 1) <= Shape(frames=1, channels=s.channels) <= s
    True
    >>> (0, 0) <= s
    False
    >>> Shape(frames=3, channels=2) <= s
    False
    >>> Shape(frames=10, channels=0) <= s
    False
    """
    frames: int
    channels: int

    def __le__(self, other: tuple[int, int]) -> bool:
        return (self[0] in (1, other[0])) and (self[1] in (1, other[1]))

    def __ge__(self, other: tuple[int, int]) -> bool:
        return (other[0] in (1, self[0])) and (other[1] in (1, self[1]))

    @classmethod
    def of_array(cls, array: np.ndarray) -> typing.Self:
        return cls(*array.shape)

    def grow(self, new_frames: int) -> typing.Self:
        return Shape(frames=self.frames + new_frames,
                     channels=self.channels)


@attr.s(auto_attribs=True, frozen=True, kw_only=True)
class BlockLoc:
    position: int
    shape: Shape

    @property
    def stop(self) -> int:
        return self.position + self.shape[0]
