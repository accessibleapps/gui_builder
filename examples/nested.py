from gui_builder import fields, forms
import wx


class CheckBoxes(forms.Panel):
    @fields.CheckBox(label="Frob!", default_value=True)
    def frob(self, event):
        # Code to be called when the checkbox is checked
        print("Frob checkbox is now:", event.IsChecked())

    tob = fields.CheckBox(
        label="Tob!", default_value=True
    )  # this checkbox doesn't do anything special when it's clicked.


class MainFrame(forms.Frame):
    text = fields.Text(label="Type something here!", min_size=(200, 100))
    options = CheckBoxes()


if __name__ == "__main__":
    app = wx.App()
    f = MainFrame(title="Testing nesting", top_level_window=True)
    f.display()
    app.MainLoop()
