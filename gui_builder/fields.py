from widgets import wx_widgets as widgets

class GUIField(object):
 _GUI_FIELD = True
 creation_counter = 0
 widget_type = None
 __autolabel__ = True
 widget_args = None
 widget_kwargs = None

 def __init__(self, widget_type=None, label=None, *args, **kwargs):
  if widget_type is None:
   widget_type = self.widget_type
  if self.widget_args is None:
   self.widget_args = []
  if self.widget_kwargs is None:
   self.widget_kwargs = {}
  self.widget_type = widget_type
  GUIField.creation_counter += 1
  self.creation_counter = GUIField.creation_counter
  super(GUIField, self).__init__()
  self.control_label = label
  self.widget_args.extend(args)
  self.widget_kwargs.update(kwargs)
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
  self.widget = self.widget_type(*self.widget_args, **widget_kwargs)
  self.widget.create_control()

 def postrender(self):
  self.widget.postrender()

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

class ListBox(GUIField):
 widget_type = widgets.ListBox
