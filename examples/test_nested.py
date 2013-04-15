from gui_builder import fields, forms
import wx
app = wx.App()

class CheckBoxes(forms.Panel):

 def do_something_fun(self):
  #put some code here to be called when the checkbox is checked
  pass

 frob = fields.CheckBox(label="Frob!", default_value=True, callback=do_something_fun)
 tob = fields.CheckBox(label="Tob!", default_value=True) #this checkbox doesn't do anything special when it's clicked. 

class MainFrame(forms.Frame):
 text = fields.Text(label="Type something here!", min_size=(200, 100))
 options = CheckBoxes()

f = MainFrame(title="Testing nesting", top_level_window=True)
f.display()
app.MainLoop()
