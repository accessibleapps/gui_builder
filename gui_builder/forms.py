from logging import getLogger
logger = getLogger('gui_builder.forms')

import platform
import traceback

from .fields import GUIField, ChoiceField
from .widgets import wx_widgets as widgets

class BaseForm(GUIField):
 __autolabel__ = False
 unbound = False

 def __init__(self, fields, *args, **kwargs):
  self._fields = {}
  if hasattr(fields, 'items'):
   fields = fields.items()
  for name, unbound_field in fields:
   self.add_child(name, unbound_field)
  working_kwargs = dict(kwargs)
  for key, value in working_kwargs.iteritems():
   try:
    self[key].default_value = value
    kwargs.pop(key)
   except KeyError:
    pass
  super(BaseForm, self).__init__(*args, **kwargs)  
  self.is_rendered = False
  self._last_child = None

 def set_values(self, values):
  for k, v in values.iteritems():
   self[k].default_value = v
   if self.is_rendered:
    self[k].set_value(v)

 def __iter__(self):
  return self._fields.itervalues()

 def get_children(self):
  for child in self:
   yield child

 def get_all_children(self):
  for field in self.get_children():
   yield field
   if not hasattr(field, 'get_all_children'):
    continue
   for subfield in field.get_all_children():
    yield subfield

 def get_first_child(self):
  try:
   return self.get_children().next()
  except StopIteration:
   return

 def get_last_child(self):
  if self._last_child is None:
   try:
    self._last_child = list(self.get_all_children())[-1]
   except IndexError:
    pass
  return self._last_child

 def __getitem__(self, name):
  return self._fields[name]

 def __setitem__(self, name, value):
  return self.add_child(name, value)

 def add_child(self, field_name, field):
  to_call = field
  if hasattr(field, 'bind'):
   to_call = field.bind
  new_field = to_call(parent=self, name=field_name)
  if hasattr(new_field, 'bind'):
   new_field.bind(parent=self, name=field_name)
  self._fields[field_name] = new_field
  last_child = new_field
  if hasattr(last_child, 'get_all_children'):
   children = list(last_child.get_all_children())
   if children:
    last_child = list(last_child.get_all_children())[-1]
  self._last_child = last_child
  return new_field

 def delete_child(self, name):
  del self._fields[name]
  self._last_child = None

 def get_value(self):
  res = {}
  for field in self:
   res[field.bound_name] = field.get_value()
  return res

 def render(self, **kwargs):
  super(BaseForm, self).render(**kwargs)
  logger.debug("Super has been called by the Base form. The widget for field %r is %r" % (self, self.widget))
  logger.debug("The fields inside this form are %r" % self._fields)
  for field in self:
   logger.debug("Rendering field %r" % field)
   try:
    field.render()
   except Exception as e:
    logger.exception("Failed rendering field %r." % field)
    raise
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
    logger.debug("Setting default focus to %r" % field)
    return
  child = self.get_first_focusable_child()
  if child is not None:
   child.set_focus()
   logger.debug("Setting default focus to first focusable child %r" % child)
   return
  self.set_focus()


 def display(self):
  self._predisplay()
  self.widget.display()

 def display_modal(self):
  self._predisplay()
  return self.widget.display_modal()

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

 def __delattr__(cls, name):
  if not name.startswith('_'):
   cls._unbound_fields = None
  type.__delattr__(cls, name)

class Form(BaseForm):
 __metaclass__ = FormMeta

 def __init__(self, *args, **kwargs):
  self._extra_fields = []
  super(Form, self).__init__(self._unbound_fields, *args, **kwargs)
  for name, field in self._fields.items():
   setattr(self, name, field)

 def add_child(self, field_name, unbound_field):
  field = super(Form, self).add_child(field_name, unbound_field)
  item = (field_name, unbound_field)
  setattr(self, field_name, field)
  if item not in self._unbound_fields:
   self._extra_fields.append(item)
  return field

 def delete_child(self, name):
  field = self._fields[name]
  for field_name, field in self._unbound_fields:
   if name == field_name:
    self._unbound_fields.remove((field_name, field))
    break
  for field_name, field in self._extra_fields:
   if field_name == name:
    self._extra_fields.remove((field_name, field))
    break
  setattr(self, name, None)
  super(Form, self).delete_child(name)

 def __delattr__(self, name):
  self.delete_child(name)

 def __iter__(self):
  """ Iterate form fields in their order of definition on the form. """
  for name, _ in self._unbound_fields + self._extra_fields:
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

 def delete_child(self, name):
  child = self._fields[name]
  self.widget.remove_child(child.widget)
  super(UIForm, self).delete_child(name)

 def close(self):
  self.widget.close()
  self.destroy()

class BaseFrame(UIForm):

 def maximize(self):
  return self.widget.maximize()

 def minimize(self):
  return self.widget.minimize()

class Frame(BaseFrame):
 widget_type = widgets.Frame

class BaseDialog(UIForm):

 def end_modal(self, modal_result):
  return self.widget.end_modal(modal_result)

class Dialog(BaseDialog):
 widget_type = widgets.Dialog

class Panel(UIForm):
 widget_type = widgets.Panel

class SizedDialog(BaseDialog):
 widget_type = widgets.SizedDialog

class SizedFrame(UIForm):
 widget_type = widgets.SizedFrame

class SizedPanel(UIForm):
 widget_type = widgets.SizedPanel

class Notebook(UIForm):
 widget_type = widgets.Notebook

 def add_item(self, label, item):
  self.add_child(repr(item), item)
  self.widget.add_item(label, item.widget)
 
 def delete_item(self, item):
  self.delete_child(repr(item))
  self.widget.delete_page(item.widget)

 def render(self, **kwargs):
  super(Notebook, self).render(**kwargs)
  for field in self:
   self.widget.add_item(field.label, field.widget)

 def get_selection(self):
  return self.widget.get_selection()

 def set_selection(self, selection):
  return self.widget.set_selection(selection)

 def get_current_page(self):
  return list(self.get_children())[self.get_selection()]

 def set_current_page(self, page):
  page_index = list(self.get_children()).index(page)
  self.set_selection(page_index)

class MenuBar(UIForm):
 widget_type = widgets.MenuBar

class Menu(UIForm):
 widget_type = widgets.Menu

 def enable_menu(self):
  for menu_item in self:
   if hasattr(menu_item, 'enable_menu'):
    menu_item.enable_menu()
   else:
    menu_item.enable()

 def disable_menu(self):
  for menu_item in self:
   if hasattr(menu_item, 'disable_menu'):
    menu_item.disable_menu()
   else:
    menu_item.disable()

class SubMenu(Menu):
 widget_type = widgets.SubMenu

class ListView(UIForm, ChoiceField):

 def __init__(self, virtual=False, *args, **kwargs):
  if platform.system() == 'Windows':
   self.widget_type = widgets.ListView
  else:
   self.widget_type = widgets.DataView
   virtual = False
  super(ListView, self).__init__(self, virtual=virtual, *args, **kwargs)

 def get_children(self):
  return []

 def get_item_column(self, index, column):
  return self.widget.get_item_column(index, column)

 def set_item_column(self, index, column, data):
  return self.widget.set_item_column(index, column, data)
