Quick Start Guide
=================

Installation
------------

Install GUI Builder using pip:

.. code-block:: bash

   pip install gui_builder

Requirements
~~~~~~~~~~~~

- Python 3.8+
- wxPython 4.1.0+

Your First GUI
--------------

Here's a simple example to get you started:

.. code-block:: python

   import wx
   from gui_builder import fields, forms

   class HelloWorldFrame(forms.Frame):
       # Define UI elements as class attributes
       message = fields.Text(label="Enter a message:", value="Hello, World!")
       show_button = fields.Button(label="Show Message", default=True)
       
       # Event handler using decorator
       @show_button.add_callback
       def on_show_message(self):
           wx.MessageBox(self.message.get_value(), "Message", wx.OK | wx.ICON_INFORMATION)

   if __name__ == "__main__":
       app = wx.App()
       frame = HelloWorldFrame(title="My First GUI Builder App", top_level_window=True)
       frame.display()
       app.MainLoop()

Understanding the Framework
---------------------------

Form Classes
~~~~~~~~~~~~

GUI Builder forms inherit from the base classes in the ``forms`` module:

- ``forms.Frame``: Top-level window
- ``forms.Dialog``: Modal dialog
- ``forms.Panel``: Container panel
- ``forms.SizedPanel``: Panel with automatic sizing

Field Types
~~~~~~~~~~~

The ``fields`` module provides various UI controls:

- ``fields.Text``: Single or multi-line text input
- ``fields.Button``: Clickable button
- ``fields.CheckBox``: Boolean checkbox
- ``fields.RadioButtonGroup``: Radio button group
- ``fields.Choice``: Dropdown selection
- ``fields.ListBox``: List selection

Event Handling
~~~~~~~~~~~~~~

There are two ways to handle events:

1. **Decorator approach** (recommended):

.. code-block:: python

   @my_button.add_callback
   def on_button_click(self):
       print("Button clicked!")

2. **Direct assignment**:

.. code-block:: python

   my_button = fields.Button(label="Click Me", callback=self.on_button_click)

Next Steps
----------

- Check out the :doc:`examples` section for more complex examples
- Browse the :doc:`api` reference for detailed documentation
- Look at the examples folder in the source code for real-world usage