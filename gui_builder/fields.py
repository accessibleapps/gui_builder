from __future__ import absolute_import, annotations

import traceback
from logging import getLogger
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Optional,
    Protocol,
    Type,
    TypeVar,
    Union,
    overload,
)

from .widgets import wx_widgets as widgets

logger = getLogger("gui_builder.fields")


class SupportsStr(Protocol):
    """Protocol for objects that can be converted to string.

    This allows gui_builder to accept string-like objects (like LazyProxy from i18n)
    without knowing about specific implementations.
    """

    def __str__(self) -> str: ...


# Type variables for proper generic descriptor support
FieldType = TypeVar("FieldType", bound="GUIField[Any]", covariant=True)
FormInstanceType = TypeVar("FormInstanceType")
SelfType = TypeVar("SelfType", bound="GUIField[Any]")

# Callback type aliases
# Callbacks are flexible due to runtime introspection in callback_wrapper.
# They can be: def callback(self), def callback(self, event), def callback(self, **kwargs), etc.
CallbackFunction = Callable[..., Any]
TriggerName = str


class UnboundField(Generic[FieldType]):
    creation_counter = 0
    _GUI_FIELD = True

    def __init__(self, field: Type[FieldType], *args: Any, **kwargs: Any) -> None:
        self.field = field
        self.args = args
        self.kwargs = kwargs
        self.extra_callbacks = []
        UnboundField.creation_counter += 1
        self.creation_counter = UnboundField.creation_counter

    @overload
    def __get__(
        self: "UnboundField[FieldType]", obj: None, owner: Type[FormInstanceType]
    ) -> "UnboundField[FieldType]": ...

    @overload
    def __get__(
        self: "UnboundField[FieldType]",
        obj: FormInstanceType,
        owner: Type[FormInstanceType],
    ) -> FieldType: ...

    def __get__(self, obj: Optional[Any], owner: Any) -> Any:
        if obj is None:
            return self  # Class access returns UnboundField
        # Instance access - get bound field from form's _fields dict
        # We need to find the field name by searching the owner class
        for name, attr in owner.__dict__.items():
            if attr is self:
                return obj._fields[name]
        raise AttributeError(f"Field not found in {owner}")

    def bind(
        self, parent: Any = None, name: Optional[str] = None, **kwargs: Any
    ) -> FieldType:
        kwargs.update(self.kwargs)
        return self.field(
            bound_name=name,
            parent=parent,
            extra_callbacks=self.extra_callbacks,
            *self.args,
            **kwargs,
        )

    def add_callback(
        self, trigger: Union[TriggerName, CallbackFunction, None] = None
    ) -> Union[CallbackFunction, Callable[[CallbackFunction], CallbackFunction]]:
        """Add a callback to this field.

        Can be used as a decorator in two ways:
            @field.add_callback              # Sets default callback
            @field.add_callback("event")     # Adds event-specific callback

        Args:
            trigger: Either a trigger name (str) for event-specific callbacks,
                    or a callback function for direct assignment.

        Returns:
            Either the callback function itself (if used without trigger),
            or a decorator function (if used with trigger name).
        """
        if not isinstance(trigger, str):
            # Direct callback assignment: @field.add_callback
            self.kwargs["callback"] = trigger
            return trigger

        def add_callback_decorator(function: CallbackFunction) -> CallbackFunction:
            # Event-specific callback: @field.add_callback("event")
            self.extra_callbacks.append((trigger, function))
            return function

        return add_callback_decorator

    def __call__(self, func: CallbackFunction) -> CallbackFunction:
        """Support for using fields as decorators.

        Usage:
            @field
            def on_click(self):
                ...
        """
        self.kwargs["callback"] = func
        return func


# Helper function for clean type inference in field declarations
def Field(field_cls: Type[FieldType], **kwargs: Any) -> UnboundField[FieldType]:
    """Factory that returns the descriptor with the right generic parameter.

    Usage:
        class MyForm(forms.Frame):
            text = Field(fields.Text, label="Name")  # -> UnboundField[Text]
    """
    return UnboundField(field_cls, **kwargs)


WidgetType = TypeVar("WidgetType", bound=widgets.WXWidget)

# Type annotations for static analysis only - prevents runtime class attributes


class GUIField(Generic[WidgetType]):
    __autolabel__ = False
    widget_args = ()
    widget_kwargs = {}
    callback = None
    extra_callbacks = None
    default_value = None
    if TYPE_CHECKING:
        # These would create problematic class attributes if defined at class level
        widget_type: Type[WidgetType]
        widget: WidgetType

    @overload
    def __new__(cls: Type[SelfType]) -> "UnboundField[SelfType]": ...

    @overload
    def __new__(cls: Type[SelfType], **kwargs: Any) -> SelfType: ...

    def __new__(cls, *args, **kwargs):  # type: ignore
        if "parent" in kwargs or kwargs.get("top_level_window"):
            return super(GUIField, cls).__new__(cls)
        else:
            return UnboundField(cls, *args, **kwargs)

    def __init__(
        self,
        widget_type: Optional[Type[WidgetType]] = None,
        label: Union[str, SupportsStr, None] = None,
        parent: Optional[Any] = None,
        bound_name: Optional[str] = None,
        callback: Optional[CallbackFunction] = None,
        default_value: Any = None,
        default_focus: bool = False,
        extra_callbacks: Optional[list[tuple[TriggerName, CallbackFunction]]] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        if widget_type is None:
            widget_type = self.widget_type
        widget_kwargs = {}
        widget_args = []
        widget_kwargs.update(self.widget_kwargs)
        self.widget_kwargs = widget_kwargs
        widget_args.extend(self.widget_args)
        self.widget_args = widget_args
        logger.debug(
            "Field: %r. widget_args: %r. widget_kwargs: %r."
            % (self, self.widget_args, self.widget_kwargs)
        )
        if callback is None:
            callback = self.callback
        if default_value is None:
            default_value = self.default_value
        self.widget_type = widget_type
        super(GUIField, self).__init__()
        self.control_label = label
        self.widget_args.extend(args)
        self.parent = None
        if parent is not None:
            self.bind(parent, bound_name)
        self.widget_kwargs.update(kwargs)
        self.callback = callback
        self.default_value = default_value
        self.default_focus = default_focus
        self._last_enabled_descendant: Optional["GUIField[Any]"] = None
        if extra_callbacks is not None:
            if self.extra_callbacks is None:
                self.extra_callbacks = []
            self.extra_callbacks = list(self.extra_callbacks)
            self.extra_callbacks.extend(extra_callbacks)

    def bind(self, parent: Any, name: Optional[str] = None) -> "GUIField[WidgetType]":
        """Bind this field to a parent with an optional name.

        Args:
            parent: The parent object (typically a form) to bind to
            name: Optional name for this field binding

        Returns:
            Self for method chaining
        """
        logger.debug(
            "Binding field %r to parent %r with name %r" % (self, parent, name)
        )
        self.parent = parent
        self.bound_name = name
        return self

    @property
    def label(self) -> Optional[str]:
        """Get the label for this field."""
        if self.control_label is not None:
            return self.control_label
        if self.__autolabel__ and self.bound_name:
            return self.bound_name.replace("_", " ").title()
        return None

    def render(self, **runtime_kwargs: Any) -> None:
        """Creates this field's widget."""
        if self.widget_type is None:
            raise RuntimeError("Must set a widget_type for %r" % self)
        widget_kwargs = self.widget_kwargs
        if self.label is not None:
            widget_kwargs["label"] = self.label
        if not hasattr(self.parent, "widget"):
            widget_kwargs["parent"] = self.parent
        else:
            if self.parent is not None:
                logger.debug(
                    "The parent of this field is %r and parent of this widget is %r"
                    % (self.parent, self.parent.widget)
                )
                if self.parent.widget is None:
                    logger.warning(
                        "Parent provided without a rendered widget. Traceback follows:\n%s"
                        % traceback.format_stack()
                    )
                widget_kwargs["parent"] = self.parent.widget
        if self.callback is not None:
            widget_kwargs["callback"] = self.callback
        logger.debug("Passed in runtime kwargs: %r" % runtime_kwargs)
        widget_kwargs.update(runtime_kwargs)
        logger.debug(
            "Rendering field %r with widget type %r, and widget_kwargs:\n%r"
            % (self, self.widget_type, widget_kwargs)
        )
        try:
            self.widget = self.widget_type(
                field=self, *self.widget_args, **widget_kwargs
            )
        except Exception as e:
            logger.exception("Error creating widget.")
            raise RuntimeError(
                "Unable to create widget with type %r: %s" % (self.widget_type, str(e))
            ) from e
        self.widget.render()
        self.register_extra_callbacks()

    def register_extra_callbacks(self) -> None:
        """Pick up extra callbacks defined on the field's class and register them at render time."""
        if self.extra_callbacks is None:
            return
        for callback_set in self.extra_callbacks:
            if len(callback_set) == 1:
                callback_set = [None] + list(callback_set)
            self.register_callback(*callback_set)

    def register_callback(
        self, trigger: Optional[TriggerName] = None, callback: Optional[CallbackFunction] = None
    ) -> None:
        """Register a callback (event handler) to a trigger (event).

        Args:
            trigger: Event trigger name. If None, uses widget's default event type.
            callback: Callback function. If None, uses this field's default callback.
        """
        logger.debug(
            "Registering callback %r with trigger %r to field %r"
            % (callback, trigger, self)
        )
        self.widget.register_callback(trigger, callback)

    def unregister_callback(self, trigger: TriggerName, callback: CallbackFunction) -> None:
        """Unregister a callback from a trigger.

        Args:
            trigger: Event trigger name
            callback: Callback function to unregister
        """
        logger.debug(
            "Unregistering callback %r with trigger %r from field %r"
            % (callback, trigger, self)
        )
        self.widget.unregister_callback(trigger, callback)

    def bind_event(self, event: Any, callback: CallbackFunction) -> Any:
        """Bind an event directly to a callback.

        Args:
            event: wxPython event type
            callback: Callback function to bind

        Returns:
            Result from widget's bind_event
        """
        return self.widget.bind_event(event, callback)

    def unbind_event(self, event: Any, callback: Optional[CallbackFunction] = None) -> Any:
        """Unbind an event from a callback.

        Args:
            event: wxPython event type
            callback: Optional callback function to unbind. If None, unbinds all.

        Returns:
            Result from widget's unbind_event
        """
        return self.widget.unbind_event(event, callback)

    def is_focused(self) -> bool:
        """Return whether this field is currently focused."""
        return self.widget.is_focused()

    def set_focus(self) -> None:
        """Set focus to this field."""
        self.widget.set_focus()

    def scroll_lines(self, lines: int) -> None:
        """Scroll the contents of this field by the number of lines specified.

        Args:
            lines: Number of lines to scroll (positive = down, negative = up)
        """
        self.widget.scroll_lines(lines)

    def scroll_pages(self, pages: int) -> None:
        """Scroll the contents of this field by the number of pages specified.

        Args:
            pages: Number of pages to scroll (positive = down, negative = up)
        """
        self.widget.scroll_pages(pages)

    def center(self) -> None:
        """Center this field's widget on the screen."""
        self.widget.center()

    def center_on_parent(self) -> None:
        """Center this field's widget on its parent."""
        self.widget.center_on_parent()

    def get_foreground_color(self) -> Any:
        """Get the foreground color of this field."""
        return self.widget.get_foreground_color()

    def set_foreground_color(self, color: Any) -> None:
        """Set the foreground color of this field.

        Args:
            color: Color value (typically wx.Colour)
        """
        self.widget.set_foreground_color(color)

    foreground_color = property(get_foreground_color, set_foreground_color)

    def get_background_color(self) -> Any:
        """Get the background color of this field."""
        return self.widget.get_background_color()

    def set_background_color(self, color: Any) -> None:
        """Set the background color of this field.

        Args:
            color: Color value (typically wx.Colour)
        """
        self.widget.set_background_color(color)

    background_color = property(get_background_color, set_background_color)

    def populate(self, value: Any) -> None:
        """Provide a common abstraction for getting data into controls.

        Takes the most common form that data holds in an application and
        turns it into something this widget can deal with.

        Args:
            value: Value to populate the field with
        """
        self.set_value(value)

    def set_default_value(self) -> None:
        if self.default_value is None:
            return
        default = self.default_value
        if hasattr(default, "__unicode__"):
            self.populate(default)
            return
        while callable(default):
            default = default(self)
        logger.debug("Setting default value of field %r to %r" % (self, default))
        self.populate(default)

    def can_be_focused(self) -> bool:
        """Return whether this field type can be focused."""
        return self.widget_type.can_be_focused()

    def disable(self) -> None:
        """Disable this field, making it unusable."""
        self._reset_last_enabled_descendant()
        if "widget" in self.__dict__:
            return self.widget.disable()

    def enable(self) -> None:
        """Enable this field, making it usable."""
        self._reset_last_enabled_descendant()
        if "widget" in self.__dict__:
            return self.widget.enable()

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable this field based on the truthiness of the passed in value.

        Args:
            enabled: True to enable, False to disable
        """
        if enabled:
            self.enable()
        else:
            self.disable()

    def _reset_last_enabled_descendant(self) -> None:
        next_field = self
        while next_field is not None:
            if (
                "_last_enabled_descendant" in next_field.__dict__
                and next_field._last_enabled_descendant is not None
            ):
                next_field._last_enabled_descendant = None
            if (
                next_field
                and next_field.parent
                and "widget" in next_field.parent.__dict__
            ):
                next_field = next_field.parent
            else:
                break

    def is_enabled(self) -> bool:
        """Return whether this field is enabled."""
        return self.widget.enabled

    def freeze(self) -> None:
        """Freeze this field to prevent visual updates."""
        self.widget.freeze()

    def thaw(self) -> None:
        """Thaw this field to allow visual updates."""
        self.widget.thaw()

    def hide(self) -> None:
        """Hide this field."""
        return self.widget.hide()

    def show(self) -> None:
        """Show this field after it has been hidden."""
        return self.widget.show()

    def get_first_ancestor(self) -> Optional["GUIField[Any]"]:
        """Get the first ancestor (topmost parent) of this field.

        Returns:
            The topmost ancestor field, or None if no parent
        """
        parent = self
        current = None
        while parent is not None:
            current = parent
            parent = parent.parent
        return current

    def is_shown(self) -> bool:
        """Return whether this control is visible.

        Returns:
            True if shown, False if hidden
        """
        return self.widget.is_shown()

    def destroy(self) -> None:
        """Destroy the visual counterpart of this field."""
        self.widget.destroy()
        logger.debug("Destroyed widget for field %r" % self)

    def display(self) -> None:
        """Display this field's widget on the screen."""
        self.widget.display()

    def raise_widget(self) -> None:
        """Raise the window to the top of the window hierarchy (Z-order)."""
        return self.widget.raise_widget()

    def display_modal(self) -> Any:
        """Display this field's widget modally (for dialogs).

        Returns:
            Modal result value
        """
        return self.widget.display_modal()

    def get_label(self) -> str:
        """Return this field's current label."""
        return self.widget.get_label()

    def set_label(self, label: Union[str, SupportsStr]) -> None:
        """Set this field's label.

        Args:
            label: Label text to set (string or string-like object)
        """
        return self.widget.set_label(label)

    def set_accessible_label(self, label: Union[str, SupportsStr]) -> None:
        """Set this field's accessible label for screen readers.

        Args:
            label: Accessible label text (string or string-like object)
        """
        self.widget.set_accessible_label(label)

    def get_value(self) -> Any:
        """Return the contents of this field."""
        return self.widget.get_value()

    def set_value(self, value: Any) -> None:
        """Set the contents of this field.

        Args:
            value: Value to set
        """
        return self.widget.set_value(value)

    def get_default_value(self) -> Any:
        """Return the default value for this field."""
        return self.default_value

    def __call__(self, func: CallbackFunction) -> CallbackFunction:
        """Support for using bound fields as decorators.

        Usage:
            @field
            def on_click(self):
                ...
        """
        self.callback = func
        return func

    def add_callback(
        self, trigger: Union[TriggerName, CallbackFunction, None] = None
    ) -> Union[CallbackFunction, Callable[[CallbackFunction], CallbackFunction]]:
        """Add a callback to this bound field instance.

        Can be used as a decorator in two ways:
            @field.add_callback              # Sets default callback
            @field.add_callback("event")     # Adds event-specific callback

        Args:
            trigger: Either a trigger name (str) for event-specific callbacks,
                    or a callback function for direct assignment.

        Returns:
            Either the callback function itself (if used without trigger),
            or a decorator function (if used with trigger name).
        """
        if not isinstance(trigger, str):
            # Direct callback assignment: @field.add_callback
            self.callback = trigger
            return trigger

        def add_callback_decorator(function: CallbackFunction) -> CallbackFunction:
            # Event-specific callback: @field.add_callback("event")
            if self.extra_callbacks is None:
                self.extra_callbacks = []
            self.extra_callbacks.append((trigger, function))
            # If we're already rendered, register immediately
            if hasattr(self, "widget") and self.widget is not None:
                self.register_callback(trigger, function)
            return function

        return add_callback_decorator


class Text(GUIField[widgets.Text]):
    """A text field"""

    widget_type = widgets.Text
    widget: widgets.Text

    def set_default_value(self) -> None:
        """Set the default value and select all text."""
        super(Text, self).set_default_value()
        self.select_all()

    def append(self, text: str) -> None:
        """Append text to this text field.

        Args:
            text: Text to append
        """
        self.widget.append(text)

    def write(self, text: str) -> None:
        """Write the provided text to this text field at its current position.

        Args:
            text: Text to write
        """
        self.widget.write(text)

    def select_range(self, start: int, end: int) -> None:
        """Select the text in this control from start to end position.

        Args:
            start: Starting position (0-based index)
            end: Ending position (0-based index)
        """
        self.widget.select_range(start, end)

    def get_insertion_point(self) -> int:
        """Return the current insertion point.

        Returns:
            Zero-based index representing the user's position in the text
        """
        return self.widget.get_insertion_point()

    def set_insertion_point(self, insertion_point: int) -> None:
        """Set the insertion point.

        Args:
            insertion_point: The 0-based index representing the user's position
        """
        self.widget.set_insertion_point(insertion_point)

    def get_length(self) -> int:
        """Return the length of text contained within this control."""
        return self.widget.get_length()

    def get_line(self, line_number: int) -> str:
        """Return the text of the specified line.

        Args:
            line_number: Line number (0-based)

        Returns:
            Text of the line
        """
        return self.widget.get_line(line_number)

    def get_number_of_lines(self) -> int:
        """Return the total number of lines of text contained in this field."""
        return self.widget.get_number_of_lines()

    def get_insertion_point_from_x_y(self, x: int, y: int) -> int:
        """Return the insertion point from line and column numbers.

        Args:
            x: Column number
            y: Line number

        Returns:
            0-based index into the text
        """
        return self.widget.get_insertion_point_from_x_y(x, y)

    def get_x_y_from_insertion_point(self, insertion_point: int) -> tuple[int, int]:
        """Return line and column numbers from an insertion point.

        Args:
            insertion_point: 0-based index into the text

        Returns:
            Tuple of (column, line)
        """
        return self.widget.get_x_y_from_insertion_point(insertion_point)

    def select_all(self) -> None:
        """Select all text in this text field."""
        self.select_range(0, self.get_length())

    def clear(self) -> None:
        """Remove all text from this text field."""
        return self.widget.clear()

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
        text_color: Optional[Union[Any, str, tuple[int, int, int]]] = None,
        background_color: Optional[Union[Any, str, tuple[int, int, int]]] = None,
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
        return self.widget.set_style(
            start=start,
            end=end,
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

    def set_default_style(
        self,
        *,
        font_family: Optional[int] = None,
        font_size: Optional[int] = None,
        font_face: Optional[str] = None,
        bold: Optional[bool] = None,
        italic: Optional[bool] = None,
        underline: Optional[bool] = None,
        text_color: Optional[Union[Any, str, tuple[int, int, int]]] = None,
        background_color: Optional[Union[Any, str, tuple[int, int, int]]] = None,
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
        return self.widget.set_default_style(
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

    def get_default_style(self) -> dict[str, Any]:
        """Get the current default style.

        Returns:
            Dict containing style parameters (font_family, font_size, font_face,
            bold, italic, underline, text_color, background_color, alignment)
        """
        return self.widget.get_default_style()

    def reset_default_style(self) -> bool:
        """Reset the default style to no styling.

        This explicitly resets all style attributes so subsequently inserted text
        will have no special formatting.

        Returns:
            True on success, False on failure
        """
        return self.widget.reset_default_style()


class IntText(Text):
    """This text field will only allow the input of numbers."""

    widget_type = widgets.IntText


class Button(GUIField[widgets.Button]):
    """A standard button"""

    widget_type = widgets.Button

    def make_default(self) -> None:
        """Set this to be the default button in a dialog (called before rendering)."""
        return self.widget.make_default()

    def get_auth_needed(self) -> bool:
        """Return whether this button requires elevated privileges.

        Returns:
            True if authentication is needed
        """
        return self.widget.get_auth_needed()

    def set_auth_needed(self, auth_needed: bool) -> None:
        """Set whether this button requires elevated privileges.

        Args:
            auth_needed: True if authentication should be required
        """
        self.widget.set_auth_needed(auth_needed)

    auth_needed = property(get_auth_needed, set_auth_needed)


class CheckBox(GUIField[widgets.CheckBox]):
    """A standard Check Box"""

    widget_type = widgets.CheckBox


class ButtonSizer(GUIField[widgets.ButtonSizer]):
    widget_type = widgets.ButtonSizer

    def add_button(self, button: Button) -> None:
        """Add a button to this sizer.

        Args:
            button: Button field to add
        """
        self.widget.add_button(button.widget)

    def realize(self) -> None:
        """Realize the button sizer (finalize layout)."""
        self.widget.realize()


ChoiceWidgetType = TypeVar("ChoiceWidgetType", bound=widgets.ChoiceWidget)


class ChoiceField(GUIField[ChoiceWidgetType]):
    """A base class defining the methods available on choice fields."""

    def __init__(
        self,
        default_index: int = 0,
        choices: Optional[list[Any]] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super(ChoiceField, self).__init__(*args, **kwargs)
        self.default_index = default_index
        if choices is None:
            choices = []
        self.choices = [str(i) for i in choices]

    def render(self, **runtime_kwargs: Any) -> None:
        """Render the choice field with the specified choices."""
        runtime_kwargs.setdefault("choices", self.choices)
        super().render(**runtime_kwargs)

    def populate(self, value: Any) -> None:
        """Populate the choice field with items."""
        self.set_items(value)

    def set_default_value(self) -> None:
        """Set the default value and index."""
        super(ChoiceField, self).set_default_value()
        self.set_default_index()

    def get_default_choice(self) -> Optional[str]:
        """Return the default choice based on default_index.

        Returns:
            The default choice string, or None if no choices
        """
        if self.choices:
            return self.choices[self.default_index]
        return None

    def get_choice(self) -> Optional[str]:
        """Return the currently selected choice."""
        return self.widget.get_choice()

    def get_items(self) -> list[str]:
        """Return all items in this choice field."""
        return self.widget.get_items()

    def set_items(self, items: list[Any]) -> None:
        """Set all items in this choice field.

        Args:
            items: List of items to set
        """
        return self.widget.set_items(items)

    def delete_item(self, item: int) -> None:
        """Delete an item by index.

        Args:
            item: Index of item to delete
        """
        return self.widget.delete_item(item)

    def clear(self) -> None:
        """Clear all items from this choice field."""
        return self.widget.clear()

    def get_index(self) -> Optional[int]:
        """Return the currently selected index, or None if no selection."""
        return self.widget.get_index()

    def set_index(self, index: int) -> None:
        """Set the selected index.

        Args:
            index: Index to select
        """
        self.default_index = index
        return self.widget.set_index(index)

    def set_default_index(self) -> None:
        """Set the selection to the default index."""
        if self.get_count():
            self.set_index(self.default_index)

    def find_index(self, item: str) -> int:
        """Find the index of an item.

        Args:
            item: Item to find

        Returns:
            Index of the item

        Raises:
            ValueError: If item not found
        """
        for num, current_item in enumerate(self.get_items()):
            if item == current_item:
                return num
        raise ValueError("%r not in %r" % (item, self))

    def set_index_to_item(self, item: str) -> None:
        """Set the selection to the specified item.

        Args:
            item: Item to select
        """
        index = self.find_index(item)
        self.set_index(index)

    def insert_item(self, index: int, item: Any) -> Any:
        """Insert an item at the specified index.

        Args:
            index: Index to insert at
            item: Item to insert

        Returns:
            The inserted item
        """
        return self.widget.insert_item(index, item)

    def update_item(self, index: int, new_item: Any) -> None:
        """Update an item at the specified index.

        Args:
            index: Index of item to update
            new_item: New item value
        """
        return self.widget.update_item(index, new_item)

    def get_count(self) -> int:
        """Return the number of items in this choice field."""
        return self.widget.get_count()

    def get_item(self, index: int) -> str:
        """Get an item by index.

        Args:
            index: Index of item to get

        Returns:
            Item at the specified index
        """
        return self.widget.get_item(index)

    def set_item(self, index: int, item: Any) -> None:
        """Set an item at the specified index.

        Args:
            index: Index to set
            item: Item value
        """
        return self.widget.update_item(index, item)

    def set_value(self, value: Any) -> None:
        """Set the value by setting all items."""
        self.set_items(value)


class ComboBox(ChoiceField[widgets.ComboBox]):
    """An Edit Combo Box. Pass read_only=True to the constructor for a combo box."""

    widget_type = widgets.ComboBox

    def select_all(self) -> None:
        """Select all text in the combo box."""
        return self.widget.select_all()


class ListBox(ChoiceField[widgets.ListBox]):
    """A standard list box."""

    widget_type = widgets.ListBox


class RadioButtonGroup(ChoiceField[widgets.RadioBox]):
    """A group of choices, expressed as radio buttons."""

    widget_type = widgets.RadioBox


class ListViewColumn(GUIField):
    widget_type = widgets.ListViewColumn


class Slider(GUIField[widgets.Slider]):
    """A moveable slider."""

    widget_type = widgets.Slider

    def get_min_value(self) -> int:
        """Returns the minimum value of this slider."""
        return self.widget.get_min_value()

    def set_min_value(self, value: int):
        """Sets the minimum value of this slider."""
        self.widget.set_min_value(value)

    min_value = property(get_min_value, set_min_value)

    def get_max_value(self) -> int:
        """Returns the maximum value of this slider."""
        return self.widget.get_max_value()

    def set_max_value(self, value: int):
        """Sets the maximum value of this slider."""
        self.widget.set_max_value(value)

    max_value = property(get_max_value, set_max_value)

    def get_page_size(self) -> int:
        """Returns the number representing how many units this control will skip when the user presses page up/down."""
        return self.widget.get_page_size()

    def set_page_size(self, page_size: int):
        """Sets the number representing how many units this control will skip when the user presses page up/down."""
        return self.widget.set_page_size(page_size)

    page_size = property(get_page_size, set_page_size)

    def set_line_size(self, value: int) -> None:
        """Set the line size (arrow key increment).

        Args:
            value: Line size value
        """
        self.widget.set_line_size(value)

    def get_line_size(self) -> int:
        """Return the line size (arrow key increment)."""
        return self.widget.get_line_size()

    line_size = property(get_line_size, set_line_size)


class FilePicker(GUIField):
    widget_type = widgets.FilePicker


class MenuItem(GUIField[widgets.MenuItem]):
    """An item in a menu which is not a submenu."""

    widget_type = widgets.MenuItem

    def check(self) -> None:
        """Check this menu item."""
        self.widget.check()

    def uncheck(self) -> None:
        """Uncheck this menu item."""
        self.widget.uncheck()

    def set_checked(self, checked: bool) -> None:
        """Set whether this menu item should be checked.

        Args:
            checked: True to check, False to uncheck
        """
        if checked:
            self.check()
        else:
            self.uncheck()

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable this menu item.

        Args:
            enabled: True to enable, False to disable
        """
        if enabled:
            self.enable()
        else:
            self.disable()

    def set_as_mac_about_menu_item(self) -> None:
        """Indicate to macOS that this is the About... item in the help menu."""
        self.widget.set_as_mac_about_menu_item()

    def set_as_mac_exit_menu_item(self) -> None:
        """Indicate to macOS that clicking this menu item will exit the application."""
        self.widget.set_as_mac_exit_menu_item()

    def set_as_mac_preferences_menu_item(self) -> None:
        """Indicate to macOS that clicking this menu item will invoke the application's preferences."""
        self.widget.set_as_mac_preferences_menu_item()


class StatusBar(GUIField):
    """A status bar."""

    widget_type = widgets.StatusBar

    def set_status_text(self, text, field=0):
        """Sets the status text displayed in the status bar.

        Args:
            text (str): The text to be set in the status bar field. Use an empty string to clear the field.
            field (int, optional): The field number to set, starting from zero. Defaults to 0.
        """
        self.widget.set_status_text(text, field)


class Link(GUIField):
    """A hyperlink"""

    widget_type = widgets.Link


class StaticText(GUIField):
    """Static text"""

    widget_type = widgets.StaticText

    def wrap(self, width: int) -> None:
        """Wraps the text in this control to the specified width."""
        self.widget.wrap(width)

    def is_ellipsized(self) -> bool:
        """Returns a boolean indicating whether or not the text in this control is currently ellipsized."""
        return self.widget.is_ellipsized()


class DatePicker(GUIField[widgets.DatePicker]):
    widget_type = widgets.DatePicker

    def set_range(self, start: Any, end: Any) -> None:
        """Set the minimum and maximum dates that can be picked in this control.

        Args:
            start: Minimum date (datetime.date or wx.DateTime)
            end: Maximum date (datetime.date or wx.DateTime)
        """
        self.widget.set_range(start, end)


class TreeView(GUIField[widgets.TreeView]):
    """A treeview"""

    widget_type = widgets.TreeView

    def add_root(
        self,
        text: Optional[str] = None,
        image: Any = None,
        selected_image: Any = None,
        data: Any = None,
    ) -> Any:
        """Add a root item to the tree.

        Args:
            text: Text for the root item
            image: Image for the item
            selected_image: Image when selected
            data: Associated data

        Returns:
            TreeItemId for the root item
        """
        return self.widget.add_root(
            text, image=image, selected_image=selected_image, data=data
        )

    def get_root_item(self) -> Any:
        """Return the root item of the tree.

        Returns:
            TreeItemId for the root
        """
        return self.widget.get_root_item()

    def append_item(
        self,
        parent: Optional[Any] = None,
        text: Optional[str] = None,
        image: Any = None,
        selected_image: Any = None,
        data: Any = None,
    ) -> Any:
        """Append an item to the tree.

        Args:
            parent: Parent TreeItemId (None for root)
            text: Text for the item
            image: Image for the item
            selected_image: Image when selected
            data: Associated data

        Returns:
            TreeItemId for the new item
        """
        if parent is None:
            return self.add_root(
                text=text, image=image, selected_image=selected_image, data=data
            )
        return self.widget.append_item(
            parent=parent,
            text=text,
            image=image,
            selected_image=selected_image,
            data=data,
        )

    def clear(self) -> None:
        """Delete all items from this tree view."""
        self.widget.clear()

    def collapse_all(self) -> None:
        """Collapse all tree nodes."""
        self.widget.collapse_all()

    def delete(self, item: Any) -> None:
        """Delete a tree item.

        Args:
            item: TreeItemId to delete
        """
        self.widget.delete(item)

    def get_selection(self) -> Any:
        """Return the currently selected tree item.

        Returns:
            TreeItemId of selected item
        """
        return self.widget.get_selection()

    def select_item(self, item: Any) -> None:
        """Select a tree item.

        Args:
            item: TreeItemId to select
        """
        self.widget.select_item(item)

    def get_data(self, item: Any) -> Any:
        """Get the data associated with a tree item.

        Args:
            item: TreeItemId

        Returns:
            Associated data
        """
        return self.widget.get_data(item)

    def set_item_has_children(self, item: Any, val: bool) -> None:
        """Set whether a tree item has children.

        Args:
            item: TreeItemId
            val: True if item has children
        """
        self.widget.set_item_has_children(item, val)


class ProgressBar(GUIField[widgets.ProgressBar]):
    widget_type = widgets.ProgressBar

    def set_range(self, range: int) -> None:
        """Set the maximum value of the progress bar.

        Args:
            range: Maximum value
        """
        self.widget.set_range(range)

    def get_range(self) -> int:
        """Return the maximum value of the progress bar."""
        return self.widget.get_range()

    range = property(get_range, set_range)


class ToolBarItem(GUIField[widgets.ToolBarItem]):
    widget_type = widgets.ToolBarItem


class Image(GUIField[widgets.StaticBitmap]):
    widget_type = widgets.StaticBitmap

    def load_image(self, image: Any) -> Any:
        """Load an image into this image field.

        Args:
            image: Image to load (wx.Image or compatible)

        Returns:
            Result from widget's load_image
        """
        return self.widget.load_image(image)


class SpinBox(GUIField[widgets.SpinBox]):
    widget_type = widgets.SpinBox

    def set_min(self, min: int) -> None:
        """Set the minimum value of the spin box.

        Args:
            min: Minimum value
        """
        self.widget.set_min(min)

    def set_max(self, max: int) -> None:
        """Set the maximum value of the spin box.

        Args:
            max: Maximum value
        """
        self.widget.set_max(max)
