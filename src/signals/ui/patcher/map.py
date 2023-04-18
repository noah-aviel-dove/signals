import matplotlib.pyplot as plt

import signals.map
from signals.ui.graph import (
    NodeContainer,
    PlacedCable,
)
from signals.ui.patcher import (
    Patcher,
)


class PatcherMap(signals.map.Map):

    def __init__(self, patcher: Patcher):
        super().__init__()
        self.patcher = patcher

    def add(self, info: signals.map.MappedSigInfo) -> None:
        super().add(info)

        self.patcher.expand_grid_to(info.at)
        sq = self.patcher.get_square(info.at)
        container = NodeContainer(info)
        sq.set_content(container)
        self.patcher.new_container.emit(container)

    def rm(self, at: signals.map.Coordinates) -> signals.map.LinkedSigInfo:
        info = super().rm(at)

        self.patcher.get_square(at).set_content(None)

        return info

    def edit(self, at: signals.map.Coordinates, state: signals.map.SigState) -> signals.map.SigState:
        result = super().edit(at, state)

        container = self.patcher.get_square(at).content
        container.change_state(state)

        return result

    def mv(self, at1: signals.map.Coordinates, at2: signals.map.Coordinates) -> None:
        # FIXME first container disappears if two are swapped
        super().mv(at1, at2)

        sq1 = self.patcher.get_square(at1)
        sq2 = self.patcher.get_square(at2)
        container1 = sq1.content
        container2 = sq2.content

        if container1 is not None:
            container1.relocate(sq2, at2)
        if container2 is not None:
            container2.relocate(sq1, at1)

        sq1.set_content(container2)
        sq2.set_content(container1)

    def connect(self, info: signals.map.ConnectionInfo) -> signals.map.Coordinates | None:
        result = super().connect(info)

        new_input_container = self.patcher.get_square(info.input_at).content
        output_container = self.patcher.get_square(info.output.at).content
        port = output_container.ports[info.output.port]
        if port.input is not None:
            port.input.remove()
        port.input = PlacedCable(new_input_container, port)

        return result

    def disconnect(self, info: signals.map.PortInfo) -> signals.map.Coordinates:
        result = super().disconnect(info)

        output_container = self.patcher.get_square(info.at).content
        port = output_container.ports[info.port]
        port.clear()

        return result
