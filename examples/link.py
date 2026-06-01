from logger_setup import setup_logging
import sys

sys.path.insert(0, "..")

setup_logging(console_level=10)
from gui_builder import fields, forms
import wx


class Frame(forms.Frame):
    link = fields.Link(label="Some link!", URL="http://q-continuum.net")


if __name__ == "__main__":
    app = wx.App()
    frame = Frame(title="test", parent=None)
    frame.display()
    app.MainLoop()
