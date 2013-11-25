import wx
from gui_builder import fields, forms
app = wx.App()

class TestPanel(forms.Panel):

 def reveal_choice(self):
  self.choice.set_value(self.selector.get_value())

 selector = fields.RadioButtonGroup(choices=("Launch", "Land"), callback=reveal_choice)
 choice = fields.Text(label="Choice", default_value="Launch")

class MainFrame(forms.Frame):
 panel = TestPanel()

frame = MainFrame(title="Radio button test", parent=None)
frame.display()
app.MainLoop()
