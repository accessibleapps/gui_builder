import wx
from wx.lib import sized_controls as sc

LABEL_TYPES = (wx.StaticText,)

class AutoFittingMixin(object):

 def fit(self):
  self.SetInitialSize()
  self.SetMinSize(self.GetSize())
  self.Center()

class AutoSizedPanel(AutoFittingMixin, sc.SizedPanel):
 
 def __init__(self, horizontal=False, *args, **kwargs):
  super(AutoSizedPanel, self).__init__(*args, **kwargs)
  self.row = 0
  self.column = 0
  self.sizerType = "form"
  self._SetNewSizer(wx.GridBagSizer(4, 4))
  if horizontal:
   self.SetSizerType("horizontal")

 def AddChild(self, child):
  wx.PyPanel.AddChild(self, child)
  span = (1, 1)
  position = (self.row, self.column)
  if isinstance(child, LABEL_TYPES):
   self.column = 1
  else:
   if self.column == 0:
    span = (1, 2)
   else:
    self.column = 0
   self.row += 1
  sizer = self.GetSizer()
  if isinstance(sizer, wx.GridBagSizer):
   sizer.Add(child, position, span=span)
  else:
   sizer.Add(child)


class AutoSizedMixin(AutoFittingMixin):
 
 def __init__(self, parent=None, size=None, *args, **kwargs):
  if hasattr(parent, 'Raise'):
   parent.Raise()
  self.Raise()
  self.SetExtraStyle(wx.WS_EX_VALIDATE_RECURSIVELY)
  self.borderLen = 12
  self.mainPanel = AutoSizedPanel(parent=self, id=wx.ID_ANY)
  root_sizer = wx.BoxSizer(wx.VERTICAL)
  root_sizer.Add(self.mainPanel, 1, wx.EXPAND | wx.ALL)
  self.SetSizer(root_sizer)
  self.SetAutoLayout(True)
  self.pane = self.GetContentsPane()

class AutoSizedDialog(AutoSizedMixin, sc.SizedDialog):

 def __init__(self, parent=None, id=wx.ID_ANY, *args, **kwargs):
  wx.Dialog.__init__(self, parent=parent, id=id, *args, **kwargs)
  AutoSizedMixin.__init__(self, *args, **kwargs)
  self.SetLayoutAdaptationMode(wx.DIALOG_ADAPTATION_MODE_ENABLED)
  self.EnableLayoutAdaptation(True)

class AutoSizedFrame(AutoSizedMixin, sc.SizedFrame):

 def __init__(self, parent=None, id=wx.ID_ANY, *args, **kwargs):
  wx.Frame.__init__(self, parent=parent, id=id, *args, **kwargs)
  AutoSizedMixin.__init__(self, *args, **kwargs)

