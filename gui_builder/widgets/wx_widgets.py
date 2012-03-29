from .widget import Widget
import wx

class WXWidget(Widget):
 STYLE_PREFIX = ""

 def translate_control_arguments(self, **kwargs):
  answer = dict(style=0)
  for k, v in kwargs.iteritems():
   if self.STYLE_PREFIX:
    possible_style = "%s_%s" % (self.STYLE_PREFIX, k.upper().replace("_", ""))
    if hasattr(wx, possible_style) and v is True:
     answer["style"] |= getattr(wx, possible_style)
     continue
   answer[k] = v
  return answer

class TextWidget(WXWidget):
 control_type = wx.TextCtrl
 STYLE_PREFIX = "TE"
