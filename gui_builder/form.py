
class BaseForm(object):
 widget_type = None
 widget_args = []
 widget_kwargs = {}

 def __init__(self, fields, *args, **kwargs):
  super(BaseForm, self).__init__()
  self._fields = {}
  if hasattr(fields, 'items'):
   fields = fields.items()
  for name, unbound_field in fields:
   self[name] = unbound_field
  self.widget = None
  self.widget_args.extend(args)
  self.widget_kwargs.update(kwargs)


 def __iter__(self):
  return self._fields.itervalues()

 def __getitem__(self, name):
  return self._fields[name]

 def __setitem__(self, name, value):
  self._fields[name] = value.bind(self, name)

 def __delitem__(self, name):
  del self._fields[name]

 def get_value(self):
  res = {}
  for field in self:
   res[field.bound_name] = field.get_value()
  return res

 def render(self):
  if self.widget_type is None and self._fields:
   raise RuntimeError("Must provide a widget type for this form before rendering.")
  self.widget = self.widget_type(*self.widget_args, **self.widget_kwargs)
  self.widget.create_control()
  self.widget.control.Show()
  for field in self:
   field.render()

class FormMeta(type):

 def __init__(cls, name, bases, attrs):
  type.__init__(cls, name, bases, attrs)
  cls._unbound_fields = None

 def __call__(cls, *args, **kwargs):
  if cls._unbound_fields is None:
   fields = []
   for name in dir(cls):
    if name.startswith('_'):
     continue
    unbound_field = getattr(cls, name)
    if hasattr(unbound_field, '_GUI_FIELD'):
     fields.append((name, unbound_field))
   fields.sort(key=lambda x: (x[1].creation_counter, x[0]))
   cls._unbound_fields = fields
  return type.__call__(cls, *args, **kwargs)

 def __setattr__(cls, name, value):
  if not name.startswith('_'):
   cls._unbound_fields = None
  type.__setattr__(cls, name, value)

 def __delattr__(self, name):
  if not name.startswith('_'):
   cls._unbound_fields = None
  type.__delattr__(cls, name)

class Form(BaseForm):
 __metaclass__ = FormMeta

 def __init__(self, *args, **kwargs):
  super(Form, self).__init__(self._unbound_fields, *args, **kwargs)
  for name, field in self._fields.items():
   setattr(self, name, field)

 def __iter__(self):
  """ Iterate form fields in their order of definition on the form. """
  for name, _ in self._unbound_fields:
   if name in self._fields:
    yield self._fields[name]
