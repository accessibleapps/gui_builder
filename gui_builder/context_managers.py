class Freezer(object):

 def __init__(self, to_freeze):
  self.to_freeze = to_freeze

 def __enter__(self):
  self.to_freeze.freeze()
  return self

 def __exit__(self):
  self.to_freeze.thaw()

class DisplayAndDestroy(object):

 def __init__(self, to_display):
  self.to_display = to_display

 def __enter__(self):
  return self.to_display.show_modal()

 def __exit(self):
  self.to_display.destroy()
