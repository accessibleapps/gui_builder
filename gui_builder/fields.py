from logging import getLogger
logger = getLogger('gui_builder.fields')
import traceback

from widgets import wx_widgets as widgets

class GUIField(object):
 _GUI_FIELD = True
 creation_counter = 0
 widget_type = None
 __autolabel__ = False
 widget_args = ()
 widget_kwargs = {}
 callback = None
 extra_callbacks = None
 default_value = None

 def __init__(self, widget_type=None, label=None, parent=None, bound_name=None, callback=None, default_value=None, default_focus=False, *args, **kwargs):
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
  GUIField.creation_counter += 1
  self.creation_counter = GUIField.creation_counter
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
  if self.widget_type is None:
   raise RuntimeError("Must set a widget_type for %r" % self)
  widget_kwargs = self.widget_kwargs
  if self.label is not None:
   widget_kwargs['label'] = self.label
  if not hasattr(self.parent, '_GUI_FIELD'):
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
   raise RuntimeError("Unable to create widget with type %r" % self.widget_type, e)
  self.widget.render()
  self.register_extra_callbacks()

 def register_extra_callbacks(self):
  if self.extra_callbacks is None:
   return
  for callback_set in self.extra_callbacks:
   self.register_callback(*callback_set)


 def register_callback(self, trigger, callback):
  logger.debug("Registering callback %r with trigger %r to field %r" % (callback, trigger, self))
  self.widget.register_callback(trigger, callback)

 def unregister_callback(self, trigger, callback):
  self.widget.unregister_callback(trigger, callback)

 def is_focused(self):
  return self.widget.is_focused()

 def set_focus(self):
  self.widget.set_focus()

 def populate(self, value):
  self.widget.populate(value)

 def set_default_value(self):
  if self.default_value is None:
   return
  default = self.default_value
  while callable(default):
   default = default(self)
  logger.debug("Setting default value of field %r to %r" % (self, default))
  self.populate(default)

 def can_be_focused(self):
  return self.widget_type.can_be_focused()

 def disable(self):
  return self.widget.disable()

 def enable(self):
  return self.widget.enable()

 def hide(self):
  return self.widget.hide()

 def destroy(self):
  self.widget.destroy()

 def __del__(self):
  self.destroy()

 def display(self):
  self.widget.display()

 def display_modal(self):
  self.widget.display_modal()

 def get_label(self):
  return self.widget.get_label()

 def set_label(self, label):
  return self.widget.set_label(label)

 def get_value(self):
  return self.widget.get_value()

 def set_value(self, value):
  return self.widget.set_value(value)

 def get_default_value(self):
  return self.default_value

class Text(GUIField):
 widget_type = widgets.Text

 def render(self):
  super(Text, self).render()
  self.select_all()

 def select_range(self, start, end):
  self.widget.select_range(start, end)

 def get_length(self):
  return self.widget.get_length()

 def select_all(self):
  self.select_range(0, self.get_length())

class IntText(Text):
 widget_type = widgets.IntText

class Button(GUIField):
 widget_type = widgets.Button

class CheckBox(GUIField):
 widget_type = widgets.CheckBox

class ButtonSizer(GUIField):
 widget_type = widgets.ButtonSizer

class ChoiceField(GUIField):

 def __init__(self, default_index=0, choices=None, *args, **kwargs):
  super(ChoiceField, self).__init__(*args, **kwargs)
  self.default_index = default_index
  if choices is None:
   choices = []
  self.choices = choices

 def render(self, **runtime_kwargs):
  runtime_kwargs.setdefault('choices', self.choices)
  super(ChoiceField, self).render(**runtime_kwargs)


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
  return self.widget.set_index(index)

 def set_default_index(self):
  if self.default_value and self.default_index is not None:
   self.set_index(self.default_index)

 def find_index(self, item):
  for num, current_item in enumerate(self.get_items()):
   if item == current_item:
    return num
  raise ValueError('%r not in %r' % (item, self))

 def insert_item(self, index, item):
  return self.widget.insert_item(index, item)

 def update_item(self, index, new_item):
  return self.widget.update_item(index, new_item)

 def get_count(self):
  return self.widget.get_count()

class ComboBox(ChoiceField):
 widget_type = widgets.ComboBox


class ListBox(ChoiceField):
 widget_type = widgets.ListBox


class RadioButtonGroup(ChoiceField):
 widget_type = widgets.RadioBox


class ListViewColumn(GUIField):
 widget_type = widgets.ListViewColumn

class Slider(GUIField):
 widget_type = widgets.Slider

class FilePicker(GUIField):
 widget_type = widgets.FilePicker

class MenuItem(GUIField):
 widget_type = widgets.MenuItem

class StatusBar(GUIField):
 widget_type = widgets.StatusBar

class Link(GUIField):
 widget_type = widgets.Link

class StaticText(GUIField):
 widget_type = widgets.StaticText
