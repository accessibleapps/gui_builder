from .widget import Widget
import wx
from wx.lib import sized_controls as sc
LABELED_CONTROLS = (wx.Button, wx.CheckBox, wx.Panel) #Controls that have their own labels
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
   super(WXWidget, self).create_control(parent=self.parent.control, label=self.label)
  else:
   if self.label:
    self.label_control = wx.StaticText(parent=self.parent.control, label=self.label)
   parent = getattr(self.parent, "control", None)
   super(WXWidget, self).create_control(parent=parent)
  if self.DEFAULT_EVENT is not None and callable(self.callback):
   self.control.Bind(self.DEFAULT_EVENT, self.callback)

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

class BaseContainer(WXWidget):

 def create_control(self):
  super(BaseContainer, self).create_control()
  self.control.Show()


class SizedDialog(BaseContainer):
 control_type = sc.SizedDialog

class SizedFrame(BaseContainer):
 control_type = sc.SizedFrame

class Frame(BaseContainer):
 control_type = wx.Frame

class Dialog(BaseContainer):
 control_type = wx.Dialog
