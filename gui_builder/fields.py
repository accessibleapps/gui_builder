class GUIField(object):
 creation_counter = 0
 control = None
 field_type = None


 def __init__(self, control_type=None, label=None, *args, **kwargs):
  if control_type is None:
   control_type = self.control_type
  if control_type is None:
   raise ValueError("Must provide a valid control type")
  GUIField.creation_counter += 1
  self.creation_counter = GUIField.creation_counter
  super(GUIField, self).__init__()
  self.control_type = control_type
  self.control_label = label
  self.control_args = args
  self.control_kwargs = kwargs
  self.label = None
  self.control = None


 def __call__(self, parent=None, **kwargs):
  