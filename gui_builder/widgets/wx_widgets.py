from logging import getLogger
logger = getLogger("gui_components.widgets.wx_widgets")

import inspect
from .widget import Widget
import wx
from wx.lib import intctrl
from wx.lib import sized_controls as sc
import wx_autosizing

LABELED_CONTROLS = (wx.HyperlinkCtrl, wx.Button, wx.CheckBox, wx.RadioBox)  #Controls that have their own labels
UNFOCUSABLE_CONTROLS = (wx.StaticText, wx.Gauge, wx.Panel, wx.MenuBar, wx.Menu, wx.MenuItem, wx_autosizing.AutoSizedFrame, wx_autosizing.AutoSizedDialog, wx_autosizing.AutoSizedPanel) #controls which cannot directly take focus
AUTOSIZED_CONTROLS = (wx_autosizing.AutoSizedFrame, wx_autosizing.AutoSizedDialog)
NONLABELED_CONTROLS = (wx.Menu, wx.MenuItem, wx.Panel, wx.Dialog, wx.Frame, sc.SizedPanel, sc.SizedDialog, sc.SizedFrame, wx_autosizing.AutoSizedPanel, wx_autosizing.AutoSizedDialog, wx_autosizing.AutoSizedFrame)

is_labeled = lambda control: is_subclass_or_instance(control, LABELED_CONTROLS)
is_focusable = lambda control: not is_subclass_or_instance(control, UNFOCUSABLE_CONTROLS)
is_autosized = lambda control: is_subclass_or_instance(control, AUTOSIZED_CONTROLS)
should_be_labeled = lambda control: not is_subclass_or_instance(control, NONLABELED_CONTROLS)

def is_subclass_or_instance(unknown, possible):
 try:
  return issubclass(unknown, possible)
 except TypeError:
  return isinstance(unknown, possible)

def find_wx_attribute(prefix, attr):
 if prefix:
  prefix = "%s_" % prefix
 underscore = "%s%s" % (prefix, attr)
 no_underscore = "%s%s" % (prefix, attr.replace("_", ""))
 underscore = underscore.upper()
 no_underscore = no_underscore.upper()
 val = getattr(wx, underscore, None)
 if not val:
  val = getattr(wx, no_underscore)
 return val

def wx_attributes(prefix="", result_key="style", **attrs):
 answer = {result_key:0}
 for k, v in attrs.iteritems():
  if v is not True:
   answer[k] = v
  else:
   try:
    answer[result_key] |= find_wx_attribute(prefix, k)
   except AttributeError:
    try:
     answer[result_key] |= find_wx_attribute("", k)
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
  if argspec and argspec[0] == "self":
   a.insert(0, widget.parent.field)
  try:
   callback(*a, **k)
  except:
   logger.exception("Error calling callback")
   raise
 return wrapper

  

class WXWidget(Widget):
 style_prefix = ""
 default_callback_type = None #the default event which triggers this widget's callback
 callback = None
 label = ""

 def __init__(self, parent=None, label="", callback=None, min_size=(-1, -1), enabled=True, *args, **kwargs):
  super(WXWidget, self).__init__(*args, **kwargs)
  if callback is None:
   callback = self.callback
  self.callback = callback
  if label == "":
   label = self.label
  self.label = label
  self.parent = parent
  self.min_size = min_size
  self.label_control = None
  self.control_enabled = enabled

 def create_control(self, **kwargs):
  label = kwargs.pop('label', getattr(self, 'label', ''))
  if label:
   kwargs['label'] = label
  if label is not None and should_be_labeled(self.control_type) and not is_labeled(self.control_type):
   label = kwargs.pop('label')
   try:
    self.label_control = wx.StaticText(parent=self.parent_control, label=label)
   except:
    logger.exception("Error creating label for control %r" % self.control_type)
    raise
  if 'label' in kwargs and not should_be_labeled(self.control_type):
   del kwargs['label']
  super(WXWidget, self).create_control(parent=self.parent_control, **kwargs)
  self.control.SetMinSize(self.min_size)

 def render(self, **runtime_kwargs):
  super(WXWidget, self).render(**runtime_kwargs)
  if self.control is None:
   return
  self.register_callback()
  self.enabled = self.control_enabled

 def register_callback(self, callback_type=None, callback=None):
  if callback_type is None:
   callback_type = self.default_callback_type
  if callback is None:
   callback = self.callback
  if callback_type is None:
   return
  callback_event = self.resolve_callback_type(callback_type)
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
  return find_wx_attribute("EVT", callback_type)


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

 def hide(self):
  self.control.Hide()

 def display(self):
  self.control.Show()

 def get_value(self):
  """Returns the most Pythonic representation of this control's current value."""
  if hasattr(self.control, 'GetValue'):
   return self.control.GetValue()

 def set_value(self, value):
  self.control.SetValue(value)

 def populate(self, value):
  """this is to provide a common abstraction for getting data into controls. It will take the most common form that data holds in an application and turn it into something this widget can deal with."""
  self.set_value(value)


 @property
 def parent_control(self):
  parent = getattr(self.parent, "control", None)
  if isinstance(parent, AUTOSIZED_CONTROLS):
   parent = parent.pane
  return parent

 def translate_control_arguments(self, **kwargs):
  return wx_attributes(self.style_prefix, result_key="style", **kwargs)
 
 def set_focus(self):
  self.control.SetFocus()

 @classmethod
 def can_be_focused(cls):
  return cls.control_type is not None and cls.control_type not in UNFOCUSABLE_CONTROLS

class ChoiceWidget(WXWidget):

 def get_items(self):
  return self.control.GetItems()

 def set_items(self, items):
  return self.control.SetItems(items)

 def get_item(self, index):
  return self.control.get_string(index)

 def __getitem___(self, index):
  return self.get_item(index)

 def get_index(self):
  return self.control.GetSelection()

 def set_index(self, index):
  return self.control.SetSelection(index)

 def get_choice(self):
  return self.get_item(self.get_index())

 def populate(self, value):
  self.set_items(value)

 def get_count(self):
  return self.control.GetCount()

 def delete_item(self, index):
  self.control.Delete(index)

class Text(WXWidget):
 control_type = wx.TextCtrl
 style_prefix = "TE"
 default_callback_type = "char"


 def translate_control_arguments(self, **kwargs):
  res = super(Text, self).translate_control_arguments(**kwargs)
  if 'style' not in res:
   return {}
  if res['style'] | wx.TE_READONLY == res['style']:
   res['style'] |= wx.TE_MULTILINE
  return res


 def select_range(self, start, end):
  self.control.SetSelection(start, end)


 def get_length(self):
  #this annoys me
  val = self.get_value()
  length = len(val)
  del val
  return length

class IntText(Text):
 widget_type = intctrl.IntCtrl

 def set_value(self, value):
  self.control.SetValue(unicode(value))

class CheckBox(WXWidget):
 control_type = wx.CheckBox
 default_callback_type = "checkbox"

class ComboBox(ChoiceWidget):
 control_type = wx.ComboBox
 style_prefix = "CB"
 default_callback_type = "combobox"

class Button(WXWidget):
 control_type = wx.Button
 style_prefix = "BTN"
 default_callback_type = "button"

 def __init__(self, default=False, *args, **kwargs):
  super(Button, self).__init__(*args, **kwargs)
  self.default = default

 def render(self):
  super(Button, self).render()
  if self.default:
   self.control.SetDefault()

class Slider(WXWidget):
 style_prefix = "SL"
 control_type = wx.Slider
 default_callback_type = "slider"

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
 default_callback_type = "LIST_ITEM_FOCUSED"

 def __init__(self, choices=None, **kwargs):
  super(ListView, self).__init__(**kwargs)
  if choices is None:
   choices = []
  self.choices = choices
  self._last_added_column = -1

 def get_index(self):
  return self.control.GetFirstSelected() - 1

 def set_index(self, index):
  self.control.Select(index)
  self.control.Focus(index)

 def get_count(self):
  return self.control.GetItemCount()

 def get_item(self, index):
  return self.control.GetItem(index)

 def get_items(self):
  res = []
  for num in xrange(self.get_count()):
   res.append(self.get_item(num))
   return res

 def set_items(self, items):
  self.control.DeleteAllItems()
  for item in items:
   self.control.Append(item)

 def delete_item(self, index):
  self.control.DeleteItem(index)

 def render(self, **kwargs):
  super(ListView, self).render(**kwargs)
  self.set_items(self.choices)

 def add_column(self, column_number=None, label="", width=None, **format):
  if column_number is None:
   column_number = self._last_added_column + 1
  if width is None:
   width = -1
  format = wx_attributes(format)
  if not isinstance(format, (int, long)):
   format = wx.LIST_FORMAT_LEFT
  self.control.InsertColumn(column_number, label, width=width, format=format)
  self._last_added_column = column_number

 def delete_column(self, column_number):
  self.control.DeleteColumn(column_number)

class ListViewColumn(WXWidget):

 def create_control(self, **runtime_kwargs):
  kwargs = self.control_kwargs
  kwargs.update(runtime_kwargs)
  kwargs['label'] = self.label
  translated_kwargs = self.translate_control_arguments(**kwargs)
  self.control = self.parent.add_column(**translated_kwargs)

 def render(self):
  logger.debug("Rendering ListView column")
  self.create_control()


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
  return self.control.FindWindowById(self._modal_result)

class SizedDialog(BaseDialog):
 control_type = sc.SizedDialog

class SizedFrame(BaseContainer):
 control_type = sc.SizedFrame

class SizedPanel(BaseContainer):
 control_type = sc.SizedPanel

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

class Notebook(BaseContainer):
 control_type = wx.Notebook
 default_callback_type = "notebook_page_changed"

 def add_item(self, name, item):
  self.control.AddPage(item.control, name)

class AutoSizedContainer(BaseContainer):

 def display(self):
  super(AutoSizedContainer, self).display()
  self.control.fit()

class AutoSizedPanel(SizedPanel): #doesn't require fitting
 control_type = wx_autosizing.AutoSizedPanel

class AutoSizedFrame(AutoSizedContainer):
 control_type = wx_autosizing.AutoSizedFrame

class AutoSizedDialog(AutoSizedContainer, BaseDialog):
 control_type = wx_autosizing.AutoSizedDialog

 def display_modal(self):
  res = super(AutoSizedDialog, self).display_modal()
  self.control.fit()
  return res


class RadioBox(ChoiceWidget):
 control_type = wx.RadioBox
 default_callback_type = "RADIOBOX"
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


 def create_control(self, **kwargs):
  self.control = wx.MenuBar()
  wx.GetApp().GetTopWindow().SetMenuBar(self.control)


 def add_item(self, name=None, item=None):
  if item is None:
   raise TypeError("Must provide a MenuItem")
  name = name or item.name
  control = item.control
  self.control.Append(control, name)

class Menu(WXWidget):
 control_type = wx.Menu

 def create_control(self, **kwargs):
  label = kwargs.get('label', self.label)
  self.control = wx.Menu()
  self.parent_control.Append(self.control, title=label)

class MenuItem(WXWidget):
 control_type = wx.MenuItem
 default_callback_type = "MENU"

 def __init__(self, hotkey=None, help_message="", **kwargs):
  self.hotkey = hotkey
  self.help_message = help_message
  self.control_id = None
  super(MenuItem, self).__init__(**kwargs)

 def create_control(self, **kwargs):
  label = kwargs.get('label', self.label)
  if not label: #This menu item is a separator
   self.control = self.parent_control.AppendSeparator()
   return
  if self.hotkey is not None:
   label = "%s\t%s" % (label, self.hotkey)
  self.control_id = wx.NewId()
  self.control = self.parent_control.Append(id=self.control_id, text=label, help=self.help_message)

 def bind_event(self, callback_event, wrapped_callback):
  self.parent.control.Bind(callback_event, wrapped_callback, self.control)


class SubMenu(WXWidget):
 def create_control(self, **kwargs):
  label = kwargs.get('label', self.label)
  self.control = self.parent_control.Parent.AppendSubMenu(self.parent_control, label=label)

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
 control_type = wx.HyperlinkCtrl
 default_callback_type = "hyperlink"
