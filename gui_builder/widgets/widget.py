
class Widget(object):
 """Base class which represents a common abstraction over UI elements."""
 control_type = None #the underlying control

 def __init__(self, **kwargs):
  self.control_kwargs = kwargs
  self.control = None

 def translate_control_arguments(self, **kwargs):
  """This method should be implemented on subfields to translate arguments to the particular UI backend being supported."""
  return kwargs

 def create_control(self):
  control_args = self.translate_control_arguments(**self.control_kwargs)
  self.control = self.control_type(**control_args)
