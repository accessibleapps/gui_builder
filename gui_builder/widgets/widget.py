from logging import getLogger
logger = getLogger('gui_builder.widgets.widget')
from collections import defaultdict
import weakref

class Widget(object):
 """Base class which represents a common abstraction over UI elements."""
 control_type = None #the underlying control


 def __init__(self, field, callbacks=None, **kwargs):
  self.field = weakref.proxy(field)
  self.control_kwargs = kwargs
  self.control = None
  self.callbacks = defaultdict(list)
  if callbacks is None:
   callbacks = {}
  self.unregistered_callbacks = callbacks


 def register_unregistered_callbacks(self):
  for key, value in dict(self.unregistered_callbacks).iteritems():
   self.register_callback(key, value)
   del self.unregistered_callbacks[key]


 def translate_control_arguments(self, **kwargs):
  """This method should be implemented on subfields to translate arguments to the particular UI backend being supported."""
  return kwargs

 def create_control(self, **kwargs):
  if self.control_type is None:
   raise RuntimeError("No control type provided")
  try:
   self.control = self.control_type(**kwargs)
  except Exception as e:
   logger.exception("Error rendering widget %r" % self)
   raise RuntimeError("Unable to render control type %r with field %r" % (self.control_type, self.field), e)

 def render(self, **runtime_kwargs):
  control_args = self.translate_control_arguments(**self.control_kwargs)
  control_args.update(self.translate_control_arguments(**runtime_kwargs))
  self.create_control(**control_args)
  self.register_unregistered_callbacks()
  #super(Widget, self).render()

 def register_callback(self, callback_type=None, callback=None):
  self.callbacks[callback_type].append(callback)

 def unregister_callback(self, callback_type, callback):
  self.callbacks[callback_type].remove(callback)


 def set_focus(self):
  """Sets focus to this widget. Must be provided by subclasses."""
  raise NotImplementedError

 def can_be_focused(self):
  raise NotImplementedError

 def display(self):
  raise NotImplementedError
