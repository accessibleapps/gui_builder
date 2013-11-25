from logger_setup import setup_logging
setup_logging(console_level=10)
from gui_builder import fields, forms
import wx
app = wx.App()

class Frame(forms.Frame):
 link = fields.Link(label="Some link!", URL="http://q-continuum.net")

frame = Frame(title="test", parent=None)
frame.display()
app.MainLoop()
