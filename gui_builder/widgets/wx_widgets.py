from logging import getLogger
logger = getLogger("gui_components.widgets.wx_widgets")

import inspect
from .widget import Widget
import wx
import wx.dataview
from wx.lib import intctrl
from wx.lib import sized_controls as sc
from wx.lib.agw import hyperlink
import platform

import gui_builder

UNFOCUSABLE_CONTROLS = (wx.StaticText, wx.Gauge, ) #controls which cannot directly take focus

def inheritors(klass):
 subclasses = set()
 work = [klass]
 while work:
  parent = work.pop()
  for child in parent.__subclasses__():
   if child not in subclasses:
    subclasses.add(child)
    work.append(child)
 return subclasses

is_labeled = lambda control: is_subclass_or_instance(control, [cls for cls in inheriters(WXWidget) if cls.selflabeled])

MODAL_RESULTS = {
 wx.ID_OK: gui_builder.OK,
 wx.ID_APPLY: gui_builder.APPLY,
 wx.ID_CANCEL: gui_builder.CANCEL,
 wx.ID_CLOSE: gui_builder.CLOSE,
 wx.ID_FIND: gui_builder.FIND,
}


def is_subclass_or_instance(unknown, possible):
 try:
  return issubclass(unknown, possible)
 except TypeError:
  return isinstance(unknown, possible)

def find_wx_attribute(prefix, attr, module=wx):
 if prefix:
  prefix = "%s_" % prefix
 underscore = "%s%s" % (prefix, attr)
 no_underscore = "%s%s" % (prefix, attr.replace("_", ""))
 underscore = underscore.upper()
 no_underscore = no_underscore.upper()
 val = getattr(module, underscore, None)
 if not val:
  val = getattr(module, no_underscore)
 return val

def wx_attributes(prefix="", result_key="style", module=wx, **attrs):
 answer = {result_key:0}
 for k, v in attrs.iteritems():
  if v is not True:
   answer[k] = v
  else:
   try:
    answer[result_key] |= find_wx_attribute(prefix, k, module=module)
   except AttributeError:
    try:
     answer[result_key] |= find_wx_attribute("", k, module=module)
    except AttributeError:
     answer[k] = v
 if result_key in answer and answer[result_key] == 0:
  del answer[result_key]
 return answer



def callback_wrapper(widget, callback):
 def wrapper(evt, *a, **k):
  evt.Skip(True)
  a = list(a)
  argspec = inspect.getargspec(callback).args
  if argspec and argspec[0] == "self" and not hasattr(callback, "im_self"):
   parent = widget.parent
   if parent is None:
    parent = widget
   a.insert(0, parent.field)
  try:
   callback(*a, **k)
  except Exception as e:
   if not isinstance(e, SystemExit):
    logger.exception("Error calling callback")
   raise
 return wrapper

def translate_none(val):
 if val == -1:
  val = None
 return val

class WXWidget(Widget):
 style_prefix = ''
 event_prefix = 'EVT'
 event_module = wx
 selflabeled = False
 unlabeled = False
 focusable = True
 default_callback_type = None #the default event which triggers this widget's callback
 callback = None
 label = ""

 def __init__(self, parent=None, label="", callback=None, min_size=None, enabled=True, hidden=False, *args, **kwargs):
  super(WXWidget, self).__init__(*args, **kwargs)
  if callback is None:
   callback = self.callback
  self.callback = callback
  if label == "":
   label = self.label
  self.label_text = label
  self.parent = parent
  self.min_size = min_size
  self.label_control = None
  self.control_enabled = enabled
  self.control_hidden = hidden

 def create_control(self, **kwargs):
  logger.debug("Creating control for widget %r. Widget parent: %r. Widget parent control: %r" % (self, self.parent, self.get_parent_control()))
  kwargs = self.create_label_control(**kwargs)
  if 'title' in kwargs:
   kwargs['title'] = unicode(kwargs['title'])
  super(WXWidget, self).create_control(parent=self.get_parent_control(), **kwargs)
  if self.label_text:
   self.set_label(unicode(self.label_text))
  if self.min_size is not None:
   self.control.SetMinSize(self.min_size)

 def create_label_control(self, label=None, **kwargs):
  if label is None:
   label = self.label_text
  if self.unlabeled:
   return kwargs
  if self.selflabeled:
   if label:
    kwargs['label'] = unicode(label)
   return kwargs
  try:
   self.label_control = wx.StaticText(parent=self.get_parent_control(), label=unicode(label))
  except:
   logger.exception("Error creating label for control %r" % self.control_type)
   raise
  return kwargs

 def render(self, **runtime_kwargs):
  super(WXWidget, self).render(**runtime_kwargs)
  if self.control is None:
   return
  self.register_callback()
  self.enabled = self.control_enabled
  if self.control_hidden:
   self.hide()

 def register_callback(self, callback_type=None, callback=None):
  if callback_type is None:
   callback_type = self.default_callback_type
  if callback is None:
   callback = self.callback
  if callback_type is None:
   return
  callback_event = self.resolve_callback_type(callback_type)
  logger.debug("Resolved %r to %r" % (callback_type, callback_event))
  if callback_event is None or not callable(callback):
   return

  wrapped_callback = callback_wrapper(self, callback)
  super(WXWidget, self).register_callback(callback_type, wrapped_callback)
  self.bind_event(callback_event, wrapped_callback)

 def bind_event(self, callback_event, wrapped_callback):
  self.control.Bind(callback_event, wrapped_callback)

 def resolve_callback_type(self, callback_type):
  if isinstance(callback_type, wx.PyEventBinder):
   return callback_type
  try:
   res = find_wx_attribute(self.event_prefix, callback_type, module=self.event_module)
  except AttributeError:
   try:
    res = find_wx_attribute(WXWidget.event_prefix, callback_type, module=self.event_module)
   except AttributeError:
    res = find_wx_attribute(WXWidget.event_prefix, callback_type, module=WXWidget.event_module)
  return res

 @property
 def enabled(self):
  return self.control.Enabled

 @enabled.setter
 def enabled(self, val):
  self.control.Enabled = bool(val)

 def enable(self):
  self.enabled = True

 def disable(self):
  self.enabled = False

 def freeze(self):
  self.control.Freeze()

 def thaw(self):
  self.control.Thaw()

 def destroy(self):
  try:
   self.control.Destroy()
  except wx._core.PyDeadObjectError:
   pass

 def hide(self):
  self.control.Hide()

 def show(self):
  self.control.Show()

 def display(self):
  self.control.Raise()
  self.show()


 def get_control(self):
  return self.control

 def get_parent_control(self):
  if isinstance(self.parent, Widget):
   return self.parent.get_control()
  return self.parent

 def get_label(self):
  if self.label_control is not None:
   return self.label_control.GetLabel()
  return self.control.GetLabel()

 def set_label(self, label):
  if self.label_control is not None:
   self.label_control.SetLabel(label)
  self.control.SetLabel(label)

 def get_value(self):
  """Returns the most Pythonic representation of this control's current value."""
  if hasattr(self.control, 'GetValue'):
   return self.control.GetValue()

 def set_value(self, value):
  self.control.SetValue(value)

 def populate(self, value):
  """this is to provide a common abstraction for getting data into controls. It will take the most common form that data holds in an application and turn it into something this widget can deal with."""
  self.set_value(value)

 def translate_control_arguments(self, **kwargs):
  return wx_attributes(self.style_prefix, result_key="style", **kwargs)

 def is_focused(self):
  return self.control.HasFocus()

 def set_focus(self):
  self.control.SetFocus()


 @classmethod
 def can_be_focused(cls):
  return cls.control_type is not None and cls.focusable

class ChoiceWidget(WXWidget):

 def get_items(self):
  return self.control.GetItems()

 def set_items(self, items):
  return self.control.SetItems([unicode(item) for item in items])

 def get_item(self, index):
  return self.control.GetString(index)

 def __getitem___(self, index):
  return self.get_item(index)

 def get_index(self):
  return translate_none(self.control.GetSelection())

 def set_index(self, index):
  return self.control.SetSelection(index)

 def get_choice(self):
  return self.get_item(self.get_index())

 def get_value(self):
  return self.get_choice()

 def populate(self, value):
  self.set_items(value)

 def get_count(self):
  return self.control.GetCount()

 def delete_item(self, index):
  self.control.Delete(index)

 def insert_item(self, index, item):
  return self.control.InsertItems([item], index)

 def update_item(self, index, item):
  self.delete_item(index)
  self.insert_item(index, item)

 def clear(self):
  self.control.Clear()

class BaseText(WXWidget):
 event_prefix = 'EVT_TEXT'

 def __init__(self, max_length=None, *args, **kwargs):
  super(BaseText, self).__init__(*args, **kwargs)
  self.max_length = max_length

 def select_range(self, start, end):
  self.control.SetSelection(start, end)

 def get_length(self):
  #this annoys me
  val = self.get_value()
  length = len(val)
  del val
  return length

 def get_insertion_point(self):
  return self.control.GetInsertionPoint()

 def set_insertion_point(self, insertion_point):
  self.control.SetInsertionPoint(insertion_point)

 def set_max_length(self, length):
  self.control.SetMaxLen(length)

 def render(self, *args, **kwargs):
  super(BaseText, self).render(*args, **kwargs)
  if self.max_length is not None:
   self.set_max_length(self.max_length)

 def set_label(self, label):
  self.label_control.SetLabel(label)

class Text(BaseText):
 control_type = wx.TextCtrl
 style_prefix = "TE"
 default_callback_type = "char"

 def translate_control_arguments(self, **kwargs):
  res = super(Text, self).translate_control_arguments(**kwargs)
  if 'style' not in res:
   return res
  if res['style'] | wx.TE_READONLY == res['style']:
   res['style'] |= wx.TE_MULTILINE
  return res

 def get_number_of_lines(self):
  return self.control.GetNumberOfLines()

 def get_insertion_point_from_x_y(self, x, y):
  return self.control.XYToPosition(x, y)

 def get_x_y_from_insertion_point(self, insertion_point):
  return self.control.PositionToXY(insertion_point)


class IntText(Text):
 widget_type = intctrl.IntCtrl

 def set_value(self, value):
  self.control.SetValue(unicode(value))

 def get_value(self):
  value = super(IntText, self).get_value()
  if value:
   value = int(value)
  return value

class StaticText(WXWidget):
 control_type = wx.StaticText
 selflabeled = True

class CheckBox(WXWidget):
 control_type = wx.CheckBox
 default_callback_type = "checkbox"
 selflabeled = True


class ComboBox(ChoiceWidget):
 control_type = wx.ComboBox
 style_prefix = "CB"
 default_callback_type = "combobox"

class Button(WXWidget):
 control_type = wx.Button
 default_callback_type = "button"
 selflabeled = True

 def __init__(self, default=False, *args, **kwargs):
  super(Button, self).__init__(*args, **kwargs)
  self.default = default

 def render(self):
  super(Button, self).render()
  if self.default:
   self.make_default()

 def translate_control_arguments(self, **kwargs):
  return wx_attributes("ID", result_key="id", **kwargs)

 def make_default(self):
  self.control.SetDefault()


class Slider(WXWidget):
 style_prefix = "SL"
 control_type = wx.Slider
 default_callback_type = "slider"

 def __init__(self, page_size=None, *args, **kwargs):
  super(Slider, self).__init__(*args, **kwargs)
  self._page_size = page_size

 def render(self, *args, **kwargs):
  super(Slider, self).render(*args, **kwargs)
  if self._page_size is not None:
   self.set_page_size(self._page_size)

 def get_page_size(self):
  return self.control.GetPageSize()

 def set_page_size(self, page_size):
  return self.control.SetPageSize(page_size)

class ScrollBar(WXWidget):
 control_type = wx.ScrollBar
 style_prefix = "SB"
 default_callback_type = "scrollbar"

class ListBox(ChoiceWidget):
 control_type = wx.ListBox
 style_prefix = "LB"
 default_callback_type = "listbox"

class ListView(ChoiceWidget):
 control_type = wx.ListView
 style_prefix = "LC"
 event_prefix = 'EVT_LIST'
 default_callback_type = 'ITEM_SELECTED'

 def __init__(self, choices=None, **kwargs):
  self.virtual = kwargs.pop('virtual', False)
  if self.virtual:
   self.control_type = VirtualListView
   kwargs['style'] = kwargs.get('style', 0)
   kwargs['style'] |= wx.LC_VIRTUAL|wx.LC_REPORT
  super(ListView, self).__init__(**kwargs)
  if choices is None:
   choices = []
  self.choices = choices
  self._last_added_column = -1

 def get_index(self):
  return translate_none(self.control.GetFirstSelected())

 def set_index(self, index):
  if index is None:
   index = -1
  self.control.Select(index)
  self.control.Focus(index)

 def get_count(self):
  return self.control.GetItemCount()

 def get_column_count(self):
  return self.control.GetColumnCount()

 def get_item(self, index):
  res = []
  for column in xrange(self.get_column_count()):
   res.append(self.get_item_column(index, column))
  return tuple(res)

 def get_items(self):
  res = []
  for num in xrange(self.get_count()):
   res.append(self.get_item(num))
  return res


 def get_item_column(self, index, column):
  return self.control.GetItemText(index, column)

 def set_item_column(self, index, column, data):
  self.control.SetStringItem(index, column, data)

 def add_item(self, item):
  self.control.Append(item)

 def set_item(self, index, item):
  for column, subitem in enumerate(item):
   self.set_item_column(index, column, unicode(subitem))

 def update_item(self, index, item):
  self.set_item(index, item)

 def set_items(self, items):
  if self.virtual:
   self.control.SetItems(list(items))
   return
  self.clear()
  for item in items:
   self.add_item(item)

 def insert_item(self, index, item):
  self.control.InsertStringItem(index, item)

 def delete_item(self, index):
  self.control.DeleteItem(index)

 def clear(self):
  self.control.DeleteAllItems()

 def render(self, **kwargs):
  super(ListView, self).render(**kwargs)
  self.set_value(self.choices)

 def add_column(self, column_number=None, label="", width=None, **format):
  if column_number is None:
   column_number = self._last_added_column + 1
  if width is None:
   width = -1
  format = wx_attributes(format)
  if not isinstance(format, (int, long)):
   format = wx.ALIGN_LEFT
  self.create_column(column_number, label, width=width, format=format)
  self._last_added_column = column_number

 def create_column(self, column_number, label, width, format):
  self.control.InsertColumn(column_number, label, width=width, format=format)

 def delete_column(self, column_number):
  self.control.DeleteColumn(column_number)

 def get_value(self):
  return self.get_items()

 def set_value(self, value):
  return self.set_items(value)


class ListViewColumn(WXWidget):

 def create_control(self, **runtime_kwargs):
  kwargs = self.control_kwargs
  kwargs.update(runtime_kwargs)
  kwargs['label'] = unicode(self.label)
  translated_kwargs = self.translate_control_arguments(**kwargs)
  self.control = self.parent.add_column(**translated_kwargs)

 def render(self):
  logger.debug("Rendering ListView column")
  self.create_control()

 def set_item(self, index, item):
  for column, subitem in enumerate(item):
   self.control.SetStringItem(index, column, subitem)


class DataView(ListView):
 control_type = wx.dataview.DataViewListCtrl
 event_prefix = 'EVT_DATAVIEW'
 style_prefix = ""
 event_module = wx.dataview
 default_callback_type = 'selection_changed'

 def add_item(self, item):
  self.control.AppendItem(item)

 def insert_item(self, index, item):
  return self.control.InsertItem(index, item)

 def get_count(self):
  return self.control.GetStore().GetCount()

 def get_column_count(self):
  return self.control.GetStore().GetColumnCount()

 def get_index(self):
  return translate_none(self.control.GetSelectedRow())
 
 def set_index(self, index):
  if index is None:
   return
  index = int(index)
  if index == 0 and self.get_count() == 0:
   return
  self.control.SelectRow(index)

 def create_column(self, column_number, label, width, format):
  self.control.AppendTextColumn(label, align=format, width=width)

 def get_item_column(self, index, column):
  return self.control.GetTextValue(index, column)

 def set_item_column(self, index, column, data):
  self.control.SetTextValue(data, index, column)

class ToolBar(WXWidget):
 control_type = wx.ToolBar
 style_prefix = "TB"

class SpinBox(WXWidget):
 control_type = wx.SpinCtrl
 style_prefix = "SP"
 default_callback_type = "SPINCTRL"

class ButtonSizer(WXWidget):
 control_type = wx.StdDialogButtonSizer

 def translate_control_arguments(self, **kwargs):
  return wx_attributes("", result_key="flags", **kwargs)

 def create_control(self, **runtime_kwargs):
  callbacks = {}
  kwargs = self.control_kwargs
  kwargs.update(runtime_kwargs)
  for kwarg, val in kwargs.items():
   if callable(val):
    kwargs[kwarg] = True
    try:
     logger.debug("Finding id for kwarg %s" % kwarg)
     callbacks[kwarg] = (find_wx_attribute("ID", kwarg), val)
     logger.debug("Found callback %s" % str(callbacks[kwarg]))
    except AttributeError:
      pass
  control_kwargs = self.translate_control_arguments(**kwargs)
  self.control = self.parent.control.CreateStdDialogButtonSizer(**control_kwargs)
  for control_id, callback in callbacks.itervalues():
   for child_sizer in self.control.GetChildren():
    window = child_sizer.GetWindow()
    if window is not None and window.GetId() == control_id:
     window.Bind(wx.EVT_BUTTON, callback_wrapper(self, callback))
     logger.debug("Bound callback %s" % str(callback))
     break

 def render(self):
  self.create_control()
  self.parent.control.SetButtonSizer(self.control)

class BaseContainer(WXWidget):
 unlabeled = True

 def __init__(self, top_level_window=False, *args, **kwargs):
  super(BaseContainer, self).__init__(*args, **kwargs)
  self.top_level_window = top_level_window

 def render(self):
  super(BaseContainer, self).render()
  if self.top_level_window:
   wx.GetApp().SetTopWindow(self.control)

 def set_title(self, title):
  self.control.SetTitle(title)

 def get_title(self):
  return self.control.GetTitle()

 def set_label(self, label):
  pass

 def close(self):
  self.control.Close()

class BaseDialog(BaseContainer):

 def __init__(self, *args, **kwargs):
  super(BaseDialog, self).__init__(*args, **kwargs)
  self._modal_result = None

 def display_modal(self):
  self._modal_result = self.control.ShowModal()
  return self.get_modal_result()

 def get_modal_result(self):
  if self._modal_result is None:
   raise RuntimeError("%r has not yet been displayed modally, hence no result is available." % self)
  #control = self.control.FindWindowById(self._modal_result)
  result = self._modal_result
  try:
   return MODAL_RESULTS[result]
  except KeyError:
   return result


class SizedDialog(BaseDialog):
 control_type = sc.SizedDialog

class SizedFrame(BaseContainer):
 control_type = sc.SizedFrame

class SizedPanel(BaseContainer):
 control_type = sc.SizedPanel
 focusable = False

 def __init__(self, sizer_type="vertical", *args, **kwargs):
  super(SizedPanel, self).__init__(*args, **kwargs)
  self.sizer_type = sizer_type

 def render(self):
  super(SizedPanel, self).render()
  self.control.SetSizerType(self.sizer_type)

class Frame(BaseContainer):
 control_type = wx.Frame

class Dialog(BaseDialog):
 control_type = wx.Dialog

class Panel(BaseContainer):
 control_type = wx.Panel
 focusable = False


class Notebook(BaseContainer):
 control_type = wx.Notebook
 event_prefix = 'EVT_NOTEBOOK'
 default_callback_type = 'page_changed'

 def add_item(self, name, item):
  self.control.AddPage(item.control, unicode(name))
  #Now, we shall have much hackyness to work around WX bug 11909
  children = list(item.field.get_all_children())
  first_child = children[0]
  last_child = children[-1]
  last_child._was_focused = False
  def on_focus(evt):
   evt.Skip()
   last_child._was_focused = True
  def on_navigation_key(evt):
   if evt.GetDirection() and last_child._was_focused:
    self.set_focus()
   else:
    evt.Skip()
   last_child._was_focused = False
  last_child.widget.bind_event(wx.EVT_SET_FOCUS, on_focus)
  first_child.widget.bind_event(wx.EVT_NAVIGATION_KEY, on_navigation_key)

 def render(self, *args, **kwargs):
  super(Notebook, self).render(*args, **kwargs)
  def on_notebook_navigation(evt):
   if not evt.GetDirection() and evt.GetCurrentFocus() is None:
    list(self.field.get_current_page().get_children())[-1].set_focus()
   else:
    evt.Skip()
  self.bind_event(wx.EVT_NAVIGATION_KEY, on_notebook_navigation)

 def get_selection(self):
  return self.control.GetSelection()

 def set_selection(self, selection):
  return self.control.SetSelection(selection)

class RadioBox(ChoiceWidget):
 control_type = wx.RadioBox
 default_callback_type = "RADIOBOX"
 selflabeled = True
 style_prefix = "RA"

 def get_value(self):
  return self.control.GetStringSelection()

 def set_value(self, value):
  self.control.SetStringSelection(value)

 def get_items(self):
  return self.control.GetChoices()

 def set_items(self, items):
  return self.control.SetItems(items)

class CheckListBox(ListBox):
 default_callback_type = "CHECKLISTBOX"
 control_type = wx.CheckListBox

class FilePicker(WXWidget):
 control_type = wx.FilePickerCtrl

class MenuBar(WXWidget):
 control_type = wx.MenuBar
 focusable = False
 unlabeled = True

 def create_control(self, **kwargs):
  self.control = wx.MenuBar()
  wx.GetApp().GetTopWindow().SetMenuBar(self.control)

 def render(self):
  super(MenuBar, self).render()
  if platform.system() == 'Darwin':
   wx.MenuBar.MacSetCommonMenuBar(self.control)

 def add_item(self, name=None, item=None):
  if item is None:
   raise TypeError("Must provide a MenuItem")
  name = name or item.name
  control = item.control
  self.control.Append(control, name)

class Menu(WXWidget):
 control_type = wx.Menu
 focusable = False

 def create_control(self, **kwargs):
  label = unicode(kwargs.get('label', self.label_text))
  self.control = wx.Menu()
  self.get_parent_control().Append(self.control, title=label)

class MenuItem(WXWidget):
 control_type = wx.MenuItem
 default_callback_type = "MENU"
 focusable = False
 unlabled = True

 def __init__(self, hotkey=None, help_message="", checkable=False, **kwargs):
  self.hotkey = hotkey
  self.help_message = help_message
  self.checkable = checkable
  self.control_id = None
  super(MenuItem, self).__init__(**kwargs)

 def create_control(self, **kwargs):
  label = unicode(kwargs.get('label', self.label_text))
  if not label: #This menu item is a separator
   self.control = self.get_parent_control().AppendSeparator()
   return
  if self.hotkey is not None:
   label = "%s\t%s" % (label, self.hotkey)
  self.control_id = wx.NewId()
  self.control = self.get_parent_control().Append(self.control_id, label, self.help_message, )
  if self.checkable:
   self.control.SetCheckable(True)

 def bind_event(self, callback_event, wrapped_callback):
  self.parent.control.Bind(callback_event, wrapped_callback, self.control)

 def render(self):
  super(MenuItem, self).render()
  if not self.control_enabled:
   self.disable()


 def enable(self):
  self.control.Enable(True)

 def disable(self):
  self.control.Enable(False)

 def check(self):
  self.control.Check(True)

 def uncheck(self):
  self.control.Check(False)

class SubMenu(WXWidget):
 def create_control(self, **kwargs):
  label = unicode(kwargs.get('label', self.label_text))
  self.control = self.get_parent_control().Parent.AppendSubMenu(self.get_parent_control(), label=label)

class StatusBar(WXWidget):
 control_type = wx.StatusBar
 style_prefix = 'SB'

 def create_control(self, **kwargs):
  self.control = self.parent.control.CreateStatusBar(**kwargs)

 def set_value(self, value):
  self.control.SetStatusText(value)

 def get_value(self):
  return self.control.GetStatusText()

class Link(WXWidget):
 control_type = hyperlink.HyperLinkCtrl
 default_callback_type = "hyperlink"
 selflabeled = True

class DatePicker(WXWidget):
 control_type = wx.DatePickerCtrl

class VirtualListView(wx.ListCtrl):

 def __init__(self, *args, **kwargs):
  super(VirtualListView, self).__init__(*args, **kwargs)
  self.items = []

 def Append(self, item):
  self.items.append(item)
  self.SetItemCount(len(self.items))

 def SetItems(self, items):
  self.items = items
  self.SetItemCount(len(self.items))

 def OnGetItemText(self, item, col):
  return self.items[item][col]

 def DeleteAllItems(self):
  self.items = []
  self.SetItemCount(0)

 def SetStringItem(self, index, column, data):
  row = list(self.items[index])
  row[column] = data
  self.items[index] = row

class TreeView(WXWidget):
 control_type = wx.TreeCtrl
 style_prefix = "TR"
 event_prefix = 'EVT_TREE'
 default_callback_type = 'SEL_CHANGED'

 def add_root(self, text, image, selected_image, data):
  return self.control.AddRoot(text, image, selected_image, data)

 def get_root_item(self):
  return self.control.GetRootItem()

 def append_item(self, parent, text, image, selected_image, data):
  return self.control.AppendItem(parent, text, image, selected_image, data)

 def clear(self):
  self.control.DeleteAllItems()

 def delete(self, item):
  self.control.Delete(item)

 def get_selection(self):
  return self.control.GetSelection()

 def select_item(self, item):
  self.control.SelectItem(item)
