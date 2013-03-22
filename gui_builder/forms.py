from logging import getLogger
logger = getLogger('gui_builder.forms')
import platform

from .fields import GUIField, ChoiceField
from .widgets import wx_widgets as widgets

class BaseForm(GUIField):
 __autolabel__ = False

 def __init__(self, fields, *args, **kwargs):
  self._fields = {}
  if hasattr(fields, 'items'):
   fields = fields.items()
  for name, unbound_field in fields:
   self[name] = unbound_field
  working_kwargs = dict(kwargs)
  for key, value in working_kwargs.iteritems():
   try:
    self[key].default_value = value
    kwargs.pop(key)
   except KeyError:
    pass
  super(BaseForm, self).__init__(*args, **kwargs)  
  self.is_rendered = False

 def __iter__(self):
  return self._fields.itervalues()

 def get_children(self):
  for child in self:
   yield child

 def get_all_children(self):
  for field in self:
   yield field
   if not hasattr(field, 'get_all_children'):
    continue
   for subfield in field.get_all_children():
    yield subfield

 def get_first_child(self):
  return self.get_children().next()

 def __getitem__(self, name):
  return self._fields[name]

 def __setitem__(self, name, value):
  self.add_child(name, value)

 def add_child(self, field_name, field):
  self._fields[field_name] = field.bind(self, field_name)

 def delete_child(self, name):
  del self._fields[name]

 def get_value(self):
  res = {}
  for field in self:
   res[field.bound_name] = field.get_value()
  return res

 def render(self):
  super(BaseForm, self).render()
  logger.debug("Super has been called by the Base form. The widget for field %r is %r" % (self, self.widget))
  logger.debug("The fields inside this form are %r" % self._fields)
  for field in self:
   field.parent = self
   logger.debug("Rendering field %r" % field)
   try:
    field.render()
   except Exception as e:
    logger.exception("Failed rendering field %r" % field)
    raise RuntimeError("Failed to render field %r" % field, e)
  self.set_default_value()
  self.is_rendered = True

 def set_default_value(self):
  super(BaseForm, self).set_default_value()
  for field in self:
   field.set_default_value()

 def set_default_focus(self):
  for field in self:
   if field.default_focus and field.can_be_focused():
    field.set_focus()
  else:
   child = self.get_first_focusable_child()
   if child is not None:
    child.set_focus()
    return
   self.set_focus()


 def display(self):
  self._predisplay()
  self.widget.display()

 def display_modal(self):
  self._predisplay()
  self.widget.display_modal()

 def _predisplay(self):
  if not self.is_rendered:
   self.render()
  self.set_default_focus()

class FormMeta(type):

 def __init__(cls, name, bases, attrs):
  type.__init__(cls, name, bases, attrs)
  cls._unbound_fields = None

 def __call__(cls, *args, **kwargs):
  if cls._unbound_fields is None:
   fields = []
   for name in dir(cls):
    if name.startswith('_'):
     continue
    unbound_field = getattr(cls, name)
    if hasattr(unbound_field, '_GUI_FIELD'):
     fields.append((name, unbound_field))
   fields.sort(key=lambda x: (x[1].creation_counter, x[0]))
   cls._unbound_fields = fields
  return type.__call__(cls, *args, **kwargs)

 def __setattr__(cls, name, value):
  if not name.startswith('_'):
   cls._unbound_fields = None
  type.__setattr__(cls, name, value)

 """
 def __delattr__(cls, name):
  if not name.startswith('_'):
   cls._unbound_fields = None
  type.__delattr__(cls, name)
 """

class Form(BaseForm):
 __metaclass__ = FormMeta

 def __init__(self, *args, **kwargs):
  self._extra_unbound_fields = []
  super(Form, self).__init__(self._unbound_fields, *args, **kwargs)
  for name, field in self._fields.items():
   setattr(self, name, field)

 def add_child(self, field_name, field):
  super(Form, self).add_child(field_name, field)
  item = (field_name, field)
  setattr(self, field_name, field)
  if item not in self._unbound_fields:
   self._extra_unbound_fields.append(item)

 def delete_child(self, name):
  field = self._fields[name]
  try:
   self._unbound_fields.remove((name, field))
  except ValueError:
   self._extra_unbound_fields.remove((name, field))
  setattr(self, name, None)
  if hasattr(self.__class__, 'name'):
   delattr(self.__class__, name)
  super(Form, self).delete_child(name)

 def __delattr__(self, name):
  self.delete_child(name)

 def __iter__(self):
  """ Iterate form fields in their order of definition on the form. """
  for name, _ in self._unbound_fields + self._extra_unbound_fields:
   if name in self._fields:
    yield self._fields[name]

class UIForm(Form):

 def get_title(self):
  return self.widget.get_title()

 def set_title(self, title):
  return self.widget.set_title(title)

 def get_first_focusable_child(self):
  for child in self.get_all_children():
   if child.can_be_focused():
    return child


 def close(self):
  self.widget.close()
  self.destroy()

class Frame(UIForm):
 widget_type = widgets.Frame

class Dialog(UIForm):
 widget_type = widgets.Dialog

class Panel(UIForm):
 widget_type = widgets.Panel

class SizedDialog(UIForm):
 widget_type = widgets.SizedDialog

class SizedFrame(UIForm):
 widget_type = widgets.SizedFrame

class SizedPanel(UIForm):
 widget_type = widgets.SizedPanel

class Notebook(UIForm):
 widget_type = widgets.Notebook

 def render(self):
  super(Notebook, self).render()
  for field in self:
   self.widget.add_item(field.label, field.widget)

class MenuBar(UIForm):
 widget_type = widgets.MenuBar

class Menu(UIForm):
 widget_type = widgets.Menu

class SubMenu(UIForm):
 widget_type = widgets.SubMenu

class ListView(UIForm, ChoiceField):

 def __init__(self, virtual=False, *args, **kwargs):
  if platform.system() == 'Windows' or virtual:
   self.widget_type = widgets.ListView
  else:
   self.widget_type = widgets.DataView
  super(ListView, self).__init__(self, virtual=virtual, *args, **kwargs)

 def get_item_column(self, index, column):
  return self.widget.get_item_column(index, column)

 def set_item_column(self, index, column, data):
  return self.widget.set_item_column(index, column, data)
