import attr

import signals.map
from signals.ui.patcher import (
    Patcher,
)
from signals.ui.graph import (
    PlacedCable,
)


class PatcherMap(signals.map.Map):

    def __init__(self, patcher: Patcher):
        super().__init__()
        self.patcher = patcher

    def add(self, info: signals.map.MappedSigInfo) -> None:
        super().add(info)

        self.patcher.expand_grid_to(info.at)
        sq = self.patcher.get_square(info.at)
        sq.set_content(info)
        self.patcher.map_changed.emit(sq.content)

    def rm(self, at: signals.map.Coordinates) -> signals.map.LinkedSigInfo:
        info = super().rm(at)

        self.patcher.get_square(at).set_content(None)
        self.patcher.map_changed.emit(None)

        return info

    def edit(self, at: signals.map.Coordinates, state: signals.map.SigState) -> signals.map.SigState:
        result = super().edit(at, state)

        container = self.patcher.get_square(at).content
        container.set_signal(attr.evolve(container.signal, state=state))

        self.patcher.map_changed.emit(container)

        return result

    def mv(self, at1: signals.map.Coordinates, at2: signals.map.Coordinates) -> None:
        super().mv(at1, at2)

        sq1 = self.patcher.get_square(at1)
        sq2 = self.patcher.get_square(at2)
        container = sq1.content
        sq1.set_content(None)
        container.set_signal(attr.evolve(container.signal, at=at2))
        sq2.set_content(container)

        self.patcher.map_changed.emit(container)

    def connect(self, info: signals.map.ConnectionInfo) -> signals.map.Coordinates | None:
        result = super().connect(info)

        new_input_container = self.patcher.get_square(info.input_at).content
        output_container = self.patcher.get_square(info.output.at).content
        slot = output_container.slots[info.output.slot]
        if slot.input is not None:
            slot.input.remove()
        slot.input = PlacedCable(new_input_container, slot)

        self.patcher.map_changed.emit(None)

        return result

    def disconnect(self, slot_info: signals.map.SlotInfo) -> signals.map.Coordinates:
        result = super().disconnect(slot_info)

        output_container = self.patcher.get_square(slot_info.at).content
        slot = output_container.slots[slot_info.slot]
        slot.input.remove()
        slot.input = None

        self.patcher.map_changed.emit(None)

        return result
