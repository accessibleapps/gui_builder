from __future__ import annotations

import platform
from logging import getLogger
from typing import (
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Tuple,
    TypeVar,
    TYPE_CHECKING,
    Union,
)

from .fields import ChoiceField, GUIField, UnboundField
from .widgets import wx_widgets as widgets

logger = getLogger("gui_builder.forms")

FormWidgetType = TypeVar("FormWidgetType", bound=widgets.BaseContainer)


class BaseForm(GUIField[FormWidgetType]):
    __autolabel__ = False
    unbound = False

    # Map of field name -> bound field instance
    _fields: Dict[str, GUIField[Any]]
    _last_child: Optional[GUIField[Any]]
    _last_enabled_descendant: Optional[GUIField[Any]]
    is_rendered: bool

    def __init__(
        self,
        fields: Union[
            Mapping[str, Union[UnboundField, GUIField[Any]]],
            Iterable[Tuple[str, Union[UnboundField, GUIField[Any]]]],
        ],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self._fields = {}
        if hasattr(fields, "items"):
            fields = fields.items()  # type: ignore[assignment]
        for name, unbound_field in fields:  # type: ignore[assignment]
            self.add_child(name, unbound_field)
        working_kwargs: MutableMapping[str, Any] = dict(kwargs)
        for key, value in working_kwargs.items():  # type: ignore[attr-defined]
            try:
                self[key].default_value = value
                kwargs.pop(key)
            except KeyError:
                pass
        super().__init__(*args, **kwargs)
        self.is_rendered = False
        self._last_child = None
        self._last_enabled_descendant = None

    def set_values(self, values: Mapping[str, Any]) -> None:
        """Given a dictionary mapping field names to values, sets fields on this form to the values provided."""
        for k, v in values.items():
            self[k].default_value = v
            if self.is_rendered:
                self[k].set_value(v)

    def __iter__(self) -> Iterator[GUIField[Any]]:
        """Iterate over this form's fields."""
        return iter(self._fields.values())

    def get_children(self) -> Iterator[GUIField[Any]]:
        """Returns a generator which produces children of this form, but not their children."""
        for child in self:
            yield child

    def get_all_children(self) -> Iterator[GUIField[Any]]:
        """Produces a generator which yields all descendants of this form."""
        from typing import cast

        for field in self.get_children():
            yield field
            if not hasattr(field, "get_all_children"):
                continue
            # We know it's safe to cast after hasattr check
            for subfield in cast(UIForm, field).get_all_children():
                yield subfield

    def get_first_child(self) -> Optional[GUIField[Any]]:
        """Returns the first child field of this form."""
        try:
            return next(self.get_children())
        except StopIteration:
            return

    def get_last_child(self) -> Optional[GUIField[Any]]:
        """Returns the last child field of this form."""
        if self._last_child is None:
            try:
                self._last_child = list(self.get_all_children())[-1]
            except IndexError:
                pass
        return self._last_child

    def get_last_enabled_descendant(self) -> Optional[GUIField[Any]]:
        if self._last_enabled_descendant is not None:
            return self._last_enabled_descendant
        enabled_focusable_children = [
            child
            for child in self.get_all_children()
            if child.widget.enabled
            and child.can_be_focused()
            and child.widget.can_accept_focus()
        ]
        if not enabled_focusable_children:
            return None
        descendant = enabled_focusable_children[-1]
        self._last_enabled_descendant = descendant
        return descendant

    def get_first_enabled_descendant(self) -> Optional[GUIField[Any]]:
        """Returns the first child that is both enabled and focusable."""
        enabled_focusable_children = [
            child
            for child in self.get_all_children()
            if child.widget.enabled
            and child.can_be_focused()
            and child.widget.can_accept_focus()
        ]
        if not enabled_focusable_children:
            return None
        return enabled_focusable_children[0]

    def invalidate_descendant_cache(self) -> None:
        """Invalidates cached descendant references when children's state changes."""
        self._last_enabled_descendant = None
        self._last_child = None

    def __getitem__(self, name: str) -> GUIField[Any]:
        return self._fields[name]

    def __setitem__(
        self, name: str, value: Union[UnboundField, GUIField[Any]]
    ) -> GUIField[Any]:
        return self.add_child(name, value)

    def add_child(
        self, field_name: str, field: Union[UnboundField, GUIField[Any]]
    ) -> GUIField[Any]:
        to_call = field
        if hasattr(field, "bind"):
            to_call = field.bind
        new_field = to_call(parent=self, name=field_name)  # type: ignore[misc]
        if hasattr(new_field, "bind"):
            new_field.bind(parent=self, name=field_name)  # type: ignore[call-arg]
        self._fields[field_name] = new_field  # type: ignore[assignment]
        last_child = new_field
        if hasattr(last_child, "get_all_children"):
            children = list(last_child.get_all_children())  # type: ignore[attr-defined]
            if children:
                last_child = list(last_child.get_all_children())[-1]  # type: ignore[index]
        self._last_child = last_child
        return new_field  # type: ignore[return-value]

    def delete_child(self, name: str) -> None:
        """Removes a child from this form."""
        del self._fields[name]
        self._last_child = None
        self._last_enabled_descendant = None

    def get_value(self) -> Dict[str, Any]:
        """Returns a dictionary whose keys are fieldnames and whose values are the values of those fields."""
        res = {}
        for field in self:
            res[field.bound_name] = field.get_value()
        return res

    def render(self, **kwargs: Any) -> None:
        """Renders this form and all children."""
        super(BaseForm, self).render(**kwargs)
        logger.debug(
            "Super has been called by the Base form. The widget for field %r is %r"
            % (self, self.widget)
        )
        logger.debug("The fields inside this form are %r" % self._fields)
        for field in self:
            logger.debug("Rendering field %r" % field)
            try:
                field.render()
            except Exception:
                logger.exception("Failed rendering field %r." % field)
                raise
        self.set_default_value()
        self.is_rendered = True

    def set_default_value(self) -> None:
        super(BaseForm, self).set_default_value()
        for field in self:
            field.set_default_value()

    def set_default_focus(self) -> None:
        """Sets focus to the field on this form which was preset to be the default focused field."""
        for field in self.get_all_children():
            if field.default_focus and field.can_be_focused():
                field.set_focus()
                logger.debug("Setting default focus to %r" % field)
                return
        child = self.get_first_focusable_child()
        if child is not None:
            child.set_focus()
            logger.debug("Setting default focus to first focusable child %r" % child)
            return
        self.set_focus()

    def get_first_focusable_child(self) -> Optional[GUIField[Any]]:
        for child in self.get_all_children():
            if child.can_be_focused():
                return child
        return None

    def display(self) -> None:
        """Does the work of actually displaying this form on the screen."""
        self._predisplay()
        self.widget.display()

    def display_modal(self):
        self._predisplay()
        return self.widget.display_modal()

    def _predisplay(self) -> None:
        if not self.is_rendered:
            self.render()
        self.set_default_focus()


class FormMeta(type):
    def __init__(cls, name, bases, attrs) -> None:
        type.__init__(cls, name, bases, attrs)
        cls._unbound_fields: Optional[List[Tuple[str, UnboundField]]] = None

    def __call__(cls, *args, **kwargs):
        if cls._unbound_fields is None:
            fields: List[Tuple[str, UnboundField]] = []
            for name in dir(cls):
                if name.startswith("_"):
                    continue
                unbound_field = getattr(cls, name)
                if hasattr(unbound_field, "_GUI_FIELD"):
                    fields.append((name, unbound_field))  # type: ignore[arg-type]
            fields.sort(key=lambda x: (x[1].creation_counter, x[0]))
            cls._unbound_fields = fields
        return type.__call__(cls, *args, **kwargs)

    def __setattr__(cls, name, value) -> None:
        if not name.startswith("_"):
            cls._unbound_fields = None
        type.__setattr__(cls, name, value)

    def __delattr__(cls, name) -> None:
        if not name.startswith("_"):
            cls._unbound_fields = None
        type.__delattr__(cls, name)


class Form(BaseForm[FormWidgetType], metaclass=FormMeta):
    _unbound_fields: List[Tuple[str, UnboundField]]
    _extra_fields: List[Tuple[str, UnboundField]]

    def __init__(self, *args: Any, **kwargs: Any):
        self._extra_fields = []
        super(Form, self).__init__(self._unbound_fields or [], *args, **kwargs)
        for name, field in self._fields.items():
            setattr(self, name, field)

    def add_child(
        self, field_name: str, field: Union[UnboundField, GUIField[Any]]
    ) -> GUIField[Any]:
        new_field = super().add_child(field_name, field)
        item: Tuple[str, UnboundField] = (field_name, new_field)
        setattr(self, field_name, new_field)
        if not self._unbound_fields or not any(
            name == field_name for name, _ in self._unbound_fields
        ):
            self._extra_fields.append(item)
        return new_field

    def delete_child(self, name: str) -> None:
        field = self._fields[name]
        if self._unbound_fields is not None:
            for field_name, field in list(self._unbound_fields):
                if name == field_name:
                    self._unbound_fields.remove((field_name, field))
                    break
        for field_name, field in list(self._extra_fields):
            if field_name == name:
                self._extra_fields.remove((field_name, field))
                break
        setattr(self, name, None)
        super(Form, self).delete_child(name)

    def __delattr__(self, name: str) -> None:
        try:
            self.delete_child(name)
        except KeyError:
            super(Form, self).__delattr__(name)

    def __iter__(self) -> Iterator[GUIField[Any]]:
        """Iterates form fields in their order of definition on the form."""
        for name, _ in (self._unbound_fields or []) + self._extra_fields:
            if name in self._fields:
                yield self._fields[name]


class UIForm(Form[FormWidgetType]):
    def set_value(self, items: Mapping[str, Any]) -> None:
        """Given a mapping of field ids to values, populates each field with the corresponding value"""
        for key, value in items.items():
            self[key].populate(value)

    def get_title(self) -> str:
        """Returns the form's title"""
        return self.widget.get_title()

    def set_title(self, title: str):
        """Sets the form's title to the string provided."""
        return self.widget.set_title(title)

    def delete_child(self, name: str) -> None:
        child = self._fields[name]
        self.widget.remove_child(child.widget)
        super(UIForm, self).delete_child(name)

    def close(self) -> None:
        """Closes this form."""
        self.widget.close()
        self.destroy()


class BaseFrame(UIForm[widgets.BaseFrame]):
    def maximize(self):
        """Maximizes the frame."""
        return self.widget.maximize()

    def restore(self):
        "Restores the frame"
        return self.widget.restore()

    def minimize(self):
        """Minimizes the frame."""
        return self.widget.minimize()


class Frame(BaseFrame):
    widget_type = widgets.Frame


class MDIParentFrame(BaseFrame):
    widget_type = widgets.MDIParentFrame


class MDIChildFrame(BaseFrame):
    widget_type = widgets.MDIChildFrame


class BaseDialog(UIForm[widgets.BaseDialog]):
    def end_modal(self, modal_result):
        return self.widget.end_modal(modal_result)


class Dialog(BaseDialog):
    widget_type = widgets.Dialog


class Panel(UIForm):
    widget_type = widgets.Panel


class SizedDialog(BaseDialog):
    widget_type = widgets.SizedDialog


class SizedFrame(BaseFrame):
    widget_type = widgets.SizedFrame
    if TYPE_CHECKING:
        # These would create problematic class attributes if defined at class level
        widget: widgets.SizedFrame

    def set_content_padding(self, padding: int):
        """Set padding around the frame's content area.

        Args:
            padding (int): Padding in pixels around all content
        """
        return self.widget.set_content_padding(padding)


class SizedPanel(UIForm):
    widget_type = widgets.SizedPanel


class Notebook(UIForm[widgets.Notebook]):
    widget_type = widgets.Notebook

    def add_item(self, label: str, item: UIForm[Any]) -> None:
        """Adds a panel to the notebook. Requires a panel object and a label, which will be displayed on the tab strip."""
        self.add_child(repr(item), item)
        self.widget.add_item(label, item.widget)

    def delete_item(self, item: UIForm[Any]) -> None:
        """Removes a panel from a notebook. Required: The panel to remove."""
        self.delete_child(repr(item))
        self.widget.delete_page(item.widget)

    def render(self, **kwargs: Any) -> None:
        super(Notebook, self).render(**kwargs)
        for field in self:
            self.widget.add_item(field.label, field.widget)

    def get_selection(self) -> int:
        return self.widget.get_selection()

    def set_selection(self, selection: int):
        return self.widget.set_selection(selection)

    def get_current_page(self) -> Optional[GUIField[Any]]:
        """Returns the currently-selected page of the notebook as the original panel. If there are no panels, returns None."""
        children = list(self.get_children())
        if not children:
            return
        selection = self.get_selection()
        if selection == -1:
            return
        return children[selection]

    def set_current_page(self, page: GUIField[Any]) -> None:
        """Given a panel which is currently in the notebook, sets focus to it."""
        page_index = list(self.get_children()).index(page)
        self.set_selection(page_index)


class MenuBar(UIForm[widgets.MenuBar]):
    widget_type = widgets.MenuBar


class Menu(UIForm):
    widget_type = widgets.Menu

    def enable_menu(self) -> None:
        """Enables all menu items in this menu."""
        for menu_item in self:
            if hasattr(menu_item, "enable_menu"):
                menu_item.enable_menu()
            else:
                menu_item.enable()

    def disable_menu(self) -> None:
        """Disables all menu items in this menu"""
        for menu_item in self:
            if hasattr(menu_item, "disable_menu"):
                menu_item.disable_menu()
            else:
                menu_item.disable()

    def popup(self, position: Optional[Any] = None) -> None:
        """Pops up the menu, for use in context menu handlers."""
        self.widget.popup(position)

    def context_menu(self) -> bool:
        """Simplified context menu handler, performs the basic steps to display a context menu. return the result of this function from your event handler to avoid issues"""
        self.popup()
        self.destroy()
        return True


class SubMenu(Menu):
    widget_type = widgets.SubMenu


class ListView(ChoiceField, UIForm[widgets.ListView]):
    def __init__(self, virtual: bool = False, *args: Any, **kwargs: Any):
        if platform.system() == "Windows":
            self.widget_type = widgets.ListView
        else:
            self.widget_type = widgets.DataView
            virtual = False
        super().__init__(virtual=virtual, *args, **kwargs)

    def get_children(self) -> List[GUIField[Any]]:
        return []

    def get_item_column(self, index: int, column: int) -> Any:
        """Returns the string at the given column and index"""
        return self.widget.get_item_column(index, column)

    def set_item_column(self, index: int, column: int, data: Any):
        """Sets the string at the provided column and index to the provided value"""
        return self.widget.set_item_column(index, column, data)

class ToolBar(UIForm):
    widget_type = widgets.ToolBar

    def render(self, *args: Any, **kwargs: Any) -> None:
        super(ToolBar, self).render(*args, **kwargs)
        self.widget.realize()


class FrameToolBar(ToolBar):
    widget_type = widgets.FrameToolBar
