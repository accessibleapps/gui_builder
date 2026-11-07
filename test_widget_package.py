"""Exercise the restored package through real field and form consumers."""

import pytest
import wx

from gui_builder import fields, forms
from gui_builder.widgets import wx_widgets


class Label:
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text


@pytest.fixture(scope="module")
def app():
    application = wx.App.Get() or wx.App()
    yield application


def test_fields_render_labels_visibility_callbacks_and_refresh(app):
    caption = Label("Original")
    received = []

    class Window(forms.SizedFrame):
        text = fields.Text(label=caption)
        button = fields.Button(label="Run")

        @button.add_callback()
        def clicked(self, event=None):
            received.append(event)
            return True

    window = Window(parent=None, title="Package integration")
    try:
        window.render()
        assert window.text.label == "Original"
        assert window.text.widget.label_control.GetLabel() == "Original"
        window.text.set_label(Label("Changed"))
        assert window.text.get_label() == "Changed"
        window.text.set_value("Keep this text")
        window.text.set_accessible_label(Label("Accessible"))
        assert window.text.get_value() == "Keep this text"
        assert window.text.get_label() == "Changed"
        window.text.hide()
        assert not window.text.widget.control.IsShown()
        assert not window.text.widget.label_control.IsShown()
        window.text.show()
        assert window.text.widget.control.IsShown()
        assert window.text.widget.label_control.IsShown()
        caption.text = "Refreshed"
        window.refresh()
        assert window.text.get_label() == "Refreshed"
        event = wx.CommandEvent(wx.EVT_BUTTON.typeId, window.button.widget.control.GetId())
        window.button.widget.control.GetEventHandler().ProcessEvent(event)
        assert received == [event]
    finally:
        window.widget.control.Destroy()


def test_accessible_label_uses_window_name_on_older_wx():
    class LegacyControl:
        def SetName(self, name):
            self.name = name

    class Field:
        pass

    field = Field()
    widget = wx_widgets.WXWidget(field=field)
    widget.control = LegacyControl()
    widget.set_accessible_label(Label("Accessible"))
    assert widget.control.name == "Accessible"


def test_menu_refresh_keeps_hotkey(app):
    caption = Label("Original")

    class Menu(forms.Menu):
        action = fields.MenuItem(label=caption, hotkey="Ctrl+R")

    class MenuBar(forms.MenuBar):
        menu = Menu(label=caption)

    class Window(forms.SizedFrame):
        menu_bar = MenuBar()

    window = Window(parent=None, title="Menu integration")
    try:
        window.render()
        caption.text = "Refreshed"
        window.refresh()
        menu_bar = window.menu_bar.widget.control
        assert menu_bar.GetMenuLabel(0) == "Refreshed"
        assert menu_bar.GetMenu(0).GetMenuItems()[0].GetItemLabel() == "Refreshed\tCtrl+R"
    finally:
        window.widget.control.Destroy()


def test_responsive_panel_uses_shared_widget_contract(app):
    class Panel(forms.SizedPanel):
        first = fields.Text(label="First")
        second = fields.Text(label="Second")

    class Window(forms.SizedFrame):
        panel = Panel(sizer_type="horizontal", narrow_sizer_type="vertical")

    window = Window(parent=None, title="Responsive integration")
    try:
        window.render()
        panel = window.panel.widget
        assert isinstance(panel, wx_widgets.WXWidget)
        panel._set_narrow(True)
        assert panel.is_narrow
        assert panel.control.GetSizer().GetOrientation() == wx.VERTICAL
        panel._set_narrow(False)
        assert not panel.is_narrow
        assert panel.control.GetSizer().GetOrientation() == wx.HORIZONTAL
    finally:
        window.widget.control.Destroy()
