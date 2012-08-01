from logging import getLogger
logger = getLogger("gui_components.widgets.wx_widgets")

import inspect
from .widget import Widget
import wx
from wx.lib import intctrl
from wx.lib import sized_controls as sc
import wx_autosizing

LABELED_CONTROLS = (wx.Button, wx.CheckBox, wx.RadioBox)  #Controls that have their own labels
UNFOCUSABLE_CONTROLS = (wx.StaticText, wx.Gauge, wx.Panel, wx.MenuBar, wx.Menu, wx.MenuItem, ) #controls which cannot directly take focus
AUTOSIZED_CONTROLS = (wx_autosizing.AutoSizedFrame, wx_autosizing.AutoSizedDialog)
NONLABELED_CONTROLS = (wx.Menu, wx.MenuItem, wx.Panel, wx.Dialog, wx.Frame, sc.SizedPanel, sc.SizedDialog, sc.SizedFrame, wx_autosizing.AutoSizedPanel, wx_autosizing.AutoSizedDialog, wx_autosizing.AutoSizedFrame)

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



class WXWidget(Widget):
 style_prefix = ""
 default_event = None #the default event which triggers this widget's callback
 callback = None
 label = ""

 def __init__(self, parent=None, label="", callback=None, min_size=(-1, -1), *args, **kwargs):
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

 def create_control(self, **kwargs):
  label = kwargs.pop('label', getattr(self, 'label', ''))
  logger.debug("label: %r" % label)
  if label:
   kwargs['label'] = label
  if label and self.control_type is not None and self.control_type not in LABELED_CONTROLS and self.control_type not in NONLABELED_CONTROLS:
   label = kwargs.pop('label')
   try:
    self.label_control = wx.StaticText(parent=self.parent_control, label=label)
   except:
    logger.exception("Error creating label for control %r" % self.control_type)
    raise
  super(WXWidget, self).create_control(parent=self.parent_control, **kwargs)
  self.control.SetMinSize(self.min_size)

 def render(self, **runtime_kwargs):
  super(WXWidget, self).render(**runtime_kwargs)
  if self.control is None:
   return
  self.bind_callback()

 def bind_callback(self, callback=None):
  if self.default_event is None or not callable(self.callback):
   return
  def callback_wrapper(evt, *a, **k):
   a = list(a)
   argspec = inspect.getargspec(self.callback).args
   if argspec and argspec[0] == "self":
    a.insert(0, self.parent.field)
   try:
    self.callback(*a, **k)
   except:
    logger.exception("Error calling callback")
    raise
   evt.Skip()
  self.callback_wrapper = callback_wrapper
  self.control.Bind(self.default_event, self.callback_wrapper)


 def display(self):
  self.control.Show()

 def display_modal(self):
  self.control.ShowModal()

 def get_value(self):
  """Returns the most Pythonic representation of this control's current value."""
  return self.control.GetValue()

 def set_value(self, value):
  self.control.SetValue(value)

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
  return cls.control_type not in UNFOCUSABLE_CONTROLS

class ChoiceWidget(WXWidget):

 def get_items(self):
  return self.control.GetItems()

 def set_items(self, items):
  return self.control.SetItems(items)

 def get_index(self):
  return self.control.GetSelection()

 def set_index(self, index):
  return self.control.SetSelection(index)

 def get_choice(self):
  return self.get_items()[self.get_index()]

class Text(WXWidget):
 control_type = wx.TextCtrl
 style_prefix = "TE"
 default_event = wx.EVT_CHAR
 
class IntText(Text):
 widget_type = intctrl.IntCtrl

 def get_value(self):
  return int(self.control.GetValue())

 def set_value(self, value):
  self.control.SetValue(unicode(value))

class CheckBox(WXWidget):
 control_type = wx.CheckBox
 default_event = wx.EVT_CHECKBOX

class ComboBox(ChoiceWidget):
 control_type = wx.ComboBox
 style_prefix = "CB"
 default_event = wx.EVT_COMBOBOX

class Button(WXWidget):
 control_type = wx.Button
 style_prefix = "BTN"
 default_event = wx.EVT_BUTTON

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
 default_event = wx.EVT_SLIDER

class ScrollBar(WXWidget):
 control_type = wx.ScrollBar
 style_prefix = "SB"
 default_event = wx.EVT_SCROLLBAR

class ListBox(ChoiceWidget):
 control_type = wx.ListBox
 style_prefix = "LB"
 default_event = wx.EVT_LISTBOX

class ListView(WXWidget):
 control_type = wx.ListView
 style_prefix = "LC"
 default_event = wx.EVT_LIST_ITEM_ACTIVATED

 def get_index(self):
  return self.control.GetFirstSelected()

 def set_index(self, index):
  return self.control.Select(index)

 def add_column(self, column_number, column_heading="", width=None, **format):
  format = find_wx_attributes(format)
  if not isinstance(format, (int, long)):
   format = 0
  self.control.InsertColumn(column_number, column_heading, width=width, format=format)

 def delete_column(self, column_number):
  self.control.DeleteColumn(column_number)


class ToolBar(WXWidget):
 control_type = wx.ToolBar
 style_prefix = "TB"

class SpinBox(WXWidget):
 control_type = wx.SpinCtrl
 style_prefix = "SP"
 default_event = wx.EVT_SPINCTRL


class ButtonSizer(WXWidget):

 def translate_control_arguments(self, **kwargs):
  return wx_attributes("", result_key="flags", **kwargs)

 def create_control(self, **runtime_kwargs):
  kwargs = self.control_kwargs
  kwargs.update(runtime_kwargs)
  translated_kwargs = self.translate_control_arguments(**kwargs)
  self.control = self.parent.control.CreateStdDialogButtonSizer(**translated_kwargs)

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

class SizedDialog(BaseContainer):
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

class Dialog(BaseContainer):
 control_type = wx.Dialog

class Panel(BaseContainer):
 control_type = wx.Panel

class Notebook(BaseContainer):
 control_type = wx.Notebook

 def add_item(self, name, item):
  self.control.AddPage(item.control, name)

class AutoSizedContainer(BaseContainer):

 def display(self):
  super(AutoSizedContainer, self).display()
  self.control.fit()

 def display_modal(self):
  super(AutoSizedContainer, self).display_modal()
  self.control.fit()

class AutoSizedPanel(SizedPanel): #doesn't require fitting
 control_type = wx_autosizing.AutoSizedPanel

class AutoSizedFrame(AutoSizedContainer):
 control_type = wx_autosizing.AutoSizedFrame

class AutoSizedDialog(AutoSizedContainer):
 control_type = wx_autosizing.AutoSizedDialog

class RadioBox(ChoiceWidget):
 control_type = wx.RadioBox
 default_event = wx.EVT_RADIOBOX
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
 default_event = wx.EVT_CHECKLISTBOX
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
 default_event = wx.EVT_MENU

 def __init__(self, hotkey=None, help_message="", **kwargs):
  self.hotkey = hotkey
  self.help_message = help_message
  super(MenuItem, self).__init__(**kwargs)

 def create_control(self, **kwargs):
  label = kwargs.get('label', self.label)
  if self.hotkey is not None:
   label = "%s\t%s" % (label, self.hotkey)
  self.control = self.parent_control.Append(wx.NewId(), text=label, help=self.help_message)

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
