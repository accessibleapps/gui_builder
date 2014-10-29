from logging import getLogger
logger = getLogger('gui_builder.fields')

import traceback

from .widgets import wx_widgets as widgets

class UnboundField(object):
 creation_counter = 0
 _GUI_FIELD = True

 def __init__(self, field, *args, **kwargs):
  self.field = field
  self.args = args
  self.kwargs = kwargs
  self.extra_callbacks = []
  UnboundField.creation_counter += 1
  self.creation_counter = UnboundField.creation_counter

 def bind(self, parent=None, name=None, **kwargs):
  kwargs.update(self.kwargs)
  return self.field(bound_name=name, parent=parent, extra_callbacks=self.extra_callbacks, *self.args, **kwargs)

 def add_callback(self, trigger=None):
  if not isinstance(trigger, basestring):
   self.kwargs['callback'] = trigger
   return trigger
  def add_callback_decorator(function):
   self.extra_callbacks.append((trigger, function))
   return function
  return add_callback_decorator

class GUIField(object):
 widget_type = None
 __autolabel__ = False
 widget_args = ()
 widget_kwargs = {}
 callback = None
 extra_callbacks = None
 default_value = None

 def __new__(cls, *args, **kwargs):
  if 'parent' in kwargs or kwargs.get('top_level_window'):
   return super(GUIField, cls).__new__(cls)
  else:
   return UnboundField(cls, *args, **kwargs)

 def __init__(self, widget_type=None, label=None, parent=None, bound_name=None, callback=None, default_value=None, default_focus=False, extra_callbacks=None, *args, **kwargs):
  if widget_type is None:
   widget_type = self.widget_type
  widget_kwargs = {}
  widget_args = []
  widget_kwargs.update(self.widget_kwargs)
  self.widget_kwargs = widget_kwargs
  widget_args.extend(self.widget_args)
  self.widget_args = widget_args
  logger.debug("Field: %r. widget_args: %r. widget_kwargs: %r." % (self, self.widget_args, self.widget_kwargs))
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
  self.widget = None
  if extra_callbacks is not None:
   if self.extra_callbacks is None:
    self.extra_callbacks = []
   self.extra_callbacks = list(self.extra_callbacks)
   self.extra_callbacks.extend(extra_callbacks)

 def bind(self, parent, name=None):
  logger.debug("Binding field %r to parent %r with name %r" % (self, parent, name))
  self.parent = parent
  self.bound_name = name
  return self

 @property
 def label(self):
  if self.control_label is not None:
   return self.control_label
  if self.__autolabel__ and self.bound_name:
   return self.bound_name.replace("_", " ").title()

 def render(self, **runtime_kwargs):
  """Creates this field's widget."""
  if self.widget_type is None:
   raise RuntimeError("Must set a widget_type for %r" % self)
  widget_kwargs = self.widget_kwargs
  if self.label is not None:
   widget_kwargs['label'] = self.label
  if not hasattr(self.parent, 'widget'):
   widget_kwargs['parent'] = self.parent
  else:
   if self.parent is not None:
    logger.debug("The parent of this field is %r and parent of this widget is %r" % (self.parent, self.parent.widget))
    if self.parent.widget is None:
     logger.warning("Parent provided without a rendered widget. Traceback follows:\n%s" % traceback.format_stack())
    widget_kwargs['parent'] = self.parent.widget
  if self.callback is not None:
   widget_kwargs['callback'] = self.callback
  logger.debug("Passed in runtime kwargs: %r" % runtime_kwargs)
  widget_kwargs.update(runtime_kwargs)
  logger.debug("Rendering field %r with widget type %r, and widget_kwargs:\n%r" % (self, self.widget_type, widget_kwargs))
  try:
   self.widget = self.widget_type(field=self, *self.widget_args, **widget_kwargs)
  except Exception as e:
   logger.exception("Error creating widget.")
   raise RuntimeError("Unable to create widget with type %r" % self.widget_type, traceback.format_exc(e), e)
  self.widget.render()
  self.register_extra_callbacks()

 def register_extra_callbacks(self):
  """Picks up extra callbacks defined on the field's class and registers them at render time."""
  if self.extra_callbacks is None:
   return
  for callback_set in self.extra_callbacks:
   if len(callback_set) == 1:
    callback_set = [None].extend(callback_set)
   self.register_callback(*callback_set)

 def register_callback(self, trigger=None, callback=None):
  """Registers a callback, I.E. an event handler, to a certain trigger (event). If the callback is not provided it is assumed to be this field's default callback. If a trigger is not provided, assumes the trigger is this field's widget's default event type"""
  logger.debug("Registering callback %r with trigger %r to field %r" % (callback, trigger, self))
  self.widget.register_callback(trigger, callback)

 def unregister_callback(self, trigger, callback):
  """Unregisters a callback from a trigger"""
  self.widget.unregister_callback(trigger, callback)

 def bind_event(self, event, callback):
  return self.widget.bind_event(event, callback)

 def unbind_event(self, event, callback=None):
  return self.widget.unbind_event(event, callback)

 def is_focused(self):
  """Returns a boolean indicating if this field is currently focused."""
  return self.widget.is_focused()

 def set_focus(self):
  """Sets focus to this field."""
  self.widget.set_focus()

 def populate(self, value):
  """this is to provide a common abstraction for getting data into controls. It will take the most common form that data holds in an application and turn it into something this widget can deal with."""
  self.set_value(value)

 def set_default_value(self):
  if self.default_value is None:
   return
  default = self.default_value
  if hasattr(default, '__unicode__'):
   self.populate(default)
   return
  while callable(default):
   default = default(self)
  logger.debug("Setting default value of field %r to %r" % (self, default))
  self.populate(default)

 def can_be_focused(self):
  return self.widget_type.can_be_focused()

 def disable(self):
  """Disables this field, I.E. makes it unuseable."""
  return self.widget.disable()

 def enable(self):
  """Enables this field, making it useable."""
  return self.widget.enable()

 def set_enabled(self, enabled):
  """A method to enable/disable this field based on the truthyness of the passed in value"""
  if enabled:
   self.enable()
  else:
   self.disable()

 def freeze(self):
  self.widget.freeze()

 def thaw(self):
  self.widget.thaw()

 def hide(self):
  """Hides this field"""
  return self.widget.hide()

 def show(self):
  """Shows this field, perhaps after it has been hidden"""
  return self.widget.show()

 def is_shown(self):
  """Returns a boolean. If it is False, this control is hidden. If it is true, it is not."""
  return self.widget.is_shown()

 def destroy(self):
  """Destroys the visual counterpart of this field."""
  self.widget.destroy()

 def __del__(self):
  if self.widget is None:
   return
  self.destroy()
  self.widget = None

 def display(self):
  """Display's this field's widget on the screen."""
  self.widget.display()

 def display_modal(self):
  self.widget.display_modal()

 def get_label(self):
  """Returns this field's current label."""
  return self.widget.get_label()

 def set_label(self, label):
  """Given a string, sets this field's label to it."""
  return self.widget.set_label(label)

 def set_accessible_label(self, label):
  self.widget.set_accessible_label(label)

 def get_value(self):
  """Returns the contents of this field."""
  return self.widget.get_value()

 def set_value(self, value):
  """Sets the contents of this field."""
  return self.widget.set_value(value)

 def get_default_value(self):
  return self.default_value

class Text(GUIField):
 """A text field"""
 widget_type = widgets.Text

 def set_default_value(self):
  super(Text, self).set_default_value()
  self.select_all()

 def append(self, text):
  """Appends text to this text field."""
  self.widget.append(text)

 def write(self, text):
  """Writes the provided text to this text field at its current position"""
  self.widget.write(text)

 def select_range(self, start, end):
  """Selects the text in this control from the position specified by start to the position specified by end"""
  self.widget.select_range(start, end)

 def get_insertion_point(self):
  """Returns the current insertion point, a zero-based index representing the user's position into the text contained in this field"""
  return self.widget.get_insertion_point()

 def set_insertion_point(self, insertion_point):
  """Sets the insertion point, the 0-based index representing the user's position in this field."""
  self.widget.set_insertion_point(insertion_point)

 def get_length(self):
  """Returns the length of text contained within this control."""
  return self.widget.get_length()

 def get_line(self, line_number):
  """Returns the line number of the currently-focused line in this field."""
  return self.widget.get_line(line_number)

 def get_number_of_lines(self):
  """Returns the total number of lines of text contained in this field."""
  return self.widget.get_number_of_lines()

 def get_insertion_point_from_x_y(self, x, y):
  """Returns the line and column numbers of the given index into this contents of this text field"""
  return self.widget.get_insertion_point_from_x_y(x, y)

 def get_x_y_from_insertion_point(self, insertion_point):
  """Given a line and column number, returns the 0-based index of the specified character in the contents of this field"""
  return self.widget.get_x_y_from_insertion_point(insertion_point)

 def select_all(self):
  """Selects all text in this text field"""
  self.select_range(0, self.get_length())

 def clear(self):
  """Removes all text from this text field."""
  return self.widget.clear()

class IntText(Text):
 """This text field will only allow the input of numbers."""
 widget_type = widgets.IntText


class Button(GUIField):
 """A standard button"""
 widget_type = widgets.Button

 def make_default(self):
  """Called before rendering, sets this to be the default button in a dialog"""
  return self.widget.make_default()

class CheckBox(GUIField):
 """A standard Check Box"""
 widget_type = widgets.CheckBox

class ButtonSizer(GUIField):
 widget_type = widgets.ButtonSizer

class ChoiceField(GUIField):
 """A base class defining the methods available on choice fields."""

 def __init__(self, default_index=0, choices=None, *args, **kwargs):
  super(ChoiceField, self).__init__(*args, **kwargs)
  self.default_index = default_index
  if choices is None:
   choices = []
  self.choices = [unicode(i) for i in choices]

 def render(self, **runtime_kwargs):
  runtime_kwargs.setdefault('choices', self.choices)
  super(ChoiceField, self).render(**runtime_kwargs)

 def populate(self, value):
  self.set_items(value)

 def set_items(self, items):
  self.widget.set_items(items)

 def set_default_value(self):
  super(ChoiceField, self).set_default_value()
  self.set_default_index()

 def get_default_choice(self):
  if self.choices:
   return self.choices[self.default_index]

 def get_choice(self):
  return self.widget.get_choice()

 def get_items(self):
  return self.widget.get_items()

 def set_items(self, items):
  return self.widget.set_items(items)

 def delete_item(self, item):
  return self.widget.delete_item(item)

 def clear(self):
  return self.widget.clear()

 def get_index(self):
  return self.widget.get_index()

 def set_index(self, index):
  self.default_index = index
  return self.widget.set_index(index)

 def set_default_index(self):
  if self.get_count():
   self.set_index(self.default_index)

 def find_index(self, item):
  for num, current_item in enumerate(self.get_items()):
   if item == current_item:
    return num
  raise ValueError('%r not in %r' % (item, self))

 def set_index_to_item(self, item):
  index = self.find_index(item)
  self.set_index(index)

 def insert_item(self, index, item):
  return self.widget.insert_item(index, item)

 def update_item(self, index, new_item):
  return self.widget.update_item(index, new_item)

 def get_count(self):
  return self.widget.get_count()

 def get_item(self, index):
  return self.widget.get_item(index)

 def set_item(self, index, item):
  return self.widget.set_item(index, item)

 def set_value(self, value):
  self.set_items(value)


class ComboBox(ChoiceField):
 """An Edit Combo Box. Pass read_only=True to the constructor for a combo box."""
 widget_type = widgets.ComboBox


class ListBox(ChoiceField):
 """A standard list box."""
 widget_type = widgets.ListBox


class RadioButtonGroup(ChoiceField):
 """A group of choices, expressed as radio buttons."""
 widget_type = widgets.RadioBox


class ListViewColumn(GUIField):
 widget_type = widgets.ListViewColumn

class Slider(GUIField):
 """A moveable slider."""
 widget_type = widgets.Slider

 def get_page_size(self):
  """Returns the number representing how many units this control will skip when the user presses page up/down."""
  return self.widget.get_page_size()

 def set_page_size(self, page_size):
  """Sets the number representing how many units this control will skip when the user presses page up/down."""
  return self.widget.set_page_size(page_size)

class FilePicker(GUIField):
 widget_type = widgets.FilePicker

class MenuItem(GUIField):
 """An item in a menu which is not a submenu."""
 widget_type = widgets.MenuItem

 def check(self):
  """Check this menu item."""
  self.widget.check()

 def uncheck(self):
  """Uncheck this menu item."""
  self.widget.uncheck()

 def set_checked(self, checked):
  """Pass in a boolean representing whether or not this menu item should be checked."""
  if checked:
   self.check()
  else:
   self.uncheck()

 def set_enabled(self, enabled):
  if enabled:
   self.enable()
  else:
   self.disable()

 def set_as_mac_about_menu_item(self):
  """Indicate to OS X that this is the About... item in the help menu"""
  self.widget.set_as_mac_about_menu_item()

 def set_as_mac_exit_menu_item(self):
  """Indicate to OS X that clicking this menu item will exit the application"""
  self.widget.set_as_mac_exit_menu_item()

 def set_as_mac_preferences_menu_item(self):
  """Indicate to OS X that clicking this menu item will invoke the application's preferences"""
  self.widget.set_as_mac_preferences_menu_item()

class StatusBar(GUIField):
 """A status bar."""
 widget_type = widgets.StatusBar

class Link(GUIField):
 """A hyperlink"""
 widget_type = widgets.Link

class StaticText(GUIField):
 """Static text"""
 widget_type = widgets.StaticText

class DatePicker(GUIField):
 widget_type = widgets.DatePicker

class TreeView(GUIField):
 """A treeview"""
 widget_type = widgets.TreeView

 def add_root(self, text=None, image=None, selected_image=None, data=None):
  return self.widget.add_root(text, image=image, selected_image=selected_image, data=data)

 def get_root_item(self):
  return self.widget.get_root_item()

 def append_item(self, parent=None, text=None, image=None, selected_image=None, data=None):
  if parent is None:
   return self.add_root(text=text, image=image, selected_image=selected_image, data=data)
  return self.widget.append_item(parent=parent, text=text, image=image, selected_image=selected_image, data=data)

 def clear(self):
  self.widget.clear()

 def delete(self, item):
  self.widget.delete(item)

 def get_selection(self):
  return self.widget.get_selection()

 def select_item(self, item):
  self.widget.select_item(item)

 def get_py_data(self, item):
  return self.widget.get_py_data(item)

 def set_item_has_children(self, item, val):
  self.widget.set_item_has_children(item, val)

class ProgressBar(GUIField):
 widget_type = widgets.ProgressBar

class ToolBarItem(GUIField):
 widget_type = widgets.ToolBarItem

