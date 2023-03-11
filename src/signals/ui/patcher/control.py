import abc

import attr

import signals.map.control
from signals.ui.graph import PlacedCable
from signals.ui.patcher import Patcher

super_cls = signals.map.control.CommandSet

# Not currently using this approach but keeping the code for now
@attr.s(auto_attribs=True, frozen=True, kw_only=True)
class PatcherCommand(signals.map.control.Command, abc.ABC):
    patcher: Patcher


class PatcherCommandSet(super_cls):

    def __init__(self, patcher: Patcher):
        super().__init__()
        self.patcher = patcher

    def _create_cmd(self,
                    cmd_cls: type[PatcherCommand],
                    cmd_args: dict
                    ) -> PatcherCommand:
        return cmd_cls(patcher=self.patcher, **cmd_args)

    @attr.s(auto_attribs=True, frozen=True, kw_only=True)
    class Add(PatcherCommand, super_cls.Add):

        def do(self, sig_map: signals.map.Map):
            super().do(sig_map)
            self.patcher.expand_grid_to(self.signal.at)
            self.patcher.get_square(self.signal.at).set_content(self.signal)

        def undo(self, sig_map: signals.map.Map):
            super().undo(sig_map)
            # FIXME consider shrinking the grid (to a minimum of the initial size)
            #  if there are gaps at the edges
            self.patcher.get_square(self.signal.at).set_content(None)

    @attr.s(auto_attribs=True, frozen=True, kw_only=True)
    class Remove(PatcherCommand, super_cls.Remove):

        def do(self, sig_map: signals.map.Map):
            super().do(sig_map)
            self.patcher.get_square(self.at).set_content(None)

        def undo(self, sig_map: signals.map.Map):
            super().undo(sig_map)
            self.patcher.get_square(self.at).set_content(self.stash)

    @attr.s(auto_attribs=True, frozen=True, kw_only=True)
    class Move(PatcherCommand, super_cls.Move):

        def do(self, sig_map: signals.map.Map):
            super().do(sig_map)
            self.patcher.get_square(self.at1).set_content(None)
            self.patcher.get_square(self.at2).set

        def undo(self, sig_map: signals.map.Map):
            super().undo(sig_map)
            self.patcher.get_square(self.at).set_content(self.stash)
