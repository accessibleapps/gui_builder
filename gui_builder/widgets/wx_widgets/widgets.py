from __future__ import annotations

import ctypes
import datetime
import platform
from typing import TYPE_CHECKING, Any, Dict, Generic, List, Optional, Sequence, Tuple, TypeVar, Union, cast

import wx
from wx.lib import intctrl
from wx.lib import calendar
from wx.lib import sized_controls as sc

from ... import APPLY, CANCEL, CLOSE, FIND, NO, OK, VETO, YES
from .base import (
    BaseText, ChoiceItemInputType, ChoiceItemOutputType, ChoiceWidget,
    FieldType, MODAL_RESULTS, PyDeadObjectError, WXWidget, callback_wrapper,
    find_wx_attribute, logger, translate_to_none, wx_attributes,
)

try:
    import wx.dataview as dataview
except ImportError:
    dataview = None

try:
    import wx.adv
except ImportError:
    pass


class Text(BaseText[FieldType, wx.TextCtrl]):
    control_type = wx.TextCtrl
    style_prefix = "TE"
    default_callback_type = "text"

    def __init__(self, text_margins=None, *args, **kwargs):
        """Extra kwargs beyond WXWidget:

        Args:
            text_margins: Optional (left, top) pixel pair applied to the
                wx.TextCtrl via SetMargins after construction. Useful for
                breathable padding inside long-form reading text. None =
                use platform default. Note: on wx.TextCtrl backed by Win32
                RichEdit, only the left margin is honored reliably.
        """
        super().__init__(*args, **kwargs)
        self.text_margins = text_margins

    def on_keypress(self, raw_key_code=None, modifiers=None, **kwargs):
        if raw_key_code == ord("A") and modifiers == wx.MOD_CONTROL:
            self.field.select_all()
            return True

    def render(self, *args, **kwargs):
        super().render(*args, **kwargs)
        self.register_callback("char_hook", self.on_keypress)
        # Fix: ReadOnly TextCtrl's fail to appear in tab order.
        self.control.AcceptsFocusFromKeyboard = lambda: True
        if self.text_margins is not None:
            left, top = self.text_margins
            self.control.SetMargins(wx.Point(left, top))

    def get_number_of_lines(self) -> int:
        return self.control.GetNumberOfLines()

    def get_insertion_point_from_x_y(self, x: int, y: int) -> int:
        return self.control.XYToPosition(x, y)

    def get_x_y_from_insertion_point(self, insertion_point: int) -> Tuple[int, int]:
        found, x, y = self.control.PositionToXY(insertion_point)
        if not found:
            raise ValueError(
                "No text coordinates for insertion point %r" % insertion_point
            )
        return x, y

    def clear(self) -> None:
        return self.control.Clear()

    def _to_wx_colour(
        self, color: Union[wx.Colour, str, Tuple[int, int, int]]
    ) -> wx.Colour:
        """Convert various color formats to wx.Colour.

        Args:
            color: Color as wx.Colour, color name string, or RGB tuple

        Returns:
            wx.Colour object
        """
        if isinstance(color, wx.Colour):
            return color
        elif isinstance(color, str):
            return wx.Colour(color)
        elif isinstance(color, tuple) and len(color) == 3:
            return wx.Colour(*color)
        else:
            raise ValueError(f"Invalid color format: {color}")

    def _from_wx_colour(self, color: wx.Colour) -> Optional[Tuple[int, int, int]]:
        """Convert wx.Colour to RGB tuple.

        Args:
            color: wx.Colour object

        Returns:
            RGB tuple or None if color is invalid
        """
        if color.IsOk():
            return (color.Red(), color.Green(), color.Blue())
        return None

    def _create_text_attr(
        self,
        font_family: Optional[int] = None,
        font_size: Optional[int] = None,
        font_face: Optional[str] = None,
        bold: Optional[bool] = None,
        italic: Optional[bool] = None,
        underline: Optional[bool] = None,
        text_color: Optional[Union[wx.Colour, str, Tuple[int, int, int]]] = None,
        background_color: Optional[Union[wx.Colour, str, Tuple[int, int, int]]] = None,
        alignment: Optional[int] = None,
    ) -> wx.TextAttr:
        """Create a wx.TextAttr from the provided styling parameters.

        Args:
            font_family: Font family constant (wx.FONTFAMILY_DEFAULT, wx.FONTFAMILY_ROMAN, etc.)
            font_size: Font size in points
            font_face: Font face name like "Arial" or "Courier New"
            bold: Whether text should be bold
            italic: Whether text should be italic
            underline: Whether text should be underlined
            text_color: Text color (wx.Colour, color name string, or RGB tuple)
            background_color: Background color (wx.Colour, color name string, or RGB tuple)
            alignment: Text alignment (wx.TEXT_ALIGNMENT_LEFT, etc.)

        Returns:
            Configured wx.TextAttr object
        """
        attr = wx.TextAttr()

        # Use individual TextAttr methods for more granular control
        if font_size is not None:
            attr.SetFontSize(font_size)
        if font_family is not None:
            attr.SetFontFamily(font_family)
        if font_face is not None:
            attr.SetFontFaceName(font_face)
        if bold is not None:
            attr.SetFontWeight(wx.FONTWEIGHT_BOLD if bold else wx.FONTWEIGHT_NORMAL)
        if italic is not None:
            attr.SetFontStyle(wx.FONTSTYLE_ITALIC if italic else wx.FONTSTYLE_NORMAL)
        if underline is not None:
            attr.SetFontUnderlined(underline)

        if text_color is not None:
            attr.SetTextColour(self._to_wx_colour(text_color))

        if background_color is not None:
            attr.SetBackgroundColour(self._to_wx_colour(background_color))

        if alignment is not None:
            attr.SetAlignment(alignment)

        return attr

    def _text_attr_to_dict(self, attr: wx.TextAttr) -> Dict[str, Any]:
        """Convert wx.TextAttr to a dict of style parameters.

        Args:
            attr: wx.TextAttr object

        Returns:
            Dict with style parameters matching the setter API
        """
        result: Dict[str, Any] = {}

        if attr.HasFont():
            font = attr.GetFont()
            result["font_family"] = font.GetFamily()
            result["font_size"] = font.GetPointSize()
            result["font_face"] = font.GetFaceName()
            result["bold"] = font.GetWeight() == wx.FONTWEIGHT_BOLD
            result["italic"] = font.GetStyle() == wx.FONTSTYLE_ITALIC
            result["underline"] = font.GetUnderlined()

        if attr.HasTextColour():
            result["text_color"] = self._from_wx_colour(attr.GetTextColour())

        if attr.HasBackgroundColour():
            result["background_color"] = self._from_wx_colour(
                attr.GetBackgroundColour()
            )

        if attr.HasAlignment():
            result["alignment"] = attr.GetAlignment()

        return result

    def set_style(
        self,
        start: int,
        end: int,
        *,
        font_family: Optional[int] = None,
        font_size: Optional[int] = None,
        font_face: Optional[str] = None,
        bold: Optional[bool] = None,
        italic: Optional[bool] = None,
        underline: Optional[bool] = None,
        text_color: Optional[Union[wx.Colour, str, Tuple[int, int, int]]] = None,
        background_color: Optional[Union[wx.Colour, str, Tuple[int, int, int]]] = None,
        alignment: Optional[int] = None,
    ) -> bool:
        """Apply style to existing text in the range [start, end).

        Note: The text control must have wx.TE_RICH or wx.TE_RICH2 style for this to work.

        Args:
            start: Starting position (0-based index)
            end: Ending position (0-based index)
            font_family: Font family constant (wx.FONTFAMILY_DEFAULT, wx.FONTFAMILY_ROMAN, etc.)
            font_size: Font size in points
            font_face: Font face name like "Arial" or "Courier New"
            bold: Whether text should be bold
            italic: Whether text should be italic
            underline: Whether text should be underlined
            text_color: Text color (wx.Colour, color name string, or RGB tuple)
            background_color: Background color (wx.Colour, color name string, or RGB tuple)
            alignment: Text alignment (wx.TEXT_ALIGNMENT_LEFT, etc.)

        Returns:
            True on success, False on failure
        """
        attr = self._create_text_attr(
            font_family=font_family,
            font_size=font_size,
            font_face=font_face,
            bold=bold,
            italic=italic,
            underline=underline,
            text_color=text_color,
            background_color=background_color,
            alignment=alignment,
        )
        return self.control.SetStyle(start, end, attr)

    def set_default_style(
        self,
        *,
        font_family: Optional[int] = None,
        font_size: Optional[int] = None,
        font_face: Optional[str] = None,
        bold: Optional[bool] = None,
        italic: Optional[bool] = None,
        underline: Optional[bool] = None,
        text_color: Optional[Union[wx.Colour, str, Tuple[int, int, int]]] = None,
        background_color: Optional[Union[wx.Colour, str, Tuple[int, int, int]]] = None,
        alignment: Optional[int] = None,
    ) -> bool:
        """Set the default style for subsequently inserted text.

        This is more efficient than using set_style() after inserting text.
        Note: The text control must have wx.TE_RICH or wx.TE_RICH2 style for this to work.

        Args:
            font_family: Font family constant (wx.FONTFAMILY_DEFAULT, wx.FONTFAMILY_ROMAN, etc.)
            font_size: Font size in points
            font_face: Font face name like "Arial" or "Courier New"
            bold: Whether text should be bold
            italic: Whether text should be italic
            underline: Whether text should be underlined
            text_color: Text color (wx.Colour, color name string, or RGB tuple)
            background_color: Background color (wx.Colour, color name string, or RGB tuple)
            alignment: Text alignment (wx.TEXT_ALIGNMENT_LEFT, etc.)

        Returns:
            True on success, False on failure
        """
        attr = self._create_text_attr(
            font_family=font_family,
            font_size=font_size,
            font_face=font_face,
            bold=bold,
            italic=italic,
            underline=underline,
            text_color=text_color,
            background_color=background_color,
            alignment=alignment,
        )
        return self.control.SetDefaultStyle(attr)

    def get_default_style(self) -> Dict[str, Any]:
        """Get the current default style.

        Returns:
            Dict containing style parameters (font_family, font_size, font_face,
            bold, italic, underline, text_color, background_color, alignment)
        """
        return self._text_attr_to_dict(self.control.GetDefaultStyle())

    def reset_default_style(self) -> bool:
        """Reset the default style to no styling.

        This explicitly resets all style attributes so subsequently inserted text
        will have no special formatting.

        Returns:
            True on success, False on failure
        """
        return self.control.SetDefaultStyle(wx.TextAttr())

    def load_rtf(self, rtf: bytes) -> bool:
        """Replace the control's contents with RTF, parsed by Win32 RichEdit.

        Roughly 50x faster than loading text and then looping SetStyle for
        heavily styled documents because the parser runs entirely in
        RichEdit's C++ side. Windows only — non-Windows callers must use
        the SetStyle/AppendText API.

        The control must have wx.TE_RICH2 (or wx.TE_RICH) for RichEdit to
        be the underlying widget.

        Args:
            rtf: RTF document bytes.

        Returns:
            True on success.

        Raises:
            NotImplementedError: on non-Windows platforms.
        """
        if platform.system() != "Windows":
            raise NotImplementedError("load_rtf is currently Windows-only")
        hwnd = self.control.GetHandle()
        if not hwnd:
            return False
        return _em_streamin_rtf(int(hwnd), rtf)


# Win32 rich edit bindings for Text.load_rtf
_WM_USER = 0x0400
_EM_SETREADONLY = 0x00CF
_EM_SETTEXTEX = _WM_USER + 97
_GWL_STYLE = -16
_ES_READONLY = 0x0800
_ST_DEFAULT = 0
_ST_UNICODE = 8


if platform.system() == "Windows":

    class _SETTEXTEX(ctypes.Structure):
        _fields_ = [
            ("flags", ctypes.c_uint32),
            ("codepage", ctypes.c_uint32),
        ]


def _decode_rtf(rtf: bytes) -> str:
    try:
        return rtf.decode("utf-8")
    except UnicodeDecodeError:
        return rtf.decode("latin-1")


def _set_rtf_value(hwnd: int, rtf: bytes) -> bool:
    text = _decode_rtf(rtf)
    text_info = _SETTEXTEX(_ST_DEFAULT | _ST_UNICODE, 1200)
    user32 = ctypes.windll.user32
    user32.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
    user32.GetWindowLongW.restype = ctypes.c_long
    user32.SendMessageW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    user32.SendMessageW.restype = ctypes.c_ssize_t

    hwnd_arg = ctypes.c_void_p(hwnd)
    was_read_only = bool(user32.GetWindowLongW(hwnd_arg, _GWL_STYLE) & _ES_READONLY)
    if was_read_only:
        user32.SendMessageW(hwnd_arg, _EM_SETREADONLY, 0, 0)
    try:
        result = user32.SendMessageW(
            hwnd_arg,
            _EM_SETTEXTEX,
            ctypes.byref(text_info),
            ctypes.c_wchar_p(text),
        )
    finally:
        if was_read_only:
            user32.SendMessageW(hwnd_arg, _EM_SETREADONLY, 1, 0)
    return result != 0


if platform.system() == "Windows":

    def _em_streamin_rtf(hwnd: int, rtf: bytes) -> bool:
        return _set_rtf_value(hwnd, rtf)
else:

    def _em_streamin_rtf(hwnd: int, rtf: bytes) -> bool:
        raise NotImplementedError("load_rtf is Windows-only")


class IntText(Text):
    widget_type = intctrl.IntCtrl

    def set_value(self, value):
        self.control.SetValue(str(value))

    def get_value(self) -> Optional[int]:
        value = super().get_value()
        if value:
            try:
                value = int(value)
            except ValueError:
                pass
        return value


class StaticText(WXWidget[FieldType, wx.StaticText]):
    control_type = wx.StaticText
    selflabeled = True

    def set_value(self, value: str):
        self.control.SetLabel(value)


class _SectionHeaderPanel(wx.Panel):
    """A wx.Panel containing a bold wx.StaticText, used as a SectionHeader.

    Why a Panel wrapper rather than a wx.StaticText subclass: container
    panels that auto-arrange wx.StaticText children into a label column
    (e.g. wx_utils.autosizing.AutoSizedPanel) check isinstance against
    wx.StaticText. A subclass would still match. Wrapping in a Panel
    means the OUTER widget added to the parent's sizer is a Panel, not
    a StaticText, so it gets full-row treatment.

    The inner StaticText is created with `self` as parent so it does
    not trigger the outer container's AddChild — the StaticText only
    interacts with the Panel's own internal sizer.

    Bold is applied via SetFont on the inner StaticText.
    """

    is_section_header = True  # Honored by wx_utils.AutoSizedPanel as well.

    def __init__(self, parent, label="", **kwargs):
        # wx.Panel doesn't accept `label`. Strip it before super().
        kwargs.pop("label", None)
        super(_SectionHeaderPanel, self).__init__(parent, **kwargs)
        self._text = wx.StaticText(self, label=str(label))
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self._text, 0, wx.TOP | wx.BOTTOM, 4)
        self.SetSizer(sizer)
        base = self._text.GetFont()
        self._text.SetFont(
            wx.Font(
                base.GetPointSize(),
                base.GetFamily(),
                base.GetStyle(),
                wx.FONTWEIGHT_BOLD,
                base.GetUnderlined(),
                base.GetFaceName(),
            )
        )

    def SetLabel(self, label):
        self._text.SetLabel(str(label))
        self.Layout()

    def GetLabel(self):
        return self._text.GetLabel()

    def Wrap(self, width: int) -> None:
        self._text.Wrap(width)
        self.Layout()

    def IsEllipsized(self) -> bool:
        return self._text.IsEllipsized()


class SectionHeader(WXWidget[FieldType, wx.Panel]):
    control_type = _SectionHeaderPanel
    selflabeled = True
    focusable = False

    def set_value(self, value: str):
        self.control.SetLabel(value)

    def is_ellipsized(self) -> bool:
        """Check if the text is ellipsized (truncated with '...')."""
        return self.control.IsEllipsized()

    def wrap(self, width: int) -> None:
        """Wrap the text to fit within the specified width."""
        self.control.Wrap(width)


class CheckBox(WXWidget[FieldType, wx.CheckBox]):
    control_type = wx.CheckBox
    default_callback_type = "checkbox"
    selflabeled = True


class ComboBox(Text, ChoiceWidget[FieldType, wx.ComboBox, str, str]):
    control_type = wx.ComboBox
    style_prefix = "CB"
    default_callback_type = "combobox"

    def _convert_input_to_output(self, item: str) -> str:
        """For ComboBox, input and output are both strings."""
        return item

    def get_value(self) -> str:
        return self.control.GetValue()

    def set_label(self, label: str):
        if self.label_control is not None:
            self.label_control.SetLabel(label)

    def select_all(self):
        self.control.SelectAll()

    def insert_item(self, index: int, item: ChoiceItemInputType):
        return self.control.Insert(item, index)


class Button(WXWidget[FieldType, wx.Button]):
    control_type = wx.Button
    default_callback_type = "button"
    selflabeled = True

    def __init__(self, default=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default = default

    def render(self, *args, **kwargs):
        super().render(*args, **kwargs)
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
        super().SetValue(value)
        ctypes.windll.user32.NotifyWinEvent(
            self.EVENT_OBJECT_VALUECHANGE,
            self.Handle,
            self.OBJID_CLIENT,
            self.CHILDID_SELF,
        )

    def onSliderChar(self, evt: wx.KeyEvent):
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


class Slider(WXWidget[FieldType, wx.Slider]):
    style_prefix = "SL"
    if platform.system() == "Windows":
        control_type = FixedSlider
    else:
        control_type = wx.Slider
    default_callback_type = "slider"

    def __init__(
        self,
        page_size: Optional[int] = None,
        min_value=0,
        max_value=100,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
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


class ScrollBar(WXWidget[FieldType, wx.ScrollBar]):
    control_type = wx.ScrollBar
    style_prefix = "SB"
    default_callback_type = "scrollbar"


class ListBox(ChoiceWidget[FieldType, wx.ListBox, str, str]):
    control_type = wx.ListBox
    style_prefix = "LB"
    default_callback_type = "listbox"

    def _convert_input_to_output(self, item: str) -> str:
        """For ListBox, input and output are both strings."""
        return item


ListViewType = TypeVar("ListViewType", bound=Union[wx.ListView, "VirtualListView"])


class ListView(
    ChoiceWidget[FieldType, ListViewType, Tuple[str, ...], Tuple[str]],
    Generic[FieldType, ListViewType],
):
    control_type = wx.ListView
    style_prefix = "LC"
    event_prefix = "EVT_LIST"
    default_callback_type = "ITEM_SELECTED"

    def _convert_input_to_output(self, item: Tuple[str, ...]) -> Tuple[str, ...]:
        """For ListView, input and output are both tuples of strings."""
        return item

    def __init__(self, choices=None, **kwargs):
        self.virtual = kwargs.pop("virtual", False)
        if self.virtual:
            self.control_type = VirtualListView
            kwargs["style"] = kwargs.get("style", 0)
            kwargs["style"] |= wx.LC_VIRTUAL | wx.LC_REPORT
        super().__init__(**kwargs)
        if choices is None:
            choices = []
        self.choices = choices
        self._last_added_column = -1

    def get_index(self) -> Optional[int]:
        return translate_to_none(self.control.GetFirstSelected())

    def set_index(self, index: Optional[int]) -> None:
        if index is None:
            index = -1
        self.control.Select(index)
        self.control.Focus(index)

    def get_count(self) -> int:
        return self.control.GetItemCount()

    def get_column_count(self) -> int:
        return self.control.GetColumnCount()

    def get_item(self, index: int) -> ChoiceItemOutputType:
        res = []
        for column in range(self.get_column_count()):
            res.append(self.get_item_column(index, column))
        return cast(ChoiceItemOutputType, tuple(res))

    def get_items(self) -> Sequence[ChoiceItemOutputType]:
        res = []
        for num in range(self.get_count()):
            res.append(self.get_item(num))
        return cast(Sequence[ChoiceItemOutputType], res)

    def get_item_column(self, index: int, column: int) -> str:
        return self.control.GetItemText(index, column)

    def set_item_column(self, index, column, data):
        self.control.SetStringItem(index, column, data)

    def add_item(self, item: ChoiceItemInputType):
        self.control.Append(item)

    def set_item(self, index: int, item: ChoiceItemInputType) -> None:
        for column, subitem in enumerate(item):
            self.set_item_column(index, column, str(subitem))

    def update_item(self, index: int, item: ChoiceItemInputType):
        return self.set_item(index, item)

    def set_items(self, items: Sequence[ChoiceItemInputType]):
        if self.virtual:
            self.control.SetItems(list(items))
        self.clear()

        for item in items:
            self.add_item(item)

    def insert_item(self, index: int, item: ChoiceItemInputType):
        return self.control.InsertStringItem(index, item)

    def delete_item(self, index: int):
        self.control.DeleteItem(index)

    def clear(self):
        self.control.DeleteAllItems()

    def render(self, **kwargs):
        super().render(**kwargs)
        self.set_value(self.choices)

    def add_column(self, column_number=None, label="", width=None, **format):
        if column_number is None:
            column_number = self._last_added_column + 1
        if width is None:
            width = -1
        column_format = self._resolve_column_format(**format)
        created_column = self.create_column(
            column_number, label, width=width, format=column_format
        )
        self._last_added_column = column_number
        if created_column is None:
            return column_number
        return created_column

    def _resolve_column_format(self, **format) -> int:
        explicit_format = format.pop("format", None)
        if explicit_format is not None:
            return int(explicit_format)
        if format.pop("right", False):
            return wx.LIST_FORMAT_RIGHT
        if format.pop("center", False) or format.pop("centre", False):
            return wx.LIST_FORMAT_CENTRE
        return wx.LIST_FORMAT_LEFT

    def create_column(self, column_number: int, label: str, width: int, format: int):
        return self.control.InsertColumn(
            column_number, label, width=width, format=format
        )

    def delete_column(self, column_number: int):
        self.control.DeleteColumn(column_number)

    def get_value(self) -> Sequence[ChoiceItemOutputType]:
        return self.get_items()

    def set_value(self, value: Sequence[ChoiceItemInputType]):
        self.set_items(value)


class ListViewColumn(WXWidget[FieldType, wx.ListItem]):
    if TYPE_CHECKING:
        parent: ListView

    def create_control(self, **runtime_kwargs):
        kwargs = self.control_kwargs
        kwargs.update(runtime_kwargs)
        kwargs["label"] = str(self.label_text)
        translated_kwargs = self.translate_control_arguments(**kwargs)
        self.column_index = self.parent.add_column(**translated_kwargs)
        self.control = self.column_index

    def render(self, *args, **kwargs):
        logger.debug("Rendering ListView column")
        self.create_control()

    def set_item(self, index: int, item: Any) -> None:
        self.parent.set_item_column(index, self.column_index, str(item))

    def destroy(self) -> None:
        return None


if dataview:

    class DataView(ListView[FieldType, dataview.DataViewListCtrl]):
        control_type = dataview.DataViewListCtrl
        event_prefix = "EVT_DATAVIEW"
        style_prefix = ""
        event_module = dataview
        default_callback_type = "selection_changed"

        def __init__(self, choices=None, **kwargs):
            super().__init__(**kwargs)
            if choices is None:
                choices = []

            self.choices = choices

            def add_item(self, item):
                self.control.AppendItem(item)

            def insert_item(self, index: int, item):
                return self.control.InsertItem(index, item)

            def get_count(self) -> int:
                return self.control.GetStore().GetCount()

            def get_column_count(self) -> int:
                return self.control.GetStore().GetColumnCount()

            def get_index(self) -> Optional[int]:
                return translate_to_none(self.control.GetSelectedRow())

            def set_index(self, index: Optional[int]) -> None:
                if index is None:
                    return
                index = int(index)
                if index == 0 and self.get_count() == 0:
                    return
                self.control.SelectRow(index)

            def create_column(self, column_number, label, width, format):
                self.control.AppendTextColumn(label, align=format, width=width)

            def get_item_column(self, index: int, column: int) -> str:
                return self.control.GetTextValue(index, column)

            def set_item_column(self, index: int, column: int, data: str) -> None:
                self.control.SetTextValue(data, index, column)


class SpinBox(WXWidget[FieldType, wx.SpinCtrl]):
    control_type = wx.SpinCtrl
    style_prefix = "SP"
    default_callback_type = "SPINCTRL"

    def __init__(self, min: int = 0, max: int = 100, *args, **kwargs):
        super(SpinBox, self).__init__(*args, **kwargs)
        self.min = min
        self.max = max

    def render(self, *args, **kwargs):
        super().render(*args, **kwargs)
        self.set_min(self.min)
        self.set_max(self.max)

    def set_min(self, min: int):
        self.control.SetMin(min)
        self.min = min

    def set_max(self, max: int):
        self.control.SetMax(max)
        self.max = max


class ButtonSizer(WXWidget[FieldType, wx.StdDialogButtonSizer]):
    control_type = wx.StdDialogButtonSizer
    unlabeled = True
    focusable = False
    if TYPE_CHECKING:
        parent: BaseContainer

    def realize(self):
        self.control.Realize()

    def add_button(self, button: Button):
        self.control.AddButton(button.get_control())

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
                logger.debug("Finding id for kwarg %s" % kwarg)

                try:
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


class BaseContainer(
    WXWidget[FieldType, ContainerWidgetType], Generic[FieldType, ContainerWidgetType]
):
    unlabeled = True

    def __init__(self, top_level_window=False, *args, **kwargs):
        super(BaseContainer, self).__init__(*args, **kwargs)
        self.top_level_window = top_level_window

    def render(self, *args, **kwargs):
        super(BaseContainer, self).render(*args, **kwargs)
        if self.top_level_window:
            wx.GetApp().SetTopWindow(self.control)

    def set_title(self, title: str) -> None:
        self.control.SetTitle(str(title))

    def get_title(self) -> str:
        return self.control.GetTitle()

    def set_label(self, label):
        logger.warning("set_label called on container %r" % self)

    def close(self):
        self.control.Close()


DialogControlType = TypeVar("DialogControlType", bound=wx.Dialog)


class BaseDialog(
    BaseContainer[FieldType, DialogControlType], Generic[FieldType, DialogControlType]
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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


class SizedDialog(BaseDialog[FieldType, sc.SizedDialog]):
    control_type = sc.SizedDialog


class SizedPanel(BaseContainer[FieldType, sc.SizedPanel]):
    control_type = sc.SizedPanel
    if TYPE_CHECKING:
        control: sc.SizedPanel
    focusable = False

    def __init__(
        self,
        sizer_type="vertical",
        narrow_sizer_type=None,
        narrow_below_chars=None,
        *args,
        **kwargs,
    ):
        """Create a panel that lays its children out with a sizer.

        Args:
            sizer_type: Sizer for the normal (wide) layout: "vertical",
                "horizontal", "form" or "grid".
            narrow_sizer_type: Sizer to switch to when the wide layout does
                not fit the panel's width, using the same names. None keeps
                sizer_type at every width, except that a "horizontal" row
                wraps onto more lines (wx.WrapSizer) when it does not fit.
                Children are re-added in creation
                order, so Tab and screen reader order do not change. Child
                fields declared with hidden_when_narrow=True are hidden while
                narrow.
            narrow_below_chars: Optional fixed threshold, in average character
                widths of the panel's font: the narrow layout is used while
                the panel is narrower than this. None (the default) uses the
                narrow layout only while the wide layout's minimum width is
                larger than the panel.
        """
        super().__init__(*args, **kwargs)
        self.sizer_type = sizer_type
        if narrow_sizer_type is None and sizer_type == "horizontal":
            narrow_sizer_type = "wrap"
        self.narrow_sizer_type = narrow_sizer_type
        self.narrow_below_chars = narrow_below_chars
        self.is_narrow = False
        self._wide_min_width = 0
        self._min_size = None
        self._hidden_when_narrow = []
        self._switching = False
        self._narrow_min_width = -1

    def render(self):
        super().render()
        self._apply_sizer_type(self.sizer_type)
        if self.narrow_sizer_type is not None:
            self.control.Bind(wx.EVT_SIZE, self._on_size)
            self.control.Bind(wx.EVT_DPI_CHANGED, self._on_dpi_changed)
            # Deferred, so the window first takes the wide layout's size.
            wx.CallAfter(self._pin_narrow_min_width)

    def _pin_narrow_min_width(self):
        """Use the narrow layout's minimum width as the panel's minimum width.

        The best size stays the wide layout's, so the window still opens
        wide, but a window that takes its minimum size from its sizer can
        now be made narrow enough for the panel to switch. Measured once.
        """
        if not self.control:
            return
        if self.is_narrow:
            width = self.control.GetSizer().CalcMin().width
        else:
            self.control.Freeze()
            try:
                self._set_narrow(True)
                width = self.control.GetSizer().CalcMin().width
                self._set_narrow(False)
                self.control.Layout()
            finally:
                self.control.Thaw()
        self._narrow_min_width = width
        height = -1
        if isinstance(self.control.GetSizer(), wx.WrapSizer):
            height = self.control.GetMinSize().height
        self.control.SetMinSize(self._pinned_min_size(height))
        # Windows that read their sizer's minimum on resize pick it up.
        self.control.GetTopLevelParent().SendSizeEvent()

    def _pinned_min_size(self, height=-1):
        # The app's declared min_size, widened to the narrow layout's
        # minimum width and raised to the given height.
        min_width, min_height = self.min_size or (-1, -1)
        return wx.Size(
            max(min_width, self._narrow_min_width), max(min_height, height)
        )

    def update_layout(self) -> None:
        """Re-check whether the wide layout fits, and switch if needed.

        Called automatically on resize and DPI change, and by BaseForm.refresh.
        Call it after changing fonts, which does not resize the panel. The
        check runs after the panel's next paint: GTK measures a new font only
        in its next frame, and only for shown controls.
        """
        if self.narrow_sizer_type is None or self._switching:
            return
        if self.is_narrow and self.narrow_below_chars is None:
            # The wide layout's minimum width can only be measured in it.
            self._set_narrow(False)
        # Ignore resizes until the deferred check has measured.
        self._switching = True
        if self.control.IsShownOnScreen():
            self.control.Bind(wx.EVT_PAINT, self._on_paint_after_update)
            self.control.Refresh()
        else:
            wx.CallAfter(self._deferred_check)

    def _on_paint_after_update(self, event):
        event.Skip()
        self.control.Unbind(wx.EVT_PAINT, handler=self._on_paint_after_update)
        wx.CallAfter(self._deferred_check)

    def _deferred_check(self):
        if not self.control:
            return
        self._switching = False
        for child in self.control.GetChildren():
            child.InvalidateBestSize()
        self._check_fit()
        self._fit_in_parent()

    def _on_size(self, event):
        event.Skip()
        if self._switching:
            # Hiding or showing a field lays out the ancestors, resizing
            # this panel in the middle of a switch.
            return
        self._check_fit()
        self._fit_in_parent()

    def _on_dpi_changed(self, event):
        event.Skip()
        self.update_layout()

    def _fit_in_parent(self):
        # Switching layouts, or a wrap sizer re-flowing, changes the panel's
        # minimum size; the parent's sizer has to be told to make room.
        self.control.Layout()
        sizer = self.control.GetSizer()
        wrap = isinstance(sizer, wx.WrapSizer)
        width = self.control.GetClientSize().width
        if wrap and hasattr(sizer, "CalcMinSizeFromKnownDirection"):
            # wxWidgets 3.3: InformFirstDirection is a no-op stub there.
            min_size = sizer.CalcMinSizeFromKnownDirection(wx.HORIZONTAL, width, -1)
        else:
            if wrap:
                # wxWidgets 3.2: right after InformFirstDirection, CalcMin
                # depends only on the items and the width.
                sizer.InformFirstDirection(wx.HORIZONTAL, width, -1)
            min_size = sizer.CalcMin()
        if wrap:
            # The parent reads the panel's best size, which comes from the
            # wrap sizer's state-dependent CalcMin; on MSW it gave one row's
            # height, clipping the rest. Pin the minimum height instead.
            self.control.SetMinSize(self._pinned_min_size(min_size.height))
        if min_size != self._min_size:
            self._min_size = min_size
            self.control.InvalidateBestSize()
            wx.CallAfter(self._layout_parent)

    def _layout_parent(self):
        if self.control:
            self.control.GetParent().Layout()

    def _check_fit(self):
        if self.narrow_below_chars is not None:
            needed = self.narrow_below_chars * self.control.GetCharWidth()
        else:
            if not self.is_narrow:
                self._wide_min_width = self.control.GetSizer().CalcMin().width
            needed = self._wide_min_width
        narrow = self.control.GetClientSize().width < needed
        if narrow != self.is_narrow:
            self._set_narrow(narrow)

    def _set_narrow(self, narrow):
        self._switching = True
        try:
            self._switch_layout(narrow)
        finally:
            self._switching = False

    def _switch_layout(self, narrow):
        self.is_narrow = narrow
        if narrow:
            # Fields the app already hid are left alone, and never re-shown.
            self._hidden_when_narrow = [
                child
                for child in self.field.get_children()
                if child.hidden_when_narrow and child.is_shown()
            ]
            for child in self._hidden_when_narrow:
                child.widget.hide()
            self._apply_sizer_type(self.narrow_sizer_type)
        else:
            self._apply_sizer_type(self.sizer_type)
            for child in self._hidden_when_narrow:
                # Fields the app hid while narrow stay hidden.
                if not child.hidden_by_app:
                    child.widget.show()
            self._hidden_when_narrow = []

    def _apply_sizer_type(self, sizer_type):
        if sizer_type != "wrap":
            if isinstance(self.control.GetSizer(), wx.WrapSizer):
                # Drop the minimum height set while wrapped.
                self.control.SetMinSize(self._pinned_min_size())
            self.control.SetSizerType(sizer_type)
            return
        # SetSizerType has no wrap sizer. Move the children across in
        # GetChildren() order, keeping each one's sizer settings. Without
        # EXTEND_LAST_ON_EACH_LINE, which rewrites child proportions that
        # SetSizerType would then carry over.
        old = self.control.GetSizer()
        sizer = wx.WrapSizer(wx.HORIZONTAL, wx.REMOVE_LEADING_SPACES)
        for child in self.control.GetChildren():
            item = old.GetItem(child)
            if item is None:
                continue
            proportion, flag, border = (
                item.GetProportion(),
                item.GetFlag(),
                item.GetBorder(),
            )
            user_data = item.GetUserData()
            old.Detach(child)
            sizer.Add(child, proportion, flag, border, user_data)
        self.control.SetSizer(sizer)


FrameControlType = TypeVar("FrameControlType", bound=wx.Frame)


class BaseFrame(
    BaseContainer[FieldType, FrameControlType], Generic[FieldType, FrameControlType]
):
    def __init__(self, maximized: bool = False, *args, **kwargs):
        self.control_maximized = maximized
        super(BaseFrame, self).__init__(*args, **kwargs)

    def render(self, *args, **kwargs):
        super().render(*args, **kwargs)
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


class Frame(BaseFrame[FieldType, wx.Frame]):
    control_type = wx.Frame


class SizedFrame(BaseFrame[FieldType, sc.SizedFrame]):
    control_type = sc.SizedFrame
    if TYPE_CHECKING:
        control: sc.SizedFrame

    def get_control(self) -> wx.Panel:
        return self.control.mainPanel

    def set_content_padding(self, padding: int) -> None:
        """Set padding around the frame's content area.

        Args:
            padding (int): Padding in pixels around all content
        """
        pane: sc.SizedPanel = self.control.GetContentsPane()
        pane.SetSizerProps(border=("all", padding))


class MDIParentFrame(BaseFrame[FieldType, wx.MDIParentFrame]):
    control_type = wx.MDIParentFrame


class MDIChildFrame(BaseFrame[FieldType, wx.MDIChildFrame]):
    control_type = wx.MDIChildFrame


class Dialog(BaseDialog[FieldType, wx.Dialog]):
    control_type = wx.Dialog


class Panel(BaseContainer[FieldType, wx.Panel]):
    control_type = wx.Panel
    focusable = False


class Notebook(BaseContainer[FieldType, wx.Notebook]):
    control_type = wx.Notebook
    event_prefix = "EVT_NOTEBOOK"
    default_callback_type = "page_changed"

    def add_item(self, name, item: WXWidget):
        self.control.AddPage(item.control, str(name))
        # Now, we shall have much hackyness to work around WX bug 11909
        logger.debug(f"Adding notebook page '{name}'")
        item_children = (
            list(item.field.get_all_children()) if hasattr(item, "field") else None
        )
        if not item_children:
            logger.debug(
                f"Page '{name}' has no children, skipping navigation handler binding"
            )
            return

        def on_focus(evt):
            evt.Skip()

        def on_navigation_key(evt: wx.Event):
            # Cast to the specific event type we expect
            nav_evt = cast(wx.NavigationKeyEvent, evt)

            # Don't interfere with Ctrl+Tab or Ctrl+PageUp/PageDown - let wxPython handle tab switching
            if self.control_down:
                logger.debug(
                    "Ctrl pressed at page level, allowing default notebook tab switching"
                )
                nav_evt.Skip()
                return

            # Get the currently focused window using FindFocus instead of evt.GetCurrentFocus
            focused_window = wx.Window.FindFocus()
            direction: bool = nav_evt.GetDirection()  # True = forward, False = backward

            logger.debug(
                f"Page navigation: direction={'forward' if direction else 'backward'}"
            )

            # Get the enabled, focusable children of this page
            enabled_children = [
                child
                for child in item.field.get_all_children()
                if child.widget.enabled
                and child.can_be_focused()
                and child.widget.can_accept_focus()
            ]

            if not enabled_children:
                logger.debug("No enabled children, allowing default navigation")
                nav_evt.Skip()
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

            logger.debug(
                f"Current control: {current_control.bound_name if current_control else 'not found'}"
            )

            if current_control:
                # Forward tab from last control -> go to notebook
                if direction and current_control == last_child:
                    logger.debug(
                        f"At last control '{current_control.bound_name}', transferring focus to notebook"
                    )
                    self.set_focus()
                    return  # Consume the event

                # Backward tab from first control -> go to notebook
                elif not direction and current_control == first_child:
                    logger.debug(
                        f"At first control '{current_control.bound_name}', transferring focus to notebook"
                    )
                    self.set_focus()
                    return  # Consume the event

            # Normal intra-page navigation
            logger.debug("Allowing normal intra-page navigation")
            nav_evt.Skip()

        logger.debug(f"Binding navigation handlers to page '{name}'")
        item.bind_event(wx.EVT_CHILD_FOCUS, on_focus)
        item.bind_event(wx.EVT_NAVIGATION_KEY, on_navigation_key)

    def delete_page(self, page: BaseContainer[Any, wx.Panel]):
        self.control.DeletePage(self.find_page_number(page))

    def render(self, *args, **kwargs):
        super().render(*args, **kwargs)

        self.control_down = False
        self._setting_notebook_focus = False  # Guard against recursive focus calls

        def key_down_up(evt: wx.KeyEvent):
            self.control_down = evt.ControlDown()
            evt.Skip()

        def on_notebook_navigation(evt: wx.Event):
            # Cast to the specific event type we expect
            nav_evt = cast(wx.NavigationKeyEvent, evt)

            # Don't interfere with Ctrl+Tab or Ctrl+PageUp/PageDown - let wxPython handle tab switching
            if self.control_down:
                logger.debug("Ctrl pressed, allowing default notebook tab switching")
                nav_evt.Skip()
                return

            direction: bool = nav_evt.GetDirection()  # True = forward, False = backward
            current_page_index = self.control.GetSelection()

            logger.debug(
                f"Notebook navigation: direction={'forward' if direction else 'backward'}, page={current_page_index}"
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
                                logger.debug(
                                    f"Transferring focus to first control '{first_child.bound_name}'"
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
                                logger.debug(
                                    f"Transferring focus to last control '{last_child.bound_name}'"
                                )
                                last_child.set_focus()
                                return  # Consume the event
                            break

            # If we can't find appropriate controls, allow normal navigation
            logger.debug("Allowing normal navigation")
            nav_evt.Skip()

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


class RadioBox(ChoiceWidget[FieldType, wx.RadioBox, str, str]):
    control_type = wx.RadioBox
    default_callback_type = "RADIOBOX"
    selflabeled = True
    style_prefix = "RA"

    def _convert_input_to_output(self, item: str) -> str:
        """For RadioBox, input and output are both strings."""
        return item

    def get_value(self) -> str:
        return self.control.GetStringSelection()

    def set_value(self, value: str) -> None:
        self.control.SetStringSelection(value)

    def get_items(self) -> Sequence[str]:
        return list(self.control.GetStrings())

    def set_items(self, items: Sequence[str]) -> Sequence[str]:
        """Set items and return the converted output items."""
        converted_items = [self._convert_input_to_output(item) for item in items]
        if len(converted_items) != self.control.GetCount():
            raise NotImplementedError(
                "RadioBox choices can only be relabeled after rendering; "
                "changing the number of choices requires recreating the control."
            )
        for index, item in enumerate(converted_items):
            self.control.SetString(index, item)
        return converted_items


class CheckListBox(ListBox):
    default_callback_type = "CHECKLISTBOX"
    control_type = wx.CheckListBox


class FilePicker(WXWidget[FieldType, wx.FilePickerCtrl]):
    control_type = wx.FilePickerCtrl

    def __init__(self, initial_directory: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.initial_directory = initial_directory

    def render(self, *args, **kwargs):
        super().render(*args, **kwargs)
        if self.initial_directory is not None:
            self.set_initial_directory(self.initial_directory)

    def get_path(self) -> str:
        return self.control.GetPath()

    def set_path(self, path: str) -> None:
        self.control.SetPath(path)

    def set_initial_directory(self, directory: str) -> None:
        self.control.SetInitialDirectory(directory)


class MenuBar(WXWidget[FieldType, wx.MenuBar]):
    control_type = wx.MenuBar
    focusable = False
    unlabeled = True

    def create_control(self, **kwargs):
        self.control = self.control_type()
        wx.GetApp().GetTopWindow().SetMenuBar(self.control)

    def render(self, *args, **kwargs):
        super().render(*args, **kwargs)
        if platform.system() == "Darwin":
            wx.MenuBar.MacSetCommonMenuBar(self.control)

    def add_item(self, name=None, item=None):
        if item is None:
            raise TypeError("Must provide a MenuItem")
        name = name or item.name
        control = item.control
        self.control.Append(control, name)


class Menu(WXWidget[FieldType, wx.Menu]):
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

    def append_item(self, item):
        self.control.Append(item.control)

    def append_submenu(self, submenu, text):
        self.control.AppendSubMenu(submenu.control, text=text)

    def set_label(self, label: str) -> None:
        """Set this menu's title in its menu bar, or its item text in a parent menu.

        Args:
            label (str): The new label (any object; converted with str()).
        """
        label = str(label)
        if isinstance(self.parent, MenuBar):
            menu_bar = self.parent.control
            for pos in range(menu_bar.GetMenuCount()):
                if menu_bar.GetMenu(pos) is self.control:
                    menu_bar.SetMenuLabel(pos, label)
                    return
        parent_menu = self.control.GetParent()
        if parent_menu is not None:
            for item in parent_menu.GetMenuItems():
                if item.GetSubMenu() is self.control:
                    item.SetItemLabel(label)
                    return


class MenuItem(WXWidget[FieldType, wx.MenuItem]):
    control_type = wx.MenuItem
    if TYPE_CHECKING:
        parent: Menu
    default_callback_type = "MENU"
    focusable = False
    unlabled = True

    def __init__(self, hotkey=None, help_message="", checkable=False, **kwargs):
        self.hotkey = hotkey
        self.help_message = help_message
        self.checkable = checkable
        self.control_id = None
        self.control_text_color = None
        super().__init__(**kwargs)

    def get_parent_control(self) -> wx.Menu:
        return super().get_parent_control()

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
            self.control_id, label, str(self.help_message), kind=kind
        )

    def set_label(self, label: str) -> None:
        """Set this menu item's text, keeping its hotkey.

        Args:
            label (str): The new label (any object; converted with str()).
        """
        if self.control.IsSeparator():
            return
        label = str(label)
        if self.hotkey is not None:
            label = "%s\t%s" % (label, self.hotkey)
        self.control.SetItemLabel(label)

    def bind_event(self, callback_event, wrapped_callback):
        parent = self.get_top_level_parent()
        if parent and isinstance(parent, (WXWidget)):
            parent.control.Bind(callback_event, wrapped_callback, self.control)
        # Fix if we're called from a menu bar
        if isinstance(self.parent, SubMenu):
            self.parent.control.Bind(callback_event, wrapped_callback, self.control)

    def get_top_level_parent(self):
        parent = self.parent
        while isinstance(parent, SubMenu):
            parent = parent.parent
        return parent

    def render(self, *args, **kwargs):
        super().render(*args, **kwargs)
        if not self.control_enabled:
            self.disable()
        if self.control_text_color is not None:
            self.set_text_color(self.control_text_color)

    def enable(self):
        self.control.Enable(True)

    def disable(self):
        self.control.Enable(False)

    def is_enabled(self) -> bool:
        return self.control.IsEnabled()

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

    def is_separator(self) -> bool:
        return self.control.IsSeparator()

    def is_checked(self) -> bool:
        return self.control.IsChecked()

    def is_checkable(self) -> bool:
        return self.control.IsCheckable()

    def get_text_color(self) -> wx.Colour:
        return self.control.GetTextColour()

    def set_text_color(self, color: wx.Colour):
        self.control.SetTextColour(color)

    text_color = property(get_text_color, set_text_color)

    def destroy(self):
        self.parent.destroy_item(self)


class SubMenu(Menu):
    if TYPE_CHECKING:
        parent: Menu

    def create_control(self, **kwargs):
        text = str(kwargs.get("label", self.label_text))
        self.control = wx.Menu()
        self.parent.append_submenu(self, text=text)


class StatusBar(WXWidget[FieldType, wx.StatusBar]):
    if TYPE_CHECKING:
        parent: BaseFrame
    control_type = wx.StatusBar
    style_prefix = "SB"
    focusable = False

    def create_control(self, **kwargs):
        self.control = self.parent.control.CreateStatusBar(**kwargs)

    def set_value(self, value):
        self.set_status_text(value)

    def get_value(self, field=0) -> str:
        return self.get_status_text(field)

    def set_status_text(self, text: str, field=0):
        self.control.SetStatusText(text, field)

    def get_status_text(self, field=0) -> str:
        return self.control.GetStatusText(field)

    status_text = property(get_status_text, set_status_text)

    def get_status_field_count(self) -> int:
        return self.control.GetFieldsCount()

    def set_status_widths(self, widths: List[int]):
        self.control.SetStatusWidths(widths)

    def get_status_widths(self) -> List[int]:
        return [self.get_status_width(i) for i in range(self.get_status_field_count())]

    def get_status_width(self, field) -> int:
        return self.control.GetStatusWidth(field)


class Link(WXWidget[FieldType, wx.adv.HyperlinkCtrl]):
    control_type = wx.adv.HyperlinkCtrl
    event_module = wx.adv
    default_callback_type = "hyperlink"
    selflabeled = True

    def create_control(self, **kwargs):
        if "URL" in kwargs:
            kwargs["url"] = kwargs.pop("URL")
        return super().create_control(**kwargs)

    def get_normal_color(self) -> wx.Colour:
        return self.control.GetNormalColour()

    def set_normal_color(self, color: wx.Colour):
        self.control.SetNormalColour(color)

    normal_color = property(get_normal_color, set_normal_color)

    def get_hover_color(self) -> wx.Colour:
        return self.control.GetHoverColour()

    def set_hover_color(self, color: wx.Colour):
        self.control.SetHoverColour(color)

    hover_color = property(get_hover_color, set_hover_color)

    def get_visited_color(self) -> wx.Colour:
        return self.control.GetVisitedColour()

    def set_visited_color(self, color: wx.Colour):
        self.control.SetVisitedColour(color)

    visited_color = property(get_visited_color, set_visited_color)


class DatePicker(WXWidget[FieldType, wx.adv.DatePickerCtrl]):
    control_type = wx.adv.DatePickerCtrl
    event_module = wx.adv
    default_callback_type = "date_changed"

    def __init__(self, range=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.range = range

    def render(self, *args, **kwargs):
        super().render(*args, **kwargs)
        if self.range is not None:
            self.set_range(*self.range)

    def get_value(self):
        value: wx.DateTime = super(DatePicker, self).get_value()
        return wx.wxdate2pydate(value)

    def set_value(self, value):
        super().set_value(self.convert_datetime(value))

    def convert_datetime(
        self, dt: Union[wx.DateTime, datetime.date, datetime.datetime]
    ):
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
        super().__init__(*args, **kwargs)
        self.items: list[Sequence[str]] = []

    def Append(self, entry: Sequence[str]):
        self.items.append(entry)
        self.SetItemCount(len(self.items))

    def SetItems(self, items: list[Sequence[str]]):
        self.items = items
        self.SetItemCount(len(self.items))

    def OnGetItemText(self, item: int, column: int) -> str:
        return self.items[item][column]

    def DeleteAllItems(self):
        self.items = []
        self.SetItemCount(0)

    def SetStringItem(self, index: int, column: int, data: str):
        row = list(self.items[index])
        row[column] = data
        self.items[index] = row


class TreeView(WXWidget[FieldType, wx.TreeCtrl]):
    control_type = wx.TreeCtrl
    style_prefix = "TR"
    event_prefix = "EVT_TREE"
    default_callback_type = "SEL_CHANGED"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.image_list: Optional[wx.ImageList] = None

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
                self.image_list = self.create_image_list(image.Width, image.Height)
            image = self.image_list.Add(image.ConvertToBitmap())
        return self.control.AppendItem(parent, str(text), image, selected_image, data)

    def create_image_list(self, width=32, height=32) -> wx.ImageList:
        image_list = wx.ImageList(width, height)
        self.control.AssignImageList(image_list)
        return image_list

    def clear(self):
        self.control.DeleteAllItems()
        if self.image_list is not None:
            self.image_list.RemoveAll()
            self.image_list = None

    def collapse_all(self):
        """Collapse all tree nodes."""
        self.control.CollapseAll()

    def delete(self, item):
        """Delete a tree item."""
        self.control.Delete(item)

    def get_selection(self):
        return self.control.GetSelection()

    def select_item(self, item):
        self.control.SelectItem(item)

    def get_data(self, item):
        return self.control.GetItemData(item)

    def set_item_has_children(self, item, val):
        self.control.SetItemHasChildren(item, val)


class ProgressBar(WXWidget[FieldType, wx.Gauge]):
    control_type = wx.Gauge
    style_prefix = "GA"
    focusable = False

    def __init__(self, range=100, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.control_range = range

    def render(self, *args, **kwargs):
        super().render(*args, **kwargs)
        self.set_range(self.control_range)

    def get_value(self) -> int:
        return self.control.GetValue()

    def set_value(self, value: int) -> None:
        self.control.SetValue(value)

    def set_range(self, range: int) -> None:
        self.control.SetRange(range)
        self.control_range = range

    def get_range(self) -> int:
        return self.control.GetRange()

    range = property(get_range, set_range)

    def pulse(self):
        self.control.Pulse()


class ToolBar(WXWidget[FieldType, wx.ToolBar]):
    control_type = wx.ToolBar
    style_prefix = "TB"

    def __init__(self, tool_bitmap_size: Tuple[int, int] = (16, 16), *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tool_bitmap_size = tool_bitmap_size

    def add_simple_tool(
        self, id=wx.ID_ANY, bitmap=None, short_text="", *args, **kwargs
    ):
        if bitmap is not None:
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

    def bind_event(self, callback_event, wrapped_callback, id=None):
        return self.control.Bind(callback_event, wrapped_callback, id)

    def realize(self):
        return self.control.Realize()

    def render(self, **runtime_kwargs):
        super().render(**runtime_kwargs)
        self.set_tool_bitmap_size(self.tool_bitmap_size)

    def set_tool_bitmap_size(self, tool_bitmap_size: Tuple[int, int]):
        self.control.SetToolBitmapSize(wx.Size(*tool_bitmap_size))
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

    def bind_event(self, callback_event, wrapped_callback):
        self.parent.bind_event(callback_event, wrapped_callback, id=self.control)


class StaticBitmap(WXWidget[FieldType, wx.StaticBitmap]):
    control_type = wx.StaticBitmap

    def load_image(self, image):
        return self.control.SetBitmap(wx.BitmapFromImage(image))
