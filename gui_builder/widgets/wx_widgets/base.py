from __future__ import annotations

import inspect
import re
import weakref
from logging import getLogger
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Collection,
    Dict,
    Generic,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

import wx

from ... import APPLY, CANCEL, CLOSE, FIND, NO, OK, VETO, YES
from ..widget import Widget

logger = getLogger("gui_builder.widgets.wx_widgets")

# Type variable for generic wx.Control subclasses
ControlType = TypeVar("ControlType", bound=wx.Window)
# Type variable for the field type that owns this widget
FieldType = TypeVar("FieldType")

MenuControlType = TypeVar("MenuControlType", bound=wx.EvtHandler)

PyDeadObjectError = RuntimeError

UNFOCUSABLE_CONTROLS = (
    wx.StaticText,
    wx.Gauge,
)  # controls which cannot directly take focus


def inheritors(klass: type) -> set[Type[Any]]:
    subclasses: set[Type[Any]] = set()
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


def extract_event_data(
    event: wx.Event, requested_names: Optional[Collection[str]] = None
) -> Dict[str, Any]:
    event_args = {}
    extract_all = requested_names is None
    for attribute_name in dir(event):
        if (
            attribute_name.startswith("Get")
            and attribute_name not in UNWANTED_ATTRIBUTES
        ):
            translated_name = case_to_underscore(attribute_name[3:])
            if extract_all or translated_name in requested_names:
                event_args[translated_name] = getattr(event, attribute_name)()
    if extract_all or "event" in requested_names:
        event_args["event"] = event
    return event_args


def callback_wrapper(
    widget: "WXWidget[Any, Any]", callback: Callable[..., Any]
) -> Callable[[wx.Event], None]:
    # Callback signature and owner lookup are stable for the lifetime of this
    # binding; computing them per event is visible lag on hot event streams.
    try:
        argspec = inspect.getfullargspec(callback)
        has_kwargs = argspec.varkw is not None
    except AttributeError:
        argspec = inspect.getargspec(callback)
        has_kwargs = argspec.keywords is not None
    bound_self = getattr(callback, "__self__", getattr(callback, "im_self", None))
    is_bound_method = bound_self is not None
    should_find_self = not is_bound_method and (
        (argspec.args and argspec.args[0] == "self") or (argspec.varargs and has_kwargs)
    )
    requested_event_names = set(argspec.args)
    requested_event_names.discard("self")
    requested_event_names.update(getattr(argspec, "kwonlyargs", ()))
    found_self = False
    event_target = None

    def wrapper(evt: wx.Event, *a, **k):
        nonlocal found_self, event_target
        a = list(a)
        if should_find_self:
            if not found_self:
                try:
                    event_target = widget.find_event_target(callback)
                except ValueError:
                    event_target = None
                found_self = True
            if event_target is not None:
                a.insert(0, event_target)
        if has_kwargs and not requested_event_names:
            k.update(extract_event_data(evt))
        elif requested_event_names:
            k.update(extract_event_data(evt, requested_event_names))
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


class WXWidget(Widget[FieldType], Generic[FieldType, ControlType]):
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

    if TYPE_CHECKING:
        # These would create problematic class attributes if defined at class level
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
        background_color: Optional[wx.Colour] = None,
        foreground_color: Optional[wx.Colour] = None,
        expand: bool = False,
        proportion: Optional[int] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
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
        self.control_background_color = background_color
        self.control_foreground_color = foreground_color
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
        super().create_control(parent=self.get_parent_control(), **kwargs)
        if self.label_text:
            self.set_label(str(self.label_text))
        elif self.accessible_label:
            self.set_accessible_label(self.accessible_label)
        if self.min_size is not None:
            self.control.SetMinSize(wx.Size(*self.min_size))
        if self.tool_tip_text is not None:
            self.set_tool_tip_text(self.tool_tip_text)
        if self.control_background_color is not None:
            self.set_background_color(self.control_background_color)
        if self.control_foreground_color is not None:
            self.set_foreground_color(self.control_foreground_color)
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
        label = str(label)
        if hasattr(self.control, "SetAccessibleName"):
            self.control.SetAccessibleName(label)
        else:
            # wxPython before 4.3 has no separate accessible-name setter.
            self.control.SetName(label)

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
        super().unregister_callback(callback_type, wrapped_callback)
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
        label: Optional[wx.StaticText] = getattr(self, "label_control", None)
        if label is not None:
            try:
                label.Destroy()
            except PyDeadObjectError:
                pass
        try:
            self.control.Destroy()
        except PyDeadObjectError:
            pass

    def hide(self) -> None:
        self.control.Hide()
        if self.label_control is not None:
            self.label_control.Hide()
        self._relayout()

    def show(self) -> None:
        self.control.Show()
        if self.label_control is not None:
            self.label_control.Show()
        self._relayout()

    def _relayout(self) -> None:
        # Lay out every ancestor, not just the parent: a nested panel must also
        # grow or shrink within its own parent.
        window = self.control.GetParent()
        while window is not None:
            window.Layout()
            if window.IsTopLevel():
                break
            window = window.GetParent()

    def is_shown(self) -> bool:
        return self.control.IsShown()

    def get_tool_tip_text(self) -> str:
        return self.control.GetToolTipText()

    def set_tool_tip_text(self, text: str):
        return self.control.SetToolTipString(str(text))

    def raise_widget(self) -> None:
        """Raises the window to the top of the window hierarchy (Z-order)."""
        return self.control.Raise()

    def display(self) -> None:
        """Display the widget. For top-level windows, this shows the window."""
        self.raise_widget()
        self.show()

    def display_modal(self) -> Any:
        """Display widget modally. Only supported for dialog-type widgets."""
        raise NotImplementedError("Modal display not supported for this widget type")

    def get_control(self) -> ControlType:
        return self.control

    def get_parent_control(self) -> Optional[wx.Window]:
        if self.parent is not None and hasattr(self.parent, "get_control"):
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

    def remove_child(self, child: "WXWidget[Any, Any]") -> None:
        self.get_control().RemoveChild(child.get_control())

    def get_value(self) -> Any:
        """Returns the most Pythonic representation of this control's current value."""
        get_value_method = getattr(self.control, "GetValue", None)
        if callable(get_value_method):
            return get_value_method()
        return None

    def set_value(self, value):
        """Set the control's value. Subclasses may override for type conversion."""
        if hasattr(self.control, "SetValue"):
            self.control.SetValue(value)
        else:
            raise NotImplementedError("Control does not support setting value.")

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

    def scroll_lines(self, lines: int) -> None:
        """Scroll the control vertically by the given number of lines."""
        self.control.ScrollLines(lines)

    def scroll_pages(self, pages: int) -> None:
        """Scroll the control vertically by the given number of pages."""
        self.control.ScrollPages(pages)

    def center(self):
        """Center the control on the screen."""
        self.control.Center()

    def center_on_parent(self):
        """Center the control on its parent."""
        self.control.CenterOnParent()

    def get_foreground_color(self) -> wx.Colour:
        """Get the window's foreground color."""
        return self.control.GetForegroundColour()

    def set_foreground_color(self, color: wx.Colour) -> None:
        """Set the window's foreground color."""
        self.control.SetForegroundColour(color)
        self.control.Refresh()

    foreground_color = property(get_foreground_color, set_foreground_color)

    def get_background_color(self) -> wx.Colour:
        """Get the window's background color."""
        return self.control.GetBackgroundColour()

    def set_background_color(self, color: wx.Colour) -> None:
        """Set the window's background color."""
        self.control.SetBackgroundColour(color)
        self.control.Refresh()

    background_color = property(get_background_color, set_background_color)

    def get_font(self) -> wx.Font:
        """Get the window's font."""
        return self.control.GetFont()

    def set_font(self, font: wx.Font) -> None:
        """Set the window's font."""
        self.control.SetFont(font)
        self.control.Refresh()

    font = property(get_font, set_font)

    def get_theme_enabled(self) -> bool:
        """Get whether the window is using the current theme."""
        return self.control.GetThemeEnabled()

    def set_theme_enabled(self, enable: bool) -> None:
        """Set whether the window should use the current theme."""
        self.control.SetThemeEnabled(enable)
        self.control.Refresh()

    theme_enabled = property(get_theme_enabled, set_theme_enabled)

    def capture_mouse(self) -> None:
        """Capture all mouse input."""
        self.control.CaptureMouse()

    def release_mouse(self) -> None:
        """Release the mouse capture."""
        self.control.ReleaseMouse()

    def has_mouse_capture(self) -> bool:
        """Check if this control has mouse capture."""
        return self.control.HasCapture()

    mouse_capture = property(has_mouse_capture)


ChoiceControlType = TypeVar("ChoiceControlType", bound=wx.ControlWithItems)

ChoiceItemInputType = TypeVar(
    "ChoiceItemInputType", bound=Sequence[Any], contravariant=True
)
ChoiceItemOutputType = TypeVar("ChoiceItemOutputType", covariant=True)


class ChoiceWidget(
    WXWidget[FieldType, ChoiceControlType],
    Generic[FieldType, ChoiceControlType, ChoiceItemInputType, ChoiceItemOutputType],
):
    def get_items(self) -> Sequence[ChoiceItemOutputType]:
        return self.control.GetItems()

    def set_items(
        self, items: Sequence[ChoiceItemInputType]
    ) -> Sequence[ChoiceItemOutputType]:
        """Set items and return the converted output items."""
        converted_items = [self._convert_input_to_output(item) for item in items]
        self.control.SetItems([str(item) for item in converted_items])
        return converted_items

    def _convert_input_to_output(
        self, item: ChoiceItemInputType
    ) -> ChoiceItemOutputType:
        """Convert input item to output item type. Subclasses should override."""
        return str(item)  # type: ignore

    def get_item(self, index: int) -> ChoiceItemOutputType:
        return cast(ChoiceItemOutputType, self.control.GetString(index))

    def __getitem__(self, index: int) -> ChoiceItemOutputType:
        return self.get_item(index)

    def get_index(self) -> Optional[int]:
        return translate_to_none(self.control.GetSelection())

    def set_index(self, index: Optional[int]) -> None:
        if index is None:
            index = -1
        return self.control.SetSelection(index)

    def get_choice(self) -> Optional[ChoiceItemOutputType]:
        index = self.get_index()
        if index is not None:
            return self.get_item(index)

    def get_value(self) -> Optional[ChoiceItemOutputType]:
        return self.get_choice()

    def get_count(self) -> int:
        return self.control.GetCount()

    def delete_item(self, index: int) -> None:
        self.control.Delete(index)

    def is_empty(self) -> bool:
        return self.control.IsEmpty()

    def insert_item(
        self, index: int, item: ChoiceItemInputType
    ) -> ChoiceItemOutputType:
        """Insert item and return the converted output item."""
        converted_item = self._convert_input_to_output(item)
        self.control.InsertItems([str(converted_item)], index)
        return converted_item

    def update_item(self, index: int, item: ChoiceItemInputType):
        """Update item."""
        self.delete_item(index)
        self.insert_item(index, item)

    def clear(self) -> None:
        self.control.Clear()


TextControlType = TypeVar("TextControlType", bound=wx.TextCtrl)


class BaseText(
    WXWidget[FieldType, TextControlType], Generic[FieldType, TextControlType]
):
    event_prefix = "EVT_TEXT"

    def __init__(
        self, max_length: Optional[int] = None, *args: Any, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
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
        self.control.SetMaxLength(length)

    def get_line(self, line_number: int) -> str:
        return self.control.GetLineText(line_number)

    def render(self, *args: Any, **kwargs: Any) -> None:
        super().render(*args, **kwargs)
        if self.max_length is not None:
            self.set_max_length(self.max_length)

    def set_label(self, label: str) -> None:
        if self.label_control is not None:
            self.label_control.SetLabel(label)

    def set_value(self, value: Any) -> None:
        super().set_value(str(value))

    def copy(self) -> None:
        """Copy the currently selected text to the clipboard."""
        self.control.Copy()

    def cut(self) -> None:
        """Cut the currently selected text to the clipboard."""
        self.control.Cut()

    def paste(self) -> None:
        """Paste text from the clipboard into the text control at the current insertion point."""
        self.control.Paste()

    def append(self, text: str) -> None:
        self.control.AppendText(text)

    def write(self, text: str) -> None:
        self.control.WriteText(text)
