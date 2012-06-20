
class Widget(object):
 """Base class which represents a common abstraction over UI elements."""
 control_type = None #the underlying control

 def __init__(self, field, **kwargs):
  self.field = field
  self.control_kwargs = kwargs
  self.control = None

 def translate_control_arguments(self, **kwargs):
  """This method should be implemented on subfields to translate arguments to the particular UI backend being supported."""
  return kwargs

 def render(self, **runtime_kwargs):
  control_args = self.translate_control_arguments(**self.control_kwargs)
  control_args.update(runtime_kwargs)
  try:
   self.control = self.control_type(**control_args)
  except Exception as e:
   raise RuntimeError("Unable to render control type %r with parent %r" % (self.control_type, self.parent), e)

 def set_focus(self):
  """Sets focus to this widget. Must be provided by subclasses."""
  raise NotImplementedError
