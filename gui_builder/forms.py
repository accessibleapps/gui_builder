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
  self._last_enabled_descendant = None

 def set_values(self, values):
  """Given a dictionary mapping field names to values, sets fields on this form to the values provided."""
  for k, v in values.iteritems():
   self[k].default_value = v
   if self.is_rendered:
    self[k].set_value(v)

 def __iter__(self):
  """Iterate over this form's fields."""
  return self._fields.itervalues()

 def get_children(self):
  """Returns a generator which produces children of this form, but not their children."""
  for child in self:
   yield child

 def get_all_children(self):
  """Produces a generator which yields all descendants of this form."""
  for field in self.get_children():
   yield field
   if not hasattr(field, 'get_all_children'):
    continue
   for subfield in field.get_all_children():
    yield subfield

 def get_first_child(self):
  """Returns the first child field of this form."""
  try:
   return self.get_children().next()
  except StopIteration:
   return

 def get_last_child(self):
  """Returns the last child field of this form."""
  if self._last_child is None:
   try:
    self._last_child = list(self.get_all_children())[-1]
   except IndexError:
    pass
  return self._last_child

 def get_last_enabled_descendant(self):
  if self._last_enabled_descendant is not None:
   return self._last_enabled_descendant
  enabled_children = [child for child in self.get_all_children() if child.widget.enabled]
  descendant = enabled_children[-1]
  self._last_enabled_descendant = descendant
  return descendant

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
  """Removes a child from this form."""
  del self._fields[name]
  self._last_child = None
  self._last_enabled_descendant = None

 def get_value(self):
  """Returns a dictionary whose keys are fieldnames and whose values are the values of those fields."""
  res = {}
  for field in self:
   res[field.bound_name] = field.get_value()
  return res

 def render(self, **kwargs):
  """Renders this form and all children."""
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
  """Sets focus to the field on this form which was preset to be the default focused field."""
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
  """Does the work of actually displaying this form on the screen."""
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
  try:
   self.delete_child(name)
  except KeyError:
   super(Form, self).__delattr__(name)

 def __iter__(self):
  """ Iterates form fields in their order of definition on the form. """
  for name, _ in self._unbound_fields + self._extra_fields:
   if name in self._fields:
    yield self._fields[name]

class UIForm(Form):

 def set_value(self, items):
  """Given a mapping of field ids to values, populates each field with the corresponding value"""
  for key, value in items.iteritems():
   self[key].populate(value)

 def get_title(self):
  """Returns the form's title"""
  return self.widget.get_title()

 def set_title(self, title):
  """Sets the form's title to the string provided."""
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
  """Closes this form."""
  self.widget.close()
  self.destroy()

class BaseFrame(UIForm):

 def maximize(self):
  """Maximizes the frame."""
  return self.widget.maximize()

 def minimize(self):
  """Minimizes the frame."""
  return self.widget.minimize()

class Frame(BaseFrame):
 widget_type = widgets.Frame

class MDIParentFrame(BaseFrame):
 widget_type = widgets.MDIParentFrame

class MDIChildFrame(BaseFrame):
 widget_type = widgets.MDIChildFrame

class BaseDialog(UIForm):

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

class SizedPanel(UIForm):
 widget_type = widgets.SizedPanel

class Notebook(UIForm):
 widget_type = widgets.Notebook

 def add_item(self, label, item):
  """Adds a panel to the notebook. Requires a panel object and a label, which will be displayed on the tab strip."""
  self.add_child(repr(item), item)
  self.widget.add_item(label, item.widget)
 
 def delete_item(self, item):
  """Removes a panel from a notebook. Required: The panel to remove."""
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
  """Returns the currently-selected page of the notebook as the original panel."""
  return list(self.get_children())[self.get_selection()]

 def set_current_page(self, page):
  """Given a panel which is currently in the notebook, sets focus to it."""
  page_index = list(self.get_children()).index(page)
  self.set_selection(page_index)

class MenuBar(UIForm):
 widget_type = widgets.MenuBar

class Menu(UIForm):
 widget_type = widgets.Menu

 def enable_menu(self):
  """Enables all menu items in this menu."""
  for menu_item in self:
   if hasattr(menu_item, 'enable_menu'):
    menu_item.enable_menu()
   else:
    menu_item.enable()

 def disable_menu(self):
  """Disables all menu items in this menu"""
  for menu_item in self:
   if hasattr(menu_item, 'disable_menu'):
    menu_item.disable_menu()
   else:
    menu_item.disable()

 def popup(self, position=None):
  """Pops up the menu, for use in context menu handlers."""
  self.widget.popup(position)

 def context_menu(self):
  """Simplified context menu handler, performs the basic steps to display a context menu. return the result of this function from your event handler to avoid issues"""
  self.popup()
  self.destroy()
  return True

class SubMenu(Menu):
 widget_type = widgets.SubMenu

class ListView(ChoiceField, UIForm):

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
  """Returns the string at the given column and index"""
  return self.widget.get_item_column(index, column)

 def set_item_column(self, index, column, data):
  """Sets the string at the provided column and index to the provided value"""
  return self.widget.set_item_column(index, column, data)

class ToolBar(UIForm):
 widget_type = widgets.ToolBar

 def render(self, *args, **kwargs):
  super(ToolBar, self).render(*args, **kwargs)
  self.widget.realize()

class FrameToolBar(ToolBar):
 widget_type = widgets.FrameToolBar
