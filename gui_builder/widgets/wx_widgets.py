from .widget import Widget
import wx
from wx.lib import sized_controls as sc
import wx_autosizing

LABELED_CONTROLS = (wx.Button, wx.CheckBox)  #Controls that have their own labels
UNFOCUSABLE_CONTROLS = (wx.StaticText, wx.Gauge, wx.Panel) #controls which cannot directly take focus

class WXWidget(Widget):
 STYLE_PREFIX = ""
 DEFAULT_EVENT = None #the default event which triggers this widget's callback
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
  if self.DEFAULT_EVENT is not None and callable(self.callback):
   self.control.Bind(self.DEFAULT_EVENT, self.callback)

 @property
 def parent_control(self):
  parent = getattr(self.parent, "control", None)
  if isinstance(parent, (wx_autosizing.AutoSizedFrame, wx_autosizing.AutoSizedDialog)):
   parent = parent.pane
  return parent

 def translate_control_arguments(self, **kwargs):
  answer = dict(style=0)
  for k, v in kwargs.iteritems():
   if self.STYLE_PREFIX:
    possible_style = "%s_%s" % (self.STYLE_PREFIX, k.upper().replace("_", ""))
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
  

class Text(WXWidget):
 control_type = wx.TextCtrl
 STYLE_PREFIX = "TE"
 
class CheckBox(WXWidget):
 control_type = wx.CheckBox
 DEFAULT_EVENT = wx.EVT_CHECKBOX

class ComboBox(WXWidget):
 control_type = wx.ComboBox
 STYLE_PREFIX = "CB"
 DEFAULT_EVENT = wx.EVT_COMBOBOX

class Button(WXWidget):
 control_type = wx.Button
 STYLE_PREFIX = "BTN"
 DEFAULT_EVENT = wx.EVT_BUTTON

class Slider(wx.Slider):
 STYLE_PREFIX = "SL"
 control_type = wx.Slider
 DEFAULT_EVENT = wx.EVT_SLIDER

class ScrollBar(WXWidget):
 control_type = wx.ScrollBar
 STYLE_PREFIX = "SB"
 DEFAULT_EVENT = wx.EVT_SCROLLBAR

class ListBox(WXWidget):
 control_type = wx.ListBox
 STYLE_PREFIX = "LB"
 DEFAULT_EVENT = wx.EVT_LISTBOX

class ListView(WXWidget):
 control_type = wx.ListView
 STYLE_PREFIX = "SC"
 DEFAULT_EVENT = wx.EVT_LIST_ITEM_ACTIVATED

class ToolBar(WXWidget):
 control_type = wx.ToolBar
 STYLE_PREFIX = "TB"

class SpinBox(WXWidget):
 control_type = wx.SpinCtrl
 STYLE_PREFIX = "SP"
 DEFAULT_EVENT = wx.EVT_SPINCTRL

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
