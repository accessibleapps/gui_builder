from gui_builder.widgets.wx_widgets import callback_wrapper


class LazyEvent:
    def __init__(self):
        self.calls = []
        self.skipped = False
        self.stopped = False

    def GetSelection(self):
        self.calls.append("GetSelection")
        return 7

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


def test_callback_wrapper_only_reads_requested_keyword_only_event_fields():
    event = LazyEvent()
    received = {}

    def callback(*, selection=None):
        received["selection"] = selection

    callback_wrapper(WidgetStub(), callback)(event)

    assert received == {"selection": 7}
    assert event.calls == ["GetSelection"]
