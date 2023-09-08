import attr
import numpy as np

from signals import (
    SignalFlags,
)
from signals.chain import (
    BadStateValue,
    Emitter,
    Request,
    Shape,
    state,
)


def _validate_array(instance, attribute, new_value):
    if not (isinstance(new_value, np.ndarray) and new_value.ndim == 2):
        raise BadStateValue(instance, attribute.name, new_value, 'must be a 2D array')


class Fixed(Emitter):
    @state
    class State(Emitter.State):
        value: np.ndarray = attr.ib(
            factory=Emitter.empty_result,
            validator=_validate_array,
            on_setattr=attr.setters.validate
        )

    @classmethod
    def flags(cls) -> SignalFlags:
        return super().flags() | SignalFlags.CONSTANT

    @property
    def channels(self) -> int:
        return Shape.of_array(self._state.value).channels

    def _eval(self, request: Request) -> np.ndarray:
        return self._state.value
