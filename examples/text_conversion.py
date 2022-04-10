import codecs
import wx
from gui_builder import fields, forms


class MainPanel(forms.SizedPanel):
	def on_convert(self, event, *args, **kwargs):
		choice = self.choices.get_index()
		print("converting "+self.conversions[choice][0].lower())
		try:
			value = self.conversions[choice][1](self.text.get_value())
		except Exception as e:
			value = "error: "+str(e)
		if not self.conversion_result.is_shown():
			self.conversion_result.show()
		self.conversion_result.set_value(value)
		self.conversion_result.set_focus()

	conversions = [
		("To Hex", lambda value: codecs.encode(value.encode(), "hex").decode()),
		("From Hex", lambda value: codecs.decode(value.encode(), "hex").decode()),
		("To Base64", lambda value: codecs.encode(value.encode(), "base64").decode()),
		("From base64", lambda value: codecs.decode(value.encode(), "base64").decode()),
	]
	text = fields.Text(label="Enter some text", multiline=True)
	choices= fields.RadioButtonGroup(choices=[i[0] for i in conversions])
	convert = fields.Button(label="&Convert", callback=on_convert, default=True)
	conversion_result = fields.Text(label="Result", readonly=True, multiline=True, hidden=True)


class MainFrame(forms.Frame):
	panel = MainPanel()


if __name__ == "__main__":
	app = wx.App()
	frame = MainFrame(title="gui_builder demo", top_level_window=True)
	frame.display()
	app.MainLoop()
