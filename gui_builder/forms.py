from logging import getLogger
logger = getLogger('gui_builder.forms')

from .fields import GUIField, ChoiceField
from .widgets import wx_widgets as widgets

class BaseForm(GUIField):
 __autolabel__ = False
 default_focus = None #If set to a field on this form, automatically sets focus to it.
 #If set to a callable, calls it to determine its default focus

 def __init__(self, fields, default_focus=None, *args, **kwargs):
  self._fields = {}
  if hasattr(fields, 'items'):
   fields = fields.items()
  for name, unbound_field in fields:
   self[name] = unbound_field
  if default_focus is None:
   default_focus = self.default_focus
  if default_focus is None:
   for name, field in fields:
    if field.can_be_focused():
     default_focus = field
     break
  self.default_focus = default_focus
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

 get_children = __iter__

 def get_all_children(self):
  for field in self:
   if not hasattr(field, 'get_all_children'):
    yield field
   for subfield in field.get_all_children():
    yield subfield

 def __getitem__(self, name):
  return self._fields[name]

 def __setitem__(self, name, value):
  self._fields[name] = value.bind(self, name)

 def __delitem__(self, name):
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
   self[field.bound_name] = field   #this is an ugly hack, why does it work?

   logger.debug("Rendering field %r" % field)
   try:
    field.render()
   except Exception as e:
    logger.exception("Failed rendering field %r" % field)
    raise RuntimeError("Failed to render field %r" % field, e)
  self.set_default_value()
  self.set_default_focus()
  self.is_rendered = True

 def set_default_focus(self):
  focus = self.default_focus
  if callable(focus):
   focus = focus()
  if focus is None:
   return
  focus.set_focus()

 def set_default_value(self):
  super(BaseForm, self).set_default_value()
  for field in self:
   field.set_default_value()

 def display(self):
  self._predisplay()
  self.widget.display()

 def display_modal(self):
  self._predisplay()
  self.widget.display_modal()

 def _predisplay(self):
  if not self.is_rendered:
   self.render()

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

 def __delattr__(self, name):
  if not name.startswith('_'):
   cls._unbound_fields = None
  type.__delattr__(cls, name)

class Form(BaseForm):
 __metaclass__ = FormMeta

 def __init__(self, *args, **kwargs):
  super(Form, self).__init__(self._unbound_fields, *args, **kwargs)
  for name, field in self._fields.items():
   setattr(self, name, field)

 def __iter__(self):
  """ Iterate form fields in their order of definition on the form. """
  for name, _ in self._unbound_fields:
   if name in self._fields:
    yield self._fields[name]

class UIForm(Form):

 def get_title(self):
  return self.widget.get_title()

 def set_title(self, title):
  return self.widget.set_title(title)

 def display_modal(self):
  super(UIForm, self).display_modal()


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

class AutoSizedDialog(UIForm):
 widget_type = widgets.AutoSizedDialog

class AutoSizedFrame(UIForm):
 widget_type = widgets.AutoSizedFrame

class AutoSizedPanel(UIForm):
 widget_type = widgets.AutoSizedPanel

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
 widget_type = widgets.ListView
