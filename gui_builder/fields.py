from widgets import wx_widgets as widgets

class GUIField(object):
 _GUI_FIELD = True
 creation_counter = 0
 widget_type = None
 __autolabel__ = True
 widget_args = None
 widget_kwargs = None
 callback = None
 default_value = None

 def __init__(self, widget_type=None, label=None, parent=None, bound_name=None, callback=None, default_value=None, *args, **kwargs):
  if widget_type is None:
   widget_type = self.widget_type
  if self.widget_args is None:
   self.widget_args = []
  if self.widget_kwargs is None:
   self.widget_kwargs = {}
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
  self.bind(parent, bound_name)
  self.widget_kwargs.update(kwargs)
  self.callback = callback
  self.default_value = default_value
  self.widget = None

 def bind(self, parent, name=None):
  self.parent = parent
  self.bound_name = name
  return self

 @property
 def label(self):
  if self.control_label is not None:
   return self.control_label
  if self.__autolabel__ and self.bound_name:
   return self.bound_name.replace("_", " ").title()

 def render(self):
  if self.widget_type is None:
   raise RuntimeError("Must set a widget_type for %r" % self)
  widget_kwargs = self.widget_kwargs
  if self.label is not None:
   widget_kwargs['label'] = self.label
  if self.parent is not None:
   widget_kwargs['parent'] = self.parent.widget
  if self.callback is not None:
   widget_kwargs['callback'] = self.callback
  try:
   self.widget = self.widget_type(field=self, *self.widget_args, **widget_kwargs)
  except Exception as e:
   raise RuntimeError("Unable to create widget with type %r" % self.widget_type, e)
  self.widget.render()

 def set_focus(self):
  self.widget.set_focus()

 def populate(self, value):
  self.widget.populate(value)

 def can_be_focused(self):
  return self.widget_type.can_be_focused()

 def display(self):
  self.widget.display()

 def display_modal(self):
  self.widget.display_modal()

 def get_value(self):
  return self.widget.get_value()

 def set_value(self, value):
  return self.widget.set_value(value)

class Text(GUIField):
 widget_type = widgets.Text

class IntText(GUIField):
 widget_type = widgets.IntText

class Button(GUIField):
 widget_type = widgets.Button

class CheckBox(GUIField):
 widget_type = widgets.CheckBox

class ButtonSizer(GUIField):
 widget_type = widgets.ButtonSizer

class ChoiceField(GUIField):

 def get_choice(self):
  return self.widget.get_choice()

 def get_items(self):
  return self.widget.get_items()

 def set_items(self, items):
  return self.widget.set_items(items)

 def get_index(self):
  return self.widget.get_index()

 def set_index(self, index):
  return self.widget.set_index(index)

class ListBox(ChoiceField):
 widget_type = widgets.ListBox

class RadioButtonGroup(ChoiceField):
 widget_type = widgets.RadioBox

class ListView(ChoiceField):
 widget_type = widgets.ListView

class Slider(GUIField):
 widget_type = widgets.Slider

class FilePicker(GUIField):
 widget_type = widgets.FilePicker

class MenuItem(GUIField):
 widget_type = widgets.MenuItem

class StatusBar(GUIField):
 widget_type = widgets.StatusBar
