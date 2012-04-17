from widgets import wx_widgets as widgets

class GUIField(object):
 _GUI_FIELD = True
 creation_counter = 0
 widget_type = None
 __autolabel__ = True

 def __init__(self, widget_type=None, label=None, *args, **kwargs):
  if widget_type is None:
   widget_type = self.widget_type
  if widget_type is None:
   raise ValueError("Must provide a valid widget type")
  GUIField.creation_counter += 1
  self.creation_counter = GUIField.creation_counter
  super(GUIField, self).__init__()
  self.widget_type = widget_type
  self.control_label = label
  self.widget_args = args
  self.widget_kwargs = kwargs
  self.parent = None
  self.bound_name = None
  self.widget = None

 def bind(self, parent, name):
  self.parent = parent
  self.bound_name = name
  return self

 @property
 def label(self):
  if self.control_label is not None:
   return self.control_label
  if self.__autolabel__:
   return self.bound_name.replace("_", " ").title()

 
 def render(self):
  self.widget = self.widget_type(label=self.label, parent=self.parent.widget, *self.widget_args, **self.widget_kwargs)
  self.widget.create_control()

class Text(GUIField):
 widget_type = widgets.Text

class Button(GUIField):
 widget_type = widgets.Button
