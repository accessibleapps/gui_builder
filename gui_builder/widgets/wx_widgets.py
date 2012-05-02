from .widget import Widget
import wx
from wx.lib import intctrl
from wx.lib import sized_controls as sc
import wx_autosizing

LABELED_CONTROLS = (wx.Button, wx.CheckBox, wx.RadioBox)  #Controls that have their own labels
UNFOCUSABLE_CONTROLS = (wx.StaticText, wx.Gauge, wx.Panel) #controls which cannot directly take focus

class WXWidget(Widget):
 style_prefix = ""
 default_event = None #the default event which triggers this widget's callback
 callback = None
 label = None

 def __init__(self, parent=None, label=None, callback=None, *args, **kwargs):
  super(WXWidget, self).__init__(*args, **kwargs)
  if callback is None:
   callback = self.callback
  self.callback = callback
  if label is None:
   label = self.label
  self.label = label
  self.parent = parent
  self.label_control = None

 def create_control(self):
  if self.control_type in LABELED_CONTROLS:
   super(WXWidget, self).create_control(parent=self.parent_control, label=self.label)
  else:
   if self.label:
    self.label_control = wx.StaticText(parent=self.parent_control, label=self.label)
   super(WXWidget, self).create_control(parent=self.parent_control)
  if self.default_event is not None and callable(self.callback):
   self.callback_wrapper = lambda *a, **k: self.callback(self.parent.field, *a, **k)
   self.control.Bind(self.default_event, self.callback_wrapper)
  
 def get_value(self):
  """Returns the most Pythonic representation of this control's current value."""
  return self.control.GetValue()

 def set_value(self, value):
  self.control.SetValue(value)

 @property
 def parent_control(self):
  parent = getattr(self.parent, "control", None)
  if isinstance(parent, (wx_autosizing.AutoSizedFrame, wx_autosizing.AutoSizedDialog)):
   parent = parent.pane
  return parent

 def translate_control_arguments(self, **kwargs):
  answer = dict(style=0)
  for k, v in kwargs.iteritems():
   if self.style_prefix:
    possible_style = "%s_%s" % (self.style_prefix, k.upper().replace("_", ""))
    if hasattr(wx, possible_style) and v is True:
     answer['style'] |= getattr(wx, possible_style)
     continue
   if hasattr(wx, k.upper()) and v is True: #It's unprefixed, I.E. wx.WANTS_CHARS
    answer['style'] |= getattr(wx, k.upper())
    continue
   answer[k] = v
  if answer["style"] == 0:
   del answer["style"]
  return answer
  

 def set_focus(self):
  self.control.SetFocus()

class ChoiceWidget(WXWidget):

 def get_items(self):
  return self.control.GetItems()

 def set_items(self, items):
  return self.control.SetItems(items)


class Text(WXWidget):
 control_type = wx.TextCtrl
 style_prefix = "TE"
 default_event = wx.EVT_CHAR
 
class IntText(Text):
 widget_type = intctrl.IntCtrl

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

class Slider(wx.Slider):
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
 style_prefix = "SC"
 default_event = wx.EVT_LIST_ITEM_ACTIVATED

class ToolBar(WXWidget):
 control_type = wx.ToolBar
 style_prefix = "TB"

class SpinBox(WXWidget):
 control_type = wx.SpinCtrl
 style_prefix = "SP"
 default_event = wx.EVT_SPINCTRL



class ButtonSizer(WXWidget):

 def translate_control_arguments(self, **kwargs):
  new_kwargs = dict(flags=0)
  for k, v in kwargs.iteritems():
   if hasattr(wx, k.upper()) and v is True:
    new_kwargs['flags'] |= getattr(wx, k.upper())
   else:
    new_kwargs[k] = v
  if new_kwargs['flags'] == 0:
   del new_kwargs['flags']
  return new_kwargs

 def create_control(self, **runtime_kwargs):
  kwargs = self.control_kwargs
  kwargs.update(runtime_kwargs)
  translated_kwargs = self.translate_control_arguments(**kwargs)
  self.control = self.parent.control.CreateStdDialogButtonSizer(**translated_kwargs)

 def render(self):
  self.parent.control.SetButtonSizer(self.control)


class BaseContainer(WXWidget):

 def create_control(self):
  super(BaseContainer, self).create_control()
  self.control.Show()

class SizedDialog(BaseContainer):
 control_type = sc.SizedDialog

class SizedFrame(BaseContainer):
 control_type = sc.SizedFrame

class SizedPanel(BaseContainer):
 control_type = sc.SizedPanel

class Frame(BaseContainer):
 control_type = wx.Frame

class Dialog(BaseContainer):
 control_type = wx.Dialog

class Panel(BaseContainer):
 control_type = wx.Panel

class Notebook(BaseContainer):
 control_type = wx.Notebook


class AutoSizedContainer(BaseContainer):

 def postrender(self):
  self.control.fit()

class AutoSizedPanel(BaseContainer): #doesn't require fitting
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
