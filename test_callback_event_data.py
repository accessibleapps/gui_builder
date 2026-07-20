import sys
import types


class WxStub(types.ModuleType):
    def __getattr__(self, name):
        value = type(name, (), {})
        setattr(self, name, value)
        return value


def install_wx_stub():
    wx = WxStub("wx")
    wx.__path__ = []
    for name in (
        "Window",
        "EvtHandler",
        "Event",
        "PyEventBinder",
        "StaticText",
        "Gauge",
        "Control",
        "ControlWithItems",
        "TextCtrl",
        "Panel",
        "Slider",
        "ListCtrl",
        "TopLevelWindow",
        "Dialog",
        "Frame",
        "MDIParentFrame",
        "MDIChildFrame",
        "Notebook",
        "MenuBar",
        "Menu",
        "MenuItem",
    ):
        setattr(wx, name, type(name, (), {}))
    for index, name in enumerate(
        (
            "ID_OK",
            "ID_APPLY",
            "ID_CANCEL",
            "ID_CLOSE",
            "ID_FIND",
            "ID_YES",
            "ID_NO",
            "ID_ANY",
        ),
        start=1,
    ):
        setattr(wx, name, index)

    wx_lib = types.ModuleType("wx.lib")
    intctrl = types.ModuleType("wx.lib.intctrl")
    intctrl.IntCtrl = type("IntCtrl", (), {})
    sized_controls = types.ModuleType("wx.lib.sized_controls")
    sized_controls.SizedDialog = type("SizedDialog", (), {})
    sized_controls.SizedPanel = type("SizedPanel", (), {})
    sized_controls.SizedFrame = type("SizedFrame", (), {})
    calendar = types.ModuleType("wx.lib.calendar")
    adv = WxStub("wx.adv")
    adv.__path__ = []
    wx.adv = adv

    sys.modules.setdefault("wx", wx)
    sys.modules.setdefault("wx.lib", wx_lib)
    sys.modules.setdefault("wx.lib.intctrl", intctrl)
    sys.modules.setdefault("wx.lib.sized_controls", sized_controls)
    sys.modules.setdefault("wx.lib.calendar", calendar)
    sys.modules.setdefault("wx.adv", adv)


try:
    import wx  # noqa: F401
except ModuleNotFoundError:
    install_wx_stub()

from gui_builder.widgets.wx_widgets import callback_wrapper


class LazyEvent:
    def __init__(self):
        self.calls = []
        self.skipped = False
        self.stopped = False

    def GetSelection(self):
        self.calls.append("GetSelection")
        return 7

    def GetKeyCode(self):
        self.calls.append("GetKeyCode")
        return 315

    def GetString(self):
        self.calls.append("GetString")
        raise AssertionError("unrequested getter was called")

    def Skip(self):
        self.skipped = True

    def StopPropagation(self):
        self.stopped = True


class WidgetStub:
    def find_event_target(self, callback):
        raise ValueError("callback is not attached to this widget")


class CompleteEvent:
    def __init__(self):
        self.calls = []

    def GetSelection(self):
        self.calls.append("GetSelection")
        return 7

    def GetString(self):
        self.calls.append("GetString")
        return "value"

    def Skip(self):
        self.calls.append("Skip")

    def StopPropagation(self):
        self.calls.append("StopPropagation")


class CountingWidgetStub:
    def __init__(self, event_target):
        self.calls = []
        self.event_target = event_target

    def find_event_target(self, callback):
        self.calls.append(callback)
        return self.event_target


def test_callback_wrapper_only_reads_requested_defaulted_event_fields():
    event = LazyEvent()
    received = {}

    def callback(selection=None):
        received["selection"] = selection

    callback_wrapper(WidgetStub(), callback)(event)

    assert received == {"selection": 7}
    assert event.calls == ["GetSelection"]
    assert event.skipped is True
    assert event.stopped is False


def test_callback_wrapper_event_argument_does_not_read_event_getters():
    event = LazyEvent()
    received = {}

    def callback(event=None):
        received["event"] = event

    callback_wrapper(WidgetStub(), callback)(event)

    assert received == {"event": event}
    assert event.calls == []


def test_callback_wrapper_named_event_with_kwargs_does_not_read_event_getters():
    event = LazyEvent()
    received = {}

    def callback(event=None, **kwargs):
        received["event"] = event
        received["kwargs"] = kwargs

    callback_wrapper(WidgetStub(), callback)(event)

    assert received == {"event": event, "kwargs": {}}
    assert event.calls == []


def test_callback_wrapper_bare_kwargs_still_receives_all_event_data():
    event = CompleteEvent()
    received = {}

    def callback(**kwargs):
        received.update(kwargs)

    callback_wrapper(WidgetStub(), callback)(event)

    assert received == {"selection": 7, "string": "value", "event": event}
    assert event.calls == ["GetSelection", "GetString", "Skip"]


def test_callback_wrapper_reuses_event_target_lookup_for_repeated_events():
    event_target = object()
    widget = CountingWidgetStub(event_target)
    received = []

    def callback(self, event=None):
        received.append((self, event))

    wrapper = callback_wrapper(widget, callback)
    first_event = LazyEvent()
    second_event = LazyEvent()

    wrapper(first_event)
    wrapper(second_event)

    assert received == [(event_target, first_event), (event_target, second_event)]
    assert widget.calls == [callback]


def test_callback_wrapper_bound_key_callback_skips_event_target_lookup():
    event_target = object()
    widget = CountingWidgetStub(event_target)
    received = []

    class Handler:
        def callback(self, key_code=None):
            received.append((self, key_code))

    handler = Handler()
    event = LazyEvent()

    callback_wrapper(widget, handler.callback)(event)

    assert received == [(handler, 315)]
    assert widget.calls == []
    assert event.calls == ["GetKeyCode"]


def test_callback_wrapper_only_reads_requested_keyword_only_event_fields():
    event = LazyEvent()
    received = {}

    def callback(*, selection=None):
        received["selection"] = selection

    callback_wrapper(WidgetStub(), callback)(event)

    assert received == {"selection": 7}
    assert event.calls == ["GetSelection"]
