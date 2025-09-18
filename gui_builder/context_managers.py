from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .widgets.wx_widgets import WXWidget


class FreezeAndThaw(object):
    def __init__(self, to_freeze: WXWidget):
        self.to_freeze = to_freeze

    def __enter__(self):
        self.to_freeze.freeze()
        return self

    def __exit__(self, *args):
        self.to_freeze.thaw()


class DisplayAndDestroy(object):
    def __init__(self, to_display):
        self.to_display = to_display

    def __enter__(self):
        return self.to_display.show_modal()

    def __exit(self, *args):
        self.to_display.destroy()
