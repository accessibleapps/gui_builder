import ctypes

import platform
from wx.lib.agw import hyperlink
from wx.lib import sized_controls as sc
from wx.lib import intctrl
import wx
from .widget import Widget
from .. import APPLY, CANCEL, CLOSE, FIND, NO, OK, YES, VETO
import weakref
import re
import inspect
import datetime
from logging import getLogger
from typing import (
    Any,
    Callable,
    Optional,
    Sequence,
    TypeVar,
    Generic,
    Type,
    Union,
    List,
    Tuple,
    Dict,
    overload,
)

logger = getLogger("gui_builder.widgets.wx_widgets")

# Type variable for generic wx.Control subclasses
ControlType = TypeVar("ControlType", bound=wx.Window)

MenuControlType = TypeVar("MenuControlType", bound=wx.EvtHandler)

from wx.lib import calendar

try:
    import wx.dataview as dataview
except ImportError:
    dataview = None

try:
    import wx.adv
except ImportError:
    pass


try:
    PyDeadObjectError = wx._core.PyDeadObjectError
except AttributeError:
    PyDeadObjectError = RuntimeError

UNFOCUSABLE_CONTROLS = (
    wx.StaticText,
    wx.Gauge,
)  # controls which cannot directly take focus


def inheritors(klass: type) -> set:
    subclasses = set()
    work = [klass]
    while work:
        parent = work.pop()
        for child in parent.__subclasses__():
            if child not in subclasses:
                subclasses.add(child)
                work.append(child)
    return subclasses


def is_labeled(control: Union[type, object]) -> bool:
    return is_subclass_or_instance(
        control, [cls for cls in inheritors(WXWidget) if cls.selflabeled]
    )


MODAL_RESULTS = {
    wx.ID_OK: OK,
    wx.ID_APPLY: APPLY,
    wx.ID_CANCEL: CANCEL,
    wx.ID_CLOSE: CLOSE,
    wx.ID_FIND: FIND,
    wx.ID_YES: YES,
    wx.ID_NO: NO,
}


def is_subclass_or_instance(
    unknown: Any, possible: Union[Type, Sequence[Type]]
) -> bool:
    # Convert Sequence to tuple for isinstance/issubclass compatibility
    if isinstance(possible, Sequence) and not isinstance(possible, type):
        possible = tuple(possible)
    try:
        return issubclass(unknown, possible)
    except TypeError:
        return isinstance(unknown, possible)


def find_wx_attribute(prefix: str, attr: str, module: Any = wx) -> Any:
    if prefix:
        prefix = "%s_" % prefix
    underscore = "%s%s" % (prefix, attr)
    no_underscore = "%s%s" % (prefix, attr.replace("_", ""))
    underscore = underscore.upper()
    no_underscore = no_underscore.upper()
    val = getattr(module, underscore, None)
    if not val:
        val = getattr(module, no_underscore)
    return val


def wx_attributes(
    prefix: str = "",
    result_key: str = "style",
    modules: Optional[List[Any]] = None,
    **attrs: Any,
) -> Dict[str, Any]:
    if modules is None:
        modules = [wx]
    answer = {result_key: 0}
    for k, v in attrs.items():
        if v is not True:
            answer[k] = v
            continue
        for module in modules:
            try:
                answer[result_key] |= find_wx_attribute(prefix, k, module=module)
            except AttributeError:
                try:
                    answer[result_key] |= find_wx_attribute("", k, module=module)
                except AttributeError:
                    continue
            break
        else:
            answer[k] = v
    if result_key in answer and answer[result_key] == 0:
        del answer[result_key]
    return answer


def case_to_underscore(s: str) -> str:
    return s[0].lower() + re.sub(r"([A-Z])", lambda m: "_" + m.group(0).lower(), s[1:])


UNWANTED_ATTRIBUTES = {"GetLoggingOff", "GetClientData", "GetClientObject"}


def extract_event_data(event: wx.Event) -> Dict[str, Any]:
    event_args = {}
    for attribute_name in dir(event):
        if (
            attribute_name.startswith("Get")
            and attribute_name not in UNWANTED_ATTRIBUTES
        ):
            translated_name = case_to_underscore(attribute_name[3:])
            event_args[translated_name] = getattr(event, attribute_name)()
    event_args["event"] = event
    return event_args


def callback_wrapper(
    widget: "WXWidget", callback: Callable[..., Any]
) -> Callable[[wx.Event], None]:
    def wrapper(evt, *a, **k):
        a = list(a)
        # Use getfullargspec for Python 3.3+ compatibility, fallback to getargspec for older versions
        try:
            argspec = inspect.getfullargspec(callback)
            has_kwargs = argspec.varkw is not None
        except AttributeError:
            argspec = inspect.getargspec(callback)
            has_kwargs = argspec.keywords is not None
        if (
            argspec.args
            and argspec.args[0] == "self"
            and not hasattr(callback, "im_self")
        ) or (argspec.varargs and has_kwargs):
            try:
                self = widget.find_event_target(callback)
            except ValueError:
                self = None
            if self is not None:
                a.insert(0, self)
        if has_kwargs:
            k.update(extract_event_data(evt))
        if argspec.defaults is not None:
            extracted = extract_event_data(evt)
            for arg in argspec.args:
                if arg in extracted:
                    k[arg] = extracted[arg]
        try:
            result = callback(*a, **k)
        except Exception as e:
            if not isinstance(e, SystemExit):
                logger.exception("Error calling callback")
            raise
        if result == VETO:
            evt.StopPropagation()
        elif not result:
            evt.Skip()

    return wrapper


def translate_to_none(val: int) -> Optional[int]:
    res = val
    if res == -1:
        res = None
    return res


class WXWidget(Widget, Generic[ControlType]):
    style_prefix = ""
    event_prefix = "EVT"
    event_module = wx
    style_module = None
    selflabeled: bool = False
    unlabeled: bool = False
    focusable: bool = True
    default_callback_type: Optional[str] = (
        None  # the default event which triggers this widget's callback
    )
    callback: Optional[Callable[..., Any]] = None
    label: str = ""
    control_type: Type[ControlType]
    control: ControlType

    def __init__(
        self,
        parent: Optional["Widget"] = None,
        label: str = "",
        accessible_label: str = "",
        callback: Optional[Callable[..., Any]] = None,
        min_size: Optional[Tuple[int, int]] = None,
        enabled: bool = True,
        hidden: bool = False,
        tool_tip_text: Optional[str] = None,
        expand: bool = False,
        proportion: Optional[int] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super(WXWidget, self).__init__(*args, **kwargs)
        if callback is None:
            callback = self.callback
        self.callback = callback
        if label == "":
            label = self.label
        self.label_text = label
        if accessible_label == "":
            accessible_label = label
        self.accessible_label = accessible_label
        self.parent = parent
        self.min_size = min_size
        self.label_control = None
        self.control_enabled = enabled
        self.control_hidden = hidden
        self.tool_tip_text = tool_tip_text
        self.expand = expand
        self.proportion = proportion
        self.wrapped_callbacks = weakref.WeakKeyDictionary()

    def create_control(self, **kwargs):
        logger.debug(
            "Creating control for widget %r. Widget parent: %r. Widget parent control: %r"
            % (self, self.parent, self.get_parent_control())
        )
        kwargs = self.create_label_control(**kwargs)
        if "title" in kwargs:
            kwargs["title"] = str(kwargs["title"])
        super(WXWidget, self).create_control(parent=self.get_parent_control(), **kwargs)
        if self.label_text:
            self.set_label(str(self.label_text))
        elif self.accessible_label:
            self.set_accessible_label(self.accessible_label)
        if self.min_size is not None:
            self.control.SetMinSize(self.min_size)
        if self.tool_tip_text is not None:
            self.set_tool_tip_text(self.tool_tip_text)
        if self.expand:
            self.control.SetSizerProp("expand", True)
        if self.proportion is not None:
            self.control.SetSizerProp("proportion", self.proportion)

    def create_label_control(
        self, label: Optional[str] = None, **kwargs: Any
    ) -> Dict[str, Any]:
        if label is None:
            label = self.label_text
        if self.unlabeled:
            return kwargs
        if self.selflabeled:
            if label:
                kwargs["label"] = str(label)
            return kwargs
        if label:
            try:
                self.label_control = wx.StaticText(
                    parent=self.get_parent_control(), label=str(label)
                )
            except:
                logger.exception(
                    "Error creating label for control %r" % self.control_type
                )
                raise
        return kwargs

    def set_accessible_label(self, label: str) -> None:
        self.control.SetLabel(str(label))

    def render(self, **runtime_kwargs):
        super(WXWidget, self).render(**runtime_kwargs)
        if self.control is None:
            return
        self.register_callback()
        self.enabled = self.control_enabled
        if self.control_hidden:
            self.hide()

    def register_callback(
        self,
        callback_type: Optional[str] = None,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        if callback_type is None:
            callback_type = self.default_callback_type
        if callback is None:
            callback = self.callback
        if callback_type is None:
            return
        callback_event = self.resolve_callback_type(callback_type)
        logger.debug("Resolved %r to %r" % (callback_type, callback_event))
        if callback_event is None or not callable(callback):
            return

        wrapped_callback = callback_wrapper(self, callback)
        self.wrapped_callbacks[callback] = wrapped_callback
        super(WXWidget, self).register_callback(callback_type, wrapped_callback)
        self.bind_event(callback_event, wrapped_callback)

    def unregister_callback(
        self, callback_type: str, callback: Callable[..., Any]
    ) -> None:
        wrapped_callback = self.wrapped_callbacks.pop(callback)
        super(WXWidget, self).unregister_callback(callback_type, wrapped_callback)
        callback_event = self.resolve_callback_type(callback_type)
        self.unbind_event(callback_event, wrapped_callback)

    def bind_event(
        self,
        callback_event: wx.PyEventBinder,
        wrapped_callback: Callable[[wx.Event], None],
    ) -> None:
        self.control.Bind(callback_event, wrapped_callback)

    def unbind_event(
        self,
        callback_event: wx.PyEventBinder,
        wrapped_callback: Optional[Callable[[wx.Event], None]] = None,
    ) -> None:
        self.control.Unbind(callback_event, handler=wrapped_callback)

    def resolve_callback_type(
        self, callback_type: Union[str, wx.PyEventBinder]
    ) -> wx.PyEventBinder:
        if isinstance(callback_type, wx.PyEventBinder):
            return callback_type
        try:
            res = find_wx_attribute(
                self.event_prefix, callback_type, module=self.event_module
            )
        except AttributeError:
            try:
                res = find_wx_attribute(
                    WXWidget.event_prefix, callback_type, module=self.event_module
                )
            except AttributeError:
                res = find_wx_attribute(
                    WXWidget.event_prefix, callback_type, module=WXWidget.event_module
                )
        return res

    def find_event_target(self, callback: Callable[..., Any]) -> Any:
        """Find the widget instance whose field contains the given callback.
        This is used to determine the 'self' argument when calling a callback.
        The search order is:
        1. This widget's field
        2. This widget's parent's field
        3. This widget's children's fields (if any)
        If the callback is not found, a ValueError is raised.
        """

        if self.find_callback_in_dict(callback):
            return self.field
        if self.parent is not None and self.parent.find_callback_in_dict(callback):
            return self.parent.field
        if hasattr(self.field, "get_all_children"):
            for child in self.field.get_all_children():
                if hasattr(
                    child.widget, "find_callback_in_dict"
                ) and child.widget.find_callback_in_dict(callback):
                    return child
        raise ValueError(
            "Unable to find callback %r in class %r or its parent or children."
            % (callback, self)
        )

    def find_callback_in_dict(self, callback) -> bool:
        dic = dict(inspect.getmembers(self.field))
        dic.pop("callback", None)
        for val in dic.values():
            func = getattr(val, "__func__", getattr(val, "im_func", None))
            if func is callback:
                return True
        return False

    @property
    def enabled(self) -> bool:
        return self.control.Enabled

    @enabled.setter
    def enabled(self, val: bool):
        old_enabled = getattr(self.control, "Enabled", None)
        self.control.Enabled = bool(val)
        # Invalidate parent form's descendant cache if enabled state changed
        if (
            old_enabled is not None
            and old_enabled != bool(val)
            and hasattr(self, "field")
            and hasattr(self.field, "parent")
            and self.field.parent
            and hasattr(self.field.parent, "invalidate_descendant_cache")
        ):
            self.field.parent.invalidate_descendant_cache()

    def can_accept_focus(self) -> bool:
        """Check if the underlying control can actually accept focus."""
        if not self.control:
            return False
        return self.control.CanAcceptFocus()

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False

    def freeze(self) -> None:
        self.control.Freeze()

    def thaw(self) -> None:
        self.control.Thaw()

    def destroy(self) -> None:
        if getattr(self, "label_control", None) is not None:
            try:
                self.label_control.Destroy()
            except PyDeadObjectError:
                pass
        try:
            self.control.Destroy()
        except PyDeadObjectError:
            pass

    def hide(self) -> None:
        self.control.Hide()

    def show(self) -> None:
        self.control.Show()

    def is_shown(self) -> bool:
        return self.control.IsShown()

    def get_tool_tip_text(self) -> str:
        return self.control.GetToolTipString()

    def set_tool_tip_text(self, text: str):
        return self.control.SetToolTipString(str(text))

    def raise_widget(self) -> None:
        """Raises the window to the top of the window hierarchy (Z-order)."""
        return self.control.Raise()

    def display(self) -> None:
        self.raise_widget()
        self.show()

    def get_control(self):
        return self.control

    def get_parent_control(self) -> wx.Window:
        if self.parent and isinstance(self.parent, Widget):
            return self.parent.get_control()
        return self.parent

    def get_label(self) -> str:
        if self.label_control is not None:
            return self.label_control.GetLabel()
        return self.control.GetLabel()

    def set_label(self, label: str):
        if self.label_control is not None:
            self.label_control.SetLabel(label)
        self.control.SetLabel(label)

    def remove_child(self, child):
        self.get_control().RemoveChild(child.get_control())

    def get_value(self):
        """Returns the most Pythonic representation of this control's current value."""
        if hasattr(self.control, "GetValue"):
            return self.control.GetValue()

    def set_value(self, value):
        self.control.SetValue(value)

    def translate_control_arguments(self, **kwargs):
        modules = [wx]
        if self.style_module is not None:
            modules.insert(0, self.style_module)
        return wx_attributes(
            self.style_prefix, result_key="style", modules=modules, **kwargs
        )

    def is_focused(self) -> bool:
        return self.control.HasFocus()

    def set_focus(self):
        """Set focus to this control, if it can accept focus."""
        self.control.SetFocus()

    @classmethod
    def can_be_focused(cls):
        return cls.control_type is not None and cls.focusable


class ChoiceControl(wx.ItemContainer, wx.Control):
    pass


ChoiceControlType = TypeVar("ChoiceControlType", bound=ChoiceControl)


class ChoiceWidget(WXWidget[ChoiceControlType]):
    def get_items(self) -> List[str]:
        return self.control.GetItems()

    def set_items(self, items: Sequence[str]) -> None:
        return self.control.SetItems([str(item) for item in items])

    def get_item(self, index: int) -> str:
        return self.control.GetString(index)

    def __getitem___(self, index):
        return self.get_item(index)

    def get_index(self) -> int:
        return self.control.GetSelection()

    def set_index(self, index: Optional[int]):
        return self.control.SetSelection(index)

    def get_choice(self) -> str:
        return self.get_item(self.get_index())

    def get_value(self):
        return self.get_choice()

    def get_count(self) -> int:
        return self.control.GetCount()

    def delete_item(self, index: int) -> None:
        self.control.Delete(index)

    def insert_item(self, index: int, item: str) -> None:
        return self.control.InsertItems([item], index)

    def update_item(self, index: int, item: str) -> None:
        self.delete_item(index)
        self.insert_item(index, item)

    def clear(self) -> None:
        self.control.Clear()


TextControlType = TypeVar("TextControlType", bound=wx.TextCtrl)


class BaseText(WXWidget[TextControlType]):
    event_prefix = "EVT_TEXT"

    def __init__(
        self, max_length: Optional[int] = None, *args: Any, **kwargs: Any
    ) -> None:
        super(BaseText, self).__init__(*args, **kwargs)
        self.max_length = max_length

    def select_range(self, start: int, end: int) -> None:
        self.control.SetSelection(start, end)

    def get_length(self) -> int:
        return self.control.GetLastPosition()

    def get_insertion_point(self) -> int:
        return self.control.GetInsertionPoint()

    def set_insertion_point(self, insertion_point: int) -> None:
        self.control.SetInsertionPoint(insertion_point)

    def set_max_length(self, length: int) -> None:
        self.control.SetMaxLen(length)

    def get_line(self, line_number: int) -> str:
        return self.control.GetLineText(line_number)

    def render(self, *args: Any, **kwargs: Any) -> None:
        super(BaseText, self).render(*args, **kwargs)
        if self.max_length is not None:
            self.set_max_length(self.max_length)

    def set_label(self, label: str) -> None:
        self.label_control.SetLabel(label)

    def set_value(self, value: Any) -> None:
        super(BaseText, self).set_value(str(value))

    def append(self, text: str) -> None:
        self.control.AppendText(text)

    def write(self, text: str) -> None:
        self.control.WriteText(text)


class Text(BaseText[wx.TextCtrl]):
    control_type = wx.TextCtrl
    style_prefix = "TE"
    default_callback_type = "text"

    def on_keypress(self, raw_key_code=None, modifiers=None, **kwargs):
        if raw_key_code == ord("A") and modifiers == wx.MOD_CONTROL:
            self.field.select_all()
            return True

    def render(self, *args, **kwargs):
        super(Text, self).render(*args, **kwargs)
        self.register_callback("char_hook", self.on_keypress)
        # Fix: ReadOnly TextCtrl's fail to appear in tab order.
        self.control.AcceptsFocusFromKeyboard = lambda: True

    def get_number_of_lines(self):
        return self.control.GetNumberOfLines()

    def get_insertion_point_from_x_y(self, x, y):
        return self.control.XYToPosition(x, y)

    def get_x_y_from_insertion_point(self, insertion_point):
        return self.control.PositionToXY(insertion_point)

    def clear(self):
        return self.control.Clear()


class IntText(Text):
    widget_type = intctrl.IntCtrl

    def set_value(self, value):
        self.control.SetValue(str(value))

    def get_value(self):
        value = super(IntText, self).get_value()
        if value:
            try:
                value = int(value)
            except ValueError:
                pass
        return value


class StaticText(WXWidget[wx.StaticText]):
    control_type = wx.StaticText
    selflabeled = True

    def set_value(self, value: str):
        self.control.SetLabel(value)


class CheckBox(WXWidget[wx.CheckBox]):
    control_type = wx.CheckBox
    default_callback_type = "checkbox"
    selflabeled = True


class ComboBox(ChoiceWidget):
    control_type = wx.ComboBox
    style_prefix = "CB"
    default_callback_type = "combobox"

    def get_value(self):
        return self.control.GetValue()

    def set_label(self, label):
        if self.label_control is not None:
            self.label_control.SetLabel(label)

    def select_all(self):
        self.control.SelectAll()

    def insert_item(self, index: int, item: str):
        return self.control.Insert(item, index)


class Button(WXWidget[wx.Button]):
    control_type = wx.Button
    default_callback_type = "button"
    selflabeled = True

    def __init__(self, default=False, *args, **kwargs):
        super(Button, self).__init__(*args, **kwargs)
        self.default = default

    def render(self, *args, **kwargs):
        super(Button, self).render(*args, **kwargs)
        if self.default:
            self.make_default()

    def translate_control_arguments(self, **kwargs):
        return wx_attributes("ID", result_key="id", **kwargs)

    def make_default(self):
        self.control.SetDefault()

    def get_auth_needed(self) -> bool:
        return self.control.GetAuthNeeded()

    def set_auth_needed(self, needed: bool):
        self.control.SetAuthNeeded(needed)

    auth_needed = property(get_auth_needed, set_auth_needed)


class FixedSlider(wx.Slider):
    EVENT_OBJECT_VALUECHANGE = 0x800E
    CHILDID_SELF = 0
    OBJID_CLIENT = -4

    def __init__(self, *args, **kwargs):
        super(FixedSlider, self).__init__(*args, **kwargs)
        self.Bind(wx.EVT_CHAR, self.onSliderChar)

    def SetValue(self, value):
        value = int(value)
        super(FixedSlider, self).SetValue(value)
        ctypes.windll.user32.NotifyWinEvent(
            self.EVENT_OBJECT_VALUECHANGE,
            self.Handle,
            self.OBJID_CLIENT,
            self.CHILDID_SELF,
        )

    def onSliderChar(self, evt):
        key = evt.KeyCode
        if key == wx.WXK_UP:
            newValue = min(self.Value + self.LineSize, self.Max)
        elif key == wx.WXK_DOWN:
            newValue = max(self.Value - self.LineSize, self.Min)
        elif key == wx.WXK_PAGEUP:
            newValue = min(self.Value + self.PageSize, self.Max)
        elif key == wx.WXK_PAGEDOWN:
            newValue = max(self.Value - self.PageSize, self.Min)
        elif key == wx.WXK_HOME:
            newValue = self.Max
        elif key == wx.WXK_END:
            newValue = self.Min
        else:
            evt.Skip()
            return
        self.SetValue(newValue)


class Slider(WXWidget[wx.Slider]):
    style_prefix = "SL"
    if platform.system() == "Windows":
        control_type = FixedSlider
    else:
        control_type = wx.Slider
    default_callback_type = "slider"

    def __init__(self, page_size=None, min_value=0, max_value=100, *args, **kwargs):
        super(Slider, self).__init__(*args, **kwargs)
        self._page_size = page_size
        self._min_value = min_value
        self._max_value = max_value

    def render(self, *args, **kwargs):
        super(Slider, self).render(*args, **kwargs)
        if self._page_size is not None:
            self.set_page_size(self._page_size)
        self.set_min_value(self._min_value)
        self.set_max_value(self._max_value)

    def set_min_value(self, value: int):
        self.control.SetMin(value)

    def get_min_value(self) -> int:
        return self.control.GetMin()

    def get_max_value(self) -> int:
        return self.control.GetMax()

    def set_max_value(self, value: int):
        self.control.SetMax(value)

    def get_page_size(self) -> int:
        return self.control.GetPageSize()

    def set_page_size(self, page_size: int):
        return self.control.SetPageSize(page_size)

    def set_line_size(self, value):
        self.control.SetLineSize(value)

    def get_line_size(self) -> int:
        return self.control.GetLineSize()


class ScrollBar(WXWidget[wx.ScrollBar]):
    control_type = wx.ScrollBar
    style_prefix = "SB"
    default_callback_type = "scrollbar"


class ListBox(ChoiceWidget):
    control_type = wx.ListBox
    style_prefix = "LB"
    default_callback_type = "listbox"


class ListView(ChoiceWidget):
    control_type = wx.ListView
    style_prefix = "LC"
    event_prefix = "EVT_LIST"
    default_callback_type = "ITEM_SELECTED"

    def __init__(self, choices=None, **kwargs):
        self.virtual = kwargs.pop("virtual", False)
        if self.virtual:
            self.control_type = VirtualListView
            kwargs["style"] = kwargs.get("style", 0)
            kwargs["style"] |= wx.LC_VIRTUAL | wx.LC_REPORT
        super(ListView, self).__init__(**kwargs)
        if choices is None:
            choices = []
        self.choices = choices
        self._last_added_column = -1

    def get_index(self):
        return translate_to_none(self.control.GetFirstSelected())

    def set_index(self, index):
        if index is None:
            index = -1
        self.control.Select(index)
        self.control.Focus(index)

    def get_count(self):
        return self.control.GetItemCount()

    def get_column_count(self):
        return self.control.GetColumnCount()

    def get_item(self, index: int) -> tuple:
        res = []
        for column in range(self.get_column_count()):
            res.append(self.get_item_column(index, column))
        return tuple(res)

    def get_items(self):
        res = []
        for num in range(self.get_count()):
            res.append(self.get_item(num))
        return res

    def get_item_column(self, index: int, column: int) -> str:
        return self.control.GetItemText(index, column)

    def set_item_column(self, index, column, data):
        self.control.SetStringItem(index, column, data)

    def add_item(self, item):
        self.control.Append(item)

    def set_item(self, index, item):
        for column, subitem in enumerate(item):
            self.set_item_column(index, column, str(subitem))

    def update_item(self, index, item):
        self.set_item(index, item)

    def set_items(self, items):
        if self.virtual:
            self.control.SetItems(list(items))
            return
        self.clear()
        for item in items:
            self.add_item(item)

    def insert_item(self, index, item):
        self.control.InsertStringItem(index, item)

    def delete_item(self, index):
        self.control.DeleteItem(index)

    def clear(self):
        self.control.DeleteAllItems()

    def render(self, **kwargs):
        super(ListView, self).render(**kwargs)
        self.set_value(self.choices)

    def add_column(self, column_number=None, label="", width=None, **format):
        if column_number is None:
            column_number = self._last_added_column + 1
        if width is None:
            width = -1
        format = wx_attributes(format)
        if not isinstance(format, (int)):
            format = wx.ALIGN_LEFT
        self.create_column(column_number, label, width=width, format=format)
        self._last_added_column = column_number

    def create_column(self, column_number: int, label: str, width: int, format: int):
        return self.control.InsertColumn(
            column_number, label, width=width, format=format
        )

    def delete_column(self, column_number: int):
        self.control.DeleteColumn(column_number)

    def get_value(self):
        return self.get_items()

    def set_value(self, value):
        return self.set_items(value)


class ListViewColumn(WXWidget):
    parent: ListView

    def create_control(self, **runtime_kwargs):
        kwargs = self.control_kwargs
        kwargs.update(runtime_kwargs)
        kwargs["label"] = str(self.label_text)
        translated_kwargs = self.translate_control_arguments(**kwargs)
        self.control = self.parent.add_column(**translated_kwargs)

    def render(self, *args, **kwargs):
        logger.debug("Rendering ListView column")
        self.create_control()

    def set_item(self, index: int, item: Sequence[str]):
        for column, subitem in enumerate(item):
            self.control.SetStringItem(index, column, subitem)


if dataview:

    class DataView(ListView):
        control_type = dataview.DataViewListCtrl
        event_prefix = "EVT_DATAVIEW"
        style_prefix = ""
        event_module = dataview
        default_callback_type = "selection_changed"

        def add_item(self, item):
            self.control.AppendItem(item)

        def insert_item(self, index, item):
            return self.control.InsertItem(index, item)

        def get_count(self):
            return self.control.GetStore().GetCount()

        def get_column_count(self):
            return self.control.GetStore().GetColumnCount()

        def get_index(self):
            return translate_to_none(self.control.GetSelectedRow())

        def set_index(self, index):
            if index is None:
                return
            index = int(index)
            if index == 0 and self.get_count() == 0:
                return
            self.control.SelectRow(index)

        def create_column(self, column_number, label, width, format):
            self.control.AppendTextColumn(label, align=format, width=width)

        def get_item_column(self, index, column):
            return self.control.GetTextValue(index, column)

        def set_item_column(self, index, column, data):
            self.control.SetTextValue(data, index, column)


class SpinBox(WXWidget[wx.SpinCtrl]):
    control_type = wx.SpinCtrl
    style_prefix = "SP"
    default_callback_type = "SPINCTRL"

    def __init__(self, min=0, max=100, *args, **kwargs):
        super(SpinBox, self).__init__(*args, **kwargs)
        self.min = min
        self.max = max

    def render(self, *args, **kwargs):
        super(SpinBox, self).render(*args, **kwargs)
        self.set_min(self.min)
        self.set_max(self.max)

    def set_min(self, min):
        self.control.SetMin(min)
        self.min = min

    def set_max(self, max):
        self.control.SetMax(max)
        self.max = max


class ButtonSizer(WXWidget):
    control_type = wx.StdDialogButtonSizer
    control: wx.StdDialogButtonSizer
    unlabeled = True
    focusable = False
    parent: WXWidget

    def translate_control_arguments(self, **kwargs):
        return wx_attributes("", result_key="flags", **kwargs)

    def create_control(self, **runtime_kwargs):
        callbacks = {}
        kwargs = self.control_kwargs
        kwargs.update(runtime_kwargs)
        if "close" in kwargs:
            kwargs["close"] = self.parent.destroy
        for kwarg, val in kwargs.items():
            if callable(val):
                kwargs[kwarg] = True
                try:
                    logger.debug("Finding id for kwarg %s" % kwarg)
                    callbacks[kwarg] = (find_wx_attribute("ID", kwarg), val)
                    logger.debug("Found callback %s" % str(callbacks[kwarg]))
                except AttributeError:
                    pass
        control_kwargs = self.translate_control_arguments(**kwargs)
        self.control = self.parent.control.CreateStdDialogButtonSizer(**control_kwargs)
        for control_id, callback in callbacks.values():
            for child_sizer in self.control.GetChildren():
                window = child_sizer.GetWindow()
                if window is not None and window.GetId() == control_id:
                    window.Bind(wx.EVT_BUTTON, callback_wrapper(self, callback))
                    logger.debug("Bound callback %s" % str(callback))
                    if window.GetId() == wx.ID_CLOSE:
                        self.parent.control.SetEscapeId(wx.ID_CLOSE)
                    break

    def render(self, **kwargs):
        self.create_control()
        self.parent.control.SetButtonSizer(self.control)


ContainerWidgetType = TypeVar("ContainerWidgetType", bound=wx.TopLevelWindow)


class BaseContainer(WXWidget[ContainerWidgetType]):
    unlabeled = True

    def __init__(self, top_level_window=False, *args, **kwargs):
        super(BaseContainer, self).__init__(*args, **kwargs)
        self.top_level_window = top_level_window

    def render(self, *args, **kwargs):
        super(BaseContainer, self).render(*args, **kwargs)
        if self.top_level_window:
            wx.GetApp().SetTopWindow(self.control)

    def set_title(self, title):
        self.control.SetTitle(title)

    def get_title(self):
        return self.control.GetTitle()

    def set_label(self, label):
        logger.warning("set_label called on container %r" % self)

    def close(self):
        self.control.Close()


class BaseDialog(BaseContainer[wx.Dialog]):
    def __init__(self, *args, **kwargs):
        super(BaseDialog, self).__init__(*args, **kwargs)
        self._modal_result = None

    def display_modal(self):
        self.raise_widget()
        self._modal_result = self.control.ShowModal()
        return self.get_modal_result()

    def end_modal(self, modal_result):
        modal_map = dict(zip(MODAL_RESULTS.values(), MODAL_RESULTS.keys()))
        self.control.EndModal(modal_map[modal_result])

    def get_modal_result(self):
        if self._modal_result is None:
            raise RuntimeError(
                "%r has not yet been displayed modally, hence no result is available."
                % self
            )
        # control = self.control.FindWindowById(self._modal_result)
        result = self._modal_result
        try:
            return MODAL_RESULTS[result]
        except KeyError:
            return result


class SizedDialog(BaseDialog):
    control_type = sc.SizedDialog


class SizedPanel(BaseContainer):
    control_type = sc.SizedPanel
    control: sc.SizedPanel
    focusable = False

    def __init__(self, sizer_type="vertical", *args, **kwargs):
        super(SizedPanel, self).__init__(*args, **kwargs)
        self.sizer_type = sizer_type

    def render(self):
        super(SizedPanel, self).render()
        self.control.SetSizerType(self.sizer_type)


class BaseFrame(BaseContainer):
    control: wx.Frame

    def __init__(self, maximized=False, *args, **kwargs):
        self.control_maximized = maximized
        super(BaseFrame, self).__init__(*args, **kwargs)

    def render(self, *args, **kwargs):
        super(BaseFrame, self).render(*args, **kwargs)
        if self.control_maximized:
            self.maximize()

    def maximize(self):
        return self.control.Maximize(True)

    def restore(self):
        if hasattr(self.control, "Restore"):
            return self.control.Restore()
        return self.control.Maximize(False)

    def minimize(self):
        return self.control.Maximize(False)


class Frame(BaseContainer):
    control_type = wx.Frame


class SizedFrame(BaseFrame):
    control_type = sc.SizedFrame
    control: sc.SizedFrame

    def get_control(self):
        return self.control.mainPanel

    def set_content_padding(self, padding):
        """Set padding around the frame's content area.

        Args:
            padding (int): Padding in pixels around all content
        """
        pane = self.control.GetContentsPane()
        pane.SetSizerProps(border=("all", padding))


class MDIParentFrame(BaseFrame):
    control_type = wx.MDIParentFrame


class MDIChildFrame(BaseFrame):
    control_type = wx.MDIChildFrame


class Dialog(BaseDialog):
    control_type = wx.Dialog


class Panel(BaseContainer):
    control_type = wx.Panel
    focusable = False


class Notebook(BaseContainer):
    control_type = wx.Notebook
    control: wx.Notebook
    event_prefix = "EVT_NOTEBOOK"
    default_callback_type = "page_changed"

    def add_item(self, name, item):
        self.control.AddPage(item.control, str(name))
        # Now, we shall have much hackyness to work around WX bug 11909
        if not list(self.field.get_all_children()):
            return

        def on_focus(evt):
            evt.Skip()

        def on_navigation_key(evt):
            # Get the currently focused window using FindFocus instead of evt.GetCurrentFocus
            focused_window = wx.Window.FindFocus()
            direction = evt.GetDirection()  # True = forward, False = backward

            # Get the enabled, focusable children of this page
            enabled_children = [
                child
                for child in item.field.get_all_children()
                if child.widget.enabled
                and child.can_be_focused()
                and child.widget.can_accept_focus()
            ]

            if not enabled_children:
                evt.Skip()
                return

            first_child = enabled_children[0]
            last_child = enabled_children[-1]

            # Check if we're at a boundary that should go to notebook
            current_control = None
            for child in enabled_children:
                if hasattr(child.widget, "get_control"):
                    control = child.widget.get_control()
                    if control == focused_window:
                        current_control = child
                        break

            if current_control:
                # Forward tab from last control -> go to notebook
                if direction and current_control == last_child:
                    logger.debug(
                        f"Tab navigation: transferring from last control '{current_control.bound_name}' to notebook"
                    )
                    self.set_focus()
                    return  # Consume the event

                # Backward tab from first control -> go to notebook
                elif not direction and current_control == first_child:
                    logger.debug(
                        f"Shift+Tab navigation: transferring from first control '{current_control.bound_name}' to notebook"
                    )
                    self.set_focus()
                    return  # Consume the event

            # Normal intra-page navigation
            evt.Skip()

        item.bind_event(wx.EVT_CHILD_FOCUS, on_focus)
        item.bind_event(wx.EVT_NAVIGATION_KEY, on_navigation_key)

    def delete_page(self, page):
        self.control.DeletePage(self.find_page_number(page))

    def render(self, *args, **kwargs):
        super(Notebook, self).render(*args, **kwargs)

        self.control_down = False
        self._setting_notebook_focus = False  # Guard against recursive focus calls

        def key_down_up(evt):
            self.control_down = evt.ControlDown()
            evt.Skip()

        def on_notebook_navigation(evt):
            direction = evt.GetDirection()  # True = forward, False = backward
            current_page_index = self.control.GetSelection()
            focused_window = wx.Window.FindFocus()
            event_object = evt.GetEventObject()

            logger.info(
                f"[NOTEBOOK_NAV] Navigation event: direction={'forward' if direction else 'backward'}"
            )
            logger.info(f"[NOTEBOOK_NAV] Current page: {current_page_index}")
            logger.info(f"[NOTEBOOK_NAV] Focused window: {focused_window}")
            logger.info(f"[NOTEBOOK_NAV] Event object: {event_object}")
            logger.info(f"[NOTEBOOK_NAV] Notebook control: {self.control}")
            logger.info(
                f"[NOTEBOOK_NAV] Focus on notebook? {focused_window == self.control}"
            )

            if direction:
                # Forward tab from notebook -> focus first control of current page
                current_page = (
                    self.control.GetPage(current_page_index)
                    if current_page_index >= 0
                    else None
                )
                if current_page:
                    # Find the field object for this page
                    for field in self.field.get_children():
                        if (
                            hasattr(field.widget, "control")
                            and field.widget.control == current_page
                        ):
                            first_child = field.get_first_enabled_descendant()
                            if first_child:
                                logger.info(
                                    f"[NOTEBOOK_NAV] CONSUMING EVENT: transferring focus to first control '{first_child.bound_name}'"
                                )
                                first_child.set_focus()
                                return  # Consume the event
                            break
            else:
                # Backward tab from notebook -> focus last control of current page
                current_page = (
                    self.control.GetPage(current_page_index)
                    if current_page_index >= 0
                    else None
                )
                if current_page:
                    # Find the field object for this page
                    for field in self.field.get_children():
                        if (
                            hasattr(field.widget, "control")
                            and field.widget.control == current_page
                        ):
                            last_child = field.get_last_enabled_descendant()
                            if last_child:
                                logger.info(
                                    f"[NOTEBOOK_NAV] CONSUMING EVENT: transferring focus to last control '{last_child.bound_name}'"
                                )
                                last_child.set_focus()
                                return  # Consume the event
                            break

            # If we can't find appropriate controls, allow normal navigation
            logger.info("[NOTEBOOK_NAV] SKIPPING EVENT: allowing normal navigation")
            evt.Skip()

        self.bind_event(wx.EVT_NAVIGATION_KEY, on_notebook_navigation)
        self.bind_event(wx.EVT_KEY_DOWN, key_down_up)
        self.bind_event(wx.EVT_KEY_UP, key_down_up)

    def find_page_number(self, page):
        for page_num in range(self.control.GetPageCount()):
            if self.control.GetPage(page_num) is page.control:
                return page_num

    def get_selection(self):
        return self.control.GetSelection()

    def set_selection(self, selection):
        return self.control.SetSelection(selection)

    def find_event_target(self, callback):
        if self.parent is None:
            return None
        return self.parent.field


class RadioBox(ChoiceWidget[wx.RadioBox]):
    control_type = wx.RadioBox
    default_callback_type = "RADIOBOX"
    selflabeled = True
    style_prefix = "RA"

    def get_value(self):
        return self.control.GetStringSelection()

    def set_value(self, value):
        self.control.SetStringSelection([str(i) for i in value])

    def get_items(self):
        return self.control.GetChoices()

    def set_items(self, items):
        return self.control.SetItems(items)


class CheckListBox(ListBox):
    default_callback_type = "CHECKLISTBOX"
    control_type = wx.CheckListBox


class FilePicker(WXWidget):
    control_type = wx.FilePickerCtrl


class MenuBar(WXWidget):
    control_type = wx.MenuBar
    focusable = False
    unlabeled = True

    def create_control(self, **kwargs):
        self.control = wx.MenuBar()
        wx.GetApp().GetTopWindow().SetMenuBar(self.control)

    def render(self, *args, **kwargs):
        super(MenuBar, self).render(*args, **kwargs)
        if platform.system() == "Darwin":
            wx.MenuBar.MacSetCommonMenuBar(self.control)

    def add_item(self, name=None, item=None):
        if item is None:
            raise TypeError("Must provide a MenuItem")
        name = name or item.name
        control = item.control
        self.control.Append(control, name)


class Menu(WXWidget):
    control_type = wx.Menu
    focusable = False

    def create_control(self, **kwargs):
        label = str(kwargs.get("label", self.label_text))
        self.control = wx.Menu()
        if self.get_parent_control() is not None and (
            isinstance(self.parent, MenuBar) or isinstance(self.parent, Menu)
        ):
            self.get_parent_control().Append(self.control, title=label)

    def popup(self, position=None):
        if position is None:
            position = wx.DefaultPosition
        self.get_parent_control().PopupMenu(self.control, position)

    def destroy_item(self, item):
        self.control.DestroyItem(item.control)


class MenuItem(WXWidget[wx.MenuItem]):
    control_type = wx.MenuItem
    parent: Menu
    default_callback_type = "MENU"
    focusable = False
    unlabled = True

    def __init__(self, hotkey=None, help_message="", checkable=False, **kwargs):
        self.hotkey = hotkey
        self.help_message = help_message
        self.checkable = checkable
        self.control_id = None
        super(MenuItem, self).__init__(**kwargs)

    def get_parent_control(self) -> wx.Menu:
        return super(MenuItem, self).get_parent_control()

    def create_control(self, **kwargs):
        label = str(kwargs.get("label", self.label_text))
        if not label:  # This menu item is a separator
            self.control = self.get_parent_control().AppendSeparator()
            return
        if self.hotkey is not None:
            label = "%s\t%s" % (label, self.hotkey)
        self.control_id = wx.NewId()
        kind = wx.ITEM_NORMAL
        if self.checkable:
            kind = wx.ITEM_CHECK
        self.control = self.get_parent_control().Append(
            self.control_id, label, self.help_message, kind=kind
        )

    def bind_event(self, callback_event, wrapped_callback):
        parent = self.parent
        while isinstance(parent, SubMenu):
            parent = parent.parent
        if parent and isinstance(parent, (WXWidget)):
            parent.control.Bind(callback_event, wrapped_callback, self.control)
        # Fix if we're called from a menu bar
        if isinstance(self.parent, SubMenu):
            self.parent.control.Bind(callback_event, wrapped_callback, self.control)

    def render(self, *args, **kwargs):
        super(MenuItem, self).render(*args, **kwargs)
        if not self.control_enabled:
            self.disable()

    def enable(self):
        self.control.Enable(True)

    def disable(self):
        self.control.Enable(False)

    def check(self):
        self.control.Check(True)

    def uncheck(self):
        self.control.Check(False)

    def set_as_mac_about_menu_item(self):
        wx.GetApp().SetMacAboutMenuItemId(self.control_id)

    def set_as_mac_exit_menu_item(self):
        wx.GetApp().SetMacExitMenuItemId(self.control_id)

    def set_as_mac_preferences_menu_item(self):
        wx.GetApp().SetMacPreferencesMenuItemId(self.control_id)

    def destroy(self):
        self.parent.destroy_item(self)


class SubMenu(Menu):
    parent: Union[MenuBar, Menu]

    def create_control(self, **kwargs):
        text = str(kwargs.get("label", self.label_text))
        self.control = wx.Menu()
        self.parent.control.AppendSubMenu(self.control, text=text)


class StatusBar(WXWidget[wx.StatusBar]):
    parent: BaseFrame
    control_type = wx.StatusBar
    style_prefix = "SB"

    def create_control(self, **kwargs):
        self.control = self.parent.control.CreateStatusBar(**kwargs)

    def set_value(self, value):
        self.control.SetStatusText(value)

    def get_value(self, field=0):
        return self.control.GetStatusText(field)

    def set_status_text(self, text, field=0):
        self.control.SetStatusText(text, field)


class Link(WXWidget[wx.adv.HyperlinkCtrl]):
    if hasattr(wx, "adv"):
        control_type = wx.adv.HyperlinkCtrl
        event_module = wx.adv
        default_callback_type = "hyperlink"
    else:
        control_type = hyperlink.HyperLinkCtrl
        event_module = hyperlink
        default_callback_type = "hyperlink_left"
    selflabeled = True

    def create_control(self, **kwargs):
        # prefer wx.adv.HyperlinkCtrl when available
        # otherwise, standardize URL case for backward compatibility
        if hasattr(wx, "adv") and "URL" in kwargs:
            kwargs["url"] = kwargs["URL"]
            del kwargs["URL"]
        return super(Link, self).create_control(**kwargs)


class DatePicker(WXWidget[wx.adv.DatePickerCtrl]):
    if hasattr(wx, "adv"):
        control_type = wx.adv.DatePickerCtrl
        event_module = wx.adv
    else:
        control_type = wx.DatePickerCtrl
    default_callback_type = "date_changed"

    def __init__(self, range=None, *args, **kwargs):
        super(DatePicker, self).__init__(*args, **kwargs)
        self.range = range

    def render(self, *args, **kwargs):
        super(DatePicker, self).render(*args, **kwargs)
        if self.range is not None:
            self.set_range(*self.range)

    def get_value(self):
        value: wx.DateTime = super(DatePicker, self).get_value()
        return wx.wxdate2pydate(value)

    def set_value(self, value):
        super(DatePicker, self).set_value(self.convert_datetime(value))

    def convert_datetime(self, dt):
        pydate2wxdate = getattr(
            calendar, "_pydate2wxdate", getattr(wx, "pydate2wxdate")
        )
        if isinstance(dt, (datetime.date, datetime.datetime)):
            dt = pydate2wxdate(dt)
        return dt

    def set_range(self, start, end):
        start = self.convert_datetime(start)
        end = self.convert_datetime(end)
        self.control.SetRange(start, end)
        self.range = (start, end)


class VirtualListView(wx.ListCtrl):
    def __init__(self, *args, **kwargs):
        super(VirtualListView, self).__init__(*args, **kwargs)
        self.items = []

    def Append(self, entry):
        self.items.append(entry)
        self.SetItemCount(len(self.items))

    def SetItems(self, items):
        self.items = items
        self.SetItemCount(len(self.items))

    def OnGetItemText(self, item, column):
        return self.items[item][column]

    def DeleteAllItems(self):
        self.items = []
        self.SetItemCount(0)

    def SetStringItem(self, index, column, data):
        row = list(self.items[index])
        row[column] = data
        self.items[index] = row


class TreeView(WXWidget[wx.TreeCtrl]):
    control_type = wx.TreeCtrl
    style_prefix = "TR"
    event_prefix = "EVT_TREE"
    default_callback_type = "SEL_CHANGED"

    def __init__(self, *args, **kwargs):
        super(TreeView, self).__init__(*args, **kwargs)
        self.image_list = None

    def add_root(self, text=None, image=None, selected_image=None, data=None):
        if text is None:
            text = ""
        if image is None:
            image = -1
        if selected_image is None:
            selected_image = -1
        return self.control.AddRoot(text, image, selected_image, data)

    def get_root_item(self):
        return self.control.GetRootItem()

    def append_item(
        self, parent, text=None, image=None, selected_image=None, data=None
    ):
        if text is None:
            text = ""
        if image is None:
            image = -1
        if selected_image is None:
            selected_image = -1
        if isinstance(image, wx.Image):
            if self.image_list is None:
                self.create_image_list(image.Width, image.Height)
            image = self.image_list.Add(image.ConvertToBitmap())
        return self.control.AppendItem(parent, str(text), image, selected_image, data)

    def create_image_list(self, width=32, height=32):
        self.image_list = wx.ImageList(width, height)
        self.control.AssignImageList(self.image_list)

    def clear(self):
        self.control.DeleteAllItems()
        if self.image_list is not None:
            self.image_list.RemoveAll()
            self.image_list = None

    def delete(self, item):
        self.control.Delete(item)

    def get_selection(self):
        return self.control.GetSelection()

    def select_item(self, item):
        self.control.SelectItem(item)

    def get_data(self, item):
        return self.control.GetItemData(item)

    def set_item_has_children(self, item, val):
        self.control.SetItemHasChildren(item, val)


class ProgressBar(WXWidget[wx.Gauge]):
    control_type = wx.Gauge
    focusable = False


class ToolBar(WXWidget[wx.ToolBar]):
    control_type = wx.ToolBar
    style_prefix = "TB"

    def __init__(self, tool_bitmap_size=(16, 16), *args, **kwargs):
        super(ToolBar, self).__init__(*args, **kwargs)
        self.tool_bitmap_size = tool_bitmap_size

    def add_simple_tool(
        self, id=wx.ID_ANY, bitmap=wx.NullBitmap, short_text="", *args, **kwargs
    ):
        if bitmap is not wx.NullBitmap:
            bitmap = (
                wx.Image(bitmap, wx.BITMAP_TYPE_PNG)
                .Scale(quality=wx.IMAGE_QUALITY_HIGH, *self.tool_bitmap_size)
                .ConvertToBitmap()
            )
        short_text = str(short_text)
        if hasattr(self.control, "AddSimpleTool"):
            return self.control.AddSimpleTool(
                id, bitmap=bitmap, shortHelpString=short_text, *args, **kwargs
            )

    def add_separator(self):
        return self.control.AddSeparator()

    def bind_event(self, callback_type, callback, id=None):
        return self.control.Bind(callback_type, callback, id)

    def realize(self):
        return self.control.Realize()

    def render(self, **runtime_kwargs):
        super(ToolBar, self).render(**runtime_kwargs)
        self.set_tool_bitmap_size(self.tool_bitmap_size)

    def set_tool_bitmap_size(self, tool_bitmap_size):
        self.control.SetToolBitmapSize(tool_bitmap_size)
        self.tool_bitmap_size = tool_bitmap_size


class FrameToolBar(ToolBar):
    parent: BaseFrame

    def create_control(self, *args, **kwargs):
        self.control = self.parent.control.CreateToolBar(*args, **kwargs)


class ToolBarItem(WXWidget):
    default_callback_type = "menu"
    parent: ToolBar

    def create_control(self, bitmap=None, id=None, *args, **kwargs):
        if not self.label_text:
            self.control = self.parent.add_separator()
            return
        if id is None:
            id = wx.NewId()
        self.control = self.parent.add_simple_tool(
            id=id, short_text=self.label_text, bitmap=bitmap, *args, **kwargs
        )

    def bind_event(self, callback_type, callback):
        self.parent.bind_event(callback_type, callback, id=self.control)


class StaticBitmap(WXWidget[wx.StaticBitmap]):
    control_type = wx.StaticBitmap

    def load_image(self, image):
        return self.control.SetBitmap(wx.BitmapFromImage(image))
